"""Attach current floor-source evidence over the complete published parent.

Keep every historical attribute, topology item and component unchanged. New
source evidence is a separate versioned scope, not an inherited HIL approval.
"""
import argparse
import copy
import hashlib
import shutil
from pathlib import Path

from confirm_crossview_paths import encode, load, sha
from junction_rebased_plan_attributes import verify_output as verify_corridor_attributes
from current_remaining_floor_plan_scopes import verify_output as verify_remaining
from attach_external_feed_plan_attributes import verify_output as verify_parent

MODE = 'current_floor_plan_scope_adoption_v1'
ROOT = 'sourceCurrentFloorPlanScopeAdoption'
FIELD = 'current_floor_plan_scope_evidence'
AUDIT = 'current-floor-plan-scope-adoption-audit.json'


def adopt(parent, stages, evidence, floor, parent_hash):
    if ROOT in parent or any(FIELD in e for e in parent['edges']): raise ValueError('Current floor scopes already adopted')
    existing = {e['edge_id']: e for e in parent['edges']}
    expected = {eid for eid, e in existing.items() if e.get('cross_view_attributes', {}).get('floor') == floor}
    if not expected or len(existing) != len(parent['edges']): raise ValueError('Complete historical floor parent required')
    result = copy.deepcopy(parent); target = {e['edge_id']: e for e in result['edges']}; rows = []; claimed = set(); plan_writers = set()
    plan_hash = None; source_hash = None; axis_hash = None
    for key, stage in stages.items():
        if stage.get('physical_values_fused') is not False or stage.get('human_accepted') is not False: raise ValueError('Source stage already promoted physical values or HIL')
        graph = stage['graph_sha256']; current_plan = graph['plan'] if isinstance(graph, dict) else graph
        sources = stage['source_sha256']; plan_source = sources['plan'] if isinstance(sources, dict) else sources
        current_axis = graph.get('iso') if isinstance(graph, dict) else stage.get('iso_graph_sha256')
        if plan_hash is None: plan_hash, source_hash = current_plan, plan_source
        if current_plan != plan_hash or plan_source != source_hash: raise ValueError('Current floor stages use different plan versions')
        if current_axis is not None:
            if axis_hash is not None and current_axis != axis_hash: raise ValueError('Current floor stages use different local axis versions')
            axis_hash = current_axis
        for row in stage['records']:
            if row['floor'] != floor or len(row['plan_edges']) != 1 or len(row['iso_edges']) != 1: raise ValueError('Current floor scope requires one-to-one declared paths')
            eid = row['iso_edges'][0]; pe = row['plan_edges'][0]
            if eid not in expected or eid in claimed or pe in plan_writers: raise ValueError('Current floor scope has an unexpected or repeated writer')
            claimed.add(eid); plan_writers.add(pe); old = existing[eid]['cross_view_attributes']; dn = row['diameter']; metric = row['horizontal_projection']
            if (any(old[k] != row[k] for k in ('floor', 'system', 'plan_edges', 'iso_edges')) or old.get('human_accepted') is not False
                    or dn['edge_id'] != pe or dn['system'] != row['system'] or dn.get('human_accepted') is not False):
                raise ValueError('Current floor source path, service or historical acceptance differs')
            old_value = old['diameter'].get('plan_drawn_nominal_mm')
            if old_value is None: old_value = (old['diameter'].get('plan_candidate') or {}).get('nominal_mm')
            if (old_value != dn['nominal_mm'] or old['horizontal_projection']['value_mm'] != metric['value_mm']
                    or old['horizontal_projection']['pieces'] != metric['pieces']):
                raise ValueError('Current floor values changed; explicit reconciliation required')
            if old['source_hashes']['plan'] != source_hash: raise ValueError('Historical source drawing changed')
            candidates = []
            for candidate in stage.get('axis_local_DN_candidates', {}).get('observations', []):
                if candidate['edge_id'] != eid: continue
                index = candidate['segment_index']; paths = existing[eid]['attribute_paths']
                if len(paths) != 1 or index < 0 or index+1 >= len(paths[0]): raise ValueError('Axis annotation original segment changed')
                candidates.append(dict(candidate, path_index=0, scope_points=copy.deepcopy(paths[0][index:index+2]),
                    whole_axis_DN_selected=False, inter_floor_riser_proved=False, physical_length_mm=None, human_accepted=False))
            item = dict(current_mapping_id=row['mapping_id'], historical_mapping_id=old['mapping_id'], edge_id=eid,
                mapping_kind=row['kind'], floor=floor, system=row['system'], plan_edges=list(row['plan_edges']), iso_edges=list(row['iso_edges']),
                source_sha256=dict(plan=source_hash, iso=old['source_hashes']['isometric']), plan_graph_sha256=current_plan,
                iso_graph_sha256=old['source_hashes']['local_iso_graph'], prior_plan_graph_sha256=old['source_hashes']['plan_graph'],
                source_scope_sha256=evidence[key]['sha256'], source_scope_path=evidence[key]['path'], source_stage=key,
                diameter=copy.deepcopy(dn), horizontal_projection=copy.deepcopy(metric), axis_local_DN_candidates=candidates,
                historical_attribute_sha256=hashlib.sha256(encode(old)).hexdigest(), historical_attributes=copy.deepcopy(old),
                whole_axis_DN_selected=False, whole_axis_physical_length_mm=None, physical_ports_verified=False,
                equal_plan_axis_segment_extents_proved=False, related_HIL_confirmation_inherited=False, human_accepted=False)
            target[eid][FIELD] = item; rows.append(copy.deepcopy(item))
    if claimed != expected or axis_hash is None or any(r['iso_graph_sha256'] != axis_hash for r in rows):
        raise ValueError('Current floor scopes do not cover the complete declared historical floor')
    stage = dict(mode=MODE, status='current_floor_source_scopes_adopted_complete_parent_hil_pending', floor=floor, records=rows,
        source_scope_files=copy.deepcopy(evidence), plan_graph_sha256=plan_hash, iso_graph_sha256=axis_hash,
        parent_graph_sha256=parent_hash, retained_historical_attributes=len(expected), source_checked_plan_scopes=len(rows),
        known_DN_scopes=sum(r['diameter']['nominal_mm'] is not None for r in rows),
        measured_plan_XY_scopes=sum(r['horizontal_projection']['value_mm'] is not None for r in rows),
        unmeasured_detail_scopes=sum(r['horizontal_projection']['value_mm'] is None for r in rows),
        prior_topology_components_and_all_attributes_preserved=True, whole_values_or_connections_added=0,
        related_HIL_confirmation_inherited=False, human_accepted=False)
    result[ROOT] = stage
    result.setdefault('metadata', {}).update(hil_ready=False, graph_complete=False, review_status='unreviewed_after_current_floor_source_scope_adoption')
    restored = copy.deepcopy(result); restored.pop(ROOT); restored['metadata'] = copy.deepcopy(parent.get('metadata', {}))
    for edge in restored['edges']: edge.pop(FIELD, None)
    if restored != parent: raise ValueError('Current floor evidence changed historical graph or values')
    return result, stage


def compute(paths, policy):
    for key, path in paths.items():
        if key != 'policy' and sha(path) != policy.get(key+'_sha256'): raise ValueError('Floor adoption dependency changed: '+key)
    remaining_dir = Path(paths['remaining']).resolve().parent
    if Path(paths['remaining_receipt']).resolve() != remaining_dir/'remaining-scope-receipt.json': raise ValueError('Canonical remaining scope receipt required')
    remaining = verify_remaining(remaining_dir)
    # The remaining owner independently replays the exact paired DN/XY root.
    rr = load(paths['remaining_receipt']); pairs = rr['inputs']
    if (pairs['paired_attributes']['sha256'] != sha(paths['paired']) or pairs['paired_receipt']['sha256'] != sha(paths['paired_receipt'])
            or remaining['paired_parent_sha256'] != sha(paths['paired'])): raise ValueError('Freshly replayed paired scope differs from adoption input')
    paired = load(paths['paired'])
    corridor_dir = Path(paths['corridor']).resolve().parent
    if Path(paths['corridor_receipt']).resolve() != corridor_dir/'corridor-plan-attribute-receipt.json': raise ValueError('Canonical corridor attribute receipt required')
    corridor = verify_corridor_attributes(corridor_dir)
    parent = verify_parent(Path(paths['parent_graph']).parent)
    if parent['output_graph_sha256'] != sha(paths['parent_graph']) or parent['inputs']['devices']['sha256'] != sha(paths['devices']):
        raise ValueError('Complete axis parent or canonical components changed')
    stages = dict(corridor=corridor, paired=paired, remaining=remaining)
    evidence = {k: dict(path=str(Path(paths[k]).resolve()), sha256=sha(paths[k])) for k in stages}
    graph, stage = adopt(load(paths['parent_graph']), stages, evidence, policy['floor'], sha(paths['parent_graph']))
    if stage['source_checked_plan_scopes'] != policy['expected_scopes']: raise ValueError('Declared floor acceptance scope differs')
    return graph, dict(stage=stage, parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()), sha256=sha(paths['parent_graph'])),
        verified_complete_parent=parent, native_local_graph=parent['native_local_graph'])


def implementation_hashes():
    from current_remaining_floor_plan_scopes import implementation_hashes as remaining_hashes
    from junction_rebased_plan_attributes import implementation_hashes as corridor_hashes
    from attach_external_feed_plan_attributes import implementation_hashes as parent_hashes
    values = remaining_hashes(); values.update(corridor_hashes()); values.update(parent_hashes()); values[Path(__file__).name] = sha(Path(__file__))
    return values


def verify_output(directory):
    directory = Path(directory); audit = load(directory/AUDIT)
    if audit.get('mode') != MODE or audit['implementation_sha256'] != implementation_hashes(): raise ValueError('Floor adoption implementation changed')
    for row in audit['inputs'].values():
        if sha(row['path']) != row['sha256']: raise ValueError('Floor adoption input changed')
    graph, proof = compute({k: r['path'] for k, r in audit['inputs'].items()}, load(audit['inputs']['policy']['path']))
    if encode(graph) != (directory/'graph_with_edges.json').read_bytes() or audit['output_graph_sha256'] != sha(directory/'graph_with_edges.json') or any(audit.get(k) != v for k, v in proof.items()):
        raise ValueError('Floor adoption complete independent replay differs')
    if (directory/'edge_device_instances.csv').read_bytes() != Path(audit['inputs']['devices']['path']).read_bytes(): raise ValueError('Floor adoption changed components')
    return audit


def main():
    p = argparse.ArgumentParser(); p.add_argument('--policy', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); policy = load(a.policy); paths = {k: Path(v['path']) for k, v in policy['inputs'].items()}; paths['policy'] = a.policy
    if a.output.exists(): raise FileExistsError(a.output)
    graph, proof = compute(paths, policy); a.output.mkdir(parents=True); target = a.output/'graph_with_edges.json'; target.write_bytes(encode(graph))
    shutil.copyfile(paths['devices'], a.output/'edge_device_instances.csv')
    shutil.copyfile(Path(paths['parent_graph']).parent/'source-comparison-gate.json', a.output/'source-comparison-gate.json')
    (a.output/AUDIT).write_bytes(encode(dict(proof, mode=MODE, inputs={k: dict(path=str(v.resolve()), sha256=sha(v)) for k, v in paths.items()},
        implementation_sha256=implementation_hashes(), output_graph_sha256=sha(target), human_accepted=False, hil_ready=False)))
    print(dict(current_floor_scopes=proof['stage']['source_checked_plan_scopes'], original_all_attributes_preserved=True, human_accepted=False), flush=True)


if __name__ == '__main__': main()
