"""Fresh common-anchor corridors on the latest native-junction inventory.

Reuse unique native LINE corridors, mutual main order and source path coverage.
Do not relax whole-floor isomorphism, graft an old receipt onto a new graph, or
infer the missing continuations between independent drawing subviews.
"""
import argparse
import copy
import re
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from crossview_equipment_branch_inventory import index_graph, service_route
from match_source_checked_crossview_paths import native_main_corridor, mutual_main_paths, selected_snapshot
from native_path_coverage_audit import audit as audit_paths
from pending_junction_branch_inventory import MODE as INVENTORY_MODE, verify_output as verify_inventory
from source_readability import read_source

MODE = 'source_checked_junction_rebased_corridor_groups_v1'


def record_key(row):
    return row['kind'], row['system'], row['floor'], row.get('equipment_id'), tuple(row.get('endpoint_equipment_ids', []))


def historical_lineage(result, previous, original_plan_hash):
    if (previous.get('plan_graph_sha256') != original_plan_hash
            or previous.get('iso_graph_sha256') != result['iso_graph_sha256']
            or previous.get('source_sha256') != result['source_sha256']
            or set(previous['equipment_scope']) != set(result['equipment_scope'])):
        raise ValueError('Historical source/axis/equipment scope changed')
    old = {record_key(r): r for r in previous['records']}
    current = {record_key(r): r for r in result['records']}
    if len(old) != len(previous['records']) or len(current) != len(result['records']) or set(old) != set(current):
        raise ValueError('Historical mapped paths lost or duplicated')
    lineage = []
    for key, row in current.items():
        prior = old[key]
        for name in ('plan_edges', 'iso_edges', 'plan_start', 'plan_end', 'iso_start', 'iso_end', 'plan_snapshot', 'iso_snapshot'):
            if row[name] != prior[name]:
                raise ValueError('Mapped local path changed and needs explicit reconciliation: '+name)
        lineage.append(dict(previous_mapping_id=prior['mapping_id'], current_mapping_id=row['mapping_id'],
            local_paths_and_snapshots_preserved=True, human_confirmation_transferred=False))
    return lineage


def correspond_group(docs, graphs, inventory, group, hashes):
    selected, floor, prefix = group.get('equipment_ids'), group.get('floor'), group.get('mapping_prefix', '')
    if (not isinstance(selected, list) or len(selected) < 3 or len(set(selected)) != len(selected)
            or type(floor) is not int or not re.fullmatch('[A-Z0-9-]+', prefix)):
        raise ValueError('Explicit independent multi-equipment corridor scope required')
    by = {r['equipment_id']: r for r in inventory['records']}
    if len(by) != len(inventory['records']) or any(d not in by or by[d]['floor'] != floor or by[d].get('ready_for_mapping_comparison') is not True for d in selected):
        raise ValueError('Selected equipment has not passed complete native service checks')
    rows, topology, coverage = [], {}, {}
    for system in ('supply', 'return'):
        taps = {v: {} for v in graphs}
        for view in graphs:
            for did in selected:
                trace = service_route(graphs[view], did, system)
                prior = by[did]['views'][view]['services'][system]
                if (trace != prior['trace'] or trace.get('status') != 'unique_graph_service_to_T'
                        or len(trace['edges']) != 1 or prior.get('ready_for_mapping_comparison') is not True):
                    raise ValueError('Current native service owner or route differs')
                taps[view][did] = trace['tee']
        corridors = {v: native_main_corridor(docs[v], graphs[v], taps[v], system, floor) for v in graphs}
        check = mutual_main_paths({v: corridors[v][0] for v in graphs}, taps, system, floor)
        check['native_corridors'] = {v: corridors[v][1] for v in graphs}
        topology[system] = check
        for did in selected:
            rows.append(dict(kind='equipment_branch', equipment_id=did, system=system, floor=floor,
                plan_edges=by[did]['views']['plan']['services'][system]['trace']['edges'],
                iso_edges=by[did]['views']['iso']['services'][system]['trace']['edges'],
                plan_start=taps['plan'][did], iso_start=taps['iso'][did], plan_end=did, iso_end=did,
                local_evidence={v: copy.deepcopy(by[did]['views'][v]['services'][system]) for v in graphs}))
        for pair in check['adjacent']:
            a, b = pair['equipment_order']
            routes = pair['routes']
            rows.append(dict(kind='main_between_equipment_branches', endpoint_equipment_ids=[a, b], system=system, floor=floor,
                plan_edges=routes['plan']['edges'], iso_edges=routes['iso']['edges'],
                plan_start=taps['plan'][a], plan_end=taps['plan'][b], iso_start=taps['iso'][a], iso_end=taps['iso'][b]))
    for view in graphs:
        all_ids = [eid for row in rows for eid in row[view+'_edges']]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError('Corridor repeats a local branch/main edge')
        main_ids = [eid for row in rows if row['kind'] == 'main_between_equipment_branches' for eid in row[view+'_edges']]
        h = hashes[view]
        evidence = audit_paths(docs[view], graphs[view], dict(h, edges=main_ids), h['source_sha256'], h['graph_sha256'])
        if any(s['status'] != 'single_source_line_covers' for e in evidence['edges'] for s in e['segments']):
            raise ValueError('Main correspondence lacks unique native LINE coverage')
        coverage[view] = evidence
    for index, row in enumerate(rows, 1):
        row.update(mapping_id=prefix+'-'+str(index).zfill(4), status='source_checked_current_corridor_human_pending',
            decision_basis='fresh_native_services_unique_LINE_corridor_and_mutual_main_order',
            physical_ports_verified=False, human_accepted=False,
            plan_snapshot=selected_snapshot(graphs['plan'], row['plan_edges']), iso_snapshot=selected_snapshot(graphs['iso'], row['iso_edges']))
    if len(rows) != 4*len(selected)-2:
        raise ValueError('Complete paired-service corridor scope differs')
    return dict(status='source_checked_path_correspondence_attributes_pending', floor=floor, equipment_scope=selected, records=rows,
        plan_graph_sha256=hashes['plan']['graph_sha256'], iso_graph_sha256=hashes['iso']['graph_sha256'],
        source_sha256={v: h['source_sha256'] for v, h in hashes.items()}, evidence=dict(main_topology=topology, main_coverage=coverage),
        local_graphs_mutated=False, expert_confirmation_claimed=False, human_accepted=False, hil_ready=False)


def groups_correspond(docs, graphs, inventory, groups, hashes, original_plan_hash):
    if not groups or len({g['group_id'] for g in groups}) != len(groups):
        raise ValueError('Explicit unique corridor group identities required')
    results, records, equipment = [], [], set()
    used = {v: set() for v in graphs}
    for group in groups:
        prior = group['previous_mapping']
        if sha(prior['path']) != prior['sha256']:
            raise ValueError('Historical mapping artifact changed')
        result = correspond_group(docs, graphs, inventory, group, hashes)
        lineage = historical_lineage(result, load(prior['path']), original_plan_hash)
        if equipment & set(result['equipment_scope']):
            raise ValueError('Corridor groups repeat equipment')
        equipment.update(result['equipment_scope'])
        for view in graphs:
            ids = {eid for row in result['records'] for eid in row[view+'_edges']}
            if ids & used[view]:
                raise ValueError('Corridor groups overlap local writers')
            used[view].update(ids)
        result.update(group_id=group['group_id'], previous_mapping_sha256=prior['sha256'], historical_mapping_lineage=lineage)
        results.append(result)
        records += [dict(row, group_id=group['group_id']) for row in result['records']]
    if len({r['mapping_id'] for r in records}) != len(records):
        raise ValueError('Corridor mapping IDs collide')
    return dict(mode=MODE, status='source_checked_path_correspondence_attributes_pending', groups=results, records=records,
        equipment_scope=sorted(equipment), source_sha256={v: h['source_sha256'] for v, h in hashes.items()},
        plan_graph_sha256=hashes['plan']['graph_sha256'], iso_graph_sha256=hashes['iso']['graph_sha256'],
        local_graphs_mutated=False, expert_confirmation_claimed=False, physical_values_assigned=0,
        whole_floor_connectivity_confirmed=False, human_accepted=False, hil_ready=False)


def compute(paths, policy):
    for key in ('inventory', 'inventory_receipt'):
        if sha(paths[key]) != policy.get(key+'_sha256'):
            raise ValueError('Current corridor inventory changed: '+key)
    folder = Path(paths['inventory']).resolve().parent
    if Path(paths['inventory_receipt']).resolve() != folder/'inventory-receipt.json' or Path(paths['inventory']).resolve() != folder/'inventory.json':
        raise ValueError('Canonical latest native inventory required')
    receipt = load(paths['inventory_receipt'])
    if receipt.get('mode') != INVENTORY_MODE:
        raise ValueError('Latest native junction inventory mode required')
    inventory = verify_inventory(folder)
    local = receipt['local_inputs']
    for item in local.values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('Current local source/graph dependency changed')
    docs, graphs, hashes = {}, {}, {}
    for view in ('plan', 'iso'):
        docs[view], _ = read_source(local[view+'_source']['path'])
        graphs[view] = load(local[view+'_graph']['path'])
        hashes[view] = dict(source_sha256=local[view+'_source']['sha256'], graph_sha256=local[view+'_graph']['sha256'])
    old_plan_hash = load(receipt['inputs']['parent_receipt']['path'])['inputs']['plan_graph']['sha256']
    result = groups_correspond(docs, graphs, inventory, policy['groups'], hashes, old_plan_hash)
    result['evidence'] = dict(inventory_sha256=sha(paths['inventory']), inventory_receipt_sha256=sha(paths['inventory_receipt']),
        original_plan_graph_sha256=old_plan_hash, latest_native_inventory_mode=INVENTORY_MODE,
        inherited_pending_scope=copy.deepcopy(inventory['pending_native_junction_inventory_rebase']))
    return result, copy.deepcopy(local)


def implementation_hashes():
    from pending_junction_branch_inventory import implementation_hashes as inventory_hashes
    values = inventory_hashes()
    for name in ('match_junction_rebased_corridors.py', 'match_source_checked_crossview_paths.py', 'native_path_coverage_audit.py'):
        values[name] = sha(Path(__file__).with_name(name))
    return values


def verify_output(directory):
    directory = Path(directory)
    receipt = load(directory/'source-mapping-receipt.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('Current corridor implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('Current corridor input changed')
    paths = {k: v['path'] for k, v in receipt['inputs'].items()}
    result, local = compute(paths, load(paths['policy']))
    if (encode(result) != (directory/'mapping.json').read_bytes() or receipt['output_sha256'] != sha(directory/'mapping.json')
            or receipt['local_inputs'] != local):
        raise ValueError('Current corridor independent native replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in ('inventory-run', 'policy', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    paths = dict(inventory=args.inventory_run/'inventory.json', inventory_receipt=args.inventory_run/'inventory-receipt.json', policy=args.policy)
    if args.output.exists(): raise FileExistsError(args.output)
    result, local = compute(paths, load(args.policy))
    args.output.mkdir(parents=True)
    target = args.output/'mapping.json'; target.write_bytes(encode(result))
    (args.output/'source-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()},
        local_inputs=local, implementation_sha256=implementation_hashes(), output_sha256=sha(target),
        human_accepted=False, hil_ready=False)))
    print(dict(groups=len(result['groups']), equipment=len(result['equipment_scope']), mapped_paths=len(result['records'])), flush=True)


if __name__ == '__main__': main()
