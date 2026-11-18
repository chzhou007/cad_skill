"""Recompute calibrated plan DN scopes on current native corridor mappings."""
import argparse
import copy
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from current_graph_calibrated_dn import collect as calibrated_collect
from match_junction_rebased_corridors import MODE as MAPPING_MODE, verify_output as verify_mapping
from plan_pipe_diameter_scopes import catalog, group_evidence
from qualified_inline_DN_evidence import collect as component_collect
from source_checked_plan_path_coverage import audit as audit_paths
from source_direct_dn_evidence import collect as strict_collect
from source_readability import read_source

MODE = 'junction_rebased_calibrated_plan_DN_scopes_v1'


def check_scope(mapping, scope):
    equipment = {b['equipment_id'] for b in scope['branches']}
    matches = [g for g in mapping['groups'] if set(g['equipment_scope']) == equipment and g['floor'] == scope['floor']]
    if len(matches) != 1:
        raise ValueError('Original DN scope has no unique current corridor group')
    group = matches[0]
    branches = {(b['edge_id'], b['tee'], b['equipment_id'], b['system']) for b in scope['branches']}
    current = {(r['plan_edges'][0], r['plan_start'], r['equipment_id'], r['system']) for r in group['records'] if r['kind'] == 'equipment_branch'}
    mains = {r['plan_edges'][0] for r in group['records'] if r['kind'] == 'main_between_equipment_branches'}
    if (any(len(r['plan_edges']) != 1 for r in group['records']) or branches != current or set(scope['main_edges']) != mains):
        raise ValueError('Current DN branch/main source scope changed')
    return group['group_id']


def attribute(doc, graph, original, mapping, origin_scope, origin_calibration, source_hash, graph_hash, original_hash):
    if (mapping.get('mode') != MAPPING_MODE or mapping.get('plan_graph_sha256') != graph_hash
            or mapping['source_sha256']['plan'] != source_hash or mapping.get('human_accepted') is not False
            or origin_scope.get('graph_sha256') != original_hash or origin_scope.get('source_sha256') != source_hash
            or not origin_scope.get('expert_T_inheritance_rule')):
        raise ValueError('Current native mapping and exact original calibrated scope required')
    groups = origin_scope['groups']
    associations = [check_scope(mapping, scope) for scope in groups]
    if len(set(associations)) != len(groups) or set(associations) != {g['group_id'] for g in mapping['groups']}:
        raise ValueError('Complete independent current DN group coverage required')
    ids = [eid for g in groups for eid in g['main_edges']+[b['edge_id'] for b in g['branches']]]
    if len(ids) != len(set(ids)):
        raise ValueError('DN groups overlap physical plan writers')
    bindings = calibrated_collect(doc, graph, original, origin_calibration, source_hash, graph_hash, original_hash)
    allowed = {r['text_handle']: r for r in origin_calibration['selections']}

    def direct(document, current, selection, sh, gh):
        selected = selection['selections']
        if all(s['text_handle'] in allowed for s in selected):
            if any(s != allowed[s['text_handle']] for s in selected):
                raise ValueError('Calibrated target differs from exact native origin')
            return calibrated_collect(document, current, original, dict(origin_calibration, selections=selected), sh, gh, original_hash)
        if any(s['text_handle'] in allowed for s in selected):
            raise ValueError('Mixed calibrated and strict DN selections require separate calls')
        return strict_collect(document, current, selection, sh, gh)

    texts, annotation_inventory = catalog(doc, graph, ids, source_hash, graph_hash)
    component_strokes = ()
    if origin_scope.get('qualified_component_DN'):
        qualifier = copy.deepcopy(origin_scope['qualified_component_DN'])
        if qualifier['graph_sha256'] != original_hash or qualifier['source_sha256'] != source_hash:
            raise ValueError('Component DN qualification origin differs')
        qualifier['graph_sha256'] = graph_hash
        labels = component_collect(doc, graph, qualifier, source_hash, graph_hash)
        consumed = set(labels['consumed_DN_text_handles'])
        texts = [t for t in texts if t['handle'] not in consumed]
        component_strokes = labels['consumed_leader_handles']
        annotation_inventory['qualified_component_DN'] = labels
    before = encode(graph)
    results = []
    for scope, group_id in zip(groups, associations):
        result = group_evidence(doc, graph, scope, texts, source_hash, graph_hash, set(annotation_inventory['F_text_handles']),
            direct_collector=direct, path_auditor=audit_paths, verified_nonpipe_annotation_strokes=component_strokes)
        result['current_mapping_group_id'] = group_id
        results.append(result)
    if encode(graph) != before:
        raise ValueError('DN recomputation mutated local topology')
    return dict(mode=MODE, status='source_checked_plan_DN_scopes_human_pending', source_sha256=source_hash, graph_sha256=graph_hash,
        original_graph_sha256=original_hash, source_annotation_inventory=annotation_inventory, groups=results,
        records=[r for g in results for r in g['records']], calibrated_direct_binding=bindings,
        local_graph_mutated=False, scope='native_plan_pipe_scopes_only_not_whole_axis_edges_or_unshown_connectors',
        expert_rule=origin_scope['expert_T_inheritance_rule'], physical_values_fused=False, human_accepted=False)


def compute(paths, policy):
    for key in ('mapping', 'mapping_receipt', 'origin_scope', 'origin_calibration', 'origin_graph'):
        if sha(paths[key]) != policy.get(key+'_sha256'):
            raise ValueError('Current plan DN input changed: '+key)
    folder = Path(paths['mapping']).resolve().parent
    if Path(paths['mapping_receipt']).resolve() != folder/'source-mapping-receipt.json' or Path(paths['mapping']).resolve() != folder/'mapping.json':
        raise ValueError('Canonical current mapping required')
    mapping = verify_mapping(folder)
    receipt = load(paths['mapping_receipt']); local = receipt['local_inputs']
    original_hash = sha(paths['origin_graph'])
    if mapping['evidence']['original_plan_graph_sha256'] != original_hash:
        raise ValueError('Control graph is not the current mapping original ancestor')
    for key in ('plan_source', 'plan_graph'):
        if sha(local[key]['path']) != local[key]['sha256']:
            raise ValueError('Current plan source/graph changed')
    scope = load(paths['origin_scope'])
    if scope['calibration_policy_sha256'] != sha(paths['origin_calibration']):
        raise ValueError('Original calibrated scope and control policy differ')
    doc, preflight = read_source(local['plan_source']['path'])
    result = attribute(doc, load(local['plan_graph']['path']), load(paths['origin_graph']), mapping, scope,
        load(paths['origin_calibration']), local['plan_source']['sha256'], local['plan_graph']['sha256'], original_hash)
    result.update(mapping_sha256=sha(paths['mapping']), source_preflight=preflight,
                  original_scope_sha256=sha(paths['origin_scope']), original_calibration_sha256=sha(paths['origin_calibration']))
    return result


def implementation_hashes():
    from match_junction_rebased_corridors import implementation_hashes as mapping_hashes
    from plan_calibrated_DN_scopes import implementation_hashes as attribute_hashes
    values = mapping_hashes(); values.update(attribute_hashes())
    for name in ('junction_rebased_plan_DN_scopes.py', 'current_graph_calibrated_dn.py'):
        values[name] = sha(Path(__file__).with_name(name))
    return values


def verify_output(directory):
    directory = Path(directory); receipt = load(directory/'plan-DN-scope-receipt.json')
    if receipt.get('mode') != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('Current DN implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('Current DN dependency changed')
    paths = {k: v['path'] for k, v in receipt['inputs'].items()}
    result = compute(paths, load(paths['policy']))
    if encode(result) != (directory/'plan-DN-scopes.json').read_bytes() or receipt['output_sha256'] != sha(directory/'plan-DN-scopes.json'):
        raise ValueError('Current DN independent native replay differs')
    return result


def main():
    parser = argparse.ArgumentParser()
    for key in ('mapping-run', 'origin-scope', 'origin-calibration', 'origin-graph', 'policy', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    paths = dict(mapping=args.mapping_run/'mapping.json', mapping_receipt=args.mapping_run/'source-mapping-receipt.json',
        origin_scope=args.origin_scope, origin_calibration=args.origin_calibration, origin_graph=args.origin_graph, policy=args.policy)
    if args.output.exists(): raise FileExistsError(args.output)
    result = compute(paths, load(args.policy)); args.output.mkdir(parents=True)
    target = args.output/'plan-DN-scopes.json'; target.write_bytes(encode(result))
    (args.output/'plan-DN-scope-receipt.json').write_bytes(encode(dict(mode=MODE,
        inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()},
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False)))
    print(dict(plan_edges=len(result['records']), known_DN=sum(r['nominal_mm'] is not None for r in result['records'])), flush=True)


if __name__ == '__main__': main()
