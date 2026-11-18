"""Rebuild the entire changed floor after a native wave/main cohort stage.

The complete parent is independently replayed once per bounded process batch.
Unchanged floor results retain their original evidence. All current services
on the changed floor are freshly read, then the complete axis partition is
regenerated. No former failed flag is promoted without current source proof.
"""
import argparse
import copy
import csv
import math
from pathlib import Path

from confirm_crossview_paths import load,sha,encode
from apply_crossview_rule_batch import checked,verify_output as verify_parent
from reconstruct_wave_main_cohorts import verify_output as verify_cohort
from fresh_reviewed_plan_inventory import inspect_view,compare_ready
from crossview_equipment_branch_inventory import index_graph,service_route,_caption
from native_path_coverage_audit import audit as line_audit
from native_replay_session import verify_once
from batch_apply_crossview_rules import discover_floor,evaluate_all_axis_edges
from batch_native_path_coverage import collect as batch_coverage
from batch_rule_contract import check
from native_plan_projection_lengths import unit_evidence,lengths
from source_readability import read_source

MODE='wave_cohort_current_floor_crossview_batch_v1'


def wave_branch(doc,graph,did,system,source_hash,graph_hash):
    trace=service_route(graph,did,system)
    root=graph['sourceWaveMainCohort'];matches=[r for r in root['records'] if r['equipment_id']==did and r['system']==system]
    if len(matches)!=1 or trace.get('status')!='unique_graph_service_to_T' or trace['edges']!=[matches[0]['branch_edge']] or trace['tee']!=matches[0]['tee_id']:
        raise ValueError('current wave branch route differs from native cohort')
    row=matches[0];nodes,edges,adj=index_graph(graph);edge=edges[row['branch_edge']];tee=nodes[row['tee_id']]
    original=row['original_branch']
    if edge['attribute_paths']!=original['attribute_paths'] or edge['path_length']!=original['path_length']:
        raise ValueError('wave reconstruction changed source-drawn branch metric scope')
    proof=line_audit(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=[edge['edge_id']]),source_hash,graph_hash)
    if any(s['status']!='single_source_line_covers' for e in proof['edges'] for s in e['segments']):raise ValueError('wave branch lacks unique native path coverage')
    incident=adj[tee['node_id']]
    if len(incident)!=3 or {e['system'] for e in incident}!={system}:raise ValueError('wave branch needs a current same-service three-ray junction')
    point=[tee['x'],tee['y']];rays=[]
    for peer in incident:
        if peer['edge_id']==edge['edge_id']:
            direction=[-x for x in row['outward']]
            witness=dict(source_line_handle=row['branch_contact']['source_line_handle'],
                rule='calibrated_native_wave_omitted_branch_ray',native_line_XYZ=row['branch_contact']['line_XYZ'],
                native_wave_handle=row['wave']['wave_handle'],omitted_span_physical_length_mm=None)
        else:
            path=peer['path'] if peer['start_node_id']==tee['node_id'] else list(reversed(peer['path']))
            if math.dist(path[0],point)>.05:raise ValueError('current main child misses wave T')
            tip=next((p for p in path[1:] if math.dist(point,p)>.05),None)
            if tip is None:raise ValueError('empty current wave main child ray')
            direction=[tip[i]-point[i] for i in (0,1)]
            witness=dict(source_line_handle=row['target']['source_handle'],rule='native_main_LINE_at_calibrated_wave_landing')
        rays.append(dict(edge_id=peer['edge_id'],direction=direction,**witness))
    junction=dict(source_sha256=source_hash,graph_sha256=graph_hash,graph_mutated=False,
        junctions=[dict(node_id=tee['node_id'],position=point,system=system,source_rays=rays)],
        connection_rule='source_calibrated_paired_wave_main_cohort',physical_flow_direction_inferred=False,human_accepted=False)
    return dict(trace=trace,status='native_wave_main_branch_checks_passed_comparison_pending',ready_for_mapping_comparison=True,
        junction_evidence=junction,coverage=proof,logical_ownership_basis='original_source_reviewed_owner_plus_replayed_wave_main_cohort',
        physical_ports_verified=False,whole_physical_length_mm=None)


def inspect_current_floor(plan_doc,axis_doc,plan,axis,old,local,axis_devices,circle_policy,plan_hash,axis_hash):
    floor=old['records'][0]['floor'];records=[]
    expected={r['equipment_id'] for r in old['records']}
    actual={n['node_id'] for n in plan['nodes'] if n.get('node_type')=='equipment' and n.get('floor')==floor}
    if actual!=expected:raise ValueError('wave batch cannot drop or rename physical equipment')
    wave_keys={(r['equipment_id'],r['system']) for r in plan['sourceWaveMainCohort']['records']}
    for did in sorted(expected):
        views={}
        for view,doc,graph,h in [('plan',plan_doc,plan,plan_hash),('iso',axis_doc,axis,axis_hash)]:
            if view=='plan' and any((did,s) in wave_keys for s in ('supply','return')):
                captions=[e for e in doc.modelspace().query('TEXT MTEXT') if e.plain_text()==did]
                if len(captions)!=1:raise ValueError('native wave equipment caption missing or ambiguous')
                views[view]=dict(status='native_caption_read',caption=_caption(doc,captions[0].dxf.handle,did),
                    services={s:wave_branch(doc,graph,did,s,h['source_sha256'],h['graph_sha256']) for s in ('supply','return')})
            else:
                views[view]=inspect_view(doc,graph,did,floor,h,view,axis_devices,circle_policy if view=='plan' else None)
        records.append(dict(equipment_id=did,floor=floor,views=views,
            ready_for_mapping_comparison=all(views[v].get('services',{}).get(s,{}).get('ready_for_mapping_comparison') is True for v in ('plan','iso') for s in ('supply','return'))))
    result=dict(status='source_comparison_inventory_not_mapping',records=records,
        counts=dict(equipment=len(records),ready_for_mapping_comparison=sum(r['ready_for_mapping_comparison'] for r in records)),
        local_graphs_mutated=False,mapped_paths=0,human_accepted=False,hil_ready=False,
        fresh_current_service_checks=dict(plan=2*len(records),iso=2*len(records)),inventory_mode=MODE)
    result['historical_ready_comparison']=compare_ready(result,old)
    if result['historical_ready_comparison']['regressions']:raise ValueError('wave cohort regressed a previously source-ready service')
    return result


def compute(manifest,announce=lambda message:None):
    inputs={k:checked(v) for k,v in manifest['inputs'].items()}
    parent_run=inputs['parent_receipt'].parent;cohort_run=inputs['cohort_audit'].parent
    announce('Independently replaying the full original92-equipment batch once')
    parent=verify_once(parent_run,verify_parent)
    announce('Replaying all wave-main landings, source scopes and component ownership')
    audit=verify_once(cohort_run,verify_cohort)
    scope=load(cohort_run/'graph_with_edges.json')['sourceWaveMainCohort']
    floor=str(manifest['floor']);old=parent['inventories'][floor]
    parent_manifest=load(checked(load(inputs['parent_receipt'])['manifest']))
    identity_receipt=checked(parent_manifest['inputs']['identity_receipt']);axis_path=identity_receipt.parent/'graph_with_edges.json'
    if sha(axis_path)!=parent['identity_graph_sha256']:raise ValueError('axis changed after the complete parent batch')
    inventory_receipt=checked(parent_manifest['inputs']['inventory_receipt']);local=load(inventory_receipt)['local_inputs'][floor]
    for item in local.values():checked(item)
    if scope['input_graph_sha256']!=local['plan_graph']['sha256']:
        raise ValueError('wave cohort is not this complete parent floor graph')
    plan_path=cohort_run/'graph_with_edges.json';plan=load(plan_path);axis=load(axis_path)
    plan_doc,plan_preflight=read_source(local['plan_source']['path']);axis_doc,axis_preflight=read_source(local['iso_source']['path'])
    with (identity_receipt.parent/'edge_device_instances.csv').open(encoding='utf-8-sig',newline='') as stream:devices=list(csv.DictReader(stream))
    ph=dict(source_sha256=local['plan_source']['sha256'],graph_sha256=sha(plan_path))
    ah=dict(source_sha256=local['iso_source']['sha256'],graph_sha256=sha(axis_path),inventory_sha256=sha(identity_receipt.parent/'edge_device_instances.csv'))
    inventory=inspect_current_floor(plan_doc,axis_doc,plan,axis,old,local,devices,load(inputs['circle_policy']),ph,ah)
    announce(f'{floor}F fresh plan/axis services checked: {inventory["counts"]}')
    current=copy.deepcopy(parent);current['inventories'][floor]=inventory
    graphs=dict(plan=plan,iso=axis);correspondence=discover_floor(graphs,inventory,int(floor));current['floors'][floor]=correspondence
    native={};docs=dict(plan=plan_doc,iso=axis_doc)
    for view,h in [('plan',ph),('iso',ah)]:
        ids=sorted({eid for row in correspondence['records'] for eid in row[view+'_edges']})
        native[view]=batch_coverage(docs[view],graphs[view],ids,h['source_sha256'],h['graph_sha256'])
    current['native'][floor]=native;units=unit_evidence(plan_doc,load(inputs['metric_policy']));metrics=[]
    for row in correspondence['records']:
        record=dict(mapping_id=row['mapping_id'],plan_edges=row['plan_edges'],iso_edges=row['iso_edges'])
        try:record['projection']=lengths(plan,native['plan'],row,units)
        except ValueError as exc:record.update(projection=None,reason=str(exc))
        metrics.append(record)
    current['metrics'][floor]=metrics
    previous=load(checked(parent_manifest['inputs']['prior_attributes']))
    current['all_axis_edges']=evaluate_all_axis_edges(axis,current['floors'],previous)
    current['summary']=check(current['all_axis_edges'],axis)
    current.update(mode=MODE,parent_mode=parent['mode'],source_preflight=dict(plan=plan_preflight,iso=axis_preflight),
        current_wave_cohort=dict(floor=int(floor),source_graph_sha256=sha(plan_path),source_audit_sha256=sha(inputs['cohort_audit']),
            parent_batch_receipt_sha256=sha(inputs['parent_receipt']),native_connections=audit['proof']['connections'],
            native_source_services_rebuilt=2*len(inventory['records']),unchanged_floor_results_preserved=sorted(set(parent['floors'])-{floor})),
        attributes_fused=False,human_accepted=False,hil_ready=False)
    for item in manifest['inputs'].values():checked(item)
    return current


def implementation_hashes():
    import reconstruct_wave_main_cohorts,batch_apply_crossview_rules,fresh_reviewed_plan_inventory
    return dict(entry=sha(__file__),cohort=sha(reconstruct_wave_main_cohorts.__file__),
        matcher=sha(batch_apply_crossview_rules.__file__),inventory=sha(fresh_reviewed_plan_inventory.__file__))


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'wave-batch-receipt.json')
    if receipt['implementation_sha256']!=implementation_hashes():raise ValueError('wave cross-view batch implementation changed')
    manifest=checked(receipt['manifest']);result=compute(load(manifest))
    if encode(result)!=(directory/'wave-batch-results.json').read_bytes():raise ValueError('wave full-axis batch native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--verify-output',type=Path)
    args=parser.parse_args()
    if args.verify_output:result=verify_output(args.verify_output);print(result['summary'],flush=True);return
    if not args.manifest or not args.output:parser.error('fixed manifest and new output required')
    if args.output.exists():raise FileExistsError(args.output)
    result=compute(load(args.manifest),lambda message:print(message,flush=True));args.output.mkdir(parents=True)
    (args.output/'wave-batch-results.json').write_bytes(encode(result))
    (args.output/'wave-batch-receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(args.manifest.resolve()),sha256=sha(args.manifest)),implementation_sha256=implementation_hashes(),
        output_sha256=sha(args.output/'wave-batch-results.json'),human_accepted=False)))
    print(result['summary'],flush=True)


if __name__=='__main__':main()
