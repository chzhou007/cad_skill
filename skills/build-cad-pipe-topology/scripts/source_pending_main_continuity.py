"""Record proven continuous native mains through pending junctions.

The third branch and circle semantics stay pending; no connectivity is added.
"""
import argparse
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path
from source_readability import read_source

LAYERS = {'supply': '空调冷冻水供水', 'return': '空调冷冻水回水'}


def _distance(a, b): return math.dist(a, b)


def _point_on_main(point, a, b, tol):
    dx, dy = b[0]-a[0], b[1]-a[1]; length = math.hypot(dx, dy)
    if length <= tol: return None
    t = ((point[0]-a[0])*dx+(point[1]-a[1])*dy)/(length*length)
    projection = [a[0]+t*dx, a[1]+t*dy]
    return t if 0 < t < 1 and _distance(point, projection) <= tol else None


def attach(graph, doc, pending, source_hash, *, tol=.05):
    if not source_hash or graph.get('metadata', {}).get('source_sha256') != source_hash:
        raise ValueError('source identity mismatch')
    if not math.isfinite(tol) or tol <= 0: raise ValueError('invalid tolerance')
    result = copy.deepcopy(graph); nodes = result['nodes']; edges = result['edges']
    if len({n['node_id'] for n in nodes}) != len(nodes) or len({e['edge_id'] for e in edges}) != len(edges):
        raise ValueError('duplicate graph IDs')
    records = []
    for item in pending:
        if item.get('reason') != 'riser_or_circle_symbol_contact' or item.get('degree') != 3:
            continue
        point = [item['x'], item['y']]; system = item['system']
        if not item.get('circle_handles'):
            raise ValueError('pending circle evidence is missing')
        for circle_id in item['circle_handles']:
            circle = doc.entitydb.get(circle_id)
            if not circle or circle.dxftype() != 'CIRCLE' or circle.dxf.layer != LAYERS.get(system):
                raise ValueError('pending circle source mismatch')
            radius = float(circle.dxf.radius)
            if not math.isfinite(radius) or radius <= 0 or math.hypot(circle.dxf.center.x-point[0], circle.dxf.center.y-point[1]) > radius + tol:
                raise ValueError('pending contact lies outside source circle')
        found = [n for n in nodes if n.get('subtype') == 'pending_source_junction' and n.get('system') == system
                 and _distance([n['x'], n['y']], point) <= tol]
        if len(found) != 1: raise ValueError('pending junction not uniquely present')
        node = found[0]; incident = [e for e in edges if node['node_id'] in (e.get('start_node_id'), e.get('end_node_id'))]
        if len(incident) != 3 or any(e.get('system') != system for e in incident): raise ValueError('unexpected incident edges')
        main_candidates = [h for h in set(node.get('source_handles', []))
                           if sum(h in e.get('source_handles', []) for e in incident) == 2]
        if len(main_candidates) != 1: raise ValueError('continuous main source is ambiguous')
        handle = main_candidates[0]; main = doc.entitydb.get(handle)
        if not main or main.dxftype() != 'LINE' or main.dxf.layer != LAYERS.get(system): raise ValueError('native main layer mismatch')
        a = [main.dxf.start.x, main.dxf.start.y]; b = [main.dxf.end.x, main.dxf.end.y]
        if _point_on_main(point, a, b, tol) is None: raise ValueError('node is not in native main interior')
        main_edges = [e for e in incident if handle in e.get('source_handles', [])]
        direction = []
        for edge in main_edges:
            neighbors = []
            for path in edge.get('attribute_paths', []):
                for x, y in zip(path, path[1:]):
                    if _distance(x, point) <= tol: neighbors.append(y)
                    if _distance(y, point) <= tol: neighbors.append(x)
            if len(neighbors) != 1: raise ValueError('main edge path at node is ambiguous')
            q = neighbors[0]
            if _point_on_main(q, a, b, tol) is None and min(_distance(q, a), _distance(q, b)) > tol:
                raise ValueError('main edge leaves native source line')
            direction.append((q[0]-point[0])*(b[0]-a[0])+(q[1]-point[1])*(b[1]-a[1]))
        if direction[0]*direction[1] >= 0: raise ValueError('main portions are not on opposite sides')
        branch = next(e for e in incident if e not in main_edges)
        branch_hits = []
        for h in branch.get('source_handles', []):
            entity = doc.entitydb.get(h)
            if entity and entity.dxftype() == 'LINE' and entity.dxf.layer == LAYERS.get(system):
                if min(math.hypot(v.x-point[0], v.y-point[1]) for v in (entity.dxf.start, entity.dxf.end)) <= tol:
                    branch_hits.append(h)
        if len(branch_hits) != 1: raise ValueError('native branch endpoint is not unique')
        branch_line = doc.entitydb[branch_hits[0]]
        branch_a = [branch_line.dxf.start.x, branch_line.dxf.start.y]
        branch_b = [branch_line.dxf.end.x, branch_line.dxf.end.y]
        neighbors = []
        for path in branch.get('attribute_paths', []):
            for x, y in zip(path, path[1:]):
                if _distance(x, point) <= tol: neighbors.append(y)
                if _distance(y, point) <= tol: neighbors.append(x)
        if len(neighbors) != 1:
            raise ValueError('branch edge path at node is ambiguous')
        q = neighbors[0]
        if _point_on_main(q, branch_a, branch_b, tol) is None and min(_distance(q, branch_a), _distance(q, branch_b)) > tol:
            raise ValueError('branch edge leaves native source line')
        if _distance(q, point) <= tol:
            raise ValueError('branch edge has no source direction')
        if node.get('source_main_continuation') or node.get('resolution_state'):
            raise ValueError('existing node evidence requires reconciliation')
        record = {'source_sha256': source_hash, 'main_source_handle': handle,
                  'main_edge_ids': sorted(e['edge_id'] for e in main_edges), 'branch_edge_id': branch['edge_id'],
                  'branch_source_handle': branch_hits[0], 'circle_handles': item.get('circle_handles', []),
                  'source_point': point, 'branch_connectivity': 'pending', 'circle_semantics': 'pending'}
        node['source_main_continuation'] = record
        node['resolution_state'] = 'source_main_continuation_branch_pending'
        node['review_required'] = True
        records.append({'node_id': node['node_id'], **record})
    result.setdefault('metadata', {}).update(hil_ready=False, graph_complete=False,
                                              stage_status='source_main_continuity_branch_pending')
    return result, records


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'graph', 'pending', 'devices', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('refusing to overwrite output')
    doc, proof = read_source(args.source)
    graph = json.loads(args.graph.read_text(encoding='utf8'))
    pending = json.loads(args.pending.read_text(encoding='utf8'))
    result, records = attach(graph, doc, pending, proof['source_sha256'])
    args.output.mkdir(parents=True)
    out = args.output/'graph_with_main_continuity.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    shutil.copyfile(args.devices, args.output/'assigned_edge_device_instances.csv')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    audit = {'source_sha256': proof['source_sha256'], 'input_graph_sha256': sha(args.graph),
             'pending_source_sha256': sha(args.pending), 'devices_sha256': sha(args.devices),
             'output_graph_sha256': sha(out), 'records': records,
             'scope': 'native main continuation only; pending branch is not accepted', 'hil_ready': False}
    (args.output/'main-continuity-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'main_continuity_records': len(records), 'graph_sha256': sha(out)}))


if __name__ == '__main__': main()
