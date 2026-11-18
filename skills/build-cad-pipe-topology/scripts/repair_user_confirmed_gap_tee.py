"""Apply an explicitly confirmed branch across a drafting gap to a native main.

This is a graph-bound repair, never a detector or a proximity-based rule. A
source-confirmed branch may cross a different service without connecting to it.
"""
import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
from repair_confirmed_circle_junctions import pos, slice_path, segments_for_interval, assign_sources, TOL
from edge_endpoint_semantics import reconcile
from source_readability import read_source


def apply(doc, graph, rows, policy, source_sha256, graph_sha256):
    if (policy.get('source_sha256') != source_sha256 or
        policy.get('graph_sha256') != graph_sha256 or
        graph.get('metadata', {}).get('source_sha256') != source_sha256):
        raise ValueError('source or graph identity mismatch')
    if policy.get('confirmed_by') != 'user' or not policy.get('evidence_sha256'):
        raise ValueError('explicit user evidence required')
    g = copy.deepcopy(graph)
    nodes = {n['node_id']: n for n in g['nodes']}
    edges = {e['edge_id']: e for e in g['edges']}
    if len(nodes) != len(g['nodes']) or len(edges) != len(g['edges']):
        raise ValueError('duplicate ids')
    main = edges[policy['main_edge']]
    branch = edges[policy['branch_edge']]
    terminal = nodes[policy['terminal']]
    system = policy['system']
    if main['system'] != system or branch['system'] != system or terminal.get('system') != system:
        raise ValueError('systems do not agree')
    if terminal.get('subtype') != 'unresolved_source_terminal':
        raise ValueError('terminal is not unresolved')
    if sum(terminal['node_id'] in (e.get('start_node_id'), e.get('end_node_id')) for e in edges.values()) != 1:
        raise ValueError('terminal is not unique')
    if policy['main_handle'] not in main['source_handles'] or policy['branch_handle'] not in branch['source_handles']:
        raise ValueError('source handle mismatch')
    for h in (policy['main_handle'], policy['branch_handle']):
        ent = doc.entitydb.get(h)
        if ent is None or ent.dxftype() != 'LINE' or ent.dxf.layer != policy['source_layer']:
            raise ValueError('native line or source layer mismatch')
    p = [terminal['x'], terminal['y']]
    target = policy['junction_xy']
    line = doc.entitydb.get(policy['branch_handle'])
    if min(math.dist(p, [v.x, v.y]) for v in (line.dxf.start, line.dxf.end)) > TOL:
        raise ValueError('terminal is not a native branch endpoint')
    dx, dy = line.dxf.end.x-line.dxf.start.x, line.dxf.end.y-line.dxf.start.y
    if abs((target[0]-p[0])*dy-(target[1]-p[1])*dx) > TOL*math.hypot(dx, dy):
        raise ValueError('confirmed extension is not collinear')
    ends = [[v.x, v.y] for v in (line.dxf.start, line.dxf.end)]
    other = max(ends, key=lambda v: math.dist(v, p))
    if ((target[0]-p[0])*(p[0]-other[0]) + (target[1]-p[1])*(p[1]-other[1])) <= TOL:
        raise ValueError('extension does not continue away from native branch')
    source_main = doc.entitydb.get(policy['main_handle'])
    native_main = [[source_main.dxf.start.x, source_main.dxf.start.y], [source_main.dxf.end.x, source_main.dxf.end.y]]
    pos(native_main, target)
    path = main['path']
    total = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
    cut = pos(path, target)
    if cut <= TOL or cut >= total-TOL:
        raise ValueError('junction must be inside main')
    if any(k.startswith('diameter_') or k in ('pipe_diameter', 'source_segment_dimensions', 'physical_length', 'physical_length_mm') for k in main):
        raise ValueError('main attributes require explicit remapping')
    if main.get('equipment_names') or main.get('equipment_counts') or any(r.get('edge_id') == main['edge_id'] for r in rows):
        raise ValueError('main components require explicit remapping')
    if main.get('source_flexible_joints'):
        raise ValueError('main flexible joints require explicit remapping')
    tee, child_id = policy['tee_id'], policy['child_edge_id']
    if tee in nodes or child_id in edges:
        raise ValueError('new id collision')
    children = []
    for i, (lo, hi) in enumerate(((0, cut), (cut, total))):
        child = copy.deepcopy(main)
        child['edge_id'] = main['edge_id'] if i == 0 else child_id
        child['start_node_id'] = main['start_node_id'] if i == 0 else tee
        child['end_node_id'] = tee if i == 0 else main['end_node_id']
        child.pop('end_port_id' if i == 0 else 'start_port_id', None)
        child['path'] = slice_path(path, lo, hi)
        child['path_points'] = copy.deepcopy(child['path'])
        child['attribute_paths'] = segments_for_interval(path, main['attribute_paths'], lo, hi)
        if not child['attribute_paths']:
            raise ValueError('split has no drawn geometry')
        child['source_handles'] = assign_sources(doc, main['source_handles'], child['attribute_paths'])
        child['path_length'] = sum(math.dist(a, b) for piece in child['attribute_paths'] for a, b in zip(piece, piece[1:]))
        child['split_source_edge'] = {'edge_id': main['edge_id'], 'source_graph_sha256': graph_sha256, 'interval_native_units': [lo, hi]}
        children.append(child)
    if set(h for c in children for h in c['source_handles']) != set(main['source_handles']):
        raise ValueError('source handles lost')
    if abs(sum(c['path_length'] for c in children)-main['path_length']) > TOL:
        raise ValueError('source path length changed')
    side = 'start' if branch['start_node_id'] == terminal['node_id'] else 'end' if branch['end_node_id'] == terminal['node_id'] else None
    if not side or math.dist(branch['path'][0 if side == 'start' else -1], p) > TOL:
        raise ValueError('branch endpoint mismatch')
    branch[side+'_node_id'] = tee
    branch.pop(side+'_port_id', None)
    branch['path'] = [target]+branch['path'] if side == 'start' else branch['path']+[target]
    branch['path_points'] = copy.deepcopy(branch['path'])
    branch['path_length_complete'] = False
    branch['path_length_scope'] = 'native_drawn_geometry_only_confirmed_extension_length_unknown'
    branch['confirmed_gap_extension'] = {'from_xy': p, 'to_xy': target, 'graphical_distance_native_units': math.dist(p, target), 'physical_length': 'unknown', 'user_evidence_sha256': policy['evidence_sha256'], 'crossing_connectivity': 'other_system_not_connected'}
    nodes.pop(terminal['node_id'])
    nodes[tee] = {'node_id': tee, 'node_type': 'tee', 'subtype': 'physical_tee', 'floor': terminal['floor'], 'system': system, 'x': target[0], 'y': target[1], 'label': tee, 'source_handles': [policy['main_handle'], policy['branch_handle']], 'user_confirmed_gap_tee': True}
    edges[main['edge_id']] = children[0]
    edges[child_id] = children[1]
    g['nodes'], g['edges'] = list(nodes.values()), list(edges.values())
    g['virtual_equipment_ports'] = [p for p in g.get('virtual_equipment_ports', []) if p.get('virtual_equipment_id') != terminal['node_id']]
    g, endpoint_changes = reconcile(g)
    incident = [e for e in g['edges'] if tee in (e['start_node_id'], e['end_node_id'])]
    if len(incident) != 3 or any(e['system'] != system for e in incident):
        raise ValueError('tee invariant failed')
    g['userConfirmedGapTeeRepair'] = {'source_sha256': source_sha256, 'input_graph_sha256': graph_sha256, 'user_evidence_sha256': policy['evidence_sha256'], 'retired_terminal': terminal['node_id'], 'tee': tee, 'main_children': [main['edge_id'], child_id], 'branch': branch['edge_id'], 'crossed_system_connected': False, 'physical_length': 'unknown'}
    g['preHilComparison'] = {'status': 'pending', 'previous_comparison': copy.deepcopy(graph.get('preHilComparison')), 'reason': 'user-confirmed gap tee requires fresh source comparison'}
    g['metadata'].update(hil_ready=False, graph_complete=False, review_status='unreviewed_after_semantic_change')
    return g, {'endpoint_changes': endpoint_changes, 'repair': g['userConfirmedGapTeeRepair']}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reject_revoked_policy(policy_hash, registry):
    data = json.loads(Path(registry).read_text(encoding='utf8'))
    if data.get('schema_version') != 1 or not isinstance(data.get('revoked'), dict):
        raise ValueError('invalid revoked policy registry')
    if policy_hash in data['revoked']:
        raise ValueError('revoked policy: '+data['revoked'][policy_hash])


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'graph', 'devices', 'policy', 'evidence', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    a = parser.parse_args()
    if a.output.exists():
        raise ValueError('output exists')
    reject_revoked_policy(sha(a.policy), Path(__file__).resolve().parent.parent/'assets'/'revoked-gap-tee-policies.json')
    policy = json.loads(a.policy.read_text(encoding='utf8'))
    if policy.get('evidence_sha256') != sha(a.evidence) or policy.get('devices_sha256') != sha(a.devices):
        raise ValueError('evidence or component identity mismatch')
    doc, proof = read_source(a.source)
    graph = json.loads(a.graph.read_text(encoding='utf8'))
    with a.devices.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    result, audit = apply(doc, graph, rows, policy, proof['source_sha256'], sha(a.graph))
    a.output.mkdir(parents=True)
    target = a.output/'graph_with_confirmed_gap_tee.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    with (a.output/'assigned_edge_device_instances.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    audit.update(policy_sha256=sha(a.policy), script_sha256=sha(__file__), input_devices_sha256=sha(a.devices), output_graph_sha256=sha(target))
    (a.output/'confirmed-gap-tee-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'output_graph_sha256': sha(target), 'hil_ready': False}))


if __name__ == '__main__':
    main()
