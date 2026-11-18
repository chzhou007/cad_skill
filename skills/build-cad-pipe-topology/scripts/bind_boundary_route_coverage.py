"""Bind a fresh native-line audit to candidate axis routes, without accepting them."""
import argparse
import hashlib
import json
from pathlib import Path

from native_path_coverage_audit import audit
from source_readability import read_source


def bind(preflight, coverage, recomputed, axis_hash, source_hash):
    if (preflight.get('status') != 'boundary_mapping_preflight_not_mapping'
            or preflight.get('axis_graph_sha256') != axis_hash
            or preflight.get('mapping_ready') is not False
            or preflight.get('hil_ready') is not False):
        raise ValueError('stale or accepted mapping preflight')
    if (coverage.get('source_sha256') != source_hash or coverage.get('graph_sha256') != axis_hash
            or coverage.get('graph_mutated') is not False or coverage.get('hil_ready') is not False
            or coverage.get('status') != recomputed.get('status')
            or coverage.get('edges') != recomputed.get('edges')):
        raise ValueError('coverage does not match current source and graph')
    rows = coverage['edges']
    index = {r['edge_id']: r for r in rows}
    if len(index) != len(rows):
        raise ValueError('duplicate coverage edge')
    records = []
    for route in preflight.get('records', []):
        system = route.get('system')
        paths = route.get('axis_paths')
        if system not in ('supply', 'return') or not isinstance(paths, list) or not paths:
            raise ValueError('invalid route')
        edge_ids = sorted({edge for path in paths for edge in path})
        if not edge_ids or any(e not in index or index[e]['system'] != system or not index[e].get('segments') for e in edge_ids):
            raise ValueError('incomplete or wrong-system coverage')
        unresolved = [e for e in edge_ids if any(s['status'] != 'single_source_line_covers' for s in index[e]['segments'])]
        records.append({'system': system, 'axis_edge_ids': edge_ids, 'unverified_edge_ids': unresolved,
                        'all_segments_single_line_witnessed': not unresolved,
                        'mapping_ready': False, 'physical_length': 'unknown'})
    if not records or len({r['system'] for r in records}) != len(records):
        raise ValueError('empty or duplicate routes')
    return {'status': 'route_source_geometry_evidence_not_mapping', 'axis_graph_sha256': axis_hash,
            'axis_source_sha256': source_hash, 'records': records, 'mapping_ready': False,
            'graph_mutated': False, 'human_accepted': False, 'hil_ready': False,
            'limitations': ['Witnessed LINE geometry does not prove junction connectivity, route correspondence or physical length.',
                            'Search excludes unrelated blocks, polylines, arcs and proxies; a missing witness is not proof of absence.']}


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'axis-graph', 'preflight', 'coverage-policy', 'coverage', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    load = lambda p: json.loads(p.read_text(encoding='utf8'))
    doc, proof = read_source(args.source)
    graph = load(args.axis_graph)
    recomputed = audit(doc, graph, load(args.coverage_policy), proof['source_sha256'], sha(args.axis_graph))
    result = bind(load(args.preflight), load(args.coverage), recomputed, sha(args.axis_graph), proof['source_sha256'])
    result['input_sha256'] = {key: sha(getattr(args, key)) for key in ('preflight', 'coverage_policy', 'coverage')}
    result['script_sha256'] = sha(Path(__file__))
    result['source_preflight'] = proof
    with args.output.open('x', encoding='utf8', newline='\n') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'status': result['status'], 'routes': len(result['records'])}))


if __name__ == '__main__':
    main()
