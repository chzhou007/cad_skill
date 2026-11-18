"""Replay current context branches and named approaches without whole values."""
import argparse
import copy
import hashlib
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from junction_rebased_paired_plan_attributes import verify_output as verify_paired
from match_named_riser_floor_paths import correspond, vent_normalization, MODE as NAMED_MODE
from native_axis_riser_DN_scopes import verify_output as verify_riser
from native_named_riser_evidence import collect as collect_names
from named_riser_plan_attributes import topology_contract, named_annotation_domain
from checked_plan_DN_scope_attributes import attribute_checked_scope
from plan_pipe_diameter_scopes import catalog
from source_checked_plan_path_coverage import audit as audit_paths
from native_path_coverage_audit import audit as audit_native
from native_plan_projection_lengths import unit_evidence, lengths
from native_segment_dn_candidates import collect as collect_segment_DN
from match_source_checked_crossview_paths import selected_snapshot
from crossview_equipment_branch_inventory import service_route
from source_readability import read_source

MODE = 'current_context_branches_and_named_floor_plan_scopes_v1'


def partial_segment_evidence(graph, coverage, selections):
    """Retain unverified paths while binding only selected native segments."""
    edges = {e['edge_id']: e for e in graph['edges']}; audits = {r['edge_id']: r for r in coverage['edges']}
    rows = []
    for eid in sorted({s['edge_id'] for s in selections}):
        edge = edges[eid]; paths = edge['attribute_paths']; audit = audits[eid]
        if len(paths) != 1 or audit['system'] != edge['system'] or len(audit['segments']) != len(paths[0])-1:
            raise ValueError('Original selected segment path differs from native coverage')
        selected = {s['segment_index'] for s in selections if s['edge_id'] == eid}; segments = []
        for index, segment in enumerate(audit['segments']):
            if segment['index'] != index or paths[0][index:index+2] != [segment['start'], segment['end']]:
                raise ValueError('Native coverage lost original segment indices')
            witnesses = segment.get('witnesses', [])
            unique = segment.get('status') == 'single_source_line_covers' and len(witnesses) == 1 and witnesses[0]['scope'] == 'modelspace'
            if index in selected and not unique: raise ValueError('Selected DN segment has no unique modelspace LINE')
            segments.append(dict(segment_index=index, graph_start=segment['start'], graph_end=segment['end'],
                source_handle=witnesses[0]['source_handle'] if unique else None,
                source_layer=witnesses[0]['layer'] if unique else None,
                status='native_LINE_witness' if unique else 'unverified_retained_not_used_for_DN'))
        if not selected <= set(range(len(segments))): raise ValueError('Selected segment index outside original path')
        rows.append(dict(edge_id=eid, system=edge['system'], segments=segments,
            status='selected_native_segments_only_other_spans_not_accepted'))
    return dict(status='geometry_evidence_unreviewed', source_sha256=coverage['source_sha256'], graph_sha256=coverage['graph_sha256'],
        evidence_mode='native_partial_path_selected_segment_evidence_v1', edges=rows, native_coverage=copy.deepcopy(coverage),
        complete_edge_source_coverage_claimed=False, graph_mutated=False, hil_ready=False)


def check_history(record, previous, current_graphs, original_plan_hash, source_hashes):
    if (previous['source_hashes']['plan_graph'] != original_plan_hash
            or previous['source_hashes']['plan'] != source_hashes['plan']
            or previous['source_hashes']['isometric'] != source_hashes['iso']
            or previous['source_hashes']['local_iso_graph'] != source_hashes['iso_graph']
            or any(previous[k] != record[k] for k in ('floor', 'system', 'plan_edges', 'iso_edges'))):
        raise ValueError('Historical attribute does not identify the same original source path')
    for view in ('plan', 'iso'):
        if not record[view+'_edges'] or len(record[view+'_edges']) != len(set(record[view+'_edges'])):
            raise ValueError('Invalid current approach path')
        selected_snapshot(current_graphs[view], record[view+'_edges'])


def compute(paths, policy):
    for key, path in paths.items():
        if key != 'policy' and sha(path) != policy.get(key+'_sha256'): raise ValueError('Remaining scope input changed: '+key)
    paired_dir = Path(paths['paired_attributes']).resolve().parent
    if (Path(paths['paired_receipt']).resolve() != paired_dir/'paired-plan-attribute-receipt.json'
            or Path(paths['paired_attributes']).resolve() != paired_dir/'paired-plan-attributes.json'): raise ValueError('Canonical paired attribute parent required')
    paired = verify_paired(paired_dir); pr = load(paths['paired_receipt'])
    mp, mrp = pr['inputs']['mapping'], pr['inputs']['mapping_receipt']
    if sha(mp['path']) != mp['sha256'] or sha(mrp['path']) != mrp['sha256']: raise ValueError('Replayed paired mapping changed')
    mapping = load(mp['path']); mr = load(mrp['path']); local = mr['local_inputs']
    corridor_receipt = load(mr['inputs']['corridor_receipt']['path']); inv = corridor_receipt['inputs']['inventory']
    if sha(inv['path']) != inv['sha256']: raise ValueError('Complete replayed inventory changed')
    inventory = load(inv['path']); docs, graphs, hashes = {}, {}, {}
    for view in ('plan', 'iso'):
        for kind in ('source', 'graph'):
            item = local[view+'_'+kind]
            if sha(item['path']) != item['sha256']: raise ValueError('Current local input changed')
        docs[view] = read_source(local[view+'_source']['path'])[0]; graphs[view] = load(local[view+'_graph']['path'])
        hashes[view] = dict(source_sha256=local[view+'_source']['sha256'], graph_sha256=local[view+'_graph']['sha256'])
    graph_before = {v: encode(g) for v, g in graphs.items()}
    original_hash = mapping['original_plan_graph_sha256']; old_named = load(paths['named_history']); named_policy = load(paths['named_policy'])
    if old_named['graph_sha256'] != dict(plan=original_hash, iso=hashes['iso']['graph_sha256']): raise ValueError('Named history uses another source graph')
    riser_dir = Path(paths['riser_scope']).resolve().parent
    if (Path(paths['riser_receipt']).resolve() != riser_dir/'axis-riser-DN-scope-receipt.json'
            or Path(paths['riser_scope']).resolve() != riser_dir/'axis-riser-DN-scopes.json'): raise ValueError('Canonical independently checked riser scope required')
    if sha(paths['riser_scope']) != named_policy['riser_scope_sha256'] or sha(paths['riser_receipt']) != named_policy['riser_receipt_sha256']:
        raise ValueError('Named mapping policy identifies another riser scope')
    riser = verify_riser(riser_dir)
    if riser['graph_sha256'] != hashes['iso']['graph_sha256'] or riser['source_sha256'] != hashes['iso']['source_sha256']: raise ValueError('Named approach uses a different axis riser')
    names = {}
    for view in graphs:
        origin = load(paths[view+'_name_policy']); handles = named_policy['native_label_handles'][view]
        if sha(paths[view+'_name_policy']) != named_policy[view+'_name_policy_sha256'] or origin['source_sha256'] != hashes[view]['source_sha256']:
            raise ValueError('Original named source policy differs')
        selected = [s for s in origin['selections'] if s['text_handle'] in handles]
        if len(selected) != 2 or len(set(handles)) != 2: raise ValueError('Named source label scope differs')
        names[view] = collect_names(docs[view], graphs[view], dict(origin, graph_sha256=hashes[view]['graph_sha256'], selections=selected),
            hashes[view]['source_sha256'], hashes[view]['graph_sha256'])
    named_rows = correspond(docs, graphs, inventory, names, riser, vent_normalization(docs['iso']), named_policy, hashes)
    if len(named_rows) != len(old_named['records']) or len(named_rows) != 2: raise ValueError('Named historical population changed')
    for row, previous in zip(named_rows, old_named['records']):
        for key in ('mapping_id', 'floor', 'system', 'identifier', 'equipment_id', 'plan_edges', 'iso_edges',
                    'plan_riser_interface', 'iso_riser_junction', 'plan_equipment_main_T', 'iso_equipment_main_T'):
            if row[key] != previous[key]: raise ValueError('Named native correspondence changed: '+key)
        for view in graphs:
            if row['paths'][view]['attribute_paths'] != previous['paths'][view]['attribute_paths']: raise ValueError('Named path geometry changed')
    named_mapping = dict(mode=NAMED_MODE, records=named_rows, source_sha256=mapping['source_sha256'],
        graph_sha256={v: h['graph_sha256'] for v, h in hashes.items()}, local_graphs_mutated=False, physical_values_fused=False, human_accepted=False)
    plan = graphs['plan']; sh, gh = hashes['plan']['source_sha256'], hashes['plan']['graph_sha256']
    contract = topology_contract(docs['plan'], plan, named_mapping, sh, gh)
    domain = named_annotation_domain(docs['plan'], plan, named_mapping, sh, gh)
    metric_policy = load(paths['metric_policy'])
    if metric_policy['graph_sha256'] != original_hash or metric_policy['mapping_sha256'] != sha(paths['named_history']): raise ValueError('Original named metric scope differs')
    texts, annotation_inventory = catalog(docs['plan'], plan, contract['main_edges'], sh, gh)
    texts = [t for t in texts if t['handle'] not in set(domain['consumed_text_handles'])]
    dn = attribute_checked_scope(docs['plan'], plan,
        dict(group_id='current_named_approaches', main_edges=contract['main_edges'], branches=[], seeds=metric_policy['seeds'], line_F_frames=[]),
        texts, sh, gh, set(annotation_inventory['F_text_handles']), junctions=contract['junctions'], verified_taps=contract['verified_taps'],
        branch_frontier_edges=contract['branch_frontier_edges'], path_auditor=audit_paths, verified_nonpipe_annotation_strokes=domain['consumed_stroke_handles'])
    values = {r['edge_id']: r for r in dn['records']}
    contexts = mapping['context_only_equipment_ids']; owners = {r['equipment_id']: r for r in inventory['records']}
    branches = []
    for did in contexts:
        matches = [p for p in mapping['current_native_base_correspondence']['evidence']['paired_services'] if did in p['equipment_ids']]
        if len(matches) != 1: raise ValueError('Context equipment has no unique independent pair')
        for system, state in matches[0]['services'].items():
            row = dict(kind='equipment_branch', equipment_id=did, floor=mapping['floor'], system=system)
            for view in graphs:
                route = service_route(graphs[view], did, system); original = owners[did]['views'][view]['services'][system]
                if (original.get('ready_for_mapping_comparison') is not True or route != original['trace']
                        or route['tee'] != state['taps'][view][did] or route['edges'] != state['branches'][view][did]):
                    raise ValueError('Current context service ownership changed')
                row[view+'_edges'] = route['edges']; row[view+'_source_service'] = copy.deepcopy(original)
            branches.append(row)
    paired_DN = {r['edge_id']: r for g in paired['diameter_groups'] for r in g['records']}
    if len(paired_DN) != sum(len(g['records']) for g in paired['diameter_groups']): raise ValueError('Paired DN owners overlap')
    values.update({eid: paired_DN[eid] for r in branches for eid in r['plan_edges']})
    rows = branches+named_rows; ids = [eid for r in rows for eid in r['plan_edges']]
    if len(rows) != 4 or len(ids) != len(set(ids)): raise ValueError('Explicit two context branches and two named approaches required')
    coverage = audit_paths(docs['plan'], plan, dict(source_sha256=sh, graph_sha256=gh, edges=ids), sh, gh)
    units = unit_evidence(docs['plan'], metric_policy)
    historical = load(paths['historical_axis']); old_edges = {e['edge_id']: e for e in historical['edges']}; results = []
    original_plan_spec = pr['inputs']['original_graph']
    if sha(original_plan_spec['path']) != original_hash: raise ValueError('Original plan lineage changed')
    original_plan = load(original_plan_spec['path'])
    sources = dict(plan=sh, iso=hashes['iso']['source_sha256'], iso_graph=hashes['iso']['graph_sha256'])
    selected_writers = {v: {eid for r in mapping['records'] for eid in r[v+'_edges']} for v in graphs}
    for row in rows:
        if len(row['plan_edges']) != 1 or len(row['iso_edges']) != 1: raise ValueError('Remaining path needs explicit per-edge allocation')
        pe, ie = row['plan_edges'][0], row['iso_edges'][0]
        if any(set(row[v+'_edges']) & selected_writers[v] for v in graphs): raise ValueError('Remaining scope overlaps paired writers')
        previous = old_edges[ie]['cross_view_attributes']; check_history(row, previous, graphs, original_hash, sources)
        prior_axis = selected_snapshot(historical, row['iso_edges'])
        for edge in prior_axis['edges']:
            for field in ('cross_view_attributes', 'axis_riser_attributes', 'plan_segment_attributes',
                          'anchored_floor_main_attributes', 'network_named_lower_plan_attributes', 'external_feed_plan_attributes'):
                edge.pop(field, None)
        if prior_axis != selected_snapshot(graphs['iso'], row['iso_edges']):
            raise ValueError('Historical axis local geometry changed')
        if selected_snapshot(original_plan, row['plan_edges']) != selected_snapshot(plan, row['plan_edges']):
            raise ValueError('Historical plan local geometry changed')
        value = values[pe]; edge = next(e for e in plan['edges'] if e['edge_id'] == pe)
        if value['scope_paths'] != edge['attribute_paths'] or value['system'] != row['system']: raise ValueError('Remaining DN source extent changed')
        results.append(dict(mapping_id='CURRENT-'+previous['mapping_id'], historical_mapping_id=previous['mapping_id'],
            kind=row['kind'], floor=row['floor'], system=row['system'], plan_edges=row['plan_edges'], iso_edges=row['iso_edges'],
            diameter=copy.deepcopy(value), horizontal_projection=lengths(plan, coverage, row, units),
            native_correspondence=copy.deepcopy(row), historical_axis_DN_candidate=copy.deepcopy(previous['diameter'].get('axis_observation')),
            whole_axis_DN_selected=False, whole_axis_physical_length_mm=None, physical_ports_verified=False,
            equal_plan_axis_segment_extents_proved=False, human_confirmation_transferred=False, human_accepted=False))
    selected = policy['axis_local_DN_selections']; axis_ids = sorted({s['edge_id'] for s in selected})
    if set(axis_ids) != {r['iso_edges'][0] for r in branches}: raise ValueError('Axis DN candidate selections leave the current context branches')
    axis_coverage = audit_native(docs['iso'], graphs['iso'], dict(source_sha256=hashes['iso']['source_sha256'], graph_sha256=hashes['iso']['graph_sha256'], edges=axis_ids), hashes['iso']['source_sha256'], hashes['iso']['graph_sha256'])
    segment_evidence = partial_segment_evidence(graphs['iso'], axis_coverage, selected)
    segment_hash = hashlib.sha256(encode(segment_evidence)).hexdigest()
    candidates = collect_segment_DN(docs['iso'], graphs['iso'], segment_evidence,
        dict(source_sha256=hashes['iso']['source_sha256'], graph_sha256=hashes['iso']['graph_sha256'],
            line_evidence_sha256=segment_hash, text_layers=policy['axis_DN_text_layers'], selections=selected),
        hashes['iso']['source_sha256'], hashes['iso']['graph_sha256'], segment_hash)
    if any(encode(graphs[v]) != graph_before[v] for v in graphs): raise ValueError('Remaining scope source reading mutated local graphs')
    return dict(mode=MODE, status='current_context_and_named_plan_scopes_source_checked_not_fused', records=results,
        source_sha256=mapping['source_sha256'], graph_sha256={v: h['graph_sha256'] for v, h in hashes.items()},
        paired_parent_sha256=sha(paths['paired_attributes']), named_topology_contract=contract, named_DN_scope=dn,
        named_annotation_domain=domain, current_named_mapping=named_mapping, metric_evidence=units, coverage=coverage,
        axis_selected_segment_evidence=segment_evidence, axis_local_DN_candidates=candidates,
        local_graphs_mutated=False, physical_values_fused=False, whole_axis_DN_assigned=0,
        installed_lengths_assigned=0, human_accepted=False)


def check_result(data):
    import math
    if (data.get('mode') != MODE or data.get('status') != 'current_context_and_named_plan_scopes_source_checked_not_fused'
            or any(data.get(k) is not False for k in ('local_graphs_mutated', 'physical_values_fused', 'human_accepted'))
            or data.get('whole_axis_DN_assigned') != 0 or data.get('installed_lengths_assigned') != 0): raise ValueError('Unsupported remaining scope state')
    rows = data['records']
    if len(rows) != 4 or {r['kind'] for r in rows} != {'equipment_branch', 'named_riser_floor_approach'}: raise ValueError('Both context branches and named approaches required')
    if len({r['mapping_id'] for r in rows}) != 4 or len({r['historical_mapping_id'] for r in rows}) != 4: raise ValueError('Remaining identities repeated')
    for view in ('plan', 'iso'):
        if len({eid for r in rows for eid in r[view+'_edges']}) != 4 or any(len(r[view+'_edges']) != 1 for r in rows): raise ValueError('Remaining local writers overlap')
    for row in rows:
        d, metric = row['diameter'], row['horizontal_projection']
        if (d['edge_id'] != row['plan_edges'][0] or d['system'] != row['system'] or not d.get('lineage')
                or any(row.get(k) is not False for k in ('whole_axis_DN_selected', 'physical_ports_verified', 'equal_plan_axis_segment_extents_proved', 'human_confirmation_transferred', 'human_accepted'))
                or row.get('whole_axis_physical_length_mm') is not None or metric.get('installed_whole_edge_length_mm') is not None
                or metric.get('unshown_connection_length_mm') is not None or not metric.get('pieces')): raise ValueError('Remaining source values escaped their physical scope')
        for value in (d['nominal_mm'], metric['value_mm']):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0: raise ValueError('Remaining DN/XY is not known positive source evidence')
    candidates = data['axis_local_DN_candidates']
    if candidates.get('status') != 'segment_candidates_not_accepted' or candidates.get('graph_mutated') is not False: raise ValueError('Local axis candidates cannot become whole DN')
    return dict(status='pending', source_replay='passed', mapped_plan_attribute_scopes=4, known_DN_scopes=4, measured_plan_XY_scopes=4,
        native_axis_local_DN_candidates=len(candidates['observations']), physical_values_fused=False, whole_axis_DN_assigned=0,
        installed_lengths_assigned=0, human_accepted=False, hil_ready=False,
        pending=['Axis candidate extents are not resolved by plan-source priority; compose full parent, source comparison, viewer and HIL separately'])


def implementation_hashes():
    from junction_rebased_paired_plan_attributes import implementation_hashes as paired_hashes
    from named_riser_plan_attributes import implementation_hashes as named_hashes
    result = paired_hashes(); result.update(named_hashes())
    for name in (Path(__file__).name, 'native_segment_dn_candidates.py'):
        result[name] = sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory = Path(directory); receipt = load(directory/'remaining-scope-receipt.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes(): raise ValueError('Remaining scope implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']: raise ValueError('Remaining scope input changed')
    paths = {k: v['path'] for k, v in receipt['inputs'].items()}; result = compute(paths, load(paths['policy'])); check_result(result)
    target = directory/'remaining-plan-scopes.json'
    if encode(result) != target.read_bytes() or receipt['output_sha256'] != sha(target): raise ValueError('Remaining scope independent native replay differs')
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--policy', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args(); policy = load(a.policy); paths = {k: Path(v['path']) for k, v in policy['inputs'].items()}; paths['policy'] = a.policy
    if a.output.exists(): raise FileExistsError(a.output)
    if any(sha(v['path']) != v['sha256'] for v in policy['inputs'].values()): raise ValueError('Remaining scope policy input hash differs')
    result = compute(paths, policy); check_result(result); a.output.mkdir(parents=True); target = a.output/'remaining-plan-scopes.json'; target.write_bytes(encode(result))
    (a.output/'remaining-scope-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()},
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False)))
    print(check_result(result), flush=True)


if __name__ == '__main__': main()
