"""Replay current corridor DN and original floor/detail metric contracts.

This source stage measures only corroborated plan XY. Confirmed detail spans
remain unmeasured; no axis graph, physical connector or human review is changed.
"""
import argparse
import copy
import math
from pathlib import Path

from attach_source_checked_plan_attributes import metric_context
from confirmed_detail_projection import projection, STATUS as DETAIL_STATUS
from confirm_crossview_paths import encode, load, sha
from junction_rebased_plan_DN_scopes import MODE as DN_MODE, verify_output as verify_DN
from match_junction_rebased_corridors import MODE as MAPPING_MODE
from source_checked_plan_path_coverage import audit as audit_paths
from source_readability import read_source

MODE = 'junction_rebased_plan_DN_and_XY_scopes_v1'
STATUS = 'source_checked_junction_rebased_plan_DN_and_XY_not_fused'


def metric_bindings(mapping, specs):
    """Bind each original metric policy to its exact historical corridor."""
    groups = mapping['groups']
    if not specs or len(specs) != len(groups) or len({s['group_id'] for s in specs}) != len(specs):
        raise ValueError('Complete distinct metric group policies required')
    by = {g['group_id']: g for g in groups}
    if len(by) != len(groups) or set(by) != {s['group_id'] for s in specs}:
        raise ValueError('Metric policies do not cover the current corridor groups')
    result = {}
    for spec in specs:
        if sha(spec['path']) != spec['sha256']:
            raise ValueError('Original metric policy changed')
        policy = load(spec['path'])
        if policy.get('mapping_sha256') != by[spec['group_id']]['previous_mapping_sha256']:
            raise ValueError('Metric policy belongs to a different historical corridor')
        result[spec['group_id']] = policy
    return result


def attribute(doc, graph, mapping, diameters, policies, source_hash, graph_hash):
    if (mapping.get('mode') != MAPPING_MODE or diameters.get('mode') != DN_MODE
            or mapping.get('plan_graph_sha256') != graph_hash or diameters.get('graph_sha256') != graph_hash
            or mapping['source_sha256']['plan'] != source_hash or diameters.get('source_sha256') != source_hash
            or diameters.get('physical_values_fused') is not False or mapping.get('human_accepted') is not False
            or diameters.get('human_accepted') is not False):
        raise ValueError('Fresh current corridor and DN scopes required')
    before = encode(graph)
    edges = {e['edge_id']: e for e in graph['edges']}
    dn = {r['edge_id']: r for r in diameters['records']}
    ids = [eid for r in mapping['records'] for eid in r['plan_edges']]
    if len(ids) != len(set(ids)) or len(dn) != len(diameters['records']) or set(ids) != set(dn):
        raise ValueError('Complete unique current DN/metric writers required')
    if set(policies) != {g['group_id'] for g in mapping['groups']}:
        raise ValueError('Metric group scope differs')
    coverage = audit_paths(doc, graph, dict(source_sha256=source_hash, graph_sha256=graph_hash, edges=ids), source_hash, graph_hash)
    sources = dict(plan=source_hash, plan_graph=graph_hash)
    groups, records = [], []
    for group in mapping['groups']:
        units, allow_detail = metric_context(doc, policies[group['group_id']], graph, group)
        rows = []
        for row in group['records']:
            if len(row['plan_edges']) != 1:
                raise ValueError('A multi-edge DN scope needs explicit reconciliation')
            value = dn[row['plan_edges'][0]]
            if (value['system'] != row['system'] or value['scope_paths'] != edges[value['edge_id']]['attribute_paths']
                    or value.get('scope') != 'native_plan_drawn_pipe_paths_only' or value.get('human_accepted') is not False):
                raise ValueError('DN source path or service changed before metric replay')
            metric = projection(graph, coverage, row, units, sources, allow_detail=allow_detail)
            rows.append(dict(mapping_id=row['mapping_id'], group_id=group['group_id'], kind=row['kind'],
                floor=row['floor'], system=row['system'], plan_edges=list(row['plan_edges']), iso_edges=list(row['iso_edges']),
                diameter=copy.deepcopy(value), horizontal_projection=metric, whole_axis_DN_selected=False,
                whole_axis_physical_length_mm=None, physical_ports_verified=False, human_accepted=False))
        groups.append(dict(group_id=group['group_id'], equipment_scope=list(group['equipment_scope']),
            metric_evidence=units, record_ids=[r['mapping_id'] for r in rows]))
        records.extend(rows)
    if encode(graph) != before:
        raise ValueError('DN/XY source reading mutated local topology')
    return dict(mode=MODE, status=STATUS, source_sha256=source_hash, graph_sha256=graph_hash,
        equipment_scope=list(mapping['equipment_scope']), groups=groups, records=records, native_coverage=coverage,
        local_graphs_mutated=False, physical_values_fused=False, whole_axis_DN_assigned=0,
        installed_lengths_assigned=0, human_accepted=False)


def check_result(data):
    if (data.get('mode') != MODE or data.get('status') != STATUS
            or any(data.get(k) is not False for k in ('local_graphs_mutated', 'physical_values_fused', 'human_accepted'))
            or data.get('whole_axis_DN_assigned') != 0 or data.get('installed_lengths_assigned') != 0):
        raise ValueError('Unsupported current corridor plan attribute state')
    groups, rows = data['groups'], data['records']
    by = {r['mapping_id']: r for r in rows}
    membership = [rid for g in groups for rid in g['record_ids']]
    if (not groups or len({g['group_id'] for g in groups}) != len(groups) or len(by) != len(rows)
            or len(membership) != len(set(membership)) or set(membership) != set(by)):
        raise ValueError('Duplicate or incomplete metric group membership')
    equipment = [did for g in groups for did in g['equipment_scope']]
    if len(equipment) != len(set(equipment)) or set(equipment) != set(data['equipment_scope']):
        raise ValueError('Equipment groups overlap or differ')
    for group in groups:
        count = len(group['equipment_scope']); selected = [by[rid] for rid in group['record_ids']]
        if count < 3 or len(selected) != 4*count-2 or any(r['group_id'] != group['group_id'] for r in selected):
            raise ValueError('Complete independent multi-anchor group required')
        for system in ('supply', 'return'):
            service = [r for r in selected if r['system'] == system]
            if (sum(r['kind'] == 'equipment_branch' for r in service) != count
                    or sum(r['kind'] == 'main_between_equipment_branches' for r in service) != count-1):
                raise ValueError('Complete separate service scopes required')
    plan_ids, axis_ids = [], []
    for row in rows:
        dn, metric = row['diameter'], row['horizontal_projection']
        value = dn['nominal_mm']; length = metric['value_mm']
        if (len(row['plan_edges']) != 1 or not row['iso_edges'] or dn['edge_id'] != row['plan_edges'][0]
                or dn['system'] != row['system'] or dn.get('human_accepted') is not False
                or any(row.get(k) is not False for k in ('whole_axis_DN_selected', 'physical_ports_verified', 'human_accepted'))
                or row.get('whole_axis_physical_length_mm') is not None
                or metric.get('installed_whole_edge_length_mm') is not None or metric.get('unshown_connection_length_mm') is not None
                or not metric.get('pieces')):
            raise ValueError('Plan evidence escaped its source-only scope')
        for v in (value, length):
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0):
                raise ValueError('Invalid DN or projection value')
        if length is None:
            context = metric.get('detail_context', {})
            if (metric.get('status') != DETAIL_STATUS or context.get('physical_units_applied') is not False
                    or context.get('plan_graph_sha256') != data['graph_sha256'] or context.get('plan_source_sha256') != data['source_sha256']
                    or context.get('plan_edges') != row['plan_edges'] or context.get('human_accepted') is not False):
                raise ValueError('Unmeasured detail requires exact native context')
        elif metric.get('status') != 'native_plan_horizontal_projection_partial_length':
            raise ValueError('Unsupported metric source')
        plan_ids.extend(row['plan_edges']); axis_ids.extend(row['iso_edges'])
    if len(plan_ids) != len(set(plan_ids)) or len(axis_ids) != len(set(axis_ids)):
        raise ValueError('Repeated local path writers')
    return dict(status='pending', source_replay='passed', mapped_plan_attribute_scopes=len(rows), independent_groups=len(groups),
        equipment=len(equipment), known_DN_scopes=sum(r['diameter']['nominal_mm'] is not None for r in rows),
        measured_plan_XY_scopes=sum(r['horizontal_projection']['value_mm'] is not None for r in rows),
        unmeasured_detail_scopes=sum(r['horizontal_projection']['value_mm'] is None for r in rows),
        graph_sha256=data['graph_sha256'], source_sha256=data['source_sha256'], mapping_sha256=data['mapping_sha256'],
        physical_values_fused=False, installed_lengths_assigned=0, human_accepted=False, hil_ready=False,
        pending=['Complete-parent fusion, remaining floor correspondences, source comparison, viewer and HIL remain separate'])


def compute(paths, policy):
    for key in ('diameter', 'diameter_receipt'):
        if sha(paths[key]) != policy.get(key+'_sha256'):
            raise ValueError('Current DN dependency changed: '+key)
    folder = Path(paths['diameter']).resolve().parent
    if Path(paths['diameter_receipt']).resolve() != folder/'plan-DN-scope-receipt.json' or Path(paths['diameter']).resolve() != folder/'plan-DN-scopes.json':
        raise ValueError('Canonical current DN source stage required')
    # This owner independently replays the complete current mapping parent.
    # Its exact returned mapping input is reused only within this closed call.
    diameters = verify_DN(folder)
    dn_receipt = load(paths['diameter_receipt']); parent = dn_receipt['inputs']
    mapping_path = parent['mapping']['path']; mapping_receipt_path = parent['mapping_receipt']['path']
    if sha(mapping_path) != parent['mapping']['sha256'] or sha(mapping_receipt_path) != parent['mapping_receipt']['sha256']:
        raise ValueError('Replayed mapping parent changed during attribute reading')
    mapping = load(mapping_path); local = load(mapping_receipt_path)['local_inputs']
    if diameters['mapping_sha256'] != sha(mapping_path):
        raise ValueError('DN and metric mapping differ')
    for key in ('plan_source', 'plan_graph'):
        if sha(local[key]['path']) != local[key]['sha256']:
            raise ValueError('Metric native source/graph changed')
    policies = metric_bindings(mapping, policy['metric_policies'])
    doc, preflight = read_source(local['plan_source']['path'])
    result = attribute(doc, load(local['plan_graph']['path']), mapping, diameters, policies,
        local['plan_source']['sha256'], local['plan_graph']['sha256'])
    result.update(mapping_sha256=sha(mapping_path), diameter_scope_sha256=sha(paths['diameter']), source_preflight=preflight,
        metric_policy_lineage=copy.deepcopy(policy['metric_policies']))
    check_result(result)
    return result


def implementation_hashes():
    from junction_rebased_plan_DN_scopes import implementation_hashes as parent_hashes
    from attach_source_checked_plan_attributes import implementation_hashes as metric_hashes
    result = parent_hashes(); result.update(metric_hashes())
    result[Path(__file__).name] = sha(Path(__file__))
    return result


def verify_output(directory):
    directory = Path(directory); receipt = load(directory/'corridor-plan-attribute-receipt.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('Current corridor plan attribute implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('Current corridor plan attribute input changed')
    paths = {k: item['path'] for k, item in receipt['inputs'].items()}
    result = compute(paths, load(paths['policy'])); target = directory/'corridor-plan-attributes.json'
    if encode(result) != target.read_bytes() or receipt['output_sha256'] != sha(target):
        raise ValueError('Current DN/XY independent native replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in ('diameter-run', 'policy', 'output'): parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    paths = dict(diameter=args.diameter_run/'plan-DN-scopes.json', diameter_receipt=args.diameter_run/'plan-DN-scope-receipt.json', policy=args.policy)
    if args.output.exists(): raise FileExistsError(args.output)
    result = compute(paths, load(args.policy)); args.output.mkdir(parents=True)
    target = args.output/'corridor-plan-attributes.json'; target.write_bytes(encode(result))
    (args.output/'corridor-plan-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()},
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False)))
    print(check_result(result), flush=True)


if __name__ == '__main__': main()
