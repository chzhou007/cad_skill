"""Apply original complete-plan DN and metric owners to native anchored chains."""
import collections,copy,hashlib
from confirm_crossview_paths import encode
from legacy_named_provider_inventory import require
from cycle_gate_plan_lengths import qualify
from member_external_anchored_routes import scoped_components,ordered_components

MODE='source_checked_complementary_plan_attribute_application_v1'

def qualify_row(row,group,graphs,local_DN,profiles,units,angles,bindings):
    require(row['kind']=='native_complementary_anchored_chain_topology'and row['attribute_adoption_allowed']is True
            and row['source_detail_difference']is False and row['physical_values_assigned']==0,'chain component or topology scope is not attribute-qualified')
    pe=next(e for e in graphs['plan']['edges']if e['edge_id']==row['plan_edges'][0]);ae=next(e for e in graphs['iso']['edges']if e['edge_id']==row['axis_edge_id'])
    dn=next(r for r in local_DN['records']if r['edge_id']==pe['edge_id'])
    require(dn['scope_paths']==pe['attribute_paths']and dn['system']==row['system'],'local plan DN belongs to another pipe scope')
    if dn['nominal_mm']is not None:require(dn['status']in('direct_plan_DN','T_through_inherited_plan_DN','T_branch_inherited_plan_DN','reviewed_plan_DN_scope'),'unqualified local diameter status')
    native=copy.deepcopy(group['native']['plan']['path_coverage']);native['edges']=[e for e in native['edges']if e['edge_id']==pe['edge_id']]
    item=dict(row,classification='horizontal_only',native_path_evidence=dict(plan=native))
    metric=qualify(graphs['plan'],graphs['iso'],item,units,angles)
    scopes={v:scoped_components(profiles[v],edge['attribute_paths'],edge['edge_id'])for v,edge in [('plan',pe),('axis',ae)]}
    paths={}
    for v,edge,start in [('plan',pe,row['plan_start']),('axis',ae,row['iso_start'])]:
        paths[v]=copy.deepcopy(edge['path_points'])
        if edge['start_node_id']!=start:paths[v].reverse()
    pairs=ordered_components(scopes,paths)
    require(scopes['plan']['profile']==scopes['axis']['profile']==row['component_profiles']['plan']==row['component_profiles']['iso'],'native whole-interval component profiles changed')
    return dict(metric,source_scope_id='COMPLEMENTARY-ATTRIBUTE:'+row['mapping_id'],original_correspondence=copy.deepcopy(row),
                nominal_mm=dn['nominal_mm'],DN_status=dn['status'],plan_DN_record=copy.deepcopy(dn),
                ordered_native_component_pairs=pairs,source_bindings=copy.deepcopy(bindings),
                actual_current_T_DN_owner_reapplied=True,original_metric_readers_reused=True,
                related_HIL_confirmation_inherited=False,axis_labels_used_to_choose_horizontal_DN=False,
                vertical_values_assigned=0,physical_installed_length_mm=None,net_pipe_cut_length_mm=None,
                source_graphs_mutated=False,human_accepted=False)

def adopt_provider(original,proof,effective):
    result=copy.deepcopy(original);target={r['axis_edge_id']:r for r in proof['records']};values={r['edge_id']:r['values']for r in effective};remaining=[];completed=[]
    for old in original['remaining_horizontal_attributes']:
        row=copy.deepcopy(old);record=target.get(row['edge_id'])
        if record:
            require(row['complete_centerline']is False and row['known_whole_DN']is None,'complementary attributes overwrite an old known value')
            actual=values[row['edge_id']]
            require(actual.get('complementary_plan_centerline_mm')==record['complete_horizontal_centerline_mm']and actual.get('complementary_mapping_id')==record['source_scope_id'],'actual reader did not adopt native length and correspondence')
            require(actual.get('complementary_plan_DN_mm','')==(''if record['nominal_mm']is None else record['nominal_mm']),'actual reader did not adopt the exact local DN')
            if record['nominal_mm']is not None:require(actual.get('diameter_nominal_mm')==record['nominal_mm'],'whole-edge DN was not adopted by the actual reader')
            row['complete_centerline']=True;row['known_whole_DN']=record['nominal_mm'];row['attributes'].update({k:v for k,v in actual.items()if k.startswith('complementary_')or k.startswith('diameter_')})
            if record['nominal_mm']is not None:completed.append(row['edge_id']);continue
            row['next_scope']='known_complementary_metric_current_plan_DN_conflict'if record['DN_status']=='conflict'else'known_complementary_metric_plan_DN_unresolved'
        remaining.append(row)
    require(set(target)<={r['edge_id']for r in original['remaining_horizontal_attributes']},'new metric is outside current horizontal frontier')
    result.update(mode=MODE,remaining_horizontal_attributes=remaining,new_complementary_attribute_complete_axis_edges=sorted(completed),
                  complementary_plan_attribute_observations=copy.deepcopy(proof['records']),human_accepted=False,whole_goal_complete=False)
    frontier=result['current_horizontal_frontier'];frontier.update(records=remaining,pure_horizontal_complete=frontier['pure_horizontal_complete']+len(completed),
        pure_horizontal_complete_centerline=frontier['pure_horizontal_complete_centerline']+len(target),pure_horizontal_remaining_attributes=len(remaining),
        remaining_by_next_scope=dict(collections.Counter(r['next_scope']for r in remaining)),remaining_by_floor=dict(collections.Counter(str(r['floor'])for r in remaining)))
    result['counts'].update(pure_horizontal_complete_DN_and_centerline=frontier['pure_horizontal_complete'],pure_horizontal_complete_centerline=frontier['pure_horizontal_complete_centerline'],pure_horizontal_remaining_attributes=len(remaining),horizontal_next_scopes=frontier['remaining_by_next_scope'])
    require(all(result[k]==original[k]for k in('records','member_domain_observations','ordinary_junction_mappings','current_component_inventory')),'attribute adoption changed topology, member or axis component owners')
    return result
