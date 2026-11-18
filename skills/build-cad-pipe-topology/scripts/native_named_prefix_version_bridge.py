"""Prove old named upper-floor scopes unchanged after verified paired waves.

Reuse the historical correspondence and current local reconstruction owners.
Emit separate source/version evidence; do not rewrite mappings or fused values.
"""
import argparse
import math
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from match_source_checked_crossview_paths import selected_snapshot
from match_named_riser_floor_segments import through_role
from crossview_equipment_branch_inventory import service_route
from named_riser_plan_attributes import named_annotation_domain
from plan_pipe_diameter_scopes import catalog
from checked_plan_DN_scope_attributes import attribute_checked_scope
from touching_plan_path_coverage import audit as audit_paths
from native_touching_plan_path_chunks import measured_scopes
import named_upper_floor_plan_attributes as historical_owner
import inherited_wave_pair_continuity as current_owner

MODE = 'native_named_upper_prefix_version_preservation_v1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def native_signature(value):
    if isinstance(value, dict):
        return {k: native_signature(v) for k, v in value.items() if k != 'graph_sha256'}
    if isinstance(value, list):
        return [native_signature(v) for v in value]
    return value


def scope_values(stored, diameter, metrics):
    old = stored.get('records', [])
    require(len(old) == 4 and len({r['mapping_id'] for r in old}) == 4, 'Four distinct historical named scopes required')
    dn = {r['edge_id']: r for r in diameter['records']}
    lengths = {r['scope_id']: r['horizontal_projection'] for r in metrics['measured_scopes']}
    require(len(lengths) == len(metrics['measured_scopes']) == 4, 'Metric scope writer repeated or missing')
    plan_ids, axis_ids, result = set(), set(), []
    for row in old:
        require(len(row['plan_edges']) == len(row['iso_edges']) == 1, 'Named scope must preserve its separate pipe path')
        pid, aid = row['plan_edges'][0], row['iso_edges'][0]
        require(pid not in plan_ids and aid not in axis_ids, 'Named pipe scope counted twice')
        plan_ids.add(pid)
        axis_ids.add(aid)
        require(dn.get(pid) == row['diameter'] and lengths.get(row['mapping_id']) == row['horizontal_projection'],
            'Current native DN or XY differs; rebuild affected attributes')
        metric = lengths[row['mapping_id']]
        require(type(metric.get('value_mm')) in (int, float) and math.isfinite(metric['value_mm'])
            and metric['value_mm'] > 0 and metric.get('installed_whole_edge_length_mm') is None
            and metric.get('unshown_connection_length_mm') is None,
            'Native XY cannot certify installed or omitted connector length')
        value = dn[pid]['nominal_mm']
        require(type(value) in (int, float) and math.isfinite(value) and value > 0,
            'Preservation cannot fill unknown or invalid DN')
        require(row.get('whole_axis_DN_selected') is False and row.get('whole_axis_physical_length_mm') is None
            and row.get('physical_port_verified') is False and row.get('human_accepted') is False,
            'Historical scope claims physical or human acceptance')
        result.append(dict(mapping_id=row['mapping_id'], floor=row['floor'], system=row['system'],
            plan_edges=list(row['plan_edges']), iso_edges=list(row['iso_edges']), nominal_mm=value,
            diameter_evidence=dn[pid], horizontal_projection=lengths[row['mapping_id']],
            native_pipe_scope_and_DN_unchanged=True, whole_axis_values_assigned=False,
            physical_ports_verified=False, human_accepted=False))
    require({r['system'] for r in result} == {'supply', 'return'}
        and len({r['floor'] for r in result}) == 1, 'Named services or floor differ')
    return result


def replay_scopes(doc, graph, old, mapping, stored, policy, metric_policy, source_hash, graph_hash, old_hash):
    wave = graph.get('sourceInheritedWavePairContinuity', {})
    require(wave.get('mode') == current_owner.MODE and wave.get('source_sha256') == source_hash
        and wave.get('input_graph_sha256') == old_hash and wave.get('unpaired_continuations_inferred') is False
        and type(wave.get('physical_lengths_assigned')) is int and wave['physical_lengths_assigned'] == 0
        and wave.get('human_accepted') is False, 'One independently replayed paired-wave child required')
    require(stored.get('mode') == historical_owner.MODE and stored.get('graph_sha256') == old_hash
        and mapping.get('graph_sha256', {}).get('plan') == old_hash
        and mapping.get('source_sha256', {}).get('plan') == source_hash
        and graph.get('metadata', {}).get('source_sha256') == source_hash,
        'Historical/current plan source or original correspondence differs')
    floor = mapping['floor']
    ids = [eid for row in mapping['records'] for eid in row['plan_edges']]
    require(len(ids) == len(set(ids)) == 4, 'Four independent named pipe scopes required')
    require(selected_snapshot(graph, ids) == selected_snapshot(old, ids),
        'Selected pipe, endpoint or attribute geometry changed')
    junctions, roles, branches, mains, services = {}, [], [], [], []
    require(len(mapping['floor_interface_correspondences']) == 2, 'Both independent services required')
    for interface in mapping['floor_interface_correspondences']:
        system = interface['system']
        trace = service_route(graph, interface['equipment_id'], system)
        require(trace == service_route(old, interface['equipment_id'], system)
            and trace['status'] == 'unique_graph_service_to_T', 'Local equipment service changed')
        services.append(dict(system=system, equipment_id=interface['equipment_id'], trace=trace))
        for kind, nid in [('network', interface['plan_network_T']), ('equipment', interface['plan_equipment_T'])]:
            fresh = through_role(doc, graph, nid, system, source_hash, graph_hash)
            require(native_signature(fresh) == native_signature(interface['native_roles']['plan'][kind]),
                'Native T, source ray, branch ownership or through role changed')
            require(nid not in junctions, 'Named T reused across services')
            junctions[nid] = fresh['native_T']
            branches.append(dict(edge_id=fresh['off_edge'], tee=nid, system=system,
                role='named_RIF' if kind == 'network' else 'equipment_context'))
            roles.append(dict(node_id=nid, role=kind, proof=fresh))
        selected = [r['plan_edges'] for r in mapping['records'] if r['system'] == system
            and r['kind'] == 'named_riser_floor_segment_network_link']
        require(len(selected) == 1, 'Unique existing named main required')
        mains += selected[0]
    named = named_annotation_domain(doc, graph,
        dict(records=[dict(native_names=r['native_names']) for r in mapping['floor_interface_correspondences']]),
        source_hash, graph_hash)
    texts, annotations = catalog(doc, graph, mains + [r['edge_id'] for r in branches], source_hash, graph_hash)
    texts = [r for r in texts if r['handle'] not in set(named['consumed_text_handles'])]
    group = dict(group_id='current_named_upper_prefix_preservation', floor=floor, main_edges=mains, branches=branches,
        seeds=policy['seeds'], line_F_frames=policy.get('line_F_frames', []))
    diameter = attribute_checked_scope(doc, graph, group, texts, source_hash, graph_hash,
        set(annotations['F_text_handles']), junctions=junctions, verified_taps=sorted(junctions),
        path_auditor=audit_paths, verified_nonpipe_annotation_strokes=named['consumed_stroke_handles'])
    specs = [dict(scope_id=r['mapping_id'], floor=floor, system=r['system'], plan_edges=r['plan_edges']) for r in mapping['records']]
    metrics = measured_scopes(doc, graph, dict(view_kind='floor_plan', floor=floor, edges=ids, records=specs,
        source_sha256=source_hash, graph_sha256=graph_hash), metric_policy, source_hash, graph_hash)
    return dict(mode=MODE, status='native_current_named_prefix_scopes_preserved_mapping_adoption_pending',
        source_sha256=source_hash, current_plan_graph_sha256=graph_hash, historical_plan_graph_sha256=old_hash,
        records=scope_values(stored, diameter, metrics), native_roles=roles, independent_local_service_traces=services,
        named_annotation_domain=named, source_annotation_inventory=annotations,
        fresh_diameter_scope=diameter, fresh_metric_scope=metrics, selected_plan_snapshot_unchanged=True,
        graph_mutated=False, new_mappings=0, new_physical_values_assigned=0,
        related_HIL_confirmation_inherited=False, human_accepted=False, hil_ready=False)


def implementation_hashes():
    result = historical_owner.implementation_hashes()
    for name, digest in current_owner.implementation_hashes().items():
        require(name not in result or result[name] == digest, 'Conflicting inherited implementation identity')
        result[name] = digest
    root = Path(historical_owner.__file__).parent
    for name in ('named_riser_plan_attributes.py', 'native_touching_plan_path_chunks.py',
                 'checked_plan_DN_scope_attributes.py', 'touching_plan_path_coverage.py'):
        result[name] = sha(root / name)
    result[Path(__file__).name] = sha(__file__)
    return result


def compute(paths):
    old_run = Path(paths['historical_scope']).parent
    new_run = Path(paths['current_graph']).parent
    require(Path(paths['historical_scope']).name == 'upper-floor-plan-attributes.json'
        and Path(paths['historical_receipt']).resolve() == old_run.resolve() / 'upper-floor-plan-attribute-receipt.json'
        and Path(paths['current_receipt']).resolve() == new_run.resolve() / 'inherited-wave-receipt.json',
        'Canonical native source parents required')
    stored = historical_owner.verify_output(old_run)
    current = current_owner.verify_output(new_run)
    inputs = load(paths['historical_receipt'])['inputs']
    require(sha(paths['current_graph']) == current['output_graph_sha256']
        and current['inputs']['graph'] == inputs['graph'] and current['inputs']['source'] == inputs['source'],
        'The verified current child is not the historical scope local parent')
    doc, preflight = read_source(Path(inputs['source']['path']))
    result = replay_scopes(doc, load(paths['current_graph']), load(inputs['graph']['path']),
        load(inputs['mapping']['path']), stored, load(inputs['policy']['path']), load(inputs['metric_policy']['path']),
        inputs['source']['sha256'], sha(paths['current_graph']), inputs['graph']['sha256'])
    result.update(source_preflight=preflight, historical_attribute_scope_sha256=sha(paths['historical_scope']),
        original_mapping_sha256=inputs['mapping']['sha256'], both_native_parent_ancestries_replayed=True)
    return result


def check_result(result):
    require(result.get('mode') == MODE and result.get('both_native_parent_ancestries_replayed') is True
        and result.get('status') == 'native_current_named_prefix_scopes_preserved_mapping_adoption_pending',
        'Native prefix preservation proof required')
    for key in ('graph_mutated', 'related_HIL_confirmation_inherited', 'human_accepted', 'hil_ready'):
        require(result.get(key) is False, 'Preservation cannot promote graph or acceptance')
    for key in ('new_mappings', 'new_physical_values_assigned'):
        require(type(result.get(key)) is int and result[key] == 0, 'Preservation cannot add mappings or values')
    require(len(result.get('records', [])) == 4, 'Complete four-scope result required')
    rows = result['records']
    require(len({r.get('mapping_id') for r in rows}) == 4
        and {r.get('system') for r in rows} == {'supply', 'return'}, 'Distinct paired source scopes required')
    for row in rows:
        require(row.get('native_pipe_scope_and_DN_unchanged') is True
            and all(row.get(k) is False for k in ('whole_axis_values_assigned', 'physical_ports_verified', 'human_accepted')),
            'Preserved source row claims physical or human acceptance')
    return dict(status='pending', source_replay='passed', preserved_named_scopes=4,
        new_mappings=0, new_physical_values_assigned=0, human_accepted=False, hil_ready=False,
        pending=['Adopt current source/version evidence into the complete parent, source comparison and viewer'])


def verify_output(directory):
    directory = Path(directory)
    receipt = load(directory / 'prefix-version-bridge-receipt.json')
    require(receipt.get('mode') == MODE and receipt['implementation_sha256'] == implementation_hashes(),
        'Prefix preservation implementation differs')
    require(all(sha(r['path']) == r['sha256'] for r in receipt['inputs'].values()), 'Prefix parent evidence changed')
    result = compute({k: r['path'] for k, r in receipt['inputs'].items()})
    target = directory / 'prefix-version-bridge.json'
    require(encode(result) == target.read_bytes() and sha(target) == receipt['output_sha256'],
        'Prefix preservation independent native replay differs')
    check_result(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--historical-attributes-run', type=Path, required=True)
    parser.add_argument('--current-plan-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Output already exists')
    paths = dict(historical_scope=args.historical_attributes_run / 'upper-floor-plan-attributes.json',
        historical_receipt=args.historical_attributes_run / 'upper-floor-plan-attribute-receipt.json',
        current_graph=args.current_plan_run / 'graph_with_edges.json',
        current_receipt=args.current_plan_run / 'inherited-wave-receipt.json')
    pins = {k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()}
    result = compute(paths)
    check_result(result)
    require(all(sha(r['path']) == r['sha256'] for r in pins.values()), 'Parent changed during replay')
    args.output.mkdir(parents=True)
    target = args.output / 'prefix-version-bridge.json'
    target.write_bytes(encode(result))
    (args.output / 'prefix-version-bridge-receipt.json').write_bytes(encode(dict(mode=MODE, inputs=pins,
        implementation_sha256=implementation_hashes(), output_sha256=sha(target), human_accepted=False)))
    print(dict(preserved_named_scopes=4, both_native_parent_ancestries_replayed=True,
        new_mappings=0, human_accepted=False), flush=True)


if __name__ == '__main__':
    main()
