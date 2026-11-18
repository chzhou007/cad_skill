"""Apply source-pinned expert canvas-label exclusions without changing topology."""
import math


def apply(graph, doc, policy):
    if policy.get('source_sha256') != graph.get('metadata', {}).get('source_sha256'):
        raise ValueError('label policy source hash mismatch')
    records = policy.get('records')
    if not isinstance(records, list) or not records:
        raise ValueError('label policy requires scoped records')
    selected = []
    for r in records:
        h = r.get('source_pipe_handle')
        entity = doc.entitydb.get(h)
        if not entity or entity.dxftype() != 'LINE':
            raise ValueError('label policy source line missing')
        if not r.get('expert_issue') or not r.get('expert_note'):
            raise ValueError('label policy expert evidence missing')
        x, y = r['point']
        if not all(math.isfinite(v) for v in (x, y)):
            raise ValueError('label policy invalid point')
        a, b = entity.dxf.start, entity.dxf.end
        dx, dy = b.x-a.x, b.y-a.y
        size = dx*dx+dy*dy
        t = max(0, min(1, ((x-a.x)*dx+(y-a.y)*dy)/size)) if size else 0
        if math.hypot(x-a.x-t*dx, y-a.y-t*dy) > 0.1:
            raise ValueError('label policy point not on native source line')
        matches = [n for n in graph['nodes'] if n['node_type'] == r['node_type']
                   and h in n.get('source_handles', [])
                   and math.hypot(n['x']-x, n['y']-y) < 0.1]
        if len(matches) != 1 or any(n is matches[0] for n, _ in selected):
            raise ValueError('label policy node is missing, ambiguous or duplicated')
        selected.append((matches[0], r))
    for n, r in selected:
        if 'node_label_visible' in n or 'node_label_policy_evidence' in n:
            raise ValueError('label policy target already has label policy')
    for n, r in selected:
        n['node_label_visible'] = False
        n['node_label_policy_evidence'] = {
            'expert_issue': r['expert_issue'], 'expert_note': r['expert_note'],
            'source_pipe_handle': r['source_pipe_handle'],
            'scope': 'canvas_node_label_only', 'review_status': 'unreviewed'}
    return [{'node_id': n['node_id'], 'source_pipe_handle': r['source_pipe_handle'],
             'expert_issue': r['expert_issue']} for n, r in selected]
