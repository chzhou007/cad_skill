"""Rebuild paired-service and interior-T paths on the latest native plan.

Reuse the frozen pair/branch-target kernels. Historical paths are compared
only after native reconstruction; their receipts are never grafted forward.
"""
import argparse
import copy
import re
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from match_junction_rebased_corridors import MODE as CORRIDOR_MODE, verify_output as verify_corridors
from match_paired_service_crossview_paths import pair_paths, MODE as BASE_MODE
from match_source_checked_crossview_paths import selected_snapshot
from native_paired_junction_correspondence import collect
from native_path_coverage_audit import audit as audit_paths
from refine_paired_service_path_correspondence import refine
from source_readability import read_source

MODE = 'junction_rebased_paired_native_paths_v1'


def preserve_history(current, previous, original_plan_hash):
    if (previous.get('plan_graph_sha256') != original_plan_hash or previous.get('iso_graph_sha256') != current['iso_graph_sha256']
            or previous.get('source_sha256') != current['source_sha256'] or previous.get('floor') != current['floor']
            or previous.get('equipment_scope') != current['equipment_scope']
            or previous.get('context_only_equipment_ids') != current['context_only_equipment_ids']):
        raise ValueError('Historical paired source, owner or floor differs')
    old = {r['mapping_id']: r for r in previous['records']}; new = {r['mapping_id']: r for r in current['records']}
    if len(old) != len(previous['records']) or len(new) != len(current['records']) or old.keys() != new.keys():
        raise ValueError('Historical paired paths lost or repeated')
    fields = ('kind', 'system', 'floor', 'equipment_id', 'endpoint_equipment_ids', 'context_equipment_ids',
        'parent_pair_id', 'target_pair_id', 'target_equipment_id', 'junction_correspondence_ids',
        'plan_edges', 'iso_edges', 'plan_start', 'plan_end', 'iso_start', 'iso_end', 'plan_snapshot', 'iso_snapshot')
    for key, row in new.items():
        if any(row.get(k) != old[key].get(k) for k in fields):
            raise ValueError('Historical paired path needs explicit reconciliation: '+key)


def reconstruct(docs, graphs, inventory, old_base, old_refined, settings, refinement, hashes, original_plan_hash):
    pairs, floor = settings['equipment_pairs'], settings['floor']
    reference = settings.get('context_only_equipment_ids', [])
    selected = [did for pair in pairs for did in pair]
    if (not pairs or type(floor) is not int or any(len(p) != 2 for p in pairs)
            or len(selected) != len(set(selected)) or len(reference) != len(set(reference))
            or not set(reference) <= set(selected) or any(set(p) <= set(reference) for p in pairs)):
        raise ValueError('Explicit independent paired equipment scope required')
    by = {r['equipment_id']: r for r in inventory['records']}
    if len(by) != len(inventory['records']): raise ValueError('Duplicate inventory equipment')
    records, checks = [], []
    for index, pair in enumerate(pairs, 1):
        services = pair_paths(docs, graphs, by, pair, floor, hashes)
        checks.append(dict(pair_id=f'P{index:02d}', equipment_ids=pair, services=services))
        for system, state in services.items():
            for did in pair:
                if did in reference: continue
                records.append(dict(kind='equipment_branch', equipment_id=did, system=system, floor=floor,
                    plan_edges=state['branches']['plan'][did], iso_edges=state['branches']['iso'][did],
                    plan_start=state['taps']['plan'][did], iso_start=state['taps']['iso'][did], plan_end=did, iso_end=did,
                    local_evidence={v: by[did]['views'][v]['services'][system] for v in graphs}))
            records.append(dict(kind='main_between_equipment_branches', endpoint_equipment_ids=pair, system=system, floor=floor,
                plan_edges=state['routes']['plan']['edges'], iso_edges=state['routes']['iso']['edges'],
                plan_start=state['taps']['plan'][pair[0]], plan_end=state['taps']['plan'][pair[1]],
                iso_start=state['taps']['iso'][pair[0]], iso_end=state['taps']['iso'][pair[1]]))
    for index, row in enumerate(records, 1):
        row.update(mapping_id=f'PS-{index:04d}', physical_ports_verified=False, human_accepted=False)
        for view in graphs: row[view+'_snapshot'] = selected_snapshot(graphs[view], row[view+'_edges'])
    base = dict(mode=BASE_MODE, records=records, equipment_scope=selected, context_only_equipment_ids=reference, floor=floor,
        plan_graph_sha256=hashes['plan']['graph_sha256'], iso_graph_sha256=hashes['iso']['graph_sha256'],
        source_sha256={v: h['source_sha256'] for v, h in hashes.items()}, evidence=dict(paired_services=checks),
        local_graphs_mutated=False, expert_confirmation_claimed=False, human_accepted=False, hil_ready=False)
    preserve_history(base, old_base, original_plan_hash)
    proof = collect(docs, graphs, base, hashes)
    result = refine(base, proof, graphs, refinement['required_groups'])
    preserve_history(result, old_refined, original_plan_hash)
    coverage = {}
    for view in graphs:
        ids = [eid for r in result['records'] if r['kind'] != 'equipment_branch' for eid in r[view+'_edges']]
        coverage[view] = audit_paths(docs[view], graphs[view], dict(hashes[view], edges=ids), hashes[view]['source_sha256'], hashes[view]['graph_sha256'])
        if any(s['status'] != 'single_source_line_covers' for e in coverage[view]['edges'] for s in e['segments']):
            raise ValueError('Current paired main lacks unique native coverage')
    result['evidence']['refined_main_coverage'] = coverage
    return base, result


def check_result(data):
    if (data.get('mode') != MODE or data.get('status') != 'source_checked_current_paired_junction_paths_attributes_pending'
            or any(data.get(k) is not False for k in ('local_graphs_mutated', 'physical_values_fused', 'expert_confirmation_claimed', 'human_accepted', 'hil_ready'))
            or data.get('physical_values_assigned') != 0 or data.get('whole_floor_connectivity_confirmed') is not False):
        raise ValueError('Unsupported current paired correspondence state')
    rows = data['records']; lineage = data['historical_mapping_lineage']; base = data['current_native_base_correspondence']
    expected = {(d, s) for d in data['equipment_scope'] if d not in data['context_only_equipment_ids'] for s in ('supply', 'return')}
    branches = [r for r in rows if r['kind'] == 'equipment_branch']
    if (not rows or len({r['mapping_id'] for r in rows}) != len(rows) or len(lineage) != len(rows)
            or {r['current_mapping_id'] for r in lineage} != {r['mapping_id'] for r in rows}
            or len({r['previous_mapping_id'] for r in lineage}) != len(rows)
            or any(r.get('local_paths_and_snapshots_preserved') is not True or r.get('human_confirmation_transferred') is not False for r in lineage)
            or len(branches) != len(expected) or {(r['equipment_id'], r['system']) for r in branches} != expected
            or any(base.get(k) != data.get(k) for k in ('equipment_scope', 'context_only_equipment_ids', 'floor', 'source_sha256', 'plan_graph_sha256', 'iso_graph_sha256'))):
        raise ValueError('Current paired scope or historical lineage is incomplete')
    for view in ('plan', 'iso'):
        ids = [eid for r in rows for eid in r[view+'_edges']]
        if len(ids) != len(set(ids)): raise ValueError('Repeated paired local writer')
    for row in rows:
        if (row.get('floor') != data['floor'] or row.get('system') not in ('supply', 'return')
                or row.get('physical_ports_verified') is not False or row.get('human_accepted') is not False):
            raise ValueError('Paired path changed floor, service or physical acceptance')
    return dict(status='pending', path_correspondence='native_current_paired_service_and_branch_target_junctions_replayed',
        mapped_paths=len(rows), equipment=len(data['equipment_scope']), source_checked_pairs=len(base['evidence']['paired_services']),
        historical_paths_preserved=len(lineage), plan_graph_sha256=data['plan_graph_sha256'], physical_values_assigned=0,
        expert_confirmation_claimed=False, human_accepted=False, hil_ready=False,
        pending=['Recompute DN/XY on this current scope; named-riser, legacy paths, full-floor connectivity, fusion and HIL remain separate'])


def compute(paths, policy):
    for key in ('corridors', 'corridor_receipt', 'historical_base', 'historical_refined', 'pair_policy', 'refinement_policy'):
        if sha(paths[key]) != policy.get(key+'_sha256'): raise ValueError('Current paired dependency changed: '+key)
    directory = Path(paths['corridors']).resolve().parent
    if Path(paths['corridor_receipt']).resolve() != directory/'source-mapping-receipt.json' or Path(paths['corridors']).resolve() != directory/'mapping.json':
        raise ValueError('Canonical current corridor parent required')
    corridors = verify_corridors(directory)
    if corridors['mode'] != CORRIDOR_MODE: raise ValueError('Current native corridor owner required')
    receipt = load(paths['corridor_receipt']); local = receipt['local_inputs']; ir = receipt['inputs']['inventory']
    if sha(ir['path']) != ir['sha256']: raise ValueError('Replayed complete inventory changed')
    inventory = load(ir['path']); docs, graphs, hashes = {}, {}, {}
    for view in ('plan', 'iso'):
        for kind in ('source', 'graph'):
            item = local[view+'_'+kind]
            if sha(item['path']) != item['sha256']: raise ValueError('Paired native input changed')
        docs[view] = read_source(local[view+'_source']['path'])[0]; graphs[view] = load(local[view+'_graph']['path'])
        hashes[view] = dict(source_sha256=local[view+'_source']['sha256'], graph_sha256=local[view+'_graph']['sha256'])
    old_hash = corridors['evidence']['original_plan_graph_sha256']
    settings, refinement = load(paths['pair_policy']), load(paths['refinement_policy'])
    if refinement['base_mapping_sha256'] != sha(paths['historical_base']): raise ValueError('Original refinement uses another base')
    base, result = reconstruct(docs, graphs, inventory, load(paths['historical_base']), load(paths['historical_refined']), settings, refinement, hashes, old_hash)
    for view in graphs:
        old_ids = {eid for r in corridors['records'] for eid in r[view+'_edges']}
        if any(old_ids.intersection(r[view+'_edges']) for r in result['records']): raise ValueError('Paired paths overlap already checked corridor writers')
    prefix = policy.get('mapping_prefix', '')
    if not re.fullmatch('[A-Z0-9-]+', prefix): raise ValueError('Explicit current paired mapping prefix required')
    lineage = []
    for row in result['records']:
        old_id = row['mapping_id']; row['mapping_id'] = prefix+'-'+old_id
        lineage.append(dict(previous_mapping_id=old_id, current_mapping_id=row['mapping_id'],
            local_paths_and_snapshots_preserved=True, human_confirmation_transferred=False))
    result.update(mode=MODE, status='source_checked_current_paired_junction_paths_attributes_pending',
        current_native_base_correspondence=base, historical_mapping_lineage=lineage,
        original_plan_graph_sha256=old_hash, corridor_parent_sha256=sha(paths['corridors']),
        physical_values_assigned=0, whole_floor_connectivity_confirmed=False)
    check_result(result)
    return result, copy.deepcopy(local)


def implementation_hashes():
    from match_junction_rebased_corridors import implementation_hashes as parent_hashes
    from refine_paired_service_path_correspondence import implementation_hashes as paired_hashes
    values = parent_hashes(); values.update(paired_hashes()); values[Path(__file__).name] = sha(Path(__file__))
    return values


def verify_output(directory):
    directory = Path(directory); receipt = load(directory/'source-mapping-receipt.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes(): raise ValueError('Current paired implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']: raise ValueError('Current paired dependency changed')
    paths = {k: item['path'] for k, item in receipt['inputs'].items()}; result, local = compute(paths, load(paths['policy']))
    target = directory/'mapping.json'
    if encode(result) != target.read_bytes() or receipt['output_sha256'] != sha(target) or receipt['local_inputs'] != local:
        raise ValueError('Current paired independent native replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in ('corridor-run', 'historical-base', 'historical-refined', 'pair-policy', 'refinement-policy', 'policy', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    a = parser.parse_args()
    paths = dict(corridors=a.corridor_run/'mapping.json', corridor_receipt=a.corridor_run/'source-mapping-receipt.json',
        historical_base=a.historical_base, historical_refined=a.historical_refined, pair_policy=a.pair_policy, refinement_policy=a.refinement_policy, policy=a.policy)
    if a.output.exists(): raise FileExistsError(a.output)
    result, local = compute(paths, load(a.policy)); a.output.mkdir(parents=True); target = a.output/'mapping.json'; target.write_bytes(encode(result))
    (a.output/'source-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()}, local_inputs=local,
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False, hil_ready=False)))
    print(check_result(result), flush=True)


if __name__ == '__main__': main()
