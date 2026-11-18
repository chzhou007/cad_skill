"""Retire selected stale crossover hypotheses after source-proven separate tees.

This stage changes audit status only. It cannot create or alter connectivity,
promote display geometry to physical length, or approve a whole drawing.
"""
import argparse
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path
from source_readability import read_source


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf8')).hexdigest()


def xy(point):
    return [point.x, point.y]


def on_line(point, line, tol=.05):
    a, b = xy(line.dxf.start), xy(line.dxf.end)
    return abs(math.dist(a, point)+math.dist(point, b)-math.dist(a, b)) <= tol


def reconcile(doc, graph, policy, repair_policy, source_hash, graph_hash, evidence_hash):
    if (policy.get('source_sha256') != source_hash or policy.get('graph_sha256') != graph_hash
            or graph.get('metadata', {}).get('source_sha256') != source_hash
            or repair_policy.get('source_sha256') != source_hash
            or repair_policy.get('evidence_manifest_sha256') != evidence_hash
            or repair_policy.get('confirmed_by') != 'user'):
        raise ValueError('source, graph or confirmed evidence mismatch')
    selected = policy.get('conflict_sha256s')
    conflicts = graph.get('sourceCircleCrossoverConflicts')
    if (not isinstance(selected, list) or not selected or len(set(selected)) != len(selected)
            or not isinstance(conflicts, list)):
        raise ValueError('invalid conflict selection')
    nodes = {n['node_id']: n for n in graph['nodes']}
    edges = {e['edge_id']: e for e in graph['edges']}
    if len(nodes) != len(graph['nodes']) or len(edges) != len(graph['edges']):
        raise ValueError('duplicate graph identities')
    repairs = []
    r = graph.get('userConfirmedOverlappingBranches')
    while isinstance(r, dict):
        if (r.get('source_sha256') == source_hash and r.get('input_graph_sha256') == repair_policy.get('graph_sha256')
                and r.get('evidence_manifest_sha256') == evidence_hash):
            repairs.extend(r.get('records', []))
        r = r.get('previous_repair')
    connections = repair_policy.get('connections', [])
    resolved, remaining = [], []
    for conflict in conflicts:
        key = digest(conflict)
        if key not in selected:
            remaining.append(copy.deepcopy(conflict))
            continue
        handles = conflict.get('source_handles', [])
        crosses = conflict.get('crossings', [])
        circles = conflict.get('circle_conflicts', [])
        if (len(handles) != 2 or len(set(handles)) != 2 or len(crosses) != 1 or len(circles) != 1
                or conflict.get('reason') != 'source_circle_at_crossing_requires_comparison'):
            raise ValueError('unsupported crossover hypothesis')
        main_handle = crosses[0]['crossed_handle']
        expected = []
        for handle in handles:
            matches = [c for c in connections if c['branch_handle'] == handle and c['main_handle'] == main_handle]
            if len(matches) != 1:
                raise ValueError('missing unique confirmed branch mapping')
            expected.append(matches[0])
        if (expected[0]['system'] != expected[1]['system']
                or expected[0]['circle_handle'] == expected[1]['circle_handle']
                or circles[0]['circle_handle'] not in {c['circle_handle'] for c in expected}
                or crosses[0].get('crossed_source_system') != expected[0]['system']):
            raise ValueError('not two distinct same-system circles')
        system = expected[0]['system']
        witnesses = []
        for c in expected:
            records = [r for r in repairs if r.get('circle_handle') == c['circle_handle'] and r.get('branch_edge') == c['branch_edge']]
            if len(records) != 1:
                raise ValueError('missing confirmed repair audit')
            rec = records[0]
            node, branch = nodes.get(rec['tee']), edges.get(c['branch_edge'])
            if not node or not branch or c['terminal'] in nodes:
                raise ValueError('missing repaired graph endpoint')
            circle, main, native_branch = [doc.entitydb.get(c[k]) for k in ('circle_handle', 'main_handle', 'branch_handle')]
            if (not circle or circle.dxftype() != 'CIRCLE' or not main or main.dxftype() != 'LINE'
                    or not native_branch or native_branch.dxftype() != 'LINE'):
                raise ValueError('native circle or pipe missing')
            if main.dxf.layer != c['pipe_layer'] or native_branch.dxf.layer != c['pipe_layer']:
                raise ValueError('native pipe system changed')
            center = xy(circle.dxf.center)
            if (math.dist(center, c['circle_center']) > .05 or abs(circle.dxf.radius-c['circle_radius']) > .05
                    or math.dist(center, [node['x'], node['y']]) > .05 or not on_line(center, main)):
                raise ValueError('native circle geometry differs')
            if node.get('node_type') != 'tee' or node.get('system') != system or branch.get('system') != system:
                raise ValueError('current junction system or type differs')
            incident = [e for e in edges.values() if node['node_id'] in (e['start_node_id'], e['end_node_id'])]
            if len(incident) != 3 or any(e['system'] != system for e in incident) or branch not in incident:
                raise ValueError('current contact is not the confirmed isolated tee')
            mains = [e for e in incident if e['edge_id'] != branch['edge_id']]
            if any(main_handle not in e.get('source_handles', []) for e in mains):
                raise ValueError('tee lacks two source main segments')
            for e in mains:
                point = e['path'][0 if e['start_node_id'] == node['node_id'] else -1]
                if math.dist(point, center) > .05:
                    raise ValueError('main endpoint geometry differs from tee')
            if c['branch_handle'] not in branch.get('source_handles', []) or main_handle in branch.get('source_handles', []):
                raise ValueError('branch source ownership differs')
            for obj in (node, branch):
                ev = obj.get('user_confirmed_overlap_connection', {})
                if any(ev.get(k) != c[k] for k in ('circle_handle', 'main_handle', 'branch_handle')) or ev.get('user_evidence_manifest_sha256') != evidence_hash:
                    raise ValueError('current connection evidence differs')
                if ev.get('route_is_physical') is not False or ev.get('physical_length') != 'unknown':
                    raise ValueError('display route promoted to physical evidence')
            if branch.get('physical_length') != 'unknown' or branch.get('path_length_complete') is not False:
                raise ValueError('unproven branch length promoted')
            start = c['display_route'][0]
            if (min(math.dist(start, xy(p)) for p in (native_branch.dxf.start, native_branch.dxf.end)) > .05
                    or min(math.dist(start, conflict[k]) for k in ('a', 'b')) > .05):
                raise ValueError('conflict endpoint does not match confirmed source branch')
            witnesses.append({'branch_handle': c['branch_handle'], 'branch_edge': branch['edge_id'],
                              'circle_handle': c['circle_handle'], 'node_id': node['node_id'],
                              'main_edges': [e['edge_id'] for e in mains]})
        # A direct native main segment joins the two circles. It is not an invented
        # coincident tee connector or the old collinear gap bridge.
        tee_ids = {w['node_id'] for w in witnesses}
        between = [e for e in edges.values() if {e['start_node_id'], e['end_node_id']} == tee_ids]
        if len(between) != 1 or between[0].get('system') != system or between[0].get('source_handles') != [main_handle]:
            raise ValueError('separate tees lack unique native main interval')
        if any(not on_line(p, main) for p in between[0]['path']):
            raise ValueError('joining interval leaves native main')
        if any(set(handles).issubset(e.get('source_handles', [])) for e in edges.values()):
            raise ValueError('obsolete direct branch bridge remains')
        resolved.append({'conflict_sha256': key, 'original_conflict': copy.deepcopy(conflict),
                         'resolution': 'separate_confirmed_tees_on_native_main_not_collinear_gap',
                         'connections': witnesses, 'native_main_edge': between[0]['edge_id']})
    if len(resolved) != len(selected):
        raise ValueError('selected conflict missing or duplicated')
    out = copy.deepcopy(graph)
    out['sourceCircleCrossoverConflicts'] = remaining
    audit = {'source_sha256': source_hash, 'input_graph_sha256': graph_hash,
             'evidence_manifest_sha256': evidence_hash, 'records': resolved,
             'remaining_conflicts': len(remaining), 'connectivity_changed': False, 'hil_ready': False}
    out.setdefault('sourceCircleCrossoverConflictHistory', []).append(audit)
    out['preHilComparison'] = {'status': 'pending', 'reason': 'selected obsolete crossover hypotheses reconciled; other source comparisons remain pending',
                              'current_circle_crossover_conflicts': len(remaining),
                              'previous_comparison': copy.deepcopy(graph.get('preHilComparison', {}))}
    out.setdefault('metadata', {}).update(hil_ready=False, graph_complete=False, review_status='unreviewed')
    return out, audit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'graph', 'devices', 'policy', 'repair-policy', 'evidence-manifest', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    read = lambda f: json.loads(f.read_text(encoding='utf8'))
    policy = read(a.policy)
    for key, path in [('repair_policy_sha256', a.repair_policy), ('evidence_manifest_sha256', a.evidence_manifest), ('devices_sha256', a.devices)]:
        if policy.get(key) != sha(path):
            raise ValueError('pinned input mismatch: '+key)
    manifest = read(a.evidence_manifest)
    if not manifest.get('items'):
        raise ValueError('empty user evidence')
    for item in manifest['items']:
        if sha(item['path']) != item['sha256']:
            raise ValueError('user evidence changed')
    doc, _ = read_source(a.source)
    out, audit = reconcile(doc, read(a.graph), policy, read(a.repair_policy), sha(a.source), sha(a.graph), sha(a.evidence_manifest))
    a.output.mkdir(parents=True, exist_ok=False)
    encoded = (json.dumps(out, ensure_ascii=False, indent=2)+'\n').encode('utf8')
    (a.output/'graph_with_edges.json').write_bytes(encoded)
    audit = dict(audit, output_graph_sha256=hashlib.sha256(encoded).hexdigest(), policy_sha256=sha(a.policy))
    (a.output/'reconciliation-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    shutil.copyfile(a.devices, a.output/'assigned_edge_device_instances.csv')
    print(json.dumps({'resolved': len(audit['records']), 'remaining': audit['remaining_conflicts'], 'hil_ready': False}))


if __name__ == '__main__':
    main()
