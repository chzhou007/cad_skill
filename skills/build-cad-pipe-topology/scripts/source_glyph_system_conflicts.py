"""Attach source-verified opposite-system symbol conflicts without changing topology."""
import copy
import math
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from cad_ceiling_native_rules import match_out_of_plane_symbol
from source_readability import read_source

LAYERS = {'supply': '空调冷冻水供水', 'return': '空调冷冻水回水'}
GLYPH_LAYER = '空调立管、水平支管'


def attach(graph, doc, inventory, source_hash, *, tolerance=.05):
    if not source_hash or inventory.get('source_sha256') != source_hash or graph.get('metadata', {}).get('source_sha256') != source_hash:
        raise ValueError('source identity mismatch')
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('invalid tolerance')
    out = copy.deepcopy(graph)
    nodes = out['nodes']; edges = out['edges']; ids = [n['node_id'] for n in nodes]
    if len(ids) != len(set(ids)) or len({e['edge_id'] for e in edges}) != len(edges):
        raise ValueError('duplicate graph IDs')
    records = []
    for item in inventory['glyphs']:
        if item.get('source_system_conflict') != 'exact_opposite_system_endpoint':
            continue
        opposite = [p for p in item.get('near_opposite_system_source_endpoints', [])
                    if p['distance_to_circle_center'] <= tolerance]
        if len(opposite) != 1:
            raise ValueError('opposite source endpoint not unique')
        p = opposite[0]; circle = doc.entitydb.get(item['circle_handle']); pipe = doc.entitydb.get(p['source_handle'])
        if not circle or circle.dxftype() != 'CIRCLE' or circle.dxf.layer != LAYERS.get(item['system']):
            raise ValueError('native circle layer mismatch')
        if not pipe or pipe.dxftype() != 'LINE' or pipe.dxf.layer != LAYERS.get(p['system']) or p['system'] == item['system']:
            raise ValueError('native pipe layer mismatch')
        center = [circle.dxf.center.x, circle.dxf.center.y]
        if math.dist(center, item['center']) > tolerance or abs(circle.dxf.radius-item['radius']) > tolerance:
            raise ValueError('native circle geometry mismatch')
        points = [[pipe.dxf.start.x, pipe.dxf.start.y], [pipe.dxf.end.x, pipe.dxf.end.y]]
        if min(math.dist(center, point) for point in points) > tolerance:
            raise ValueError('native pipe is not at circle center')
        actual = [line.dxf.handle for line in doc.modelspace().query('LINE')
                  if line.dxf.layer in LAYERS.values()
                  and min(math.hypot(center[0]-v.x, center[1]-v.y)
                          for v in (line.dxf.start, line.dxf.end)) <= tolerance]
        if actual != [p['source_handle']]:
            raise ValueError('native endpoint ownership is ambiguous or changed')
        glyph = []
        for handle in item['glyph_handles']:
            entity = doc.entitydb.get(handle)
            if not entity or entity.dxftype() != 'LINE' or entity.dxf.layer != GLYPH_LAYER:
                raise ValueError('native glyph line missing')
            glyph.append({'handle': handle, 'a': [entity.dxf.start.x, entity.dxf.start.y],
                          'b': [entity.dxf.end.x, entity.dxf.end.y]})
        match = match_out_of_plane_symbol({'center': center, 'radius': circle.dxf.radius}, glyph, tolerance)
        if match is None or {x['handle'] for x in glyph} != {x['handle'] for group in match for x in group}:
            raise ValueError('native glyph is incomplete or ambiguous')
        candidates = [n for n in nodes if n.get('subtype') == 'unresolved_source_terminal'
                      and n.get('system') == p['system'] and p['source_handle'] in n.get('source_handles', [])
                      and math.dist([n['x'], n['y']], center) <= tolerance]
        if len(candidates) != 1:
            raise ValueError('source endpoint node missing or ambiguous')
        node = candidates[0]
        incident = [e for e in edges if node['node_id'] in (e.get('start_node_id'), e.get('end_node_id'))]
        if len(incident) != 1 or incident[0].get('system') != p['system'] or p['source_handle'] not in incident[0].get('source_handles', []):
            raise ValueError('source endpoint edge missing or ambiguous')
        if node.get('source_glyph_system_conflict') or node.get('resolution_state'):
            raise ValueError('existing node semantic evidence must be reconciled first')
        record = {'source_sha256': source_hash, 'circle_handle': item['circle_handle'],
                  'circle_source_system': item['system'], 'circle_source_layer': circle.dxf.layer,
                  'glyph_handles': item['glyph_handles'], 'pipe_handle': p['source_handle'],
                  'pipe_source_system': p['system'], 'pipe_source_layer': pipe.dxf.layer,
                  'edge_id': incident[0]['edge_id'], 'status': 'source_system_conflict_unresolved',
                  'remote_connection': 'unknown'}
        node['source_glyph_system_conflict'] = record
        node['resolution_state'] = 'source_glyph_system_conflict_pending'
        node['review_required'] = True
        records.append({'node_id': node['node_id'], **record})
    out.setdefault('metadata', {}).update(hil_ready=False, graph_complete=False,
                                          stage_status='source_glyph_system_conflicts_pending')
    return out, records


def main():
    parser = argparse.ArgumentParser()
    for key in ('source', 'graph', 'inventory', 'devices', 'output'):
        parser.add_argument('--'+key, required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('refusing to overwrite output')
    doc, proof = read_source(args.source)
    graph = json.loads(args.graph.read_text(encoding='utf8'))
    inventory = json.loads(args.inventory.read_text(encoding='utf8'))
    result, records = attach(graph, doc, inventory, proof['source_sha256'])
    args.output.mkdir(parents=True)
    output = args.output/'graph_with_source_glyph_conflicts.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    shutil.copyfile(args.devices, args.output/'assigned_edge_device_instances.csv')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    audit = {'source_sha256': proof['source_sha256'], 'input_graph_sha256': sha(args.graph),
             'source_inventory_sha256': sha(args.inventory), 'devices_sha256': sha(args.devices),
             'output_graph_sha256': sha(output), 'conflicts': records,
             'scope': 'source evidence only; no connectivity, ports or systems changed',
             'human_review': 'unreviewed', 'hil_ready': False}
    (args.output/'source-glyph-conflicts-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'conflicts': len(records), 'output_graph_sha256': sha(output)}))


if __name__ == '__main__': main()
