"""Apply individually confirmed, source-pinned same-service circle junctions.

This stage does not reconcile other graph references or certify a full rebuild.
"""
import copy
import math
import re
from collections import defaultdict


def apply(graph, doc, plan, policy, *, graph_sha256, source_sha256):
    if (graph.get('metadata', {}).get('source_sha256') != source_sha256 or
        plan.get('source_sha256') != source_sha256 or policy.get('source_sha256') != source_sha256 or
        plan.get('graph_sha256') != graph_sha256 or policy.get('graph_sha256') != graph_sha256):
        raise ValueError('Source or input graph hash mismatch')
    if not policy.get('user_confirmation') or not policy.get('confirmation_evidence'):
        raise ValueError('Explicit user confirmation evidence required')
    groups = plan.get('groups', [])
    handles = [g['circle_handle'] for g in groups]
    if not handles or len(handles) != len(set(handles)) or sorted(handles) != sorted(policy.get('confirmed_circle_handles', [])):
        raise ValueError('Confirmation scope does not match unique source circles')
    tolerance = policy.get('contact_tolerance', .1)
    if not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or not 0 < tolerance <= 1:
        raise ValueError('Invalid calibrated contact tolerance')
    out = copy.deepcopy(graph)
    nodes = {n['node_id']: n for n in out['nodes']}
    edges = {e['edge_id']: e for e in out['edges']}
    if len(nodes) != len(out['nodes']) or len(edges) != len(out['edges']):
        raise ValueError('Duplicate graph IDs')
    incident = defaultdict(list)
    for edge in edges.values():
        for side in ('start', 'end'):
            nid = edge[side + '_node_id']
            if nid not in nodes:
                raise ValueError('Missing incident node')
            incident[nid].append(edge['edge_id'])
    existing = [int(n[1:]) for n in nodes if re.fullmatch(r'T\d+', n)]
    next_id = max(existing, default=0) + 1
    retired, rewires, new_nodes, used_ends = {}, [], [], set()
    for group in sorted(groups, key=lambda item: item['circle_handle']):
        h = group['circle_handle']
        circle = doc.entitydb.get(h)
        center = group['center']
        radius = group['radius']
        if (not isinstance(center, (list, tuple)) or len(center) != 2 or
            not all(isinstance(v, (int, float)) and math.isfinite(v) for v in center) or
            not isinstance(radius, (int, float)) or not math.isfinite(radius)):
            raise ValueError('Invalid circle geometry: ' + h)
        if (circle is None or circle.dxftype() != 'CIRCLE' or
            tuple(circle.dxf.extrusion) != (0., 0., 1.) or
            circle.dxf.layer != group['source_layer'] or
            math.dist((circle.dxf.center.x, circle.dxf.center.y), center) > tolerance or
            abs(circle.dxf.radius - radius) > tolerance or radius <= tolerance):
            raise ValueError('Native circle witness mismatch: ' + h)
        ids = group['old_boundary_nodes']
        steps = group['proposed_edge_endpoint_rebindings']
        if len(ids) != 3 or len(set(ids)) != 3 or len(steps) != 3 or {s['existing_node_id'] for s in steps} != set(ids):
            raise ValueError('Three unique selected endpoints required: ' + h)
        old_nodes = [nodes[nid] for nid in ids]
        system = group['proposed_system']
        if system not in ('supply', 'return') or any(n.get('system') != system or n.get('subtype') != 'unresolved_source_terminal' or len(incident[n['node_id']]) != 1 for n in old_nodes):
            raise ValueError('Changed endpoint system or degree: ' + h)
        floors = {n.get('floor') for n in old_nodes}
        if len(floors) != 1 or None in floors:
            raise ValueError('Missing or conflicting floor: ' + h)
        tid = 'T' + str(next_id).zfill(3)
        next_id += 1
        new_nodes.append({'node_id':tid, 'node_type':'tee', 'subtype':'user_confirmed_circle_junction',
            'floor':next(iter(floors)), 'system':system, 'x':center[0], 'y':center[1], 'label':tid,
            'source_handles':[h], 'source_circle_handle':h, 'source_circle_radius':radius,
            'source_boundary_nodes_retired':ids, 'recognition_status':'user_confirmed_same_service_three_rim_connection',
            'user_confirmation':policy['user_confirmation'], 'local_symbol_internal_physical_length':'unknown', 'review_status':'unreviewed'})
        for step in steps:
            eid, side, nid = step['edge_id'], step['edge_side'], step['existing_node_id']
            if side not in ('start', 'end') or (eid, side) in used_ends or nid in retired:
                raise ValueError('Duplicate or invalid endpoint selection')
            edge, node = edges[eid], nodes[nid]
            if (edge['system'] != system or edge[side + '_node_id'] != nid or incident[nid] != [eid] or
                set(edge.get('source_handles', [])) != set(step.get('existing_source_handles', []))):
                raise ValueError('Stale or cross-service edge: ' + eid)
            xy = [node['x'], node['y']]
            path = edge.get('path_points') or edge.get('path')
            if (not all(isinstance(v, (int,float)) and math.isfinite(v) for v in xy) or not path or
                len(path[0 if side == 'start' else -1]) < 2 or
                not all(isinstance(v,(int,float)) and math.isfinite(v) for v in path[0 if side == 'start' else -1][:2])):
                raise ValueError('Invalid endpoint geometry: ' + nid)
            if not path or math.dist(path[0 if side == 'start' else -1][:2], xy) > tolerance or abs(math.dist(center, xy) - radius) > tolerance:
                raise ValueError('Circle rim endpoint mismatch: ' + nid)
            edge[side + '_node_id'] = tid
            edge.pop(side + '_port_id', None)
            edge['path_points'] = [center] + path if side == 'start' else path + [center]
            edge.setdefault('source_symbol_connectors', []).append({'source_circle_handle':h, 'source_rim_point':xy,
                'junction_center':center, 'geometry_role':'topology_display_only', 'physical_length':'unknown', 'source_pipe_geometry':'not asserted'})
            edge['source_path_length_before_symbol_connectors'] = edge['path_length']
            edge['path_length_scope'] = 'source_drawn_pipe_only_symbol_interior_excluded'
            edge['path_length_complete'] = False
            edge['connection_mode'] = 'user_confirmed_same_service_circle_junction; source_geometry_preserved'
            edge.setdefault('endpoint_reconciliation', []).append({'old_node_id':nid,'new_node_id':tid,'side':side,'source_circle_handle':h,'confirmation':'user_confirmed_same_service_circle_junction'})
            retired[nid] = tid
            used_ends.add((eid, side))
            rewires.append({'edge_id':eid,'side':side,'old_node_id':nid,'new_node_id':tid,'circle_handle':h,'source_rim':xy,'source_center':center})
    out['nodes'] = [n for n in out['nodes'] if n['node_id'] not in retired] + new_nodes
    final_nodes = {n['node_id']:n for n in out['nodes']}
    for edge in out['edges']:
        if edge['edge_id'] not in {r['edge_id'] for r in rewires}:
            continue
        kinds = [final_nodes[edge[side + '_node_id']]['node_type'] for side in ('start', 'end')]
        edge['edge_type'] = 'tee_to_tee' if all(k == 'tee' for k in kinds) else 'tee_to_equipment' if 'equipment' in kinds else 'tee_to_virtual_equipment'
    out['metadata'].update(hil_ready=False, graph_complete=False, stage_status='confirmed_circle_junctions_pending_reference_reconciliation')
    out.setdefault('technicalPending', []).append({'id':'CONFIRMED-CIRCLE-REFERENCE-RECONCILIATION', 'kind':'graph_reference_reconciliation',
        'reason':'Reconcile all graph-bound inventories and evidence after confirmed junctions before HIL.'})
    gate = out.setdefault('preHilComparison', {'status':'pending','families':[]})
    gate['status'] = 'pending'
    gate.setdefault('families', []).append({'id':'confirmed-circle-reference-reconciliation','status':'algorithm_pending'})
    audit = {'source_sha256':source_sha256, 'input_graph_sha256':graph_sha256, 'user_confirmation':policy['user_confirmation'],
             'confirmation_evidence':policy['confirmation_evidence'], 'retired_nodes':retired, 'rewired_edge_ends':rewires,
             'new_tee_nodes':[n['node_id'] for n in new_nodes], 'hil_ready':False}
    out['confirmedCircleJunctions'] = copy.deepcopy(audit)
    return out, audit


def main():
    import argparse
    import hashlib
    import json
    from pathlib import Path
    from source_readability import read_source

    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('graph', 'source', 'plan', 'policy', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('output directory already exists')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    graph, plan, policy = read(args.graph), read(args.plan), read(args.policy)
    doc, preflight = read_source(args.source)
    for witness in policy.get('required_source_texts', []):
        entity = doc.entitydb.get(witness['handle'])
        if entity is None or entity.dxftype() not in ('TEXT','MTEXT','ATTRIB','ATTDEF') or entity.plain_text() != witness['text']:
            raise ValueError('Required native source text is missing or differs')
    result, audit = apply(graph, doc, plan, policy, graph_sha256=digest(args.graph), source_sha256=preflight['source_sha256'])
    audit.update(plan_sha256=digest(args.plan), policy_sha256=digest(args.policy), source_preflight=preflight)
    args.output_dir.mkdir(parents=True)
    for name, data in (('graph_with_edges.json',result),('repair-audit.json',audit)):
        (args.output_dir / name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pending_reference_reconciliation','new_tees':len(audit['new_tee_nodes']),'hil_ready':False}))


if __name__ == '__main__':
    main()
