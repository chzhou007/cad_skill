"""Separate source-drawn line lengths from circle-center display connectors."""
import copy
import math


def repair(graph, doc, source_sha):
    g = copy.deepcopy(graph)
    comparison = g.get('sourceDetailComparison') or {}
    if not source_sha or comparison.get('source_sha256') != source_sha or g.get('metadata', {}).get('source_sha256') != source_sha:
        raise ValueError('detail length source identity mismatch')
    pairs = comparison.get('pairs')
    if not pairs:
        raise ValueError('source-bound detail candidates required')
    nodes = {n['node_id']: n for n in g['nodes']}
    audit, seen = [], set()
    for p in pairs:
        center_node = nodes[p['detail_tee']]
        matches = [e for e in g['edges'] if p['detail_tee'] in (e['start_node_id'], e['end_node_id']) and p['detail_pipe'] in e.get('source_handles', [])]
        if len(matches) != 1:
            raise ValueError('detail branch must match one source edge')
        e = matches[0]
        if e['edge_id'] in seen or e['system'] != p['system'] or e.get('source_handles') != [p['detail_pipe']]:
            raise ValueError('ambiguous detail branch identity')
        circle, line = doc.entitydb.get(p['detail_circle']), doc.entitydb.get(p['detail_pipe'])
        if not circle or not line or circle.dxftype() != 'CIRCLE' or line.dxftype() != 'LINE' or circle.dxf.layer != line.dxf.layer:
            raise ValueError('detail circle or pipe witness mismatch')
        c = (circle.dxf.center.x, circle.dxf.center.y)
        if math.dist(c, (center_node['x'], center_node['y'])) > 0.01:
            raise ValueError('circle center not at detail junction')
        ends = [(line.dxf.start.x, line.dxf.start.y), (line.dxf.end.x, line.dxf.end.y)]
        ends.sort(key=lambda xy: math.dist(xy, c))
        rim, far = ends
        if abs(math.dist(rim, c)-circle.dxf.radius) > 0.01:
            raise ValueError('source pipe does not end on circle rim')
        otherid = e['end_node_id'] if e['start_node_id'] == p['detail_tee'] else e['start_node_id']
        other = nodes[otherid]
        if math.dist(far, (other['x'], other['y'])) > 0.01:
            raise ValueError('source pipe far endpoint differs from graph endpoint')
        paths = e.get('attribute_paths', [])
        if len(paths) != 1 or len(paths[0]) != 2:
            raise ValueError('unsupported detail branch path')
        expected = [c, far] if e['start_node_id'] == p['detail_tee'] else [far, c]
        if any(math.dist(a, b) > 0.01 for a, b in zip(paths[0], expected)):
            raise ValueError('detail branch path changed')
        native = math.dist(rim, far)
        if abs(e['path_length'] - native - circle.dxf.radius) > 0.01:
            raise ValueError('detail branch length differs from native line plus display radius')
        original = e['path_length']
        e['attribute_paths'] = [[list(rim), list(far)] if e['start_node_id'] == p['detail_tee'] else [list(far), list(rim)]]
        e['path_length'] = native
        e['path_length_complete'] = False
        e['path_length_scope'] = 'source_drawn_pipe_only_circle_interior_unknown'
        e['source_detail_circle_length_evidence'] = {'source_circle_handle': p['detail_circle'], 'source_line_handle': p['detail_pipe'], 'circle_center': list(c), 'line_contact': list(rim), 'circle_radius_drawing_units': circle.dxf.radius, 'circle_center_to_rim_is_display_only': True, 'physical_connection_length': 'unknown'}
        audit.append({'edge_id': e['edge_id'], 'system': e['system'], 'circle_handle': p['detail_circle'], 'line_handle': p['detail_pipe'], 'old_length': original, 'source_drawn_length': native, 'removed_display_radius': circle.dxf.radius})
        seen.add(e['edge_id'])
    return g, audit
