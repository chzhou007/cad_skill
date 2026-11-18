"""Compare rebuilt junction degrees with a specific prior topology.

A matching historical exception is still pending source review. A changed or
new exception is blocking; matching IDs alone are not evidence of identity.
"""
from collections import Counter
import math
import json


def compare(current, previous, same_source=False):
    def index(graph):
        nodes = graph['nodes']
        by_id = {n['node_id']: n for n in nodes}
        if len(by_id) != len(nodes):
            raise ValueError('duplicate node ID')
        degree = Counter()
        incident = {nid: [] for nid in by_id}
        for edge in graph['edges']:
            a, b = edge['start_node_id'], edge['end_node_id']
            if a not in by_id or b not in by_id or a == b:
                raise ValueError('invalid edge endpoints')
            degree[a] += 1
            degree[b] += 1
            for endpoint, other in ((a, b), (b, a)):
                incident[endpoint].append(json.dumps({'other':other, 'system':edge.get('system'),
                    'path_points':edge.get('path_points'), 'attribute_paths':edge.get('attribute_paths')},
                    sort_keys=True, ensure_ascii=False))
        return by_id, degree, {k:sorted(v) for k,v in incident.items()}

    now, current_degree, current_incident = index(current)
    old, previous_degree, previous_incident = index(previous)
    pending, new = [], []
    for node_id, node in now.items():
        if node.get('node_type') not in ('tee', 'physical_junction'):
            continue
        degree = current_degree[node_id]
        if degree == 3:
            continue
        prior = old.get(node_id)
        same = bool(same_source and prior and all(prior.get(k) == node.get(k) for k in ('node_type', 'system'))
                    and all(isinstance(node.get(k), (int, float)) and isinstance(prior.get(k), (int, float))
                            and math.isfinite(node[k]) and math.isfinite(prior[k])
                            and abs(node[k]-prior[k]) <= 1e-6 for k in ('x','y'))
                    and previous_degree[node_id] == degree
                    and current_incident[node_id] == previous_incident[node_id])
        row = {'node_id': node_id, 'degree': degree}
        if same:
            row['reason'] = 'Matching prior junction exception; source contact still requires review'
            pending.append(row)
        else:
            row['reason'] = 'New or changed junction degree exception requires source comparison'
            new.append(row)
    return {'new_unexplained_degree_exceptions': [r['node_id'] for r in new],
            'new_exception_details': new, 'existing_pending': pending}
