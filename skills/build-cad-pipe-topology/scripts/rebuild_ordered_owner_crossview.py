"""Reapply existing cross-view/member readers after logical plan-owner repair.

Old correspondences stay versioned and keep their IDs. New source-qualified
paths receive semantic IDs, never the discovery reader's changing ordinals.
"""
import argparse,copy,csv,hashlib,importlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_replay_session import verify_once
from rebuild_ordered_sideview_owners import verify_output as verify_owner
from native_exploded_caption_identity import verify_output as verify_axis
from confirmed_compound_pipe_lanes import verify_output as verify_lanes
from confirmed_member_plan_paths import collect as member_paths
from native_plan_projection_lengths import unit_evidence
from crossview_equipment_branch_inventory import inspect_branch,service_route
from batch_apply_crossview_rules import discover_floor
from batch_native_main_chains import source_check
MODE='native_ordered_owner_crossview_member_extension_v1'

def signature(row):
    return (row['kind'],row['floor'],row['system'],tuple(row['plan_edges']),tuple(row['iso_edges']))

def additions(previous,current):
    old={signature(r):r for r in previous};new={signature(r):r for r in current}
    if len(old)!=len(previous)or len(new)!=len(current)or not old.keys()<=new.keys():raise ValueError('existing correspondence lost or duplicate path writer')
    old_ids=[r['mapping_id']for r in previous]
    if len(old_ids)!=len(set(old_ids)):raise ValueError('historical mapping IDs collide')
    occupied={v:{e for r in previous for e in r[v+'_edges']}for v in ('plan','iso')};result=[]
    for key in sorted(new.keys()-old.keys()):
        r=copy.deepcopy(new[key])
        if any(occupied[v].intersection(r[v+'_edges'])for v in occupied):raise ValueError('new correspondence overlaps historical writer')
        mid='OWNER-F'+str(r['floor'])+'-'+hashlib.sha256(encode(list(key))).hexdigest()[:16]
        if mid in old_ids:raise ValueError('semantic mapping ID collides with history')
        r['mapping_id']=mid;r.pop('plan_snapshot',None);r.pop('iso_snapshot',None)
        result.append(r)
        for v in occupied:occupied[v].update(r[v+'_edges'])
    return result

def preserve_member_runs(previous,current):
    old={r['plan_edge_id']:r for r in previous};new={r['plan_edge_id']:r for r in current}
    if len(old)!=len(previous)or len(new)!=len(current)or not old.keys()<=new.keys():raise ValueError('member run lost or duplicated')
    if any(new[k]!=r for k,r in old.items()):raise ValueError('historical native member run changed')
    return sorted(new.keys()-old.keys())

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('ordered-owner crossview input changed')
    checked();plan=load(paths['plan_graph']);axis=load(paths['axis_graph'])
    parent=verify_once(paths['plan_graph'].parent,verify_owner)
    if parent['output_graph_sha256']!=sha(paths['plan_graph']):raise ValueError('repaired plan topology differs')
    verify_once(paths['axis_graph'].parent,verify_axis)
    old=load(paths['old_batch']);floor=manifest['floor'];previous=old['floors'][str(floor)]
    if type(floor)is not int or old['identity_graph_sha256']!=sha(paths['axis_graph']):raise ValueError('axis identity or explicit floor differs')
    docs={};preflight={};graphs=dict(plan=plan,iso=axis);hashes={}
    for v in graphs:
        prefix='axis'if v=='iso'else v
        docs[v],preflight[v]=read_source(paths[prefix+'_source']);hashes[v]=dict(source_sha256=sha(paths[prefix+'_source']),graph_sha256=sha(paths[prefix+'_graph']))
        if graphs[v]['metadata']['source_sha256']!=hashes[v]['source_sha256']:raise ValueError('native source and local graph differ')
    inventory=copy.deepcopy(old['inventories'][str(floor)]);owners=load(paths['plan_graph'].with_name('ordered-owner-evidence.json'))
    changed={r['equipment_id']for r in owners['new_services']};rows={r['equipment_id']:r for r in inventory['records']};native={}
    with paths['axis_devices'].open(encoding='utf-8-sig',newline='')as stream:devices=list(csv.DictReader(stream))
    for did in sorted(changed):
        row=rows[did];native[did]={}
        for v in graphs:
            services={s:inspect_branch(docs[v],graphs[v],did,s,hashes[v],v,devices)for s in ('supply','return')}
            if any(p['ready_for_mapping_comparison']is not True for p in services.values()):raise ValueError('new owner branch lacks independent native evidence: '+did+'/'+v+'/'+str(services))
            row['views'][v]['services']=services;native[did][v]=services
        row['ready_for_mapping_comparison']=True
    # Historical traces are compared on the current graphs, not declared fresh
    # native observations. Their original evidence and graph hashes stay intact.
    for row in inventory['records']:
        for v in graphs:
            for s,p in row['views'][v].get('services',{}).items():
                if p.get('ready_for_mapping_comparison')is True and service_route(graphs[v],row['equipment_id'],s)!=p['trace']:raise ValueError('historical service trace changed')
    current=discover_floor(graphs,inventory,floor);new=additions(previous['records'],current['records']);proofs={}
    for row in new:
        mid=row['mapping_id']
        if row['kind']=='equipment_branch':
            did=row['equipment_id']
            if did not in changed:raise ValueError('new branch outside independently repaired owners')
            proofs[mid]={v:native[did][v][row['system']]for v in graphs}
        elif row['kind']=='same_floor_T_to_T_main':
            scope=dict(row,plan_nodes=[row['plan_start'],row['plan_end']],iso_nodes=[row['iso_start'],row['iso_end']])
            proofs[mid]=source_check(docs,graphs,scope,hashes)
        else:raise ValueError('unsupported newly discovered path family')
        row.update(status='native_path_correspondence_independently_source_checked',DN_used_for_mapping=False,physical_values_assigned=0,human_accepted=False)
    lanes=verify_once(paths['lanes'].parent,verify_lanes);units=unit_evidence(docs['plan'],load(paths['units']))
    with paths['plan_components'].open(encoding='utf-8-sig',newline='')as stream:components=list(csv.DictReader(stream))
    members=member_paths(docs['plan'],plan,components,lanes,load(paths['member_policy']),units,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
    old_members=verify_once(paths['old_members'].parent,importlib.import_module('confirmed_member_plan_paths').verify_output)
    new_runs=preserve_member_runs(old_members['records'],members['records']);mains={r['plan_edges'][0]:r for r in new if r['kind']=='same_floor_T_to_T_main'}
    if set(new_runs)!=mains.keys():raise ValueError('new member runs and independently mapped mains differ')
    checked();return dict(mode=MODE,inputs=manifest['inputs'],floor=floor,new_records=new,native_evidence=proofs,
        old_correspondences=copy.deepcopy(previous['records']),old_correspondence_evidence_scope='historical_native_evidence_pinned_and_current_service_routes_rechecked',
        old_mapping_IDs_preserved=True,new_mapping_ID_basis='kind_floor_service_and_original_plan_axis_path_ids_not_discovery_ordinal',
        member_plan_paths=members,new_member_plan_edges=new_runs,current_junction_mapping=current['junction_mapping'],
        full_floor_structure_passed=current['full_floor_structure']is not None,full_floor_unresolved_reason=current['full_floor_unresolved_reason'],
        source_preflight=preflight,counts=dict(old_correspondences=len(previous['records']),new_correspondences=len(new),new_equipment_branches=sum(r['kind']=='equipment_branch'for r in new),new_mains=len(mains),all_member_runs=len(members['records']),old_member_runs=len(old_members['records']),new_member_runs=len(new_runs)),
        DN_used_for_mapping=False,local_graphs_mutated=False,detail_drawing_span_used_as_physical_length=False,attributes_fused=False,human_accepted=False)

def implementation_hashes():
    names=('rebuild_ordered_sideview_owners','ordered_sideview_equipment_owners','native_exploded_caption_identity','confirmed_member_plan_paths','confirmed_compound_pipe_lanes','native_plan_projection_lengths','crossview_equipment_branch_inventory','batch_apply_crossview_rules','batch_native_main_chains','match_source_checked_crossview_paths','source_readability','native_replay_session')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);target=output/'ordered-owner-crossview.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementation_hashes(),output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'ordered-owner-crossview.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('ordered-owner mapping implementation, input or artifact changed')
    result=compute(load(m['path']))
    if encode(result)!=target.read_bytes():raise ValueError('independent native crossview extension differs')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('source-pinned manifest and fresh output required')
            r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
