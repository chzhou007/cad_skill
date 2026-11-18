"""Reconcile the frontier from the actual facade without adding correspondences."""
import collections,copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from alias_aware_provider_inventory import COMPLETE_FIELDS,positive
EXTRA_COMPLETE=('cycle_gate_complete_centerline_mm','riser_header_complete_centerline_mm','cohort_member_complete_centerline_mm','contact_owner_complete_centerline_mm','anchored_metric_complete_centerline_mm','complementary_plan_centerline_mm','alias_member_horizontal_complete_centerline_mm','plan_crossover_complete_XY_centerline_mm')

def reconcile(provider,effective,context):
    out=copy.deepcopy(provider);values={r['edge_id']:r['values']for r in effective};rows={r['edge_id']:r for r in provider['records']};oldfront={r['edge_id']:r for r in provider['remaining_horizontal_attributes']}
    if values.keys()!=rows.keys()or len(values)!=len(effective):raise ValueError('current provider/effective population differs')
    ranges={r['axis_edge_id']:r for r in context['reviewed_uniform_subroute_DN']['records']};pending=[];complete=[];lengths=0;states=collections.Counter();floor_states=collections.defaultdict(collections.Counter)
    for eid,row in rows.items():
        if row['classification']!='horizontal_only':continue
        v=values[eid];known=v.get('diameter_nominal_mm');length=any(positive(v.get(k))for k in COMPLETE_FIELDS+EXTRA_COMPLETE);lengths+=length
        state='both_known'if positive(known)and length else'only_length_missing'if positive(known)else'only_DN_missing'if length else'both_missing';states[state]+=1
        if state=='both_known':complete.append(eid);continue
        if eid not in oldfront:raise ValueError('published complete horizontal edge lost effective values: '+eid)
        r=copy.deepcopy(oldfront[eid]);r['attributes']=copy.deepcopy(v);r['known_whole_DN']=known if positive(known)else None;r['complete_centerline']=bool(length);floor_states[str(r['floor'])][state]+=1
        if eid in ranges:
            source=ranges[eid]
            if not source['whole_horizontal_edge']or known!=source['nominal_mm']or v.get('uniform_subroute_DN_scope_id')!=source['source_scope_id']:raise ValueError('reviewed uniform DN not actually effective')
            r['reviewed_range_scope_id']=source['source_scope_id'];r['individual_internal_node_identity_assigned']=False;r['next_scope']='reviewed_range_per_edge_length_allocation_unresolved'
        pending.append(r)
    out['history_before_effective_frontier']=dict(counts=copy.deepcopy(provider['counts']),frontier=copy.deepcopy(provider['current_horizontal_frontier']),remaining=copy.deepcopy(provider['remaining_horizontal_attributes']))
    out['remaining_horizontal_attributes']=pending;counts=out['counts'];counts.update(current_effective_whole_DN_known=sum(positive(v.get('diameter_nominal_mm'))for v in values.values()),pure_horizontal_complete_DN_and_centerline=len(complete),pure_horizontal_complete_centerline=lengths,pure_horizontal_remaining_attributes=len(pending),horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in pending)))
    out['current_horizontal_frontier'].update(status='actual_effective_primary_fields_reconciled_with_qualified_range_scopes',pure_horizontal_complete=len(complete),pure_horizontal_complete_centerline=lengths,pure_horizontal_remaining_attributes=len(pending),records=copy.deepcopy(pending),remaining_by_floor=dict(collections.Counter(str(r['floor'])for r in pending)),remaining_by_next_scope=counts['horizontal_next_scopes'],actual_effective_state_counts=dict(states),actual_remaining_states_by_floor={f:dict(v)for f,v in floor_states.items()})
    out['current_primary_fields_reconciled']=True;out['new_correspondences_assigned']=0;out['individual_range_node_identities_assigned']=0;out['physical_values_assigned']=0
    for key in ['records','ordinary_junction_mappings','member_domain_observations','all_current_vertical_DN_domains','current_component_inventory']:
        if out[key]!=provider[key]:raise ValueError('provider reconciliation changed source identities or vertical/component domains')
    return out
