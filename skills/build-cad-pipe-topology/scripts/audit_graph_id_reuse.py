"""Read-only source-path and node identity comparison across two graph versions.

Candidates are geometric identity evidence, never automatic review migration.
"""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def edge_key(edge):
    handles = edge.get('source_handles') or []
    paths = edge.get('attribute_paths') or []
    if not handles or not paths or any(len(p) < 2 for p in paths):
        return None
    def canonical(path):
        pts = tuple(tuple(round(float(v), 5) for v in pt[:2]) for pt in path)
        return min(pts, tuple(reversed(pts)))
    return (edge.get('system'), tuple(sorted(set(handles))), tuple(sorted(canonical(p) for p in paths)))


def node_key(node):
    if node.get('x') is None or node.get('y') is None:
        return None
    return (node.get('node_type'), node.get('system'), node.get('floor'),
            round(float(node['x']), 5), round(float(node['y']), 5))


def audit(old, new):
    result = {}
    for name, id_field, key in [('edges', 'edge_id', edge_key), ('nodes', 'node_id', node_key)]:
        prior = old[name]; current = new[name]
        if len({x[id_field] for x in prior}) != len(prior) or len({x[id_field] for x in current}) != len(current):
            raise ValueError('duplicate graph IDs')
        old_by = defaultdict(list); new_by = defaultdict(list)
        for row in prior:
            if key(row) is not None: old_by[key(row)].append(row[id_field])
        for row in current:
            if key(row) is not None: new_by[key(row)].append(row[id_field])
        new_ids = {r[id_field]: r for r in current}; rows = []
        for row in prior:
            ident = row[id_field]; k = key(row); matches = new_by.get(k, []) if k is not None else []
            unique = k is not None and len(old_by[k]) == 1 and len(matches) == 1
            same_id = new_ids.get(ident)
            collision = same_id is not None and (k is None or key(same_id) != k)
            rows.append({'old_id': ident, 'candidate_new_ids': matches, 'unique_source_geometry_match': unique,
                         'id_reused_for_different_or_unverifiable_object': collision,
                         'status': 'unique_geometry_candidate' if unique else 'unresolved'})
        result[name] = {'counts': {'old': len(prior), 'new': len(current),
                                   'unique_candidates': sum(r['unique_source_geometry_match'] for r in rows),
                                   'reused_id_conflicts': sum(r['id_reused_for_different_or_unverifiable_object'] for r in rows)},
                        'records': rows}
    return {'status': 'source_geometry_id_audit_only', **result, 'graph_mutated': False,
            'review_migration_authorized': False, 'human_accepted': False,
            'limitations': ['Exact source geometry is candidate evidence, not proof of unchanged connectivity or semantics.',
                            'Splits, merges, ambiguous or unsupported geometry remain unresolved.']}


def audit_bound(previous_path, current_path, source_sha256, spec):
    """Audit an explicitly pinned earlier graph against this source and output."""
    old_bytes = Path(previous_path).read_bytes(); new_bytes = Path(current_path).read_bytes()
    if hashlib.sha256(old_bytes).hexdigest() != spec.get('previous_graph_sha256'):
        raise ValueError('previous graph hash mismatch')
    if source_sha256 != spec.get('source_sha256'):
        raise ValueError('ID audit source hash mismatch')
    old = json.loads(old_bytes.decode('utf8')); new = json.loads(new_bytes.decode('utf8'))
    if any(g.get('metadata', {}).get('source_sha256') != source_sha256 for g in (old, new)):
        raise ValueError('graph source binding mismatch')
    report = audit(old, new)
    report.update(old_graph_sha256=hashlib.sha256(old_bytes).hexdigest(),
                  new_graph_sha256=hashlib.sha256(new_bytes).hexdigest(), source_sha256=source_sha256)
    return report


def main():
    parser = argparse.ArgumentParser()
    for flag in ('old', 'new', 'output'): parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    raw_old = args.old.read_bytes(); raw_new = args.new.read_bytes()
    report = audit(json.loads(raw_old.decode('utf8')), json.loads(raw_new.decode('utf8')))
    report['old_graph_sha256'] = hashlib.sha256(raw_old).hexdigest()
    report['new_graph_sha256'] = hashlib.sha256(raw_new).hexdigest()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: report[k]['counts'] for k in ('edges', 'nodes')}))

if __name__ == '__main__': main()
