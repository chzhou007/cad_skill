"""Recompute plan DN and XY evidence after native wave topology reconstruction.

Reuse the inherited attribute kernel for independently mapped corridors. Old
calibrations supply native controls, never acceptance of a new graph version.
Axis values, vertical lengths and unresolved view differences remain separate.
"""
import argparse,copy,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from match_wave_rebased_circle_paths import BATCH_SCHEMA,verify_output as verify_mapping
from inherited_circle_plan_attributes import attribute

MODE='wave_rebased_plan_DN_and_XY_groups_v1'
METRIC_KEYS=('view_kind','plan_window','floor_title_handle','floor_title','unit_dimensions')


def pinned(spec):
    if sha(spec['path'])!=spec['sha256']:raise ValueError('native attribute configuration origin changed')
    return load(spec['path'])


def configuration(spec,source_hash,graph_hash,parent_hash):
    original=pinned(spec['calibration_origin']);metric=pinned(spec['metric_origin'])
    if original.get('source_sha256')!=source_hash or original.get('graph_sha256')!=parent_hash:
        raise ValueError('calibration controls do not belong to the exact native wave parent')
    scope=copy.deepcopy(spec['scope']);seeds=scope.get('seeds',[])
    known={r['text_handle']:r for r in original.get('selections',[])}
    if (not seeds or len({r['text_handle'] for r in seeds})!=len(seeds)
        or any(row!=known.get(row['text_handle']) for row in seeds)):
        raise ValueError('source seed is not an unchanged explicitly calibrated selection')
    if scope.get('qualified_component_DN'):raise ValueError('component-qualified labels require their dedicated attribute entry')
    calibration=copy.deepcopy(original);calibration.update(graph_sha256=graph_hash,selections=copy.deepcopy(seeds))
    scope['group_id']=spec['group_id']
    return scope,calibration,{key:metric[key] for key in METRIC_KEYS}


def attribute_groups(doc,graph,mapping,policy,source_hash,graph_hash):
    if (mapping.get('mode')!=BATCH_SCHEMA or mapping.get('plan_graph_sha256')!=graph_hash
        or mapping.get('source_sha256',{}).get('plan')!=source_hash or mapping.get('physical_values_assigned')!=0
        or mapping.get('local_graphs_mutated') is not False or mapping.get('human_accepted') is not False):
        raise ValueError('current independently replayed wave mapping batch required')
    parent_hash=mapping['evidence']['native_wave_inventory_rebase']['old_plan_graph_sha256']
    groups=mapping['groups'];settings=policy.get('groups',[])
    if (not groups or len({g['group_id'] for g in groups})!=len(groups)
        or len({s['group_id'] for s in settings})!=len(settings)
        or {g['group_id'] for g in groups}!={s['group_id'] for s in settings}):
        raise ValueError('every independent mapped corridor needs exactly one attribute configuration')
    configured={s['group_id']:s for s in settings};results=[];rows=[];used_edges=set();used_mappings=set();before=encode(graph)
    flattened=[dict(row,group_id=group['group_id']) for group in groups for row in group['records']]
    if flattened!=mapping['records']:raise ValueError('mapping batch and independent records disagree')
    for group in groups:
        spec=configured[group['group_id']];scope,calibration,metric=configuration(spec,source_hash,graph_hash,parent_hash)
        result=attribute(doc,graph,group,scope,calibration,metric,source_hash,graph_hash)
        current_edges=[eid for row in result['records'] for eid in row['plan_edges']];current_ids=[row['mapping_id'] for row in result['records']]
        if (len(current_edges)!=len(set(current_edges)) or used_edges.intersection(current_edges)
            or len(current_ids)!=len(set(current_ids)) or used_mappings.intersection(current_ids)):
            raise ValueError('plan attribute writer overlaps an independent corridor')
        if set(current_ids)!={row['mapping_id'] for row in group['records']}:raise ValueError('mapped plan attribute scope lost')
        used_edges.update(current_edges);used_mappings.update(current_ids)
        result.update(group_id=group['group_id'],configuration_origin=copy.deepcopy(spec))
        results.append(result);rows.extend(dict(row,group_id=group['group_id']) for row in result['records'])
    if encode(graph)!=before:raise ValueError('plan attribute recomputation mutated local topology')
    return dict(mode=MODE,status='native_plan_DN_XY_recomputed_view_comparison_and_fusion_pending',groups=results,records=rows,
        source_sha256=source_hash,graph_sha256=graph_hash,iso_graph_sha256=mapping['iso_graph_sha256'],
        equipment_scope=list(mapping['equipment_scope']),historical_mapping_lineage=[dict(row,group_id=group['group_id']) for group in groups for row in group['historical_mapping_lineage']],
        old_calibration_acceptance_reused=False,local_graphs_mutated=False,physical_values_fused=False,
        whole_axis_DN_assigned=0,installed_lengths_assigned=0,axis_conflicts_resolved=False,human_accepted=False,hil_ready=False)


def compute(paths,policy):
    for key in ('mapping','mapping_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('wave attribute mapping input changed '+key)
    folder=Path(paths['mapping']).resolve().parent
    if Path(paths['mapping']).resolve()!=folder/'mapping.json' or Path(paths['mapping_receipt']).resolve()!=folder/'source-mapping-receipt.json':
        raise ValueError('noncanonical wave attribute mapping')
    mapping=verify_mapping(folder);receipt=load(paths['mapping_receipt']);local=receipt['local_inputs']
    for key in ('plan_source','plan_graph'):
        if sha(local[key]['path'])!=local[key]['sha256']:raise ValueError('current wave plan dependency changed '+key)
    doc,preflight=read_source(local['plan_source']['path']);graph=load(local['plan_graph']['path'])
    result=attribute_groups(doc,graph,mapping,policy,local['plan_source']['sha256'],local['plan_graph']['sha256'])
    result.update(source_preflight=preflight,mapping_sha256=sha(paths['mapping']))
    return result


def implementation_hashes():
    from match_wave_rebased_circle_paths import implementation_hashes as mapping_hashes
    from inherited_circle_plan_attributes import implementation_hashes as attribute_hashes
    result=mapping_hashes();result.update(attribute_hashes());result[Path(__file__).name]=sha(__file__)
    return result


def check_result(data):
    """Keep a validated batch pending until view conflicts and fusion close."""
    if (data.get('mode')!=MODE or data.get('status')!='native_plan_DN_XY_recomputed_view_comparison_and_fusion_pending'
        or any(data.get(k) is not False for k in ('old_calibration_acceptance_reused','local_graphs_mutated','physical_values_fused','axis_conflicts_resolved','human_accepted','hil_ready'))
        or data.get('whole_axis_DN_assigned')!=0 or data.get('installed_lengths_assigned')!=0):
        raise ValueError('wave plan attribute batch escaped its source-only state')
    groups=data['groups'];equipment=[];rows=[];ids=[];plan_ids=[]
    if not groups or len({g['group_id'] for g in groups})!=len(groups):raise ValueError('independent attribute groups missing or repeated')
    for group in groups:
        selected=group['records'];members=group['equipment_scope']
        if (group['graph_sha256']!=data['graph_sha256'] or group['source_sha256']!=data['source_sha256']
            or len(members)<3 or len(members)!=len(set(members)) or len(selected)!=4*len(members)-2):
            raise ValueError('independent DN/XY corridor source or extent differs')
        for system in ('supply','return'):
            services=[r for r in selected if r['system']==system]
            if (sum(r['kind']=='equipment_branch' for r in services)!=len(members)
                or sum(r['kind']=='main_between_equipment_branches' for r in services)!=len(members)-1):
                raise ValueError('paired DN/XY corridor service incomplete')
        for row in selected:
            diameter=row['diameter'];metric=row['horizontal_projection'];value=diameter.get('nominal_mm');length=metric.get('value_mm')
            if (row['floor']!=group['floor'] or len(row['plan_edges'])!=1 or not row['iso_edges']
                or diameter['edge_id']!=row['plan_edges'][0] or diameter['system']!=row['system'] or not diameter.get('lineage')
                or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (value,length))
                or any(row.get(k) is not False for k in ('physical_source_identity_resolved','physical_ports_verified','whole_axis_DN_selected','human_accepted'))
                or row.get('whole_axis_physical_length_mm') is not None or metric.get('installed_whole_edge_length_mm') is not None
                or metric.get('unshown_connection_length_mm') is not None or not metric.get('pieces')):
                raise ValueError('plan attribute escaped its source DN/XY domain')
        equipment.extend(members);rows.extend(dict(row,group_id=group['group_id']) for row in selected)
        ids.extend(row['mapping_id'] for row in selected);plan_ids.extend(eid for row in selected for eid in row['plan_edges'])
    if (rows!=data['records'] or equipment!=data['equipment_scope'] or len(equipment)!=len(set(equipment))
        or len(ids)!=len(set(ids)) or len(plan_ids)!=len(set(plan_ids))):raise ValueError('batch attribute writers or flattened scope differ')
    return dict(status='pending',source_replay='passed',mapped_DN_XY_scopes=len(rows),equipment=len(equipment),independent_groups=len(groups),
        graph_sha256=data['graph_sha256'],source_sha256=data['source_sha256'],mapping_sha256=data['mapping_sha256'],
        local_graphs_mutated=False,physical_values_fused=False,axis_conflicts_resolved=False,installed_lengths_assigned=0,human_accepted=False,hil_ready=False,
        pending=['Compare source DN extents, rebuild dependent fusion and viewer, preserve unresolved conflicts and historical HIL'])


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'wave-plan-attribute-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('wave plan attribute implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('wave plan attribute input changed')
    paths={key:item['path'] for key,item in receipt['inputs'].items()};result=compute(paths,load(paths['policy']));target=directory/'wave-plan-attributes.json'
    if encode(result)!=target.read_bytes() or sha(target)!=receipt['output_sha256']:raise ValueError('wave plan attribute native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('mapping-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(mapping=a.mapping_run/'mapping.json',mapping_receipt=a.mapping_run/'source-mapping-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'wave-plan-attributes.json';target.write_bytes(encode(result))
    (a.output/'wave-plan-attribute-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(groups=len(result['groups']),plan_DN_XY_scopes=len(result['records']),physical_values_fused=False),flush=True)


if __name__=='__main__':main()
