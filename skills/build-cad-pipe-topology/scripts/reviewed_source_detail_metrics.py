"""Reuse native T/path/metric owners after scoped component-expression feedback.

Unchanged complete-parent proofs are retained as lineage. Every selected
correspondence, native valve and centreline is freshly checked here; this is not
a claim that the entire older parent pipeline was rerun.
"""
import argparse, copy, importlib, sys
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from legacy_named_provider_inventory import require
from third_arm_crossview_paths import discover, prove, native_component_profiles
from rebuild_third_arm_crossview_batch import csvrows, implementation_hashes as parent_hashes
from source_readability import read_source
from cycle_gate_plan_lengths import qualify
from native_plan_projection_lengths import unit_evidence

MODE = 'reviewed_native_source_detail_plan_metrics_v1'


def authorize(receipt, question_id, accepted_decision, source_records):
    require(accepted_decision == '平面省略，实物按轴测两阀',
            'this owner supports only the explicit plan-omission/two-axis-valve policy')
    answers = [r for r in receipt['records'] if r['question_id'] == question_id]
    require(len(answers) == 1, 'one received source-scope answer required')
    answer = answers[0]
    require(answer['explicit_answer']['decision'] == accepted_decision,
            'expert did not choose the declared source-detail policy')
    require(answer['explicit_answer']['source_pair_sha256'] == answer['pair_sha256'],
            'expert answer belongs to another Pair')
    ev = answer['source_evidence']
    require(len(source_records) > 0
            and len({r['axis_edge_id'] for r in source_records}) == len(source_records)
            and set(ev['related_current_axis_edges']) == {r['axis_edge_id'] for r in source_records}
            and set(ev['source_plan_edges']) == {r['plan_edge_id'] for r in source_records},
            'expert scope and native mapping cohort differ')
    require(all(r['source_detail_difference'] is True
                and r['component_profiles']['plan'].keys() == {'ball_valve'}
                and r['component_profiles']['iso'].keys() == {'ball_valve'}
                and r['component_profiles']['plan']['ball_valve'] == 1
                and r['component_profiles']['iso']['ball_valve'] == 2 for r in source_records),
            'confirmed plan omission does not describe these native components')
    require(sum(r['component_profiles']['plan']['ball_valve'] for r in source_records)
            == ev['plan_native_ball_instances']
            and sum(r['component_profiles']['iso']['ball_valve'] for r in source_records)
            == ev['axis_native_ball_instances'], 'source component population changed')
    return copy.deepcopy(answer)


def compute(manifest):
    inputs = manifest['inputs']
    def checked():
        require(all(sha(v['path']) == v['sha256'] for v in inputs.values()),
                'reviewed detail input changed')
    checked()
    parent_receipt = load(inputs['third_arm_receipt']['path'])
    require(parent_receipt['implementation_sha256'] == parent_hashes(),
            'original native third-arm owner changed')
    require(parent_receipt['output_sha256']['third-arm-batch.json']
            == inputs['third_arm_proof']['sha256'], 'original native source proof changed')
    original = load(inputs['third_arm_proof']['path'])
    selected = original['records']
    receipt = load(inputs['answer_receipt']['path'])
    require(receipt['mode'] == 'version_bound_current_review_answer_intake_v1',
            'version-bound answer intake required')
    # Re-run the intake against the preserved raw export, not a saved status flag.
    visual = Path(__file__).resolve().parents[2] / 'visualize-cad-pipe-topology/scripts'
    sys.path.insert(0, str(visual))
    try:
        from receive_current_review_answers import receive, load as load_review
        _, checked_answers = receive(load_review(receipt['inputs']['definitions']['path']),
            load_review(receipt['inputs']['reply']['path']), manifest['page_root'],
            [r['question_id'] for r in receipt['records']])
        require(checked_answers['records'] == receipt['records'], 'received answer replay differs')
        require(all(sha(v['path']) == v['sha256'] for v in receipt['inputs'].values()),
                'raw answer or original definitions changed')
    finally:
        sys.path.pop(0)
    answer = authorize(receipt, manifest['question_id'], manifest['accepted_decision'], selected)
    floor = manifest['floor']
    require(all(r['floor'] == floor for r in selected), 'mixed source floors need separate metric runs')
    graphs = {v: load(inputs[k]['path']) for v, k in [('plan', 'plan_graph'), ('iso', 'axis_graph')]}
    docs, readable, hashes = {}, {}, {}
    for v, prefix in [('plan', 'plan'), ('iso', 'axis')]:
        docs[v], readable[v] = read_source(inputs[prefix + '_source']['path'])
        hashes[v] = dict(source_sha256=inputs[prefix + '_source']['sha256'],
                         graph_sha256=inputs[prefix + '_graph']['sha256'])
        for suffix in ('source', 'graph'):
            key = prefix + '_' + suffix + ('_' + str(floor) if v == 'plan' else '')
            require(inputs[prefix + '_' + suffix] == original['inputs'][key],
                    'current source scope differs from the reviewed native topology')
    legacy = load(original['inputs']['parent_provider']['path'])
    require(sha(original['inputs']['parent_provider']['path'])
            == original['inputs']['parent_provider']['sha256'], 'original anchor provider changed')
    components = dict(plan=csvrows(inputs['plan_components']['path']),
                      iso=csvrows(inputs['axis_components']['path']))
    candidates, _ = discover(graphs, legacy, floor, components)
    wanted = {r['axis_edge_id'] for r in selected}
    candidates = [r for r in candidates if r['axis_edge_id'] in wanted]
    require({r['axis_edge_id'] for r in candidates} == wanted, 'current native third-arm discovery differs')
    profiles = {v: native_component_profiles(docs[v], graphs[v], components[v],
                [r[key] for r in candidates], v) for v, key in [('plan', 'plan_edge_id'), ('iso', 'axis_edge_id')]}
    config = load(inputs['current_T_source_config']['path'])
    fresh = [prove(r, graphs, docs, legacy, hashes, config, components,
                   manifest['horizontal_directions_degrees'], profiles) for r in candidates]
    require(sorted(fresh, key=lambda r: r['mapping_id']) == sorted(selected, key=lambda r: r['mapping_id']),
            'fresh scoped native T/path/component proof differs from the reviewed mapping')
    current = load(inputs['current_provider']['path'])
    observed = {r['edge_id']: r for r in current['records']}
    frontier = {r['edge_id']: r for r in current['remaining_horizontal_attributes']}
    units = unit_evidence(docs['plan'], load(inputs['unit_policy']['path']))
    records = []
    for row in fresh:
        eid = row['axis_edge_id']
        require(eid in frontier and frontier[eid]['complete_centerline'] is False,
                'new metric would replace a prior complete length')
        matches = [o for o in observed[eid]['correspondence_observations']
                   if o['mapping_id'] == row['mapping_id'] and o['plan_edges'] == row['plan_edges']
                   and o.get('grouped_axis_edges') == row['iso_edges']]
        require(len(matches) == 1 and matches[0].get('source_detail_difference') is True,
                'current provider does not retain the reviewed native correspondence')
        spec = dict(row, classification='horizontal_only', iso_start=row['axis_anchor'],
                    iso_end=row['axis_remote'], native_path_evidence=dict(plan=row['native_proofs']['plan']['native_path']))
        metric = qualify(graphs['plan'], graphs['iso'], spec, units,
                         manifest['horizontal_directions_degrees'])
        records.append(dict(metric, source_scope_id='REVIEWED-DETAIL-METRIC:' + row['mapping_id'],
            original_observation=copy.deepcopy(matches[0]), original_correspondence=copy.deepcopy(row),
            source_detail_resolution=dict(question_id=manifest['question_id'], answer=answer['explicit_answer'],
                pair_sha256=answer['pair_sha256'], answer_receipt_sha256=inputs['answer_receipt']['sha256'],
                policy='plan_omits_axis_component_detail', physical_ball_valve_count=row['component_profiles']['iso']['ball_valve'],
                source_instances_retained=True, crossview_components_merged=False, plan_valve_positions_invented=False),
            plan_source_sha256=hashes['plan']['source_sha256'], plan_graph_sha256=hashes['plan']['graph_sha256'],
            axis_source_sha256=hashes['iso']['source_sha256'], native_axis_graph_sha256=hashes['iso']['graph_sha256'],
            DN_evidence_changed=False, related_HIL_confirmation_inherited=False))
    checked()
    return dict(mode=MODE, inputs=inputs, records=records, source_preflight=readable, units=units,
        native_component_profiles=profiles, unchanged_parent_artifacts_retained_as_lineage=True,
        complete_parent_pipeline_rerun_claimed=False, reviewed_scope_native_T_paths_and_components_replayed=True,
        original_metric_readers_reused=True, source_graphs_mutated=False, component_owners_changed=False,
        DN_values_assigned=0, vertical_values_assigned=0, installed_lengths_assigned=0,
        counts=dict(reviewed_source_intervals=len(fresh), complete_horizontal_centerlines=len(records)),
        human_accepted=False, whole_goal_complete=False)


def implementations():
    result = parent_hashes()
    result.update({n: sha(importlib.import_module(n).__file__) for n in
                   ('cycle_gate_plan_lengths', 'native_plan_projection_lengths', 'native_main_endpoint_extent')})
    result['reviewed_source_detail_metrics'] = sha(__file__)
    result['receive_current_review_answers'] = sha(Path(__file__).resolve().parents[2]
        / 'visualize-cad-pipe-topology/scripts/receive_current_review_answers.py')
    return result


def produce(manifest_path, output):
    output = Path(output)
    require(not output.exists(), 'fresh reviewed-detail output required')
    code = implementations()
    proof = compute(load(manifest_path))
    require(code == implementations(), 'native detail implementation changed')
    output.mkdir(parents=True)
    path = output / 'reviewed-detail-plan-metrics.json'
    path.write_bytes(encode(proof))
    (output / 'receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(Path(manifest_path).resolve()), sha256=sha(manifest_path)),
        implementation_sha256=code, output_sha256=sha(path))))
    return proof


def verify_output(output):
    output = Path(output)
    receipt = load(output / 'receipt.json')
    path = output / 'reviewed-detail-plan-metrics.json'
    require(receipt['mode'] == MODE and receipt['implementation_sha256'] == implementations()
            and sha(receipt['manifest']['path']) == receipt['manifest']['sha256']
            and sha(path) == receipt['output_sha256'], 'reviewed metric receipt changed')
    proof = compute(load(receipt['manifest']['path']))
    require(encode(proof) == path.read_bytes(), 'independent native reviewed metric replay differs')
    return proof


def main():
    p = argparse.ArgumentParser()
    for key in ('manifest', 'output', 'verify-output'):
        p.add_argument('--' + key, type=Path)
    a = p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        proof = verify_output(a.verify_output) if a.verify_output else produce(a.manifest, a.output)
    print(proof['counts'], flush=True)


if __name__ == '__main__':
    main()
