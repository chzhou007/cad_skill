"""Use each old mapping's original evidence domain after component correction."""
import copy
from anchor_bounded_main_paths import component_profiles
from crossview_equipment_branch_inventory import inspect_branch
from main_continuity_plan_DN import bind

MODE='native_contact_owner_existing_scope_requalification_v1'

def logical_branch(original,observation,plan_check,axis_check,mapping,plan_edge,plan_profile,axis_profile):
    if original.get('kind')!='equipment_branch'or original['plan_edges']!=observation['plan_edges']or original['iso_edges']!=observation.get('grouped_axis_edges'):
        raise ValueError('old equipment mapping scope differs')
    for checked,edges in ((plan_check,original['plan_edges']),(axis_check,original['iso_edges'])):
        if checked.get('ready_for_mapping_comparison')is not True or checked.get('trace',{}).get('status')!='unique_graph_service_to_T'or checked['trace']['edges']!=edges:
            raise ValueError('old logical equipment branch no longer independently witnessed')
    if mapping.get(plan_check['trace']['tee'])!=axis_check['trace']['tee']:
        raise ValueError('equipment branch changed its independent T identity')
    if plan_check.get('physical_ports_verified')is True or axis_check.get('physical_ports_verified')is not False:
        raise ValueError('logical scope cannot claim unshown physical ports')
    if plan_profile==[{}]:
        owner=(plan_edge.get('source_layout_equipment_interface')or plan_edge.get('confirmed_equipment_interface')or plan_edge.get('source_sideview_equipment_interface'))
        user_logical=owner and owner.get('confirmation',{}).get('confirmed_by')=='user'and owner.get('physical_port_verified')is False
        if not owner or owner.get('physical_port_verified')is True or plan_edge.get('path_length_complete')is not False or not(plan_check.get('logical_ownership_basis')or user_logical):
            raise ValueError('empty plan profile has no explicit limited interface domain')
        comparison='plan_logical_interface_does_not_render_axis_inline_details'
    else:
        if plan_profile!=axis_profile:raise ValueError('explicit equipment detail component profile differs')
        comparison='same_explicit_native_component_profile'
    return dict(equipment_id=original['equipment_id'],mapping_id=original['mapping_id'],plan_edges=copy.deepcopy(original['plan_edges']),axis_edges=copy.deepcopy(original['iso_edges']),comparison_domain=comparison,status='same_source_checked_logical_port_mapping_retained',physical_unshown_length_assigned=False,related_confirmation_inherited=False,human_accepted=False)

def requalify(provider,inventory,docs,graphs,plan_components,hashes,plan_reader,old_batch,floor):
    if inventory.get('all_component_ids_and_counts_conserved')is not True or inventory.get('source_graph_and_symbol_geometry_unchanged')is not True or inventory.get('equipment_membership_retained')is not True:raise ValueError('complete conserved native correction required')
    old_ids={change['before']['edge_id']for change in inventory['changes']};new_ids={change['after']['edge_id']for change in inventory['changes']};affected=old_ids|new_ids
    batches={row['mapping_id']:row for row in old_batch['floors'][str(floor)]['records']}
    ae={edge['edge_id']:edge for edge in graphs['iso']['edges']};pe={edge['edge_id']:edge for edge in graphs['plan']['edges']};plan_inspector=bind(inspect_branch,native_tee=plan_reader)
    records=[];unique=set()
    for current in provider['records']:
        eid=current['edge_id']
        if eid not in affected or not current['has_existing_correspondence']:continue
        if str(ae[eid].get('floor_start'))!=str(floor)or str(ae[eid].get('floor_end'))!=str(floor):raise ValueError('changed scope needs its exact floor owner')
        unique.add(eid)
        for observation in current['correspondence_observations']:
            if observation['domain']!='ordinary_local_graph'or str(observation.get('floor',floor))!=str(floor):raise ValueError('changed member or other-floor scope needs its original owner')
            plan_ids=observation['plan_edges'];axis_ids=observation.get('grouped_axis_edges',[eid]);expected=component_profiles(plan_components,plan_ids);actual=component_profiles(inventory['components'],axis_ids)
            if eid in old_ids:
                original=batches.get(observation['mapping_id'])
                if original is None or len(plan_ids)!=1:raise ValueError('changed equipment branch lacks original correspondence')
                equipment,system=original['equipment_id'],original['system']
                if ae[eid]['system']!=system or pe[plan_ids[0]]['system']!=system:raise ValueError('old equipment mapping changed service')
                plan=plan_inspector(docs['plan'],graphs['plan'],equipment,system,hashes['plan'],'plan',plan_components)
                axis=inspect_branch(docs['iso'],graphs['iso'],equipment,system,hashes['iso'],'iso',inventory['components'])
                row=logical_branch(original,observation,plan,axis,provider['ordinary_junction_mappings'][str(floor)],pe[plan_ids[0]],expected,actual)
                records.append(dict(row,axis_edge_id=eid,plan_native_check=plan,axis_native_check=axis,plan_profile=expected,axis_profile=actual))
            else:
                if expected!=actual:raise ValueError('current scoped main component profile differs')
                records.append(dict(axis_edge_id=eid,mapping_id=observation['mapping_id'],plan_edges=copy.deepcopy(plan_ids),axis_edges=copy.deepcopy(axis_ids),plan_profile=expected,axis_profile=actual,comparison_domain='original_ordinary_path_scope',status='current_native_component_profiles_agree',related_confirmation_inherited=False,human_accepted=False))
    expected={row['edge_id']for row in provider['records']if row['edge_id']in affected and row['has_existing_correspondence']}
    if unique!=expected:raise ValueError('partial affected correspondence requalification')
    return dict(mode=MODE,records=records,affected_axis_edges=sorted(affected),requalified_old_axis_edges=sorted(unique),counts=dict(old_axis_edges=len(unique),old_scope_observations=len(records),logical_equipment_branches=sum(row['status']=='same_source_checked_logical_port_mapping_retained'for row in records)),all_old_affected_scopes_requalified=True,new_correspondences_assigned=0,source_graphs_mutated=False,human_accepted=False)
