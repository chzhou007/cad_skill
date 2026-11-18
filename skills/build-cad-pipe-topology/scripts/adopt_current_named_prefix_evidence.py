"""Attach current source/version evidence without replacing old pipe values.

The native bridge and complete axis parent independently replay in compute().
The local plan, axis topology, every existing attribute and component remain
exactly restorable. Source comparison/viewer/HIL are downstream obligations.
"""
import argparse
import copy
import re
import shutil
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
from native_named_prefix_version_bridge import verify_output as verify_bridge, check_result, implementation_hashes as bridge_hashes
from attach_upper_floor_plan_attributes import selected_path

MODE = 'current_named_upper_prefix_evidence_fusion_v1'
ROOT = 'sourceCurrentNamedUpperPrefixEvidence'
FIELD = 'current_named_prefix_source_evidence'
AUDIT = 'current-named-prefix-evidence-fusion-audit.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def restore(graph, parent):
    stage = graph.get(ROOT, {})
    require(stage.get('mode') == MODE and stage.get('prior_topology_components_and_all_attributes_preserved') is True
        and stage.get('human_accepted') is False and stage.get('related_HIL_confirmation_inherited') is False
        and type(stage.get('new_mappings')) is int and stage['new_mappings'] == 0
        and type(stage.get('new_physical_values_assigned')) is int and stage['new_physical_values_assigned'] == 0,
        'Current prefix fusion changes old physical or acceptance state')
    rows = {r['axis_edge']: r for r in stage.get('records', [])}
    require(len(rows) == len(stage.get('records', [])) == 4, 'Four distinct current prefix writers required')
    result = copy.deepcopy(graph)
    result.pop(ROOT)
    found = set()
    for edge in result['edges']:
        if FIELD in edge:
            eid = edge['edge_id']
            require(eid in rows and edge[FIELD] == rows[eid], 'Current prefix edge/root evidence differs')
            edge.pop(FIELD)
            found.add(eid)
    require(found == set(rows) and result == parent,
        'Current prefix fusion changed old nodes, paths, attributes, metadata or components')
    return result


def append(parent, bridge, hashes):
    check_result(bridge)
    require(ROOT not in parent and parent.get('metadata', {}).get('hil_ready') is False,
        'Current prefix evidence already present or parent claims HIL acceptance')
    require(set(hashes) == {'parent', 'bridge'} and all(isinstance(v, str)
        and re.fullmatch('[0-9a-f]{64}', v) for v in hashes.values()), 'Invalid current prefix evidence hashes')
    old_scope = parent.get('sourceUpperFloorPlanSegmentAttributes', {})
    require(old_scope.get('source_scope_sha256') == bridge['historical_attribute_scope_sha256']
        and old_scope.get('mapping_sha256') == bridge['original_mapping_sha256']
        and old_scope.get('human_accepted') is False,
        'Complete parent uses another historical named scope')
    current_scopes = parent.get('sourceWaveRebasedPlanScopeAdoption', {}).get('records', [])
    require(current_scopes and {r['plan_graph_sha256'] for r in current_scopes}
        == {bridge['current_plan_graph_sha256']}, 'Complete parent has another current upper-floor plan')
    old_rows = {r['mapping_id']: r for r in old_scope.get('records', [])}
    require(len(old_rows) == 4 and set(old_rows) == {r['mapping_id'] for r in bridge['records']},
        'Historical named mapping scope changed or repeated')
    result = copy.deepcopy(parent)
    edges = {e['edge_id']: e for e in result['edges']}
    require(len(edges) == len(result['edges']) and not any(FIELD in e for e in result['edges']),
        'Repeated edge or preexisting prefix evidence writer')
    rows = []
    for proof in bridge['records']:
        old = old_rows[proof['mapping_id']]
        require(len(proof['iso_edges']) == 1, 'Current prefix must retain its single axis scope')
        eid = proof['iso_edges'][0]
        edge = edges[eid]
        require(edge.get('plan_segment_attributes') == [old]
            and old['edge_id'] == eid and old['plan_edges'] == proof['plan_edges']
            and old['floor'] == proof['floor'] and old['system'] == proof['system'] == edge['system']
            and old['nominal_mm'] == proof['nominal_mm']
            and old['diameter_evidence'] == proof['diameter_evidence']
            and old['horizontal_projection'] == proof['horizontal_projection']
            and old['local_graph_sha256']['plan'] == bridge['historical_plan_graph_sha256']
            and old['source_sha256']['plan'] == bridge['source_sha256']
            and old.get('human_accepted') is False and old.get('physical_port_verified') is False,
            'Current native proof differs from the exact retained segment attributes')
        selected_path(edge, dict(path_index=old['path_index'], segment_indices=old['segment_indices'],
            scope_paths=[old['scope_points']]))
        item = dict(mode=MODE, status='current_named_upper_prefix_source_checked_hil_pending',
            axis_edge=eid, mapping_id=proof['mapping_id'], floor=proof['floor'], system=proof['system'],
            plan_edges=list(proof['plan_edges']), source_sha256=bridge['source_sha256'],
            current_plan_graph_sha256=bridge['current_plan_graph_sha256'],
            historical_plan_graph_sha256=bridge['historical_plan_graph_sha256'],
            historical_attribute_scope_sha256=bridge['historical_attribute_scope_sha256'],
            original_mapping_sha256=bridge['original_mapping_sha256'],
            native_prefix_bridge_sha256=hashes['bridge'], complete_parent_graph_sha256=hashes['parent'],
            native_DN_XY_and_source_paths_preserved=True, values_replaced=False,
            related_HIL_confirmation_inherited=False, physical_ports_verified=False, human_accepted=False)
        edge[FIELD] = item
        rows.append(copy.deepcopy(item))
    stage = dict(mode=MODE, status='current_named_prefix_provenance_composed_source_comparison_viewer_HIL_pending',
        records=rows, parent_graph_sha256=hashes['parent'], native_prefix_bridge_sha256=hashes['bridge'],
        current_source_scopes=len(rows), prior_topology_components_and_all_attributes_preserved=True,
        new_mappings=0, new_physical_values_assigned=0, related_HIL_confirmation_inherited=False,
        human_accepted=False)
    result[ROOT] = stage
    restore(result, parent)
    return result, stage


def parent_owner():
    import attach_known_junction_main_plan_attributes as owner
    return owner


def compute(paths, policy):
    require(all(sha(p) == policy.get(k+'_sha256') for k, p in paths.items() if k != 'policy'),
        'Current prefix fusion input changed')
    parent = Path(paths['parent_graph'])
    directory = Path(paths['bridge']).parent
    require(parent.name == 'graph_with_edges.json' and Path(paths['devices']).resolve()
        == parent.resolve().parent / 'edge_device_instances.csv'
        and Path(paths['bridge']).name == 'prefix-version-bridge.json'
        and Path(paths['bridge_receipt']).resolve() == directory.resolve() / 'prefix-version-bridge-receipt.json',
        'Canonical complete parent, component table and native bridge required')
    native = verify_bridge(directory)
    verified_parent = parent_owner().verify_output(parent.parent)
    require(verified_parent['output_graph_sha256'] == sha(parent)
        and verified_parent['inputs']['devices']['sha256'] == sha(paths['devices']),
        'Complete parent or component inventory differs')
    graph, stage = append(load(parent), native, dict(parent=sha(parent), bridge=sha(paths['bridge'])))
    require(all(sha(p) == policy[k+'_sha256'] for k, p in paths.items() if k != 'policy'),
        'Fusion input changed during native replay')
    return graph, dict(stage=stage, verified_complete_parent=verified_parent,
        parent_graph=dict(path=str(parent.resolve()), sha256=sha(parent)),
        native_prefix_bridge=dict(path=str(Path(paths['bridge']).resolve()), sha256=sha(paths['bridge'])),
        native_local_graph=verified_parent['native_local_graph'])


def implementation_hashes():
    result = parent_owner().implementation_hashes()
    for name, digest in bridge_hashes().items():
        require(name not in result or result[name] == digest, 'Inherited implementation identity conflicts')
        result[name] = digest
    result[Path(__file__).name] = sha(__file__)
    return result


def verify_output(directory):
    directory = Path(directory)
    audit = load(directory / AUDIT)
    require(audit.get('mode') == MODE and audit['implementation_sha256'] == implementation_hashes(),
        'Current prefix fusion implementation differs')
    require(all(sha(r['path']) == r['sha256'] for r in audit['inputs'].values()), 'Fusion parent input differs')
    paths = {k: r['path'] for k, r in audit['inputs'].items()}
    graph, proof = compute(paths, load(paths['policy']))
    target = directory / 'graph_with_edges.json'
    require(encode(graph) == target.read_bytes() and sha(target) == audit['output_graph_sha256']
        and all(audit.get(k) == v for k, v in proof.items()), 'Current prefix fusion native replay differs')
    require((directory / 'edge_device_instances.csv').read_bytes() == Path(paths['devices']).read_bytes(),
        'Current prefix fusion component inventory differs')
    return audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Output already exists')
    policy = load(args.policy)
    paths = {k: Path(r['path']) for k, r in policy['inputs'].items()}
    paths['policy'] = args.policy
    graph, proof = compute(paths, policy)
    args.output.mkdir(parents=True)
    target = args.output / 'graph_with_edges.json'
    target.write_bytes(encode(graph))
    shutil.copy2(paths['devices'], args.output / 'edge_device_instances.csv')
    shutil.copy2(paths['parent_graph'].parent / 'source-comparison-gate.json', args.output / 'source-comparison-gate.json')
    (args.output / AUDIT).write_bytes(encode(dict(proof, mode=MODE,
        inputs={k: dict(path=str(p.resolve()), sha256=sha(p)) for k, p in paths.items()},
        implementation_sha256=implementation_hashes(), output_graph_sha256=sha(target),
        source_comparison_pending=True, hil_ready=False, human_accepted=False)))
    print(dict(current_source_scopes=4, prior_values_preserved=True, new_mappings=0, human_accepted=False), flush=True)


if __name__ == '__main__':
    main()
