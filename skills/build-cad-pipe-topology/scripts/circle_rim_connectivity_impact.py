"""Read-only connectivity impact of source circle-rim shape candidates.

Connectivity is diagnostic over the current graph only.  This does not prove a
candidate circle is a hydraulic junction and never mutates the graph.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def analyze(graph, screen, graph_hash, source_hash):
    if screen.get('graph_sha256') != graph_hash or screen.get('source_sha256') != source_hash:
        raise ValueError('screen source or graph is stale')
    if graph.get('metadata', {}).get('source_sha256') != source_hash:
        raise ValueError('graph source is stale')
    if screen.get('status') != 'source_shape_comparison_not_connectivity':
        raise ValueError('invalid source circle screen')
    nodes = {n['node_id']: n for n in graph['nodes']}
    edges = {e['edge_id']: e for e in graph['edges']}
    boundaries = {b['boundary_id']: b for b in graph.get('boundary_anchors', [])}
    if len(nodes) != len(graph['nodes']) or len(edges) != len(graph['edges']):
        raise ValueError('duplicate graph ID')
    if len(boundaries) != len(graph.get('boundary_anchors', [])):
        raise ValueError('duplicate boundary ID')
    parent = {}

    def find(k):
        parent.setdefault(k, k)
        if parent[k] != k:
            parent[k] = find(parent[k])
        return parent[k]

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a

    def endpoint(edge, side):
        node_id = edge[side+'_node_id']
        if node_id is None:
            boundary_id = edge.get(side+'_boundary_id')
            boundary = boundaries.get(boundary_id)
            if boundary is None or boundary.get('system') != edge['system']:
                raise ValueError('edge boundary missing or wrong system')
            # A boundary is a terminal, not a traversable graph connection.
            return (edge['system'], 'boundary', boundary_id, edge['edge_id'], side)
        if node_id not in nodes:
            raise ValueError('edge endpoint missing from graph')
        # Equipment and virtual interfaces are traversal boundaries.
        if nodes[node_id].get('node_type') in ('equipment', 'virtual_equipment'):
            return (edge['system'], node_id, edge['edge_id'])
        return (edge['system'], node_id)

    for edge in edges.values():
        if edge.get('system') not in ('supply', 'return'):
            continue
        union(endpoint(edge, 'start'), endpoint(edge, 'end'))

    def edge_component(edge_id, system):
        edge = edges.get(edge_id)
        if edge is None or edge.get('system') != system:
            raise ValueError('candidate edge missing or wrong system')
        return find(endpoint(edge, 'start'))

    results = []
    for candidate in screen['candidates']:
        system = candidate['line_system']
        main, branch = candidate['main_graph_edges'], candidate['branch_graph_edges']
        item = {'circle_handle': candidate['circle_handle'], 'system': system,
                'main_graph_edges': main, 'branch_graph_edges': branch,
                'circle_layer_matches_lines': candidate['circle_layer_matches_lines'],
                'z_consistent_within_tolerance': candidate['z_consistent_within_tolerance'],
                'status': candidate['status']}
        if len(main) == len(branch) == 1:
            same = edge_component(main[0], system) == edge_component(branch[0], system)
            item['current_graph_relation'] = 'same_component' if same else 'separate_components'
        else:
            item['current_graph_relation'] = 'ambiguous_edge_binding'
        results.append(item)
    return {'status': 'diagnostic_not_connectivity_confirmation', 'graph_sha256': graph_hash,
            'source_sha256': source_hash, 'equipment_and_virtual_interface_traversal': 'blocked',
            'limitations': ['Graph components do not establish physical connectivity or correct existing edges.',
                            'Boundary nodes are not bridged across sheets or systems.',
                            'Competing native geometry remains in the input screen.'],
            'candidates': results, 'ambiguous_native_geometry': screen['ambiguous_native_geometry']}


def main():
    p = argparse.ArgumentParser()
    for name in ('graph', 'screen', 'source', 'output'):
        p.add_argument('--'+name, required=True)
    args = p.parse_args()
    graph = json.loads(Path(args.graph).read_text(encoding='utf8'))
    screen = json.loads(Path(args.screen).read_text(encoding='utf8'))
    result = analyze(graph, screen, digest(args.graph), digest(args.source))
    result['screen_sha256'] = digest(args.screen)
    result['script_sha256'] = digest(__file__)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'status': result['status'], 'count': len(result['candidates'])}))


if __name__ == '__main__':
    main()
