"""Apply expert-bounded main partitions through the unchanged plan DN kernel.

Expert scope boundaries are evidence, not native TEXT and not a room-count
formula. All old annotation/F, T, source-path and branch-default rules remain.
"""
import argparse, copy, importlib, math, re, sys
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from legacy_named_provider_inventory import require, current_plan_reader
from source_readability import read_source
from current_junction_plan_DN import collect, preserve_known
from rebuild_inherited_full_plan_DN import configuration, implementation_hashes as original_hashes
from source_stable_junction_reapplication import prepare, unchanged_star
from projected_circle_plan_DN import infer
from batch_native_path_coverage import collect as coverage

MODE = 'native_reviewed_ring_main_partition_DN_v1'


def declared_values(message):
    """Read the explicit two values; never derive DN from room/equipment count."""
    require(isinstance(message, str) and '\ufffd' not in message, 'readable explicit expert message required')
    start, end = message.find('上'), message.find('下')
    require(0 <= start < end, 'explicit upper and lower scope clauses required')
    values = {}
    for side, clause in [('upper', message[start:end]), ('lower', message[end:])]:
        hits = re.findall(r'(?:DN\s*([1-9][0-9]*)|([1-9][0-9]*)\s*DN)', clause, re.I)
        require(len(hits) == 1, 'one explicit DN required for each reviewed main partition')
        values[side] = int(hits[0][0] or hits[0][1])
    return values


def add_partition_seeds(graph, baseline, policy, values):
    """Bind each main arm to its actual source T and declared side extent."""
    edges = {e['edge_id']: e for e in graph['edges']}
    nodes = {n['node_id']: n for n in graph['nodes']}
    rows = {r['edge_id']: r for r in baseline['records']}
    direction = policy['upper_direction_WCS']
    require(len(direction) == 2 and all(isinstance(x, (float, int)) and not isinstance(x, bool)
            and math.isfinite(x) for x in direction) and math.hypot(*direction) > 0,
            'explicit finite source-view partition direction required')
    direction = [v / math.hypot(*direction) for v in direction]
    seeds = copy.deepcopy(baseline['direct_seed_evidence'])
    direct = {s['edge_id'] for s in seeds}
    selected = {}
    for system, spec in policy['systems'].items():
        require(system in ('supply', 'return'), 'unknown reviewed pipe system')
        nid = spec['boundary_T']; node = nodes[nid]
        require(node['system'] == system and node.get('node_type') in ('tee', 'physical_junction')
                and node.get('review_required') is not True and nid in baseline['roles'],
                'reviewed main boundary needs an original proved same-system T')
        role = baseline['roles'][nid]
        require(set(role['through']) == {spec['upper_entry'], spec['lower_entry']},
                'expert partition does not bound the two actual through-main arms')
        for side, sign in [('upper', 1), ('lower', -1)]:
            ids = spec[side + '_edges']; entry = spec[side + '_entry']
            require(ids and len(set(ids)) == len(ids) and entry in ids,
                    'unique source main scope and incident entry required')
            reached = {nid}; remaining = set(ids)
            while remaining:
                connected = [eid for eid in remaining if {edges[eid]['start_node_id'], edges[eid]['end_node_id']} & reached]
                require(connected, 'reviewed main partition is disconnected from its source boundary')
                for eid in connected:
                    reached.update([edges[eid]['start_node_id'], edges[eid]['end_node_id']]); remaining.remove(eid)
            for eid in ids:
                edge, row = edges[eid], rows[eid]
                require(eid not in selected and eid not in direct and edge['system'] == system
                        and row['status'] == 'conflict' and row['nominal_mm'] is None
                        and values[side] in {l['nominal_mm'] for l in row['lineage']},
                        'reviewed main value conflicts with direct source evidence or another scope')
                origin = [node['x'], node['y']]
                offsets = [sign * sum((p[i] - origin[i]) * direction[i] for i in (0, 1))
                           for path in edge['attribute_paths'] for p in path]
                require(offsets and min(offsets) >= -.05 and max(offsets) > .05,
                        'main path crosses the declared partition boundary or lies on an unproved side')
                require({edge['start_node_id'], edge['end_node_id']} <= baseline['native_current_T_evidence'].keys(),
                        'both original main endpoints need native T evidence')
                selected[eid] = dict(side=side, boundary_T=nid, nominal_mm=values[side], system=system)
                seeds.append(dict(edge_id=eid, nominal_mm=values[side],
                    evidence_id='reviewed-main-partition:' + policy['scope_id'] + ':' + eid,
                    source_kind='explicit_expert_main_partition_boundary_not_native_TEXT'))
    require(set(policy['systems']) == {'supply', 'return'}, 'complete independent supply and return scope required')
    return seeds, selected


def compute(manifest):
    inputs = manifest['inputs']
    def checked():
        require(all(sha(v['path']) == v['sha256'] for v in inputs.values()), 'reviewed ring input changed')
    checked()
    receipt = load(inputs['expert_receipt']['path'])
    require(receipt['mode'] == 'explicit_user_annotated_plan_main_partition_receipt_v1'
            and receipt['DN_values_assigned'] == 0 and receipt['human_accepted'] is False,
            'original explicit expert scope receipt required')
    received = receipt['records']
    require({r['question_id'] for r in received} == set(manifest['question_ids']), 'reviewed question cohort differs')
    messages = {r['source_message_verbatim'] for r in received}
    require(len(messages) == 1, 'reviewed partition message differs between systems')
    values = declared_values(next(iter(messages)))
    allowed = set()
    for row in received:
        answer = row['explicit_answer']
        require(answer['comment'] == row['source_message_verbatim']
                and answer['decision'] == '按不同区段／变径边界，见说明'
                and answer['source_pair_sha256'] == row['pair_sha256'], 'explicit original partition answer differs')
        require(sha(Path(manifest['page_root']) / manifest['pair_paths'][row['question_id']]) == row['pair_sha256'],
                'original source review Pair changed')
        for image in row['source_images']:
            require(sha(image['archived']['path']) == image['archived']['sha256'], 'original expert annotated image changed')
        allowed.update(row['source_evidence']['source_plan_edges'])
    original = load(inputs['original_DN']['path'])
    original_receipt = load(inputs['original_DN_receipt']['path'])
    require(original_receipt['output_sha256'] == inputs['original_DN']['sha256']
            and original_receipt['manifest']['sha256'] == inputs['original_DN_manifest']['sha256']
            and original_receipt['implementation_sha256'] == original_hashes(), 'original complete DN source owner changed')
    old_manifest = load(inputs['original_DN_manifest']['path'])
    item = next(x for x in old_manifest['plans'] if x['floor'] == manifest['floor'])
    require(item['inputs']['source'] == inputs['source'] and item['inputs']['graph'] == inputs['original_graph'],
            'original complete DN source/graph version differs')
    old, current = load(inputs['original_graph']['path']), load(inputs['current_graph']['path'])
    sh, gh, ch = inputs['source']['sha256'], inputs['original_graph']['sha256'], inputs['current_graph']['sha256']
    doc, readable = read_source(inputs['source']['path'])
    config = load(inputs['current_T_configuration']['path'])
    baseline = collect(doc, old, original['floors'][str(manifest['floor'])], sh, gh,
                       current_plan_reader(config, sh, gh), configuration(item))
    seeds, selected = add_partition_seeds(old, baseline, manifest['partition_policy'], values)
    require(set(selected) <= allowed, 'selected main escapes the expert-reviewed source extent')
    eligible = {eid for eid, p in baseline['source_path_evidence'].items()
                if p['edges'] and all(s['status'] == 'single_source_line_covers'
                for e in p['edges'] for s in e['segments'])} - set(baseline['annotation_barriers'])
    after = infer(old, seeds, eligible, baseline['native_current_T_evidence'], sh, gh)
    preserve_known(baseline, after['records'])
    previous = {r['edge_id']: r for r in baseline['records']}
    changed = [r for r in after['records'] if r['nominal_mm'] != previous[r['edge_id']]['nominal_mm']]
    require(changed and {r['edge_id'] for r in changed} <= allowed,
            'reviewed boundary changes an unreviewed DN scope')
    require(all(next(r for r in changed if r['edge_id'] == eid)['nominal_mm'] == v['nominal_mm']
                for eid, v in selected.items()), 'reviewed main values were not applied by the inherited kernel')
    reader = prepare(config, inputs['source'], inputs['current_graph'], current, inputs['owner_transition'])
    old_edges = {e['edge_id']: e for e in old['edges']}
    now = {e['edge_id']: e for e in current['edges']}
    records = []
    for row in changed:
        eid = row['edge_id']; require(old_edges[eid] == now[eid], 'affected current source edge changed')
        cov = coverage(doc, current, [eid], sh, ch)
        require(not cov['unresolved'] and all(s['status'] == 'single_source_line_covers'
                for e in cov['edges'] for s in e['segments']), 'affected source path is not uniquely witnessed')
        native = {}
        for nid in (now[eid]['start_node_id'], now[eid]['end_node_id']):
            node = next(n for n in current['nodes'] if n['node_id'] == nid)
            if node.get('node_type') in ('tee', 'physical_junction'):
                unchanged_star(old, current, nid)
                native[nid] = reader(doc, current, nid, sh, ch)
        record = copy.deepcopy(row)
        record.update(kernel_status=row['status'], status='expert_reviewed_main_partition_DN' if eid in selected
            else 'native_T_branch_DN_inherited_after_reviewed_main_partition',
            value_origin='explicit_reviewed_main_boundary_not_native_TEXT' if eid in selected else 'original_native_branch_default_kernel',
            original_conflict=copy.deepcopy(previous[eid]), current_native_path=cov, current_native_T=native,
            reviewed_main_scope=selected.get(eid), physical_reducer_position=None, physical_length_mm=None,
            source_graph_mutated=False, human_accepted=False)
        records.append(record)
    checked()
    return dict(mode=MODE, inputs=inputs, records=records, source_preflight=readable, declared_values=values,
        baseline_native_floor=baseline, after_inherited_kernel=after, reviewed_main_scopes=selected,
        scope_id=manifest['partition_policy']['scope_id'], question_ids=manifest['question_ids'],
        complete_original_floor_annotation_T_and_path_readers_reapplied=True, all_old_known_plan_DN_preserved=True,
        source_graphs_mutated=False, room_count_used_to_calculate_DN=False, new_native_TEXT_invented=False,
        physical_reducer_positions_invented=False, physical_lengths_assigned=0, axis_values_assigned=0,
        counts=dict(selected_main_edges=len(selected), inherited_branch_edges=len(records)-len(selected),
            new_local_plan_DN=len(records), previous_known_plan_DN=baseline['counts']['known_DN'],
            current_known_plan_DN=sum(r['nominal_mm'] is not None for r in after['records'])),
        human_accepted=False, whole_goal_complete=False)


def implementations():
    names = ('current_junction_plan_DN', 'projected_circle_plan_DN', 'full_plan_DN_inheritance',
             'source_stable_junction_reapplication', 'batch_native_path_coverage', 'source_readability')
    result = original_hashes()
    result.update({name: sha(importlib.import_module(name).__file__) for name in names})
    result['reviewed_ring_main_partition'] = sha(__file__)
    return result


def produce(manifest, output):
    output = Path(output); require(not output.exists(), 'fresh partition output required')
    code = implementations(); proof = compute(load(manifest))
    require(code == implementations(), 'partition source implementation changed')
    output.mkdir(parents=True); p = output / 'reviewed-ring-plan-DN.json'; p.write_bytes(encode(proof))
    (output / 'receipt.json').write_bytes(encode(dict(mode=MODE, manifest=dict(path=str(Path(manifest).resolve()), sha256=sha(manifest)),
        implementation_sha256=code, output_sha256=sha(p))))
    return proof


def verify_output(output):
    output = Path(output); r = load(output / 'receipt.json'); p = output / 'reviewed-ring-plan-DN.json'
    require(r['mode'] == MODE and r['implementation_sha256'] == implementations()
            and sha(r['manifest']['path']) == r['manifest']['sha256'] and sha(p) == r['output_sha256'],
            'reviewed ring source receipt changed')
    proof = compute(load(r['manifest']['path']))
    require(encode(proof) == p.read_bytes(), 'independent native ring partition replay differs')
    return proof


def main():
    p = argparse.ArgumentParser()
    for k in ('manifest', 'output', 'verify-output'): p.add_argument('--' + k, type=Path)
    a = p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        proof = verify_output(a.verify_output) if a.verify_output else produce(a.manifest, a.output)
    print(proof['counts'], flush=True)


if __name__ == '__main__': main()
