"""Batch complete plan XY projections on current independently mapped crossings."""
import copy,csv,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_plan_projection_lengths import unit_evidence
from native_plan_crossover_centerline import measure,MODE
from equivalent_member_source_support import ObservationDocument,equivalent_support
from rebuild_equivalent_member_bounded_batch import verify_output as verify_cohort
from crossview_equipment_branch_inventory import index_graph,native_tee
from legacy_named_provider_inventory import current_plan_reader
from anchor_bounded_main_paths import component_profiles
from attach_anchored_floor_main_attributes import horizontal_domain
from native_main_endpoint_extent import endpoint_relation

def pending_length_edges(report):
    return {eid for group in report['groups']if group['classification']=='horizontal_only'and group['state']in('both_missing','only_length_missing')for eid in group['edge_ids']}

def csvrows(path):
    with Path(path).open(encoding='utf-8-sig',newline='')as stream:return list(csv.DictReader(stream))

def compute(manifest):
    ins=manifest['inputs']
    def checked():
        if any(sha(s['path'])!=s['sha256']for s in ins.values()):raise ValueError('current crossover metric source or parent changed')
    checked();viewer=load(ins['parent_viewer_manifest']['path']);ctx=viewer['attributeValueContext'];provider=load(ins['parent_provider']['path']);axis=load(ins['axis_graph']['path']);axis_doc,axis_text=read_source(ins['axis_source']['path']);an,ae,_=index_graph(axis);ai=csvrows(ins['axis_components']['path']);report=load(ins['current_report']['path'])
    native_binding=ctx['axis_rule_vertical_DN']['source_bindings']
    if report['bundle_id']!=viewer['bundleId']or native_binding['native_graph']!=ins['axis_graph']['sha256']or native_binding['native_source']!=ins['axis_source']['sha256']or viewer['sourceHashes']['main_dxf']!=ins['axis_source']['sha256']:raise ValueError('actual current native axis parent identity differs')
    cohort=verify_cohort(Path(ins['cohort_proof']['path']).parent)
    if encode(cohort)!=Path(ins['cohort_proof']['path']).read_bytes()or ctx['equivalent_member_application']['source_bindings']['batch_proof']!=ins['cohort_proof']['sha256']:raise ValueError('complete original member cohort differs from current parent')
    wanted=pending_length_edges(report);frontier={r['edge_id']:r for r in provider['records']};records=[];pending=[];attempts=[];preflight={};config=load(ins['current_T_source_config']['path'])
    for floor in(1,2,3):
        f=str(floor);source=ins['plan_source_'+f];gp=ins['plan_graph_'+f];plan=load(gp['path']);pn,pe,_=index_graph(plan);doc,preflight[f]=read_source(source['path']);units=unit_evidence(doc,load(ins['unit_policy_'+f]['path']));reader=current_plan_reader(config,source['sha256'],gp['sha256']);pi=csvrows(ins['plan_components_'+f]['path'])
        for eid in sorted(wanted):
            edge=ae[eid]
            if edge['floor_start']!=floor:continue
            observations=[o for o in frontier[eid]['correspondence_observations']if o['domain']=='ordinary_local_graph'and len(o['plan_edges'])==1 and len(o.get('grouped_axis_edges',[eid]))==1]
            applicable=[o for o in observations if pe[o['plan_edges'][0]].get('source_normalized_crossovers')]
            if not applicable:
                pending.append(dict(edge_id=eid,reason='original_unmapped_named_member_inline_or_other_metric_owner_retained'));continue
            row=dict(edge_id=eid,floor=floor)
            try:
                if len(applicable)!=1:raise ValueError('multiple current crossover interval writers')
                obs=applicable[0];pid=obs['plan_edges'][0];plan_edge=pe[pid]
                if obs.get('source_detail_difference'):raise ValueError('source component expression difference retains its original owner')
                aends=[edge['start_node_id'],edge['end_node_id']];pends=[plan_edge['start_node_id'],plan_edge['end_node_id']];mapping=provider['ordinary_junction_mappings'][f]
                if [mapping.get(n)for n in pends]not in(aends,aends[::-1]):raise ValueError('current complete endpoint correspondence differs')
                profiles=dict(plan=component_profiles(pi,[pid])[0],axis=component_profiles(ai,[eid])[0])
                if profiles['plan']!=profiles['axis']:raise ValueError('current native component profiles differ')
                excluded=set();observations_native=[]
                if obs['provider']=='complete_native_equivalent_source_cohort':
                    crows=[r for r in cohort['records']if r['iso_edges']==[eid]and r['plan_edges']==[pid]and r['mapping_id']==obs['mapping_id']]
                    if len(crows)!=1:raise ValueError('one complete member-cohort scope required')
                    cr=crows[0];groups=[g for g in cohort['native_bounded_batch']['groups']if g['mapping_id']in cr['source_group_ids']]
                    if {g['mapping_id']for g in groups}!=set(cr['source_group_ids']):raise ValueError('member source group missing')
                    observations_native=[o for group in groups for o in group['native']['plan']['path_coverage'].get('equivalent_member_observations',[])if o['edge_id']==pid]
                    for o in observations_native:
                        for original in o['equivalent_support']:
                            atoms=load(cohort['inputs']['native_atom_origins']['path']);compound={r['source_LINE']for r in atoms['floors'][f]['corridors']};segment=dict(start=original['segment'][0],end=original['segment'][1],witnesses=original['all_original_witnesses']);fresh=equivalent_support(doc,segment,edge['system'],cohort['native_bounded_batch']['complete_member_cohorts'],compound)
                            if fresh!=original:raise ValueError('original coincident witness member support changed')
                        excluded.update(o['excluded_handles'])
                metric=measure(ObservationDocument(doc,excluded)if excluded else doc,plan,pid,units,source['sha256'],gp['sha256'])
                plan_T={n:reader(doc,plan,n,source['sha256'],gp['sha256'])for n in pends};axis_T={n:native_tee(axis_doc,axis,n,ins['axis_source']['sha256'],ins['axis_graph']['sha256'])for n in aends}
                relation=endpoint_relation(axis,eid,floor,edge['system']);reading=dict(edge)
                if relation['path_orientation']=='end_to_start':reading['attribute_paths']=[list(reversed(edge['attribute_paths'][0]))]
                horizontal_domain(dict(axis,edges=[reading]),dict(iso_edges=[eid],iso_start=aends[0],iso_end=aends[1],floor=floor,system=edge['system']),manifest['horizontal_directions_degrees'])
                records.append(dict(mapping_id=obs['mapping_id'],axis_edge_id=eid,plan_edge_id=pid,floor=floor,system=edge['system'],axis_nodes=aends,axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),plan_nodes=pends,complete_horizontal_centerline_projection_mm=metric['complete_horizontal_centerline_projection_mm'],metric=metric,native_plan_Ts=plan_T,native_axis_Ts=axis_T,component_profiles=profiles,member_observation_evidence=copy.deepcopy(observations_native),plan_source_sha256=source['sha256'],plan_graph_sha256=gp['sha256'],installed_length_mm=None,net_pipe_cut_length_mm=None,DN_changed=False,source_paths_mutated=False,related_HIL_confirmation_inherited=False,human_accepted=False));row['status']='complete_XY_projection_source_qualified'
            except ValueError as exc:row.update(status='held',reason=str(exc));pending.append(dict(edge_id=eid,reason=str(exc)))
            attempts.append(row)
    checked()
    if {r['axis_edge_id']for r in records}&{r['edge_id']for r in pending}or len(records)+len(pending)!=len(wanted):raise ValueError('full current length-pending scope conservation failed')
    return dict(mode=MODE,inputs=ins,parent_bundle_id=viewer['bundleId'],records=records,pending=pending,attempts=attempts,source_preflight=preflight,axis_preflight=axis_text,complete_original_member_batch_replayed=True,old_complete_lengths_not_targeted=True,counts=dict(current_pending_horizontal_lengths=len(wanted),source_crossovers_screened=len(attempts),new_complete_XY_projections=len(records),remaining_pending_horizontal_lengths=len(pending)),DN_values_assigned=0,vertical_values_assigned=0,installed_lengths_assigned=0,physical_gap_lengths_assigned=0,source_graphs_mutated=False,human_accepted=False,viewer_adoption_pending=True)

def implementations():
    names=('native_plan_crossover_centerline','rebuild_equivalent_member_bounded_batch','equivalent_member_source_support','native_main_interval_metrics','inherited_circle_branch_inventory','native_plan_projection_lengths','source_readability','legacy_named_provider_inventory','crossview_equipment_branch_inventory')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementations();r=compute(load(manifest))
    if code!=implementations():raise ValueError('source metric code changed')
    output.mkdir(parents=True);p=output/'plan-crossover-centrelines.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))));return r

def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'plan-crossover-centrelines.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementations()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('crossover metric source/code/output changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('independent source XY metric replay differs')
    return r
