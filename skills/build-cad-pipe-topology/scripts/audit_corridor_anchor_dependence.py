"""Bounded native-corridor anchor audit; never an identity or HIL gate.

Reread native corridor geometry and path coverage, then test candidate-order
dependence. Full inventory ancestry remains a separately replayed prerequisite.
"""
import argparse
import copy
import itertools
import time
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from crossview_equipment_branch_inventory import service_route
from match_junction_rebased_corridors import correspond_group
from match_source_checked_crossview_paths import mutual_main_paths, native_main_corridor
from source_readability import read_source

S = Path(__file__).resolve().parent

def trial(corridors, taps, assignment, system, floor):
    """Change candidate identity assignment only; do not alter source proofs."""
    changed = copy.deepcopy(taps)
    changed['iso'] = {did: taps['iso'][assignment.get(did, did)] for did in taps['iso']}
    try:
        got = mutual_main_paths(corridors, changed, system, floor)
        return dict(status='order_only_not_rejected', pairwise_checks=len(got['pairwise_order_checks']))
    except ValueError as exc:
        return dict(status='blocked', reason=str(exc))


def audit_group(docs, graphs, inventory, spec, hashes, baseline):
    # Reread both native LINE corridors and their actual path coverage. The
    # complete inventory ancestor is intentionally NOT claimed replayed here.
    fresh = correspond_group(docs, graphs, inventory, spec, hashes)
    for key in ('floor', 'equipment_scope', 'records', 'plan_graph_sha256',
                'iso_graph_sha256', 'source_sha256', 'evidence'):
        if fresh[key] != baseline[key]:
            raise ValueError('Fresh native corridor differs: '+spec['group_id']+'/'+key)
    selected = spec['equipment_ids']
    services, anchors, holds, swaps, reversals = {}, [], [], {}, []
    by = {row['equipment_id']: row for row in inventory['records']}
    for system in ('supply', 'return'):
        taps = {view: {did: service_route(graphs[view], did, system)['tee']
                       for did in selected} for view in graphs}
        corridors = {view: native_main_corridor(docs[view], graphs[view], taps[view], system, spec['floor'])[0]
                     for view in graphs}
        full = mutual_main_paths(corridors, taps, system, spec['floor'])
        services[system] = dict(native_corridors=fresh['evidence']['main_topology'][system]['native_corridors'],
                                pairwise_order_checks=len(full['pairwise_order_checks']))
        for did in selected:
            row = next(r for r in fresh['records'] if r['kind'] == 'equipment_branch'
                       and r['equipment_id'] == did and r['system'] == system)
            anchors.append(dict(equipment_id=did, system=system, mapping_id=row['mapping_id'],
                plan_T=row['plan_start'], axis_T=row['iso_start'],
                plan_edges=row['plan_edges'], axis_edges=row['iso_edges'],
                native_service_evidence=copy.deepcopy(by[did]['views'])))
        for omitted in selected:
            reduced = {view: {did: nid for did, nid in taps[view].items() if did != omitted}
                       for view in taps}
            got = mutual_main_paths(corridors, reduced, system, spec['floor'])
            checked = []
            for pair in got['pairwise_order_checks']:
                a, b = pair['equipment_order'][0], pair['equipment_order'][-1]
                old = next(p for p in full['pairwise_order_checks']
                           if p['equipment_order'][0] == a and p['equipment_order'][-1] == b)
                if pair['routes'] != old['routes']:
                    raise ValueError('Withheld-anchor remaining path differs')
                checked.append([a, b])
            holds.append(dict(omitted_equipment=omitted, system=system,
                status='remaining_anchor_routes_consistent', remaining_equipment=len(selected)-1,
                remaining_pair_routes_checked=len(checked), omitted_T_predicted=False,
                original_omitted_owner_still_requires_native_evidence=True))
        for a, b in itertools.combinations(selected, 2):
            key = (a, b)
            swaps.setdefault(key, dict(swapped_equipment=[a, b], services={}))['services'][system] = trial(
                corridors, taps, {a: b, b: a}, system, spec['floor'])
        # An entire linear corridor is invariant under reversal. Test that
        # limitation instead of counting only easy-to-reject pair swaps.
        order = max(full['pairwise_order_checks'], key=lambda row: len(row['equipment_order']))['equipment_order']
        reversal = dict(zip(order, reversed(order)))
        reversals.append(dict(system=system, candidate_assignment=reversal,
            result=trial(corridors, taps, reversal, system, spec['floor']),
            native_label_or_equipment_ownership_replayed_for_mutation=False))
    swap_rows = list(swaps.values())
    for row in swap_rows:
        row['both_services_blocked'] = all(s['status'] == 'blocked' for s in row['services'].values())
        row['native_ownership_not_tested_by_this_mutation'] = True
    return dict(group_id=spec['group_id'], floor=spec['floor'], equipment_ids=selected,
        equipment=len(selected), source_paths=len(fresh['records']), services=services,
        anchors=anchors, mapping_records=copy.deepcopy(fresh['records']),
        leave_one_anchor_out=holds, pair_label_swaps=swap_rows, coherent_reversals=reversals,
        fresh_native_corridor_geometry_and_coverage_replayed=True,
        complete_native_inventory_ancestry_replayed=False,
        withheld_device_correspondence_predicted=False,
        whole_floor_connectivity_confirmed=False, human_accepted=False)


def compute(mapping_run):
    started = time.monotonic()
    folder = Path(mapping_run).resolve()
    mapping_path, receipt_path = folder/'mapping.json', folder/'source-mapping-receipt.json'
    mapping, receipt = load(mapping_path), load(receipt_path)
    if receipt.get('mode') != 'source_checked_junction_rebased_corridor_groups_v1':
        raise ValueError('Only the scoped current native corridor mode is supported')
    watched = {str(mapping_path): sha(mapping_path), str(receipt_path): sha(receipt_path),
               str(Path(__file__)): sha(__file__)}
    if sha(mapping_path) != receipt['output_sha256']:
        raise ValueError('Mapping receipt differs')
    for section in ('inputs', 'local_inputs'):
        for item in receipt[section].values():
            if sha(item['path']) != item['sha256']:
                raise ValueError('Input changed: '+item['path'])
            watched[item['path']] = item['sha256']
    for name, digest in receipt['implementation_sha256'].items():
        if sha(S/name) != digest:
            raise ValueError('Native implementation changed: '+name)
        watched[str(S/name)] = digest
    local = receipt['local_inputs']
    docs, graphs, hashes = {}, {}, {}
    for view in ('plan', 'iso'):
        docs[view], _ = read_source(local[view+'_source']['path'])
        graphs[view] = load(local[view+'_graph']['path'])
        hashes[view] = dict(source_sha256=local[view+'_source']['sha256'],
                            graph_sha256=local[view+'_graph']['sha256'])
    before = {view: encode(graph) for view, graph in graphs.items()}
    inventory = load(receipt['inputs']['inventory']['path'])
    policy = load(receipt['inputs']['policy']['path'])
    groups = [audit_group(docs, graphs, inventory, spec, hashes,
              next(g for g in mapping['groups'] if g['group_id'] == spec['group_id']))
              for spec in policy['groups']]
    if any(encode(graphs[view]) != before[view] for view in graphs):
        raise ValueError('Audit mutated local graph')
    if any(sha(path) != digest for path, digest in watched.items()):
        raise ValueError('Audit input changed during execution')
    reversals = [r for group in groups for r in group['coherent_reversals']]
    swap_rows = [r for group in groups for r in group['pair_label_swaps']]
    result = dict(status='native_corridor_geometry_and_label_dependency_audit_complete',
        mapping=dict(path=str(mapping_path), sha256=sha(mapping_path)),
        input_pins_checked=len(watched), input_sha256=watched, groups=groups,
        mode='corridor_anchor_dependence_audit_v1', independent_corridor_groups=len(groups), equipment=sum(g['equipment'] for g in groups),
        paired_service_anchors=sum(len(g['anchors']) for g in groups),
        source_paths=sum(g['source_paths'] for g in groups),
        leave_one_anchor_out_service_trials=sum(len(g['leave_one_anchor_out']) for g in groups),
        omitted_T_predictions=0, pair_swap_trials=len(swap_rows),
        pair_swaps_both_services_blocked=sum(r['both_services_blocked'] for r in swap_rows),
        coherent_reversal_service_trials=len(reversals),
        coherent_reversals_not_rejected_by_order=sum(r['result']['status']=='order_only_not_rejected' for r in reversals),
        fresh_native_corridor_geometry_and_coverage_replayed=True,
        complete_native_inventory_ancestry_replayed=False,
        source_graphs_and_implementation_unchanged=True,
        formal_full_mapping_receipt_replaced=False, graph_or_attribute_outputs_changed=False,
        statistical_error_probability=None, whole_floor_connectivity_confirmed=False,
        human_accepted=False, whole_goal_complete=False, elapsed_seconds=time.monotonic()-started,
        limitations=[
            'Replayed corridor geometry and coverage rely on pinned separately verified service inventory ancestry.',
            'Removing an anchor checks remaining paths; it does not independently predict the omitted owner.',
            'All-pair order checks are correlated, not independent samples.',
            'Coherent whole-chain reversal can preserve order; exact native labels and equipment ownership remain necessary.',
            'No test count implies an error probability or whole-floor acceptance.'])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mapping-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = compute(args.mapping_run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encode(result))
    print({key: result[key] for key in ('status', 'equipment', 'source_paths',
        'pair_swap_trials', 'pair_swaps_both_services_blocked',
        'coherent_reversals_not_rejected_by_order', 'elapsed_seconds')}, flush=True)


if __name__ == '__main__':
    main()
