"""Requalify bounded two-view routes without pairing simplified interior taps."""
import argparse, copy, importlib, sys
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from crossview_equipment_branch_inventory import index_graph, native_tee
from match_source_checked_crossview_paths import bridge_main_path, selected_snapshot
from batch_native_path_coverage import collect as coverage
from source_readability import read_source
from source_stable_junction_reapplication import prepare

MODE = 'native_reviewed_expression_bounded_scope_v1'


def bounded_alternate(graph, anchor_edge, boundaries, floor, system):
    """Cut declared known boundaries, never choose a shortest or residual path."""
    nodes, edges, _ = index_graph(graph)
    anchor = edges[anchor_edge]
    ends = {anchor['start_node_id'], anchor['end_node_id']}
    if (anchor['system'] != system or len(ends) != 2 or not ends <= set(boundaries)
            or any(nodes[n].get('floor') != floor for n in boundaries)):
        raise ValueError('same-floor independent boundary anchors required')
    closed = set(boundaries) - ends
    projection = dict(nodes=graph['nodes'], edges=[e for e in graph['edges']
        if e['edge_id'] != anchor_edge and e['start_node_id'] not in closed
        and e['end_node_id'] not in closed])
    route = bridge_main_path(projection, anchor['start_node_id'], anchor['end_node_id'], system, floor)
    if len(route['edges']) < 2:
        raise ValueError('alternate expression must contain a route, not another direct writer')
    return dict(route=route, closed_known_boundaries=sorted(closed),
        bypass_edge=anchor_edge, boundary_policy='stop_at_every_other_independent_known_junction',
        uniqueness_scope='declared_boundary_cut_graph_only_not_global_network',
        source_snapshot=selected_snapshot(graph, route['edges']), shortest_path_used=False)


def orient_pair(views, mapping):
    plan = views['plan']['route']; axis = views['iso']['route']
    if mapping[plan['nodes'][0]] == axis['nodes'][-1]:
        axis['nodes'].reverse(); axis['edges'].reverse()
    if [mapping[plan['nodes'][i]] for i in (0, -1)] != [axis['nodes'][i] for i in (0, -1)]:
        raise ValueError('two independent endpoint identities do not match')


def qualify(views, answer):
    if (answer.get('decision') != '同一范围，有省略或多画，见说明'
            or not answer.get('comment') or '\ufffd' in answer['comment']):
        raise ValueError('explicit readable same-range simplification reply required')
    failures = []
    for view, row in views.items():
        failures.extend(dict(view=view, node_id=n, reason=r, owner='local_topology_source_evidence')
                        for n, r in row['junction_failures'].items())
        failures.extend(dict(view=view, **r, owner='local_source_path') for r in row['path_failures'])
    return dict(status='held_local_source_evidence' if failures else 'native_bounded_range_correspondence',
        failures=failures, internal_branch_counts_equal=len(views['plan']['route']['nodes']) == len(views['iso']['route']['nodes']),
        internal_node_identities_assigned=False, per_axis_edge_metric_allocation_known=False,
        DN_values_assigned=0, length_values_assigned=0, human_accepted=False)


def compute(manifest):
    inputs = manifest['inputs']
    def checked():
        if any(sha(x['path']) != x['sha256'] for x in inputs.values()):
            raise ValueError('reviewed expression input changed')
    checked()
    reply = load(inputs['reply']['path'])
    questions = [q for section in reply['followup_sections'] for q in section['questions']
                 if q['id'] == manifest['question_id']]
    if len(questions) != 1:
        raise ValueError('one original source-bound review question required')
    question = questions[0]; answer = question['answer']; pair = inputs['review_pair']
    if answer['source_pair_sha256'] != pair['sha256']:
        raise ValueError('reply and original source Pair differ')
    evidence = question['source_evidence']
    if (evidence['plan_source_sha256'] != inputs['plan_source']['sha256']
            or evidence['axis_source_sha256'] != inputs['iso_source']['sha256']):
        raise ValueError('reviewed range and current native drawings differ')
    # Re-run the existing native cross-view owner, not just its old counters.
    from reapply_reviewed_ring_crossview_DN import verify_output as anchor_owner
    anchor_proof = anchor_owner(Path(inputs['anchor_proof']['path']).parent)
    provider = load(inputs['provider']['path']); mapping = provider['ordinary_junction_mappings'][str(manifest['floor'])]
    config_manifest = load(inputs['plan_reader_manifest']['path']); pi = config_manifest['inputs']
    for name, ours in [('source', 'plan_source'), ('current_graph', 'plan_graph')]:
        if pi[name] != inputs[ours]:
            raise ValueError('current native plan owner version differs')
    graphs = {v: load(inputs[v + '_graph']['path']) for v in ('plan', 'iso')}
    docs, preflight = {}, {}
    for v in graphs:
        docs[v], preflight[v] = read_source(inputs[v + '_source']['path'])
    reader = prepare(load(pi['current_T_configuration']['path']), pi['source'], pi['current_graph'],
                     graphs['plan'], pi['owner_transition'])
    records = []
    for spec in manifest['scopes']:
        matched = [r for r in anchor_proof['records'] if r['axis_edge_id'] == spec['iso_bypass']
                   and r['plan_edge_id'] == spec['plan_bypass'] and r['system'] == spec['system']]
        if len(matched) != 1 or matched[0]['floor'] != manifest['floor']:
            raise ValueError('existing source-qualified bypass correspondence required')
        views = {}
        for view, graph in graphs.items():
            boundaries = set(mapping) if view == 'plan' else set(mapping.values())
            views[view] = bounded_alternate(graph, spec[view + '_bypass'], boundaries,
                                            manifest['floor'], spec['system'])
        orient_pair(views, mapping)
        for view, graph in graphs.items():
            row = views[view]; sh, gh = inputs[view + '_source']['sha256'], inputs[view + '_graph']['sha256']
            cov = coverage(docs[view], graph, row['route']['edges'], sh, gh)
            row.update(path_coverage=cov, junctions={}, junction_failures={}, path_failures=[])
            row['path_failures'] = [dict(edge_id=e['edge_id'], status=s['status'])
                for e in cov['edges'] for s in e['segments'] if s['status'] != 'single_source_line_covers']
            row['path_failures'] += copy.deepcopy(cov['unresolved'])
            for nid in row['route']['nodes']:
                try:
                    row['junctions'][nid] = (reader if view == 'plan' else native_tee)(docs[view], graph, nid, sh, gh)
                except ValueError as exc:
                    row['junction_failures'][nid] = str(exc)
        result = qualify(views, answer)
        records.append(dict(scope_id=spec['scope_id'], floor=manifest['floor'], system=spec['system'],
            question_id=manifest['question_id'], answer=copy.deepcopy(answer),
            existing_bypass_mapping_id=matched[0]['mapping_id'], views=views, **result))
    checked()
    return dict(mode=MODE, inputs=inputs, records=records, source_preflight=preflight,
        native_bypass_owner_reexecuted=True, accepted_scope_count=sum(r['status']=='native_bounded_range_correspondence' for r in records),
        held_scope_count=sum(r['status']=='held_local_source_evidence' for r in records),
        graph_mutated=False, DN_values_assigned=0, length_values_assigned=0,
        per_axis_edge_correspondence_assigned=False, human_accepted=False, whole_goal_complete=False)


def implementations():
    names = ['batch_native_main_chains', 'batch_native_path_coverage', 'source_readability',
             'source_stable_junction_reapplication', 'match_source_checked_crossview_paths',
             'crossview_equipment_branch_inventory', 'reapply_reviewed_ring_crossview_DN']
    return dict(entry=sha(__file__), **{n: sha(importlib.import_module(n).__file__) for n in names})


def produce(manifest, output):
    output = Path(output)
    if output.exists(): raise FileExistsError(output)
    code = implementations(); result = compute(load(manifest))
    if code != implementations(): raise ValueError('source implementation changed')
    output.mkdir(parents=True); target = output/'reviewed-expression-scopes.json'; target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE, manifest=dict(path=str(Path(manifest).resolve()), sha256=sha(manifest)),
        implementation_sha256=code, output_sha256=sha(target))))
    return result


def verify_output(output):
    output = Path(output); receipt = load(output/'receipt.json'); target = output/'reviewed-expression-scopes.json'
    if (receipt['mode'] != MODE or receipt['implementation_sha256'] != implementations()
            or sha(receipt['manifest']['path']) != receipt['manifest']['sha256'] or sha(target) != receipt['output_sha256']):
        raise ValueError('reviewed expression receipt differs')
    fresh = compute(load(receipt['manifest']['path']))
    if encode(fresh) != target.read_bytes(): raise ValueError('native expression replay differs')
    return fresh


def main():
    p = argparse.ArgumentParser(); p.add_argument('--manifest', type=Path); p.add_argument('--output', type=Path); p.add_argument('--verify-output', type=Path)
    a = p.parse_args()
    if not a.verify_output and not (a.manifest and a.output): p.error('manifest and fresh output required')
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result = verify_output(a.verify_output) if a.verify_output else produce(a.manifest, a.output)
    print(encode(dict(mode=MODE, accepted_scopes=result['accepted_scope_count'], held_scopes=result['held_scope_count'],
        DN_values_assigned=0, length_values_assigned=0)).decode(), flush=True)


if __name__ == '__main__': main()
