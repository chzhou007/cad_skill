"""Apply existing qualified plan DN to independently paired member intervals.

Unresolved annotation scopes and native DN conflicts remain unknown. Metric
completeness comes from the new native source batch, never a display span or
the older generic extent helper's scalar length shortcut.
"""
import copy,math
from native_main_endpoint_extent import qualify
from attach_anchored_floor_main_attributes import horizontal_domain

MODE='native_equivalent_member_plan_attribute_application_v1'

def fragment_extent(plan,axis,row):
    edge=next(e for e in plan['edges']if e['edge_id']==row['plan_edges'][0]);paths=edge['attribute_paths'];nodes={n['node_id']:n for n in plan['nodes']};ends=[nodes[n]for n in(row['plan_start'],row['plan_end'])]
    if {edge['start_node_id'],edge['end_node_id']}!={row['plan_start'],row['plan_end']}or any(n.get('node_type')not in('tee','physical_junction')or n.get('floor')!=row['floor']or n.get('review_required')is True for n in ends):raise ValueError('member DN needs both independently checked current T extents')
    p,q=paths[0][0],paths[-1][-1]
    if not any(all(math.dist(v,[n['x'],n['y']])<=.05 for v,n in zip(points,ends))for points in((p,q),(q,p))):raise ValueError('native member fragments do not cover both T centres')
    gaps=any(math.dist(a[-1],b[0])>.05 for a,b in zip(paths,paths[1:]))
    proof=row['native_metric'].get('source_evidence',{})
    if gaps and (proof.get('status')!='native_source_paths_and_excluded_crossovers_replayed'or not proof.get('crossovers')):raise ValueError('DN across a source omission requires its original crossover replay')
    return dict(mode='original_native_batch_fragment_endpoints_and_axis_horizontal_scope',plan_original_attribute_paths=copy.deepcopy(paths),both_original_T_extents_checked=True,source_gap_native_evidence=copy.deepcopy(proof)if gaps else None,source_gap_length_assigned=False,source_paths_changed=False)

def apply(batch,local_DN,plan,axis,raw,rendered,angles,DN_reapplication=None):
    if (batch.get('complete_parent_rechecked')is not True or batch.get('source_graphs_mutated')is not False
        or batch.get('physical_pipe_count_inferred')is not False or batch.get('DN_used_for_mapping')is not False
        or batch.get('human_accepted')is not False):raise ValueError('source-qualified complete member batch required')
    pe={e['edge_id']:e for e in plan['edges']};ae={e['edge_id']:e for e in axis['edges']};re={e['edge_id']:e for e in raw['edges']};ve={e['edge_id']:e for e in rendered['edges']};out=[]
    seen=set();origins={r['edge_id']:r for r in(DN_reapplication or{}).get('records',[])}
    for row in batch['records']:
        if len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1:raise ValueError('one-to-one source interval required')
        pid,eid=row['plan_edges'][0],row['iso_edges'][0];edge=pe[pid];dn=local_DN[pid]
        if eid in seen:raise ValueError('competing equivalent member interval writer')
        seen.add(eid)
        if dn['system']!=row['system']or dn['scope_paths']!=edge['attribute_paths']:raise ValueError('qualified local DN scope differs from source interval')
        if any(ae[eid].get(k)!=re[eid].get(k)or re[eid].get(k)!=ve[eid].get(k)for k in('edge_id','start_node_id','end_node_id','system','attribute_paths')):raise ValueError('native axis extent differs from raw or rendered graph')
        nominal=dn.get('nominal_mm');extent=None
        if nominal is not None:
            # This existing helper checks native undirected T extents and the
            # actual axis horizontal directions. DN matching was already done.
            read_scope=dict(row,kind='same_floor_T_to_T_main')
            if len(edge['attribute_paths'])==1:extent=qualify(plan,axis,read_scope,nominal,row['native_metric'].get('projection'),angles)
            else:
                horizontal_domain(axis,read_scope,angles);extent=fragment_extent(plan,axis,row)
            state='native_specific_plan_DN_reapplied'if origins.get(pid,{}).get('specific_native_domain_applied')else'existing_qualified_native_plan_DN_retained'
        else:state='native_plan_DN_conflict'if dn.get('status')=='conflict'else'existing_native_annotation_provider_application_pending'
        complete=row['complete_horizontal_centerline_mm']
        if complete is not None and row['incomplete_reasons']:raise ValueError('incomplete native plan metric cannot become complete')
        if extent is not None and complete is not None and 'complete_horizontal_centerline_route_mm'in extent and extent['complete_horizontal_centerline_route_mm']!=complete:raise ValueError('existing source extent and complete native metric differ')
        out.append(dict(mapping_id=row['mapping_id'],axis_edge_id=eid,plan_edge_id=pid,floor=row['floor'],system=row['system'],axis_nodes=[ae[eid]['start_node_id'],ae[eid]['end_node_id']],axis_attribute_paths=copy.deepcopy(ae[eid]['attribute_paths']),plan_nodes=[row['plan_start'],row['plan_end']],plan_attribute_paths=copy.deepcopy(edge['attribute_paths']),nominal_mm=nominal,DN_status=state,qualified_plan_DN_record=copy.deepcopy(dn),previous_general_DN_record=copy.deepcopy(origins.get(pid,{}).get('previous_general_record')),native_extent_check=extent,drawn_plan_projection_mm=row['drawn_plan_projection_mm'],complete_horizontal_centerline_mm=complete,incomplete_reasons=copy.deepcopy(row['incomplete_reasons']),source_member_observation_ids=copy.deepcopy(row['source_member_observation_ids']),native_mapping=copy.deepcopy(row),installed_length_mm=None,net_pipe_cut_length_mm=None,vertical_values_assigned=0,source_paths_mutated=False,DN_used_for_mapping=False,related_HIL_confirmation_inherited=False,human_accepted=False))
    if len(out)!=batch['counts']['new_axis_intervals']:raise ValueError('partial new member population')
    return out
