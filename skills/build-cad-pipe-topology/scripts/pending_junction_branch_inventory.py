"""Rebase source-checked service evidence onto the resolved native-T child.

Reuse the complete plan-service reader and its no-regression guards. Replay the
original inventory and native child independently; do not rewrite an ancestor
inventory's graph hash or reuse its plan-side acceptance on the changed graph.
"""
import argparse
import copy
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from crossview_equipment_branch_inventory_v2 import verify_output as verify_inventory
from resolve_pending_native_junctions import verify_output as verify_junction
from source_readability import read_source
from two_arm_circle_branch_inventory import rebuild

MODE = 'pending_native_junction_rebased_branch_inventory_v1'


def check_lineage(local, junction, circle, output_hash):
    if (junction['output_graph_sha256'] != output_hash
            or junction['inputs']['graph']['sha256'] != circle['output_graph_sha256']
            or circle['inputs']['graph']['sha256'] != local['plan_graph']['sha256']
            or {junction['inputs']['source']['sha256'], circle['inputs']['source']['sha256']} != {local['plan_source']['sha256']}):
        raise ValueError('Native junction child is not this complete inventory plan descendant')


def compute(paths, policy):
    for key in ('parent_inventory', 'parent_receipt', 'junction_graph', 'junction_receipt'):
        if sha(paths[key]) != policy.get(key + '_sha256'):
            raise ValueError('Junction inventory dependency changed: ' + key)
    parent_dir = Path(paths['parent_inventory']).resolve().parent
    junction_dir = Path(paths['junction_graph']).resolve().parent
    expected = dict(parent_inventory=parent_dir/'inventory.json', parent_receipt=parent_dir/'inventory-receipt.json',
                    junction_graph=junction_dir/'graph_with_edges.json', junction_receipt=junction_dir/'pending-native-junction-audit.json')
    if any(Path(paths[k]).resolve() != v for k, v in expected.items()):
        raise ValueError('Canonical native inventory and junction run required')
    parent = verify_inventory(parent_dir)
    junction = verify_junction(junction_dir)
    circle_dir = Path(junction['inputs']['graph']['path']).resolve().parent
    circle = load(circle_dir/'two-arm-circle-continuity-audit.json')
    local = load(paths['parent_receipt'])['inputs']
    check_lineage(local, junction, circle, sha(paths['junction_graph']))
    graph = load(paths['junction_graph'])
    doc, preflight = read_source(local['plan_source']['path'])
    result = rebuild(doc, graph, parent, local['plan_source']['sha256'], sha(paths['junction_graph']))
    result['inventory_mode'] = MODE
    current = result.pop('two_arm_circle_inventory_rebase')
    current.update(mode=MODE, parent_inventory_sha256=sha(paths['parent_inventory']),
                   junction_receipt_sha256=sha(paths['junction_receipt']),
                   resolved_native_T_ids=[r['node_id'] for r in graph['sourcePendingNativeJunctionResolution']['records']],
                   inherited_circle_source_evidence_preserved=True)
    result['pending_native_junction_inventory_rebase'] = current
    result['source_preflight']['plan'] = preflight
    result['source_evidence_implementation_sha256'].update(implementation_hashes())
    bindings = copy.deepcopy(local)
    bindings['plan_graph'] = dict(path=str(Path(paths['junction_graph']).resolve()), sha256=sha(paths['junction_graph']))
    bindings['plan_devices'] = dict(path=str(junction_dir/'assigned_edge_device_instances.csv'), sha256=sha(junction_dir/'assigned_edge_device_instances.csv'))
    return result, bindings


def implementation_hashes():
    from two_arm_circle_branch_inventory import implementation_hashes as circle_hashes
    from resolve_pending_native_junctions import implementation_hashes as junction_hashes
    values = circle_hashes()
    values.update(junction_hashes())
    values[Path(__file__).name] = sha(__file__)
    return values


def verify_output(directory):
    directory = Path(directory)
    receipt = load(directory/'inventory-receipt.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('Junction inventory implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('Junction inventory input changed')
    paths = {k: v['path'] for k, v in receipt['inputs'].items()}
    result, local = compute(paths, load(paths['policy']))
    if (encode(result) != (directory/'inventory.json').read_bytes() or receipt['local_inputs'] != local
            or receipt['output_sha256'] != sha(directory/'inventory.json')):
        raise ValueError('Junction inventory independent replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in ('parent-inventory', 'junction-run', 'policy', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    paths = dict(parent_inventory=args.parent_inventory/'inventory.json', parent_receipt=args.parent_inventory/'inventory-receipt.json',
                 junction_graph=args.junction_run/'graph_with_edges.json', junction_receipt=args.junction_run/'pending-native-junction-audit.json', policy=args.policy)
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
