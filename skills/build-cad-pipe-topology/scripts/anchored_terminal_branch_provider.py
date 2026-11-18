"""Adopt only actually rendered drawing-context correspondences, not devices."""
import copy
from legacy_named_provider_inventory import require

def adopt_provider(original,proof,effective):
    result=copy.deepcopy(original);by={r['edge_id']:r for r in result['records']};values={r['edge_id']:r['values']for r in effective};targets={r['axis_edge_id']:r for r in proof['records']}
    require(len(targets)==len(proof['records']),'duplicate anchored branch writers')
    for eid,r in targets.items():
        row=by[eid];actual=values[eid]
        require(not row['has_existing_correspondence']and not row['correspondence_observations'],'old drawing branch provider cannot be replaced')
        require(actual.get('anchored_branch_mapping_id')==r['mapping_id']and actual.get('anchored_branch_plan_edge')==r['plan_edge_id']and actual.get('anchored_branch_plan_pipe_XY_mm')==r['plan_horizontal_projection']['value_mm'],'actual viewer did not adopt native drawing branch context')
        row['correspondence_observations'].append(dict(provider='anchored_terminal_branches',domain='separate_drawing_branch_context',mapping_id=r['mapping_id'],plan_edges=[r['plan_edge_id']],grouped_axis_edges=[eid],floor=r['floor'],remote_equipment_identity_inferred=False,physical_port_verified=False,whole_axis_values_assigned=False))
        row['has_existing_correspondence']=True
    result.update(mode='adopted_anchored_terminal_branch_contexts_v1',new_anchored_terminal_branch_records=copy.deepcopy(proof['records']),human_accepted=False,whole_goal_complete=False)
    result['counts'].update(existing_correspondence_edges=sum(x['has_existing_correspondence']for x in result['records']),mixed_edges_without_any_correspondence=sum(x['classification']=='mixed_horizontal_vertical'and not x['has_existing_correspondence']for x in result['records']),new_anchored_terminal_branch_contexts=len(targets))
    for key in('ordinary_junction_mappings','member_domain_observations','current_component_inventory','current_horizontal_frontier','remaining_horizontal_attributes','all_current_vertical_DN_domains'):
        require(result[key]==original[key],'drawing branch adoption changed ordinary/member/vertical/component identities or horizontal values')
    return result
