"""Fresh both-view service inventory after reviewed local topology changes.

Historical inventories are regression baselines only. Every current service is
read again from native CAD; no historical plan/axis pass flag is transplanted.
"""
import argparse
import collections
import copy
import csv
import importlib
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph, inspect_branch, _caption, unresolved_identity_candidates
from crossview_equipment_branch_inventory_v2 import extend as extend_endpoints
from native_exploded_endpoint_evidence import collect as collect_endpoints
from inherited_circle_branch_inventory import inspect as inspect_inherited_circle

MODE = 'fresh_reviewed_local_graph_branch_inventory_v1'


def checked(item):
    path = Path(item['path']).resolve()
    if sha(path) != item['sha256']:
        raise ValueError('fresh inventory input changed: ' + str(path))
    return path


def inspect_view(doc, graph, equipment, floor, hashes, view, devices, circle_policy=None):
    nodes, _, _ = index_graph(graph)
    captions = [e for e in doc.modelspace().query('TEXT MTEXT') if e.plain_text() == equipment]
    if len(captions) != 1:
        return dict(status='missing_or_ambiguous_native_caption')
    caption = _caption(doc, captions[0].dxf.handle, equipment)
    node = nodes.get(equipment)
    if not node or node.get('node_type') not in ('equipment', 'physical_equipment') or node.get('floor') != floor:
        candidates = unresolved_identity_candidates(doc, graph, equipment, floor)
        return dict(status='unresolved_equipment_identity_candidates' if candidates else 'missing_or_floor_conflicting_equipment',
            caption=caption, retained_native_equipment_candidates=candidates)
    selections = {(r['equipment_id'], r['system']): r for r in (circle_policy or {}).get('selections', [])}
    if len(selections) != len((circle_policy or {}).get('selections', [])):
        raise ValueError('duplicate inherited native circle selection')
    services = {}
    for system in ('supply', 'return'):
        selected = selections.get((equipment, system)) if view == 'plan' else None
        if selected:
            service = inspect_inherited_circle(doc, graph, equipment, system,
                hashes['source_sha256'], hashes['graph_sha256'], circle_policy)
            if service['trace']['tee'] != selected['node_id'] or service['trace']['edges'] != [selected['edge_id']]:
                raise ValueError('current inherited-circle path no longer matches its native control scope')
        else:
            service = inspect_branch(doc, graph, equipment, system, hashes, view, devices)
        services[system] = service
    return dict(status='native_caption_read', caption=caption, services=services)


def compare_ready(current, baseline):
    old = {r['equipment_id']: r for r in baseline['records']}
    new = {r['equipment_id']: r for r in current['records']}
    if len(old) != len(baseline['records']) or len(new) != len(current['records']) or set(old) != set(new):
        raise ValueError('equipment inventory changed instead of preserving all native instances')
    regressions, gains = [], []
    for did in old:
        for view in ('plan', 'iso'):
            for system in ('supply', 'return'):
                before = old[did]['views'].get(view, {}).get('services', {}).get(system, {})
                after = new[did]['views'].get(view, {}).get('services', {}).get(system, {})
                if before.get('ready_for_mapping_comparison') and not after.get('ready_for_mapping_comparison'):
                    regressions.append(dict(equipment_id=did, view=view, system=system, current=after))
                if not before.get('ready_for_mapping_comparison') and after.get('ready_for_mapping_comparison'):
                    gains.append(dict(equipment_id=did, view=view, system=system))
    return dict(regressions=regressions, gains=gains, historical_pass_flags_reused=False)


def verify_local_plan(graph_path, expected_mode):
    graph = load(graph_path)
    if expected_mode == 'reviewed_interface_owners':
        if 'sourceReviewedInterfaceOwners' not in graph:
            raise ValueError('current plan lacks reviewed owner root')
        from attach_reviewed_interface_owners import verify_output
    elif expected_mode == 'reviewed_drawing_gaps':
        if 'sourceReviewedDrawingGapContinuity' not in graph:
            raise ValueError('current plan lacks reviewed gap root')
        from reconstruct_reviewed_plan_gaps import verify_output
    else:
        raise ValueError('unsupported current plan proof mode')
    audit = verify_output(graph_path.parent)
    if audit['output_graph_sha256'] != sha(graph_path):
        raise ValueError('fresh local plan native replay differs')
    return audit


def compute(manifest, announce=lambda message: None):
    axis_paths = {k: checked(v) for k, v in manifest['axis'].items()}
    endpoint_policy_path = checked(manifest['endpoint_policy'])
    plans = manifest['plans']
    floors = [p['floor'] for p in plans]
    if len(floors) != len(set(floors)) or any(isinstance(f, bool) or not isinstance(f, int) for f in floors):
        raise ValueError('explicit distinct floor scopes required')
    prefix = manifest['equipment_prefix']
    if not isinstance(prefix, str) or not prefix:
        raise ValueError('explicit equipment prefix required')
    axis_doc, axis_readable = read_source(axis_paths['source'])
    axis_graph = load(axis_paths['graph'])
    # The fixed native local axis is checked once for this batch, then its
    # individual service paths are freshly checked below for every floor.
    from reconstruct_native_block_branches import verify_output as verify_axis
    announce('Native Chinese axis readable; independently replaying fixed local axis')
    axis_audit = verify_axis(axis_paths['graph'].parent)
    if (axis_audit['output_graph_sha256'] != sha(axis_paths['graph'])
            or axis_audit['inputs']['source']['sha256'] != sha(axis_paths['source'])
            or axis_audit['inputs']['inventory']['sha256'] != sha(axis_paths['devices'])):
        raise ValueError('native local axis graph differs')
    with axis_paths['devices'].open(encoding='utf-8-sig', newline='') as stream:
        devices = list(csv.DictReader(stream))
    axis_hashes = dict(source_sha256=sha(axis_paths['source']), graph_sha256=sha(axis_paths['graph']),
                       inventory_sha256=sha(axis_paths['devices']))
    # This is fresh native evidence, not a copy of an old endpoint receipt.
    announce('Fixed local axis replayed; reading exploded endpoint controls from native CAD')
    endpoint_evidence = collect_endpoints(axis_doc, axis_graph, devices, load(endpoint_policy_path), axis_hashes)
    outputs, baseline_diffs = {}, {}
    local_inputs = {}
    for settings in plans:
        floor = settings['floor']
        paths = {k: checked(settings[k]) for k in ('source', 'graph', 'devices', 'baseline_inventory', 'baseline_receipt')}
        circle_policy = load(checked(settings['circle_policy'])) if settings.get('circle_policy') else None
        if circle_policy and circle_policy['plan_source_sha256'] != sha(paths['source']):
            raise ValueError('inherited native circle controls belong to another drawing')
        doc, readable = read_source(paths['source'])
        announce(f'{floor}F: Chinese readable; independently replaying current local plan')
        audit = verify_local_plan(paths['graph'], settings['mode'])
        baseline_receipt = load(paths['baseline_receipt'])
        if baseline_receipt['output_sha256'] != sha(paths['baseline_inventory']):
            raise ValueError('historical inventory bytes differ from the comparison baseline receipt')
        old_inputs = baseline_receipt.get('local_inputs', baseline_receipt['inputs'])
        if (old_inputs['plan_source']['sha256'] != sha(paths['source'])
                or old_inputs['plan_graph']['sha256'] != audit['inputs']['graph']['sha256']
                or any(old_inputs[k]['sha256'] != axis_hashes[n] for k, n in
                       [('iso_source', 'source_sha256'), ('iso_graph', 'graph_sha256'), ('iso_devices', 'inventory_sha256')])):
            raise ValueError('historical comparison baseline is not this native parent/axis scope')
        if sha(paths['devices']) != sha(paths['graph'].parent / 'assigned_edge_device_instances.csv'):
            raise ValueError('current canonical plan inventory differs')
        graph = load(paths['graph'])
        if graph.get('metadata', {}).get('source_sha256') != sha(paths['source']):
            raise ValueError('current graph source differs')
        plan_hashes = dict(source_sha256=sha(paths['source']), graph_sha256=sha(paths['graph']))
        selected = sorted({n['node_id'] for g in (graph, axis_graph) for n in g['nodes']
            if n.get('node_type') in ('equipment', 'physical_equipment') and n['node_id'].startswith(prefix) and n.get('floor') == floor})
        if not selected:
            raise ValueError('empty native equipment floor scope')
        announce(f'{floor}F: local proof replayed; freshly inspecting {len(selected)} equipment in both views')
        records = []
        for did in selected:
            views = dict(plan=inspect_view(doc, graph, did, floor, plan_hashes, 'plan', [], circle_policy),
                         iso=inspect_view(axis_doc, axis_graph, did, floor, axis_hashes, 'iso', devices))
            records.append(dict(equipment_id=did, floor=floor, views=views,
                ready_for_mapping_comparison=all(views[v].get('services', {}).get(s, {}).get('ready_for_mapping_comparison', False)
                    for v in ('plan', 'iso') for s in ('supply', 'return'))))
        result = dict(status='source_comparison_inventory_not_mapping', records=records,
            counts=dict(equipment=len(records), ready_for_mapping_comparison=sum(r['ready_for_mapping_comparison'] for r in records)),
            source_preflight=dict(plan=readable, iso=axis_readable), local_graphs_mutated=False,
            mapped_paths=0, human_accepted=False, hil_ready=False,
            source_evidence_implementation_sha256=implementation_hashes())
        # Existing v2 composition rechecks precise native endpoint records;
        # its source evidence was freshly collected above on the current axis.
        result = extend_endpoints(result, endpoint_evidence)
        result['inventory_mode'] = MODE
        result['fresh_current_source_checks'] = dict(plan_services=2*len(records), axis_services=2*len(records),
            historical_pass_flags_reused=False, native_local_proofs_replayed=True, physical_ports_verified=False,
            physical_values_assigned=0, human_accepted=False)
        diff = compare_ready(result, load(paths['baseline_inventory']))
        result['historical_ready_comparison'] = diff
        outputs[str(floor)] = result
        baseline_diffs[str(floor)] = diff
        local_inputs[str(floor)] = dict(plan_source=dict(path=str(paths['source']), sha256=plan_hashes['source_sha256']),
            plan_graph=dict(path=str(paths['graph']), sha256=plan_hashes['graph_sha256']),
            iso_source=manifest['axis']['source'], iso_graph=manifest['axis']['graph'], iso_devices=manifest['axis']['devices'],
            plan_devices=settings['devices'])
        announce(f'{floor}F: complete fresh inspection; ready={result["counts"]["ready_for_mapping_comparison"]}, regressions={len(diff["regressions"])}')
    return dict(mode=MODE, floors=outputs, local_inputs=local_inputs, baseline_diffs=baseline_diffs,
        current_sources_mutated=False, old_inventories_mutated=False, native_axis_stage_replayed_once=True,
        source_pass_flags_preloaded=False, mapped_paths=0, human_accepted=False, hil_ready=False)


def implementation_hashes():
    names = ('crossview_equipment_branch_inventory', 'crossview_equipment_branch_inventory_v2',
        'native_exploded_endpoint_evidence', 'inherited_circle_branch_inventory',
        'native_inherited_duplicate_circle_evidence', 'source_readability', 'reconstruct_native_block_branches',
        'attach_reviewed_interface_owners', 'reconstruct_reviewed_plan_gaps', 'native_path_coverage_audit',
        'native_line_path_evidence', 'native_junction_ray_evidence', 'native_sideview_equipment_branch_evidence')
    return dict({name: sha(importlib.import_module(name).__file__) for name in names}, entry=sha(__file__))


def verify_output(directory):
    directory = Path(directory)
    receipt = load(directory / 'inventory-receipt.json')
    if receipt['mode'] != MODE or receipt['implementation_sha256'] != implementation_hashes():
        raise ValueError('fresh inventory implementation changed')
    manifest = checked(receipt['manifest'])
    result = compute(load(manifest))
    if (encode(result) != (directory / 'inventory-batch.json').read_bytes()
            or receipt['output_sha256'] != sha(directory / 'inventory-batch.json')):
        raise ValueError('fresh inventory independent native replay differs')
    for floor, value in result['floors'].items():
        if encode(value) != (directory / floor / 'inventory.json').read_bytes():
            raise ValueError('fresh floor inventory differs')
    if any(d['regressions'] for d in result['baseline_diffs'].values()):
        raise ValueError('fresh inventory has unresolved historical readiness regressions')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify-output', type=Path)
    args = parser.parse_args()
    if args.verify_output:
        if args.manifest or args.output:
            parser.error('verification cannot override archived inputs')
        verify_output(args.verify_output)
        print('fresh three-floor native inventory independently replayed', flush=True)
        return
    if not args.manifest or not args.output:
        parser.error('fixed manifest and new output required')
    if args.output.exists():
        raise FileExistsError(args.output)
    result = compute(load(args.manifest), lambda text: print(text, flush=True))
    args.output.mkdir(parents=True)
    (args.output / 'inventory-batch.json').write_bytes(encode(result))
    for floor, value in result['floors'].items():
        (args.output / floor).mkdir()
        (args.output / floor / 'inventory.json').write_bytes(encode(value))
    (args.output / 'inventory-receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(args.manifest.resolve()), sha256=sha(args.manifest)),
        implementation_sha256=implementation_hashes(), local_inputs=result['local_inputs'],
        output_sha256=sha(args.output / 'inventory-batch.json'), human_accepted=False, hil_ready=False)))
    if any(d['regressions'] for d in result['baseline_diffs'].values()):
        raise RuntimeError('historically ready services regressed; retain complete native inventory for diagnosis')
    print({floor: value['counts'] for floor, value in result['floors'].items()}, flush=True)


if __name__ == '__main__':
    main()
