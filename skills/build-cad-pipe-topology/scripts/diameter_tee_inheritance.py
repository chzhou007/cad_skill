"""Compute diameter candidates on explicitly verified, single-system graph portions.

No graph mutation or source verification occurs here. The caller must bind and
verify the exact graph, annotation and junction evidence before using results.
"""
from collections import defaultdict, deque
from math import isfinite


def infer(graph, seeds, verified_edges, verified_junctions):
    nodes_list = graph['nodes']
    edges_list = graph['edges']
    nodes = {n['node_id']: n for n in nodes_list}
    edges = {e['edge_id']: e for e in edges_list}
    boundary_list = graph.get('boundary_anchors', [])
    boundaries = {b['boundary_id']: b for b in boundary_list}
    if len(nodes) != len(nodes_list) or len(edges) != len(edges_list) or len(boundaries) != len(boundary_list):
        raise ValueError('duplicate node, edge or boundary identifier')

    def endpoints(edge):
        resolved = []
        for side in ('start', 'end'):
            node_id = edge.get(side + '_node_id')
            boundary_id = edge.get(side + '_boundary_id')
            if bool(node_id) == bool(boundary_id):
                raise ValueError('invalid edge endpoints')
            if node_id:
                if node_id not in nodes: raise ValueError('invalid edge endpoints')
                resolved.append(('node', node_id))
            else:
                if boundary_id not in boundaries or boundaries[boundary_id].get('system') != edge.get('system'):
                    raise ValueError('invalid source boundary or boundary system')
                resolved.append(('boundary', boundary_id))
        if resolved[0] == resolved[1]: raise ValueError('invalid edge endpoints')
        return resolved
    verified_edges = set(verified_edges)
    verified_junctions = set(verified_junctions)
    if not verified_edges <= edges.keys() or not verified_junctions <= nodes.keys():
        raise ValueError('unknown verified node or edge')
    # Verification is a prerequisite, not a substitute for checking the complete
    # current graph: a caller could otherwise pass a crossing, mixed-system contact
    # or a T whose unresolved third arm was omitted from verified_edges.
    complete_incidence = defaultdict(list)
    for edge in edges_list:
        for node_id in (edge.get('start_node_id'), edge.get('end_node_id')):
            if node_id in verified_junctions:
                complete_incidence[node_id].append(edge)
    for node_id in verified_junctions:
        node = nodes[node_id]
        if node.get('node_type') not in ('tee', 'physical_junction'):
            raise ValueError('only verified physical junctions may propagate')
        if node.get('subtype') == 'pending_source_junction' or node.get('resolution_state') in ('source_main_continuation_branch_pending','source_contact_reconstructed_pending_comparison'):
            raise ValueError('pending branch connectivity cannot propagate')
        incident = complete_incidence[node_id]
        systems = {e.get('system') for e in incident}
        if (len(incident) != 3 or len({e['edge_id'] for e in incident}) != 3
                or len(systems) != 1 or not systems <= {'supply', 'return'}):
            raise ValueError('verified junction must have exactly three same-system graph edges')
        for edge in incident:
            endpoints(edge)  # boundary anchors are valid terminals, never junctions
            # A source-specific similar-circle repair may be present as a
            # physical tee while its branch is explicitly only inferred. The
            # call-site verified set cannot clear that source uncertainty.
            link = edge.get('source_expert_circle_link')
            if isinstance(link, dict) and link.get('similar_location_inferred') is True:
                circle = link.get('circle_handle')
                handles = node.get('source_handles')
                if not circle or not handles or circle in handles:
                    raise ValueError('inferred similar-circle branch cannot propagate before source reconciliation')
    incidence = defaultdict(list)
    for edge_id in verified_edges:
        e = edges[edge_id]
        if e.get('system') not in ('supply', 'return'):
            raise ValueError('unknown pipe system')
        for kind, node_id in endpoints(e):
            if kind == 'node' and node_id in verified_junctions:
                incidence[(node_id, e['system'])].append(edge_id)
    seed_values = defaultdict(list)
    evidence_owners = {}
    for seed in seeds:
        edge_id = seed['edge_id']
        value = seed['nominal_mm']
        if edge_id not in verified_edges or isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
            raise ValueError('invalid direct diameter seed')
        if not isinstance(seed.get('evidence_id'), str) or not seed['evidence_id'].strip():
            raise ValueError('seed requires source evidence')
        if seed['evidence_id'] in evidence_owners and evidence_owners[seed['evidence_id']] != (edge_id, float(value)):
            raise ValueError('source evidence cannot seed multiple edges or diameters')
        evidence_owners[seed['evidence_id']] = (edge_id, float(value))
        seed_values[edge_id].append((float(value), seed['evidence_id']))
    if any(len({value for value, _ in values}) > 1 for values in seed_values.values()):
        raise ValueError('multiple diameters on one edge require segment-level evidence')
    # A directly annotated edge is a boundary: its value can seed its neighbors,
    # but incoming evidence cannot pass through it to the other end.
    candidates = defaultdict(lambda: defaultdict(dict))
    for edge_id in sorted(seed_values):
        for value, witness in sorted(seed_values[edge_id]):
            candidates[edge_id][value][witness] = [edge_id]
            queue = deque([(edge_id, [edge_id])]); seen = {edge_id}
            while queue:
                current, path = queue.popleft()
                e = edges[current]
                for node_id in (e.get('start_node_id'), e.get('end_node_id')):
                    for neighbor in sorted(incidence.get((node_id, e['system']), [])):
                        if neighbor in seen:
                            continue
                        seen.add(neighbor)
                        if neighbor in seed_values:
                            continue
                        new_path = path + [neighbor]
                        candidates[neighbor][value][witness] = new_path
                        queue.append((neighbor, new_path))
    result = []
    for edge_id in sorted(verified_edges):
        values = candidates[edge_id]
        all_values = sorted(values)
        status = ('unknown' if not values else 'conflict' if len(values) > 1
                  else 'direct' if edge_id in seed_values else 'inherited_candidate')
        result.append({'edge_id': edge_id, 'status': status,
                       'nominal_mm': all_values[0] if len(all_values) == 1 else None,
                       'candidates': [{'nominal_mm': v,
                                       'evidence': [{'evidence_id': w, 'edge_path': values[v][w]}
                                                    for w in sorted(values[v])]} for v in all_values]})
    return result
