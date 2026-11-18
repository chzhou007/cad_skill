"""Fresh plan service evidence after independently replayed circle continuations.

The v2 inventory is history, not an acceptance receipt for the changed graph.
Axis evidence can be retained only on its exact independently replayed inputs.
"""
import argparse
import copy
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from crossview_equipment_branch_inventory import _caption, index_graph, inspect_branch, unresolved_identity_candidates
from crossview_equipment_branch_inventory_v2 import verify_output as verify_parent
from normalize_two_arm_circle_continuity import verify_output as verify_circles
from source_readability import read_source

MODE = 'two_arm_circle_rebased_branch_inventory_v1'


def rebuild(doc, graph, parent, source_hash, graph_hash):
    if (parent.get('inventory_mode') != 'source_endpoint_branch_inventory_v2'
            or parent.get('status') != 'source_comparison_inventory_not_mapping'
            or parent.get('mapped_paths') != 0 or parent.get('local_graphs_mutated') is not False
            or parent.get('human_accepted') is not False or parent.get('hil_ready') is not False):
        raise ValueError('Complete independently replayed v2 inventory required')
    root = graph.get('sourceTwoArmCircleContinuity', {})
    if not root.get('records') or root.get('physical_Ts_added') != 0:
        raise ValueError('Native two-arm transition required')
    nodes, _, _ = index_graph(graph)
    result = copy.deepcopy(parent)
    checks = []
    for row, old in zip(result['records'], parent['records']):
        did = row['equipment_id']
        captions = [e for e in doc.modelspace().query('TEXT MTEXT') if e.plain_text() == did]
        node = nodes.get(did)
        if len(captions) != 1:
            view = dict(status='missing_or_ambiguous_native_caption')
        elif not node or node.get('node_type') not in ('equipment', 'physical_equipment') or node.get('floor') != row['floor']:
            candidates = unresolved_identity_candidates(doc, graph, did, row['floor'])
            view = dict(status='unresolved_equipment_identity_candidates' if candidates else 'missing_or_floor_conflicting_equipment',
                        caption=_caption(doc, captions[0].dxf.handle, did), retained_native_equipment_candidates=candidates)
        else:
            hashes = dict(source_sha256=source_hash, graph_sha256=graph_hash)
            services = {s: inspect_branch(doc, graph, did, s, hashes, 'plan', []) for s in ('supply', 'return')}
            view = dict(status='native_caption_read', caption=_caption(doc, captions[0].dxf.handle, did), services=services)
        row['views']['plan'] = view
        for system in ('supply', 'return'):
            before = old['views'].get('plan', {}).get('services', {}).get(system, {})
            current = view.get('services', {}).get(system, {})
            if before.get('ready_for_mapping_comparison') and not current.get('ready_for_mapping_comparison'):
                raise ValueError('Previously ready plan service regressed: ' + did + '/' + system + ': ' + str(current.get('reason')))
            checks.append(dict(equipment_id=did, system=system,
                               ready=current.get('ready_for_mapping_comparison', False),
                               reason=current.get('reason', view['status'])))
        row['ready_for_mapping_comparison'] = all(
            row['views'].get(v, {}).get('services', {}).get(s, {}).get('ready_for_mapping_comparison', False)
            for v in ('plan', 'iso') for s in ('supply', 'return'))
        if row['views'].get('iso') != old['views'].get('iso'):
            raise ValueError('Unchanged axis evidence altered')
        if old['ready_for_mapping_comparison'] and not row['ready_for_mapping_comparison']:
            raise ValueError('Previously ready equipment regressed')
    result.update(inventory_mode=MODE)
    result['counts'] = dict(equipment=len(result['records']), ready_for_mapping_comparison=sum(r['ready_for_mapping_comparison'] for r in result['records']))
    result['two_arm_circle_inventory_rebase'] = dict(mode=MODE, plan_graph_sha256=graph_hash,
        fresh_plan_service_checks=checks, preserved_axis_evidence_on_identical_inputs=True,
        edge_id_aliases=copy.deepcopy(root['edge_id_aliases']), mapped_paths=0,
        physical_ports_verified=False, physical_values_assigned=0, human_accepted=False)
    return result


def compute(paths, policy):
    for key in ('parent_inventory', 'parent_receipt', 'circle_graph', 'circle_receipt'):
        if sha(paths[key]) != policy.get(key + '_sha256'):
            raise ValueError('Circle inventory dependency changed: ' + key)
    parent_dir = Path(paths['parent_inventory']).resolve().parent
    circle_dir = Path(paths['circle_graph']).resolve().parent
    expected = dict(parent_inventory=parent_dir/'inventory.json', parent_receipt=parent_dir/'inventory-receipt.json',
                    circle_graph=circle_dir/'graph_with_edges.json', circle_receipt=circle_dir/'two-arm-circle-continuity-audit.json')
    if any(Path(paths[k]).resolve() != v for k, v in expected.items()):
        raise ValueError('Canonical inventory and circle parents required')
    parent = verify_parent(parent_dir)
    proof = verify_circles(circle_dir)
    local = load(paths['parent_receipt'])['inputs']
    if (proof['inputs']['graph']['sha256'] != local['plan_graph']['sha256']
            or proof['inputs']['source']['sha256'] != local['plan_source']['sha256']
            or proof['output_graph_sha256'] != sha(paths['circle_graph'])):
        raise ValueError('Circle graph is not this inventory parent child')
    doc, preflight = read_source(local['plan_source']['path'])
    result = rebuild(doc, load(paths['circle_graph']), parent, local['plan_source']['sha256'], sha(paths['circle_graph']))
    result['source_preflight']['plan'] = preflight
    result['source_evidence_implementation_sha256'][Path(__file__).name] = sha(__file__)
    bindings = copy.deepcopy(local)
    bindings['plan_graph'] = dict(path=str(Path(paths['circle_graph']).resolve()), sha256=sha(paths['circle_graph']))
    bindings['plan_devices'] = dict(path=str(circle_dir/'assigned_edge_device_instances.csv'), sha256=sha(circle_dir/'assigned_edge_device_instances.csv'))
    result['two_arm_circle_inventory_rebase'].update(parent_inventory_sha256=sha(paths['parent_inventory']),
        circle_receipt_sha256=sha(paths['circle_receipt']))
    return result, bindings


def implementation_hashes():
    from normalize_two_arm_circle_continuity import implementation_hashes as circle_hashes
    values = circle_hashes()
    for name in ('two_arm_circle_branch_inventory.py', 'crossview_equipment_branch_inventory.py', 'crossview_equipment_branch_inventory_v2.py'):
        values[name] = sha(Path(__file__).with_name(name))
    return values


def verify_output(directory):
    directory = Path(directory)
    receipt = load(directory/'inventory-receipt.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('Circle inventory implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('Circle inventory input changed')
    paths = {k: v['path'] for k, v in receipt['inputs'].items()}
    result, local = compute(paths, load(paths['policy']))
    if (encode(result) != (directory/'inventory.json').read_bytes() or receipt['local_inputs'] != local
            or sha(directory/'inventory.json') != receipt['output_sha256']):
        raise ValueError('Circle inventory independent replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in ('parent-inventory', 'circle-run', 'policy', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    paths = dict(parent_inventory=args.parent_inventory/'inventory.json', parent_receipt=args.parent_inventory/'inventory-receipt.json',
                 circle_graph=args.circle_run/'graph_with_edges.json', circle_receipt=args.circle_run/'two-arm-circle-continuity-audit.json', policy=args.policy)
    if args.output.exists():
        raise FileExistsError(args.output)
    result, local = compute(paths, load(args.policy))
    args.output.mkdir(parents=True)
    target = args.output/'inventory.json'
    target.write_bytes(encode(result))
    (args.output/'inventory-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()}, local_inputs=local,
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False, hil_ready=False)))
    print(result['counts'], flush=True)


if __name__ == '__main__':
    main()
