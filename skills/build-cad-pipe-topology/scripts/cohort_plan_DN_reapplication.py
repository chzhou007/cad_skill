"""Reapply native calibrated/F readers and the original whole-plan T algorithm.

The physical member was established independently. Only its equivalent LINE
query domain changes; native T evidence still reads the complete original CAD.
All original text guards and explicit DN boundaries remain in the algorithm.
"""
import copy
from native_canonical_main_family_view import CanonicalLineDocument
from full_plan_DN_inherited_annotations import inventory,barriers
from full_plan_DN_source import _has_through
from full_plan_DN_inheritance import infer
from calibrated_direct_dn_evidence import collect as calibrated_collect
from wave_rebased_plan_attributes import configuration as specific_configuration,pinned
from batch_native_path_coverage import collect as coverage

def reading_view(doc,batch):
    cohorts=batch['native_bounded_batch']['complete_member_cohorts'];excluded=set();retained=set();families={}
    for c in cohorts:
        p=c['inherited_canonical_reader_evidence']['canonical_source_projection'];excluded.update(p['excluded_from_unique_LINE_query']);retained.add(p['canonical_source_handle'])
        for h in c['source_family']:families[h]=c
    supports=[]
    for group in batch['native_bounded_batch']['groups']:
        for path in group['native']['plan']['path_coverage'].get('equivalent_member_observations',[]):
            for p in path['equivalent_support']:
                handles={w['source_handle']for w in p['all_original_witnesses']}
                if handles&families.keys():continue
                excluded.update(p['excluded_from_private_reader']);retained.add(p['representative_observation_handle']);supports.append(copy.deepcopy(p))
    if excluded&retained:raise ValueError('cohort reading projections have competing source representatives')
    return CanonicalLineDocument(doc,excluded),dict(excluded_only_equivalent_LINE_handles=sorted(excluded),retained_native_representatives=sorted(retained),cap_support=supports,raw_source_mutated=False,physical_source_identity_resolved=False)

def source_inventory(view,graph,source_hash,graph_hash,config,specific_specs,cohorts):
    annotation=inventory(view,graph,source_hash,graph_hash,config);proofs=[];resolved=set();observations=[]
    families={h for c in cohorts for h in c['source_family']}
    for spec in specific_specs:
        seeds=spec.get('scope',{}).get('seeds',[])
        if not seeds or not {s['source_line_handle']for s in seeds}<=families:raise ValueError('specific native annotation provider lies outside the proved cohort')
        origin=pinned(spec['calibration_origin']);_,calibration,_=specific_configuration(spec,source_hash,graph_hash,origin['graph_sha256'])
        proof=calibrated_collect(view,graph,calibration,source_hash,graph_hash)
        if {r['source_text']['handle']for r in proof['observations']}!={s['text_handle']for s in seeds}:raise ValueError('specific native annotation population differs')
        for row in proof['observations']:
            h=row['source_text']['handle']
            if h in resolved:raise ValueError('specific native annotation claimed twice')
            prior=[s for s in annotation['seeds']if s['evidence_id']=='source:'+h]
            if any(s['edge_id']!=row['edge_id']or s['nominal_mm']!=row['nominal_mm']for s in prior):raise ValueError('specific reader conflicts with an existing direct source owner')
            resolved.add(h);observations.append(row)
        proofs.append(dict(group_id=spec['group_id'],configuration=copy.deepcopy(spec),native_evidence=proof))
    def text_handle(row):return row.get('text_handle',row.get('selection',{}).get('text_handle',row.get('text',{}).get('handle')))
    annotation['blocked_edges']={eid:remaining for eid,rows in annotation['blocked_edges'].items()if(remaining:=[r for r in rows if text_handle(r)not in resolved])}
    for key in('assigned','pending','unparsed_candidates','exceptions'):annotation[key]=[r for r in annotation[key]if text_handle(r)not in resolved]
    annotation['seeds']=[s for s in annotation['seeds']if s['evidence_id']not in{'source:'+h for h in resolved}]
    annotation['seeds'].extend(dict(edge_id=r['edge_id'],nominal_mm=r['nominal_mm'],evidence_id='source:'+r['source_text']['handle'])for r in observations)
    annotation['specific_native_annotation_reapplication']=proofs
    return annotation

def reapply(doc,graph,batch,previous_DN,config,specific_specs,T_reader,source_hash,graph_hash):
    view,projection=reading_view(doc,batch);cohorts=batch['native_bounded_batch']['complete_member_cohorts']
    annotation=source_inventory(view,graph,source_hash,graph_hash,config,specific_specs,cohorts)
    ids=[e['edge_id']for e in graph['edges']if e['system']in('supply','return')];cov=coverage(view,graph,ids,source_hash,graph_hash)
    eligible={e['edge_id']for e in cov['edges']if e['segments']and all(s['status']=='single_source_line_covers'for s in e['segments'])};blocked=copy.deepcopy(annotation['blocked_edges']);leader_blocks,leader_issues=barriers(view,graph,annotation,eligible)
    for eid,row in leader_blocks.items():blocked.setdefault(eid,[]).append(row)
    eligible-=set(blocked);junctions={};errors={}
    for node in graph['nodes']:
        if node.get('node_type')not in('tee','physical_junction'):continue
        try:
            proof=T_reader(doc,graph,node['node_id'],source_hash,graph_hash)
            if not _has_through(proof):raise ValueError('native T has no unique source through pair')
            junctions[node['node_id']]=proof
        except ValueError as exc:errors[node['node_id']]=str(exc)
    seeds=[s for s in annotation['seeds']if s['edge_id']in eligible]
    seeds.extend(copy.deepcopy(s)for s in previous_DN['direct_seed_evidence']if s.get('scope_only')is True and s['edge_id']in eligible)
    result=infer(graph,seeds,eligible,junctions,source_hash,graph_hash);records={r['edge_id']:r for r in result['records']};prior={r['edge_id']:r for r in previous_DN['records']};selected=[]
    for mapping in batch['records']:
        eid=mapping['plan_edges'][0];old=prior[eid];new=records.get(eid)
        if old['nominal_mm']is not None and (new is None or new['nominal_mm']!=old['nominal_mm']):raise ValueError('existing qualified plan DN regressed during reader reapplication')
        # A prior explicit conflict retains its original unresolved state. This
        # adapter qualifies the formerly unread equivalent source domain only.
        current=old if old['nominal_mm']is not None or old['status']=='conflict'or new is None else new
        selected.append(dict(edge_id=eid,record=copy.deepcopy(current),previous_general_record=copy.deepcopy(old),new_native_record=copy.deepcopy(new),specific_native_domain_applied=current is new and new['nominal_mm']is not None))
    return dict(records=selected,reading_projection=projection,annotation_evidence=annotation,native_path_coverage=cov,junction_errors=errors,native_inheritance=result,leader_issues=leader_issues,all_original_T_readers_use_full_CAD=True,whole_plan_algorithms_reused=True,DN_used_for_mapping=False,source_mutated=False,values_outside_selected_batch_adopted=False,human_accepted=False)
