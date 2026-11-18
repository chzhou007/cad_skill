"""Separate a source circle's logical center from its actual pipe endpoint."""
import math


def correct_riser_source_lengths(edges, evidence, tol=0.05):
    audits = []
    for witness in evidence:
        node = witness['interface_id']
        if witness.get('graph_state') != 'loaded_connected_interface' or witness.get('semantic') != 'out_of_plane_riser_terminal':
            continue
        matches = [e for e in edges if node in (e['start_node_id'], e['end_node_id'])]
        if len(matches) != 1:
            raise ValueError(f'{node}: riser must have exactly one incident edge')
        edge = matches[0]
        if witness['pipe_handles'][0] not in edge['source_handles'] or edge['system'] != witness['system']:
            raise ValueError(f'{node}: source pipe or system mismatch')
        paths = edge['attribute_paths']
        if len(paths) != 1 or len(paths[0]) < 2:
            raise ValueError(f'{node}: unsupported source path')
        pts = [list(p) for p in paths[0]]
        start = edge['start_node_id'] == node
        end_index, next_index = (0, 1) if start else (-1, -2)
        center, rim, near = pts[end_index], witness['original_endpoint'], pts[next_index]
        span = math.dist(center, rim)
        if math.dist(center, witness['center']) > tol or span <= tol:
            raise ValueError(f'{node}: invalid center or radius')
        if abs(math.dist(center, near) - span - math.dist(rim, near)) > tol:
            raise ValueError(f'{node}: original endpoint not on terminal path')
        pts[end_index] = list(rim)
        edge['attribute_paths'] = [pts]
        edge['path_length'] -= span
        if edge['path_length'] < -tol:
            raise ValueError(f'{node}: negative source length')
        edge['path_length_complete'] = False
        edge['path_length_scope'] = 'source_drawn_pipe_only_riser_length_unknown'
        edge.setdefault('source_riser_interfaces', []).append({'circle_handle': witness['circle_handle'], 'pipe_handle': witness['pipe_handles'][0], 'original_endpoint': list(rim), 'logical_center': list(center), 'graphic_radius': span, 'physical_riser_length': 'unknown'})
        audits.append({'node_id': node, 'edge_id': edge['edge_id'], 'circle_handle': witness['circle_handle'], 'pipe_handle': witness['pipe_handles'][0], 'graphic_radius_excluded': span})
    return audits
