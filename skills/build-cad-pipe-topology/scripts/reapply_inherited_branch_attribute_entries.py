"""Compose current main-domain, marker-endpoint and normalization owners."""
import argparse,copy,csv,importlib,sys,types
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/name/'scripts'))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_replay_session import verify_once
from native_air_vent_attribute_items import collect as normalized_items
from axis_unbranched_vertical_DN import source_key,annotation_index
from inherited_marker_and_crossover_evidence import population
from native_paired_caption_geometry import collect as captions
from refresh_reviewed_ring_partition_DN import effective
from refresh_plan_seeded_axis_branch_DN import verify as previous_viewer_owner
from expanded_main_seed_bend_DN import verify_output as previous_vertical_owner
from reapply_received_scope_attributes import verify_output as received_owner
from rebuild_received_circle_expression_scopes import verify_output as source_scope_owner
import plan_seeded_axis_branch_DN as branch
import partial_uniform_main_DN as partial
import native_marker_endpoint_geometry as endpoint
import normalized_attribute_source_context as semantic
import axis_vertical_DN_batch as direct_vertical
import native_modelspace_paired_main_seeds as vertical_owner

MODE='native_current_branch_attribute_existing_entry_composition_v1'
def require(value,message):
    if not value:raise ValueError(message)

def qualify_with_endpoints(*args):
    namespace=dict(branch.qualify.__globals__,marker_ports=endpoint.collect)
    return types.FunctionType(branch.qualify.__code__,namespace,branch.qualify.__name__)(*args)

def qualify_with_normalization(row,doc,graph,route,mains,values,items,sh,gh,pop,caps,annotations,audit_spec):
    shadow,private_route,private_items,proof=semantic.prepare(doc,graph,route,items,sh,gh,audit_spec,row['axis_T'],row['axis_edge_id'])
    def source_endpoint(current,current_graph,nid,source_hash,graph_hash,source_pop):
        require(current is shadow and current_graph is graph and source_pop is pop,'private endpoint source context changed')
        return endpoint.collect(doc,graph,nid,source_hash,graph_hash,pop)
    def source_T(current,current_graph,nid,source_hash,graph_hash):
        require(current is shadow and current_graph is graph and nid==row['axis_T']and source_hash==sh and graph_hash==gh,
                'private normalized T source context changed')
        return proof['original_T_evidence']
    namespace=dict(branch.qualify.__globals__,marker_ports=source_endpoint,native_tee=source_T)
    original=types.FunctionType(branch.qualify.__code__,namespace,branch.qualify.__name__)
    record=original(row,shadow,graph,private_route,mains,values,private_items,sh,gh,pop,caps,annotations,{})
    record.update(original_normalization_attribute_context=copy.deepcopy(proof),raw_source_gap_still_unwitnessed=True,
        source_reader_role='original_applied_normalization_semantic_DN_continuity_not_raw_LINE_length')
    return record,shadow,private_route,private_items,proof

def requalify_vertical(shadow,graph,private_route,private_items,parent,normalization,source,graph_spec):
    eid=normalization['edge_id'];local=copy.deepcopy(private_route)
    local['records']=[s for s in private_route['records']if s['edge_id']==eid and s['direction_class']=='vertical']
    require(bool(local['records']),'normalized branch has no original vertical domain')
    direct=direct_vertical.collect(shadow,graph,local,Path(source['path']),Path(graph_spec['path']),workers=1)
    prepared=copy.deepcopy(parent);fresh={source_key(s):s for s in direct['pending']};key=tuple(normalization['source_domain'])
    prior=[r for r in prepared['pending']if source_key(r)==key]
    require(len(prior)==1 and prior[0]['original_reason']=='native_source_LINE_not_yet_witnessed',
            'only the exact original missing source witness may be reconsidered')
    require(fresh.get(key,{}).get('reason')=='no_qualified_axis_annotation_on_this_vertical_segment',
            'fresh original direct owner did not resolve the exact source-only hold')
    row=prior[0];row['original_raw_pending']=copy.deepcopy(row);row['fresh_direct_semantic_requalification']=copy.deepcopy(fresh[key])
    row['original_reason']=fresh[key]['reason']
    result=vertical_owner.collect(shadow,graph,private_route,prepared,private_items,source['sha256'],graph_spec['sha256'])
    for record in result['records']:
        require(source_key(record)in{source_key(r)for r in parent['pending']},'old known vertical domain cannot be replaced')
        record['semantic_source_normalization']=copy.deepcopy(normalization)
        record['source']='axis11_original_native_caption_T_and_replayed_normalization'
        record['raw_source_coverage_not_promoted']=True
    return dict(fresh_direct_annotation_owner=direct,original_axis11_paired_main_T_owner=result,
        raw_missing_witness_pending_retained_as_history=copy.deepcopy(prior[0]['original_raw_pending']),
        normalized_source_domain=list(key),new_vertical_domains=copy.deepcopy(result['records']),
        physical_lengths_assigned=0,source_plan_DN_used_for_vertical=False,human_accepted=False)

def compare_inherited(previous,current,values):
    old={r['axis_edge_id']:r for r in previous};new={r['axis_edge_id']:r for r in current}
    require(len(old)==len(previous)and len(new)==len(current)and old.keys()<=new.keys(),'a previous source-qualified branch regressed')
    for eid,record in old.items():
        fresh=new[eid]
        require({k:v for k,v in record.items()if k!='old_whole_DN'}=={k:v for k,v in fresh.items()if k!='old_whole_DN'},
                'previous native branch geometry, owners or barriers changed '+eid)
        require(fresh['old_whole_DN']==values[eid].get('diameter_nominal_mm')and fresh['old_whole_DN']==record['nominal_mm'],
                'current adopted old branch DN no longer agrees '+eid)
    return sorted(old)

def compute(manifest):
    inputs=manifest['inputs']
    def checked():require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'fixed inherited branch composition input changed')
    checked();doc,preflight=read_source(inputs['axis_source']['path'])
    viewer=Path(inputs['viewer_manifest']['path']).parents[2]
    print('Replaying the complete current233 source/viewer and current456 vertical-source parent',flush=True)
    previous_viewer=verify_once(viewer,previous_viewer_owner);require(previous_viewer['artifact_replay']=='passed','current published parent replay failed')
    prior=load(inputs['previous_branch_proof']['path']);audit=load(inputs['viewer_audit']['path'])
    require(audit['proof_sha256']==inputs['previous_branch_proof']['sha256'],'previous native proof has another current adoption')
    parent=verify_once(Path(inputs['previous_vertical_proof']['path']).parent,previous_vertical_owner)
    require(encode(parent)==Path(inputs['previous_vertical_proof']['path']).read_bytes(),'current original vertical parent replay differs')
    received=verify_once(Path(inputs['received_attribute_proof']['path']).parent,received_owner)
    scopes=verify_once(Path(inputs['received_scope_proof']['path']).parent,source_scope_owner)
    for result,key in[(received,'received_attribute_proof'),(scopes,'received_scope_proof')]:
        require(encode(result)==Path(inputs[key]['path']).read_bytes(),'original complete source scope replay differs')
    for name in('axis_source','axis_graph','routing','canonical_components'):
        require(prior['inputs'][name]==inputs[name]and parent['inputs'][name]==inputs[name],'current native source namespace differs')
    require(scopes['inputs']['iso_source']==inputs['axis_source']and scopes['inputs']['iso_graph']==inputs['axis_graph']
        and scopes['inputs']['iso_normalization_audit']==inputs['normalization_audit'],'complete source scope/normalization ancestor differs')
    vm=load(inputs['viewer_manifest']['path']);provider=load(inputs['provider']['path']);graph=load(inputs['axis_graph']['path']);route=load(inputs['routing']['path'])
    actual=effective(viewer);require(encode(actual)==Path(inputs['current_effective']['path']).read_bytes(),'actual current facade values differ')
    values={r['edge_id']:r['values']for r in actual};context=vm['attributeValueContext']
    require(context['axis_rule_vertical_DN']['source_bindings']['native_proof']==inputs['previous_vertical_proof']['sha256']
        and provider['counts']['all_current_vertical_DN_domains']==parent['counts']['current_known'],
        'actual current native vertical parent differs')
    with Path(inputs['canonical_components']['path']).open(encoding='utf-8-sig',newline='')as stream:inventory=list(csv.DictReader(stream))
    items,normalization=normalized_items(doc,graph,inventory)
    mains={r['axis_edge_id']:r for name in('reviewed_uniform_subroute_DN','received_scope_uniform_DN')for r in context[name]['records']}
    groups=load(received['inputs']['original_uniform_proof']['path'])['groups']+received['uniform_groups']
    scopes_by={r['scope_id']:r for r in scopes['records']};cap=captions(doc);partial_reports=[]
    for group in groups:
        report=partial.collect(scopes_by[group['scope_id']],group,graph,route,doc,items,cap,set(mains))
        partial_reports.append(report)
        for record in report['records']:
            require(record['axis_edge_id']not in mains,'existing qualified main domain cannot be replaced')
            mains[record['axis_edge_id']]=record
    pop=population(doc,inputs['axis_source']['sha256']);annotations=annotation_index(doc,graph,inputs['axis_source']['sha256'])
    candidates=branch.discover(graph,mains);records=[];pending=[];vertical=[];marker_cache={}
    for candidate in candidates:
        args=(candidate,doc,graph,route,mains,values,items,inputs['axis_source']['sha256'],inputs['axis_graph']['sha256'],pop,cap,annotations,marker_cache)
        try:records.append(qualify_with_endpoints(*args))
        except ValueError as exc:
            if str(exc)not in('selected ray insert mismatch','native T ray is not uniquely witnessed'):
                pending.append(dict(candidate,reason=str(exc)));continue
            try:
                rebuilt,shadow,private_route,private_items,proof=qualify_with_normalization(*args[:-1],inputs['normalization_audit'])
                # Keep source-DN qualification separate from vertical proposals.
                records.append(rebuilt)
                try:vertical.append(requalify_vertical(shadow,graph,private_route,private_items,parent,proof,inputs['axis_source'],inputs['axis_graph']))
                except ValueError as held:
                    vertical.append(dict(edge_id=candidate['axis_edge_id'],new_vertical_domains=[],reason=str(held),
                        horizontal_source_qualification_retained=True,physical_lengths_assigned=0,source_plan_DN_used_for_vertical=False))
            except ValueError as second:pending.append(dict(candidate,reason=str(second),original_raw_reason=str(exc)))
    inherited=compare_inherited(prior['records'],records,values);new=[r for r in records if r['axis_edge_id']not in inherited]
    new_vertical=[r for report in vertical for r in report['new_vertical_domains']]
    require(len({source_key(r)for r in new_vertical})==len(new_vertical),'competing new native vertical source writer')
    checked();return dict(mode=MODE,inputs=copy.deepcopy(inputs),source_preflight=preflight,inherited_air_vent_normalization=normalization,
        inherited_records=copy.deepcopy(prior['records']),fresh_all_branch_records=records,records=new,pending=pending,
        partial_main_reports=partial_reports,new_partial_main_records=[r for p in partial_reports for r in p['records']],
        independent_axis11_vertical_reapplication=vertical,new_vertical_records=new_vertical,
        counts=dict(screened_branches=len(candidates),previous_qualified_branches=len(inherited),current_qualified_branches=len(records),
            new_source_qualified_branches=len(new),held_branches=len(pending),qualified_branch_horizontal_domains=sum(len(r['horizontal_segment_domains'])for r in records),
            additional_partial_main_horizontal_domains=sum(len(r['horizontal_segment_domains'])for p in partial_reports for r in p['records']),
            previous_known_vertical_domains=parent['counts']['current_known'],new_axis11_vertical_domains=len(new_vertical),
            current_known_vertical_domains=parent['counts']['current_known']+len(new_vertical)),
        complete_current_native_viewer_and_vertical_parents_replayed=True,all_previous_source_branch_payloads_exact=True,
        source_graph_and_original_routes_unchanged=True,raw_normalization_gap_never_promoted_to_measured_LINE=True,
        vertical_values_from_axis11_only=True,graph_mutated=False,components_changed=False,physical_lengths_assigned=0,
        individual_device_mappings_assigned=0,viewer_adoption_pending=True,human_accepted=False,whole_goal_complete=False)

def implementations():
    names=('plan_seeded_axis_branch_DN','partial_uniform_main_DN','native_marker_endpoint_geometry','normalized_attribute_source_context',
        'normalized_native_junction_evidence','native_modelspace_paired_main_seeds','axis_vertical_DN_batch',
        'expanded_main_seed_bend_DN','refresh_plan_seeded_axis_branch_DN','native_air_vent_attribute_items',
        'native_paired_caption_geometry','inherited_marker_and_crossover_evidence','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh inherited branch composition output required');code=implementations()
    result=compute(load(manifest));require(code==implementations(),'inherited branch composition implementation changed')
    output.mkdir(parents=True);target=output/'inherited-branch-attribute-entries.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),
        implementation_sha256=code,output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');target=output/'inherited-branch-attribute-entries.json'
    require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()
        and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and sha(target)==receipt['output_sha256'],
        'inherited branch composition source/code/output receipt changed')
    fresh=compute(load(receipt['manifest']['path']));require(encode(fresh)==target.read_bytes(),'independent inherited branch composition differs')
    return fresh

def main():
    parser=argparse.ArgumentParser()
    for name in('manifest','output','verify-output'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        result=verify_output(args.verify_output)if args.verify_output else produce(args.manifest,args.output)
    print(dict(mode=MODE,counts=result['counts'],pending=result['pending']),flush=True)
if __name__=='__main__':main()
