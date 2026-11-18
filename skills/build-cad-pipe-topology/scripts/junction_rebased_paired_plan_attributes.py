"""Recompute paired/interior-T plan DN and XY after native reconstruction."""
import argparse
import copy
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from current_graph_calibrated_dn import control_lineage, collect as calibrated_collect
from match_junction_rebased_paired_paths import MODE as MAPPING_MODE, verify_output as verify_mapping
from paired_plan_DN_scopes import topology_contract
from plan_pipe_diameter_scopes import catalog
from checked_plan_DN_scope_attributes import attribute_checked_scope
from refined_paired_plan_DN_scopes import recompute_groups
from refine_paired_service_path_correspondence import MODE as REFINEMENT_MODE
from qualified_inline_DN_evidence import collect as component_collect
from source_direct_dn_evidence import collect as strict_collect
from source_checked_plan_path_coverage import audit as audit_paths
from native_plan_projection_lengths import unit_evidence, lengths
from source_readability import read_source

MODE = 'junction_rebased_paired_plan_DN_XY_v1'


def seed_reader(doc, graph, original, settings, calibration, selected, source_hash, graph_hash, original_hash):
    """Keep retired seed fragments local; only frontier IDs can be aliased."""
    ancestry = control_lineage(graph, original, calibration, source_hash, graph_hash, original_hash)
    aliases = graph.get('sourceTwoArmCircleContinuity', {}).get('edge_id_aliases', {})
    controls = {r['text_handle']: r for r in calibration['controls']}
    allowed_targets = {r['text_handle']: r for r in calibration['selections']}
    original_seeds, rebased_seeds = {}, {}
    updated = copy.deepcopy(settings)
    for group in updated:
        for spec in group['seeds']:
            prior = copy.deepcopy(spec); current_id = aliases.get(prior['edge_id'], prior['edge_id'])
            if prior['text_handle'] in original_seeds and original_seeds[prior['text_handle']] != prior:
                raise ValueError('Seed text has conflicting original owners')
            original_seeds[prior['text_handle']] = prior
            if current_id != prior['edge_id']:
                lineage = [r for r in ancestry if r['text_handle'] == prior['text_handle']]
                if (prior != controls.get(prior['text_handle']) or len(lineage) != 1
                        or lineage[0]['current_edge_id'] != current_id or current_id in selected):
                    raise ValueError('Retired seed needs an exact original control fragment on a nonselected frontier')
            spec['edge_id'] = current_id; rebased_seeds[prior['text_handle']] = copy.deepcopy(spec)

    def direct(document, current, selection, sh, gh):
        if current is not graph or sh != source_hash or gh != graph_hash:
            raise ValueError('Seed collector cannot switch native graph scope')
        observations = []
        for spec in selection['selections']:
            h = spec['text_handle']; prior = original_seeds.get(h)
            if prior is not None:
                if spec != rebased_seeds[h]: raise ValueError('Current seed differs from exact original configuration')
                if spec['edge_id'] != prior['edge_id']:
                    proof = strict_collect(document, original, dict(selection, graph_sha256=original_hash, selections=[prior]), sh, original_hash)
                    for row in proof['observations']:
                        row['edge_id'] = spec['edge_id']
                        row['current_frontier_seed_fragment'] = dict(original_edge_id=prior['edge_id'], current_edge_id=spec['edge_id'],
                            original_graph_sha256=original_hash, current_graph_sha256=graph_hash,
                            original_native_fragment_replayed=True, current_whole_edge_DN_assigned=False,
                            scope='native_seed_point_for_read_only_frontier_cut_only')
                elif h in allowed_targets:
                    if prior != allowed_targets[h]: raise ValueError('Calibrated target scope differs')
                    proof = calibrated_collect(document, current, original, dict(calibration, selections=[prior]), sh, gh, original_hash)
                else:
                    proof = strict_collect(document, current, dict(selection, selections=[spec]), sh, gh)
            else:
                proof = strict_collect(document, current, dict(selection, selections=[spec]), sh, gh)
            observations.extend(proof['observations'])
        return dict(observations=observations)
    return updated, direct, ancestry


def attribute(doc, graph, original, mapping, settings, calibration, metric_policy, source_hash, graph_hash, original_hash):
    if (mapping.get('mode') != MAPPING_MODE or mapping['plan_graph_sha256'] != graph_hash
            or settings['graph_sha256'] != original_hash or settings['source_sha256'] != source_hash
            or not settings.get('expert_T_inheritance_rule') or metric_policy.get('mapping_sha256') is None):
        raise ValueError('Current paired mapping and original source scope required')
    before = encode(graph); base = mapping['current_native_base_correspondence']; pairs = base['evidence']['paired_services']
    configs = settings['groups']; by = {g['pair_id']: g for g in configs}
    if len(by) != len(configs) or set(by) != {p['pair_id'] for p in pairs}: raise ValueError('Paired DN group coverage differs')
    contracts = {p['pair_id']: topology_contract(doc, graph, p, source_hash, graph_hash, mapping['floor']) for p in pairs}
    ids = [eid for c in contracts.values() for eid in c['main_edges']+[b['edge_id'] for b in c['branches']]]
    if len(ids) != len(set(ids)): raise ValueError('Paired DN base writers overlap')
    configs, direct, ancestry = seed_reader(doc, graph, original, configs, calibration, set(ids), source_hash, graph_hash, original_hash)
    by = {g['pair_id']: g for g in configs}
    texts, inventory = catalog(doc, graph, ids, source_hash, graph_hash); strokes = ()
    if settings.get('qualified_component_DN'):
        qualifier = copy.deepcopy(settings['qualified_component_DN'])
        if qualifier['graph_sha256'] != original_hash or qualifier['source_sha256'] != source_hash: raise ValueError('Component qualifier original source differs')
        qualifier['graph_sha256'] = graph_hash; qualified = component_collect(doc, graph, qualifier, source_hash, graph_hash)
        texts = [t for t in texts if t['handle'] not in set(qualified['consumed_DN_text_handles'])]
        strokes = qualified['consumed_leader_handles']; inventory['qualified_component_DN'] = qualified
    groups = []
    for pair in pairs:
        pid = pair['pair_id']; contract = contracts[pid]; config = by[pid]
        group = dict(group_id=pid, floor=mapping['floor'], main_edges=contract['main_edges'], branches=contract['branches'],
            seeds=config['seeds'], line_F_frames=config.get('line_F_frames', []))
        result = attribute_checked_scope(doc, graph, group, texts, source_hash, graph_hash, set(inventory['F_text_handles']),
            junctions=contract['junctions'], verified_taps=contract['verified_taps'], branch_frontier_edges=contract['branch_frontier_edges'],
            direct_collector=direct, path_auditor=audit_paths, verified_nonpipe_annotation_strokes=strokes)
        result['paired_topology_contract'] = contract; groups.append(result)
    base_DN = dict(source_sha256=source_hash, graph_sha256=graph_hash, groups=groups, records=[r for g in groups for r in g['records']])
    # The current entry uses the same native refinement contract. Adapt only
    # this private classifier tag; all current source witnesses stay intact.
    contract_view = copy.deepcopy(mapping); contract_view['mode'] = REFINEMENT_MODE
    expanded, promotions = recompute_groups(doc, graph, base_DN, contract_view, by, texts, set(inventory['F_text_handles']), direct, strokes)
    dn = {r['edge_id']: r for g in expanded for r in g['records']}
    mapped_ids = [eid for row in mapping['records'] for eid in row['plan_edges']]
    coverage = audit_paths(doc, graph, dict(source_sha256=source_hash, graph_sha256=graph_hash, edges=mapped_ids), source_hash, graph_hash)
    units = unit_evidence(doc, metric_policy); records = []; edges = {e['edge_id']: e for e in graph['edges']}
    for row in mapping['records']:
        if len(row['plan_edges']) != 1: raise ValueError('Paired attribute path requires separately checked DN subdivision')
        value = dn[row['plan_edges'][0]]
        if value['system'] != row['system'] or value['scope_paths'] != edges[value['edge_id']]['attribute_paths']:
            raise ValueError('Paired mapped DN scope changed')
        records.append(dict(mapping_id=row['mapping_id'], kind=row['kind'], floor=row['floor'], system=row['system'],
            plan_edges=list(row['plan_edges']), iso_edges=list(row['iso_edges']), diameter=copy.deepcopy(value),
            horizontal_projection=lengths(graph, coverage, row, units), whole_axis_DN_selected=False,
            whole_axis_physical_length_mm=None, physical_ports_verified=False, human_accepted=False))
    if encode(graph) != before: raise ValueError('Paired source attribute stage mutated local graph')
    return dict(mode=MODE, status='source_checked_current_paired_plan_DN_XY_not_fused', source_sha256=source_hash,
        graph_sha256=graph_hash, original_graph_sha256=original_hash, iso_graph_sha256=mapping['iso_graph_sha256'],
        equipment_scope=mapping['equipment_scope'], context_only_equipment_ids=mapping['context_only_equipment_ids'],
        records=records, diameter_groups=expanded, native_link_scope_extensions=promotions, native_seed_control_lineage=ancestry,
        metric_evidence=units, coverage=coverage, source_annotation_inventory=inventory, local_graphs_mutated=False,
        previous_current_base_DN_records_preserved=True, physical_values_fused=False, installed_lengths_assigned=0, human_accepted=False)


def check_result(data):
    import math
    if (data.get('mode') != MODE or data.get('status') != 'source_checked_current_paired_plan_DN_XY_not_fused'
            or any(data.get(k) is not False for k in ('local_graphs_mutated', 'physical_values_fused', 'human_accepted'))
            or data.get('previous_current_base_DN_records_preserved') is not True or data.get('installed_lengths_assigned') != 0):
        raise ValueError('Unsupported current paired DN/XY scope')
    rows = data['records']; ids = [r['mapping_id'] for r in rows]
    if not rows or len(ids) != len(set(ids)) or not data.get('native_link_scope_extensions'): raise ValueError('Paired path or native link scopes missing')
    for view in ('plan', 'iso'):
        local = [eid for r in rows for eid in r[view+'_edges']]
        if len(local) != len(set(local)): raise ValueError('Paired DN/XY writers overlap')
    for row in rows:
        d, metric = row['diameter'], row['horizontal_projection']
        if (len(row['plan_edges']) != 1 or d['edge_id'] != row['plan_edges'][0] or d['system'] != row['system']
                or d.get('human_accepted') is not False or not metric.get('pieces')
                or metric.get('status') != 'native_plan_horizontal_projection_partial_length'
                or any(row.get(k) is not False for k in ('whole_axis_DN_selected', 'physical_ports_verified', 'human_accepted'))
                or row.get('whole_axis_physical_length_mm') is not None or metric.get('installed_whole_edge_length_mm') is not None
                or metric.get('unshown_connection_length_mm') is not None): raise ValueError('Paired values escaped their plan-source domain')
        value = d['nominal_mm']; length = metric['value_mm']
        if (value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0)
                or isinstance(length, bool) or not isinstance(length, (int, float)) or not math.isfinite(length) or length <= 0):
            raise ValueError('Invalid paired DN/XY value')
    return dict(status='pending', source_replay='passed', mapped_plan_attribute_scopes=len(rows),
        known_DN_scopes=sum(r['diameter']['nominal_mm'] is not None for r in rows), measured_plan_XY_scopes=len(rows),
        native_link_extensions=len(data['native_link_scope_extensions']), graph_sha256=data['graph_sha256'],
        physical_values_fused=False, installed_lengths_assigned=0, human_accepted=False, hil_ready=False,
        pending=['Compose with the complete parent and current corridors; named/legacy scopes, whole network, source comparison, viewer and HIL remain separate'])


def compute(paths, policy):
    for key in ('mapping', 'mapping_receipt', 'original_graph', 'DN_policy', 'calibration', 'metric_policy'):
        if sha(paths[key]) != policy.get(key+'_sha256'): raise ValueError('Paired attribute dependency changed: '+key)
    folder = Path(paths['mapping']).resolve().parent
    if Path(paths['mapping_receipt']).resolve() != folder/'source-mapping-receipt.json' or Path(paths['mapping']).resolve() != folder/'mapping.json':
        raise ValueError('Canonical current paired mapping required')
    mapping = verify_mapping(folder); receipt = load(paths['mapping_receipt']); local = receipt['local_inputs']
    original_hash = sha(paths['original_graph']); settings = load(paths['DN_policy']); calibration = load(paths['calibration']); metric = load(paths['metric_policy'])
    if (mapping['original_plan_graph_sha256'] != original_hash or settings['graph_sha256'] != original_hash
            or settings['calibration_policy_sha256'] != sha(paths['calibration'])
            or settings['mapping_sha256'] != receipt['inputs']['historical_base']['sha256']
            or metric['mapping_sha256'] != receipt['inputs']['historical_refined']['sha256']):
        raise ValueError('Original DN/metric policy belongs to a different source scope')
    for key in ('plan_graph', 'plan_source'):
        if sha(local[key]['path']) != local[key]['sha256']: raise ValueError('Paired attribute native source changed')
    doc, preflight = read_source(local['plan_source']['path'])
    result = attribute(doc, load(local['plan_graph']['path']), load(paths['original_graph']), mapping, settings, calibration, metric,
        local['plan_source']['sha256'], local['plan_graph']['sha256'], original_hash)
    result.update(mapping_sha256=sha(paths['mapping']), source_preflight=preflight)
    check_result(result)
    return result


def implementation_hashes():
    from match_junction_rebased_paired_paths import implementation_hashes as parent_hashes
    from refined_paired_plan_DN_scopes import implementation_hashes as DN_hashes
    result = parent_hashes(); result.update(DN_hashes())
    for name in (Path(__file__).name, 'current_graph_calibrated_dn.py', 'native_plan_projection_lengths.py', 'source_checked_plan_path_coverage.py'):
        result[name] = sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory = Path(directory); receipt = load(directory/'paired-plan-attribute-receipt.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes(): raise ValueError('Current paired attribute implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']: raise ValueError('Current paired attribute input changed')
    paths = {k: v['path'] for k, v in receipt['inputs'].items()}; result = compute(paths, load(paths['policy'])); target = directory/'paired-plan-attributes.json'
    if encode(result) != target.read_bytes() or receipt['output_sha256'] != sha(target): raise ValueError('Current paired attribute native replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in ('mapping-run', 'original-graph', 'DN-policy', 'calibration', 'metric-policy', 'policy', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    a = parser.parse_args(); paths = dict(mapping=a.mapping_run/'mapping.json', mapping_receipt=a.mapping_run/'source-mapping-receipt.json',
        original_graph=a.original_graph, DN_policy=a.DN_policy, calibration=a.calibration, metric_policy=a.metric_policy, policy=a.policy)
    if a.output.exists(): raise FileExistsError(a.output)
    result = compute(paths, load(a.policy)); a.output.mkdir(parents=True); target = a.output/'paired-plan-attributes.json'; target.write_bytes(encode(result))
    (a.output/'paired-plan-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()},
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False)))
    print(check_result(result), flush=True)


if __name__ == '__main__': main()
