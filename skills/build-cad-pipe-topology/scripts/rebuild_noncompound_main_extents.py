"""Recheck noncompound current main lengths without assuming source point order.

Consumes existing mappings only. The complete original source parents replay
first; this producer does not discover routes, infer flow or edit local graphs.
"""
import argparse,copy,importlib,sys
from pathlib import Path
_pipeline=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_pipeline)not in sys.path:sys.path.insert(0,str(_pipeline))
from confirm_crossview_paths import load,sha,encode
from rebuild_anchor_bounded_main_batch import verify_output as verify_parent
from native_replay_session import verify_once
from ordered_anchor_branch_paths import qualified_local_DN
from native_main_endpoint_extent import qualify
from native_current_junction_reader import make_reader
from crossview_equipment_branch_inventory import native_tee
from match_source_checked_crossview_paths import selected_snapshot
from batch_native_path_coverage import collect as coverage
from native_plan_projection_lengths import unit_evidence,lengths
from source_readability import read_source
MODE='native_noncompound_undirected_main_extents_v1'
from noncompound_main_extent_guard import barriers,check as check_carrier
from rebuild_compound_member_projections import verify_output as verify_member
DERIVED_CANDIDATE_SHA='e4e6792dad053995fe7977261753dd6fea71da9e1996da6d2a8425c3c91f6684'

def compute(manifest,announce=lambda _:None):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('main extent input changed')
    checked();announce('Replaying complete native source parents and current six-main proof')
    member=verify_once(paths['member_proof'].parent,verify_member)
    if encode(member)!=paths['member_proof'].read_bytes():raise ValueError('current member parent differs')
    member_axis={r['axis_edge_id']for r in member['records']}
    # The member owner just reconstructed and byte-compared this exact parent.
    # Consume that fresh transitive result instead of replaying the same full
    # ancestry twice. No prior-job pass flag is accepted by this entry.
    if sha(paths['parent_main_proof'])!=member['source_hashes']['parent_main_proof']:raise ValueError('fresh member parent binding differs')
    parent=load(paths['parent_main_proof'])
    if encode(parent)!=paths['parent_main_proof'].read_bytes():raise ValueError('current native main parent differs')
    for key,digest in parent['source_hashes'].items():
        if key not in paths or sha(paths[key])!=digest:raise ValueError('parent native source scope differs '+key)
    raw=load(paths['raw_axis_graph']);batch=load(paths['batch_result']);axis=load(paths['axis_graph']);raw_edges={e['edge_id']:e for e in raw['edges']}
    receipt=paths['batch_result'].parent/'main-chain-batch-receipt.json'
    if raw['sourceFullPlanBatchAttributes']['source_hashes']['mapping_receipt']!=sha(receipt)or batch['identity_graph_sha256']!=sha(paths['axis_graph']):raise ValueError('qualified current mapping identity differs')
    floors=sorted(batch['floors']);plans={f:load(paths['plan_graph_'+f])for f in floors}
    local=qualified_local_DN(raw,load(paths['DN_result']),paths['DN_receipt'],paths['DN_result'],plans,{f:sha(paths['plan_source_'+f])for f in floors},{f:sha(paths['plan_graph_'+f])for f in floors})
    originals={s['mapping_id']:s for s in raw['sourceFullPlanBatchAttributes']['records']};records=[];pending=[];screened=0;preflight={};axis_doc=None
    carrier_proofs={}
    for floor in floors:
        plan=plans[floor];eligible=[]
        doc,preflight[floor]=read_source(paths['plan_source_'+floor])
        carrier_proofs[floor]=barriers(doc,plan,sha(paths['plan_source_'+floor]))
        for row in batch['floors'][floor]['records']:
            screened+=1;scope=originals[row['mapping_id']]
            if row['kind']!='same_floor_T_to_T_main'or len(row['iso_edges'])!=1 or len(row['plan_edges'])!=1 or scope['whole_axis_nominal_mm']is not None or scope['plan_drawn_nominal_mm']is None:continue
            try:
                check_carrier(row,carrier_proofs[floor])
                if member_axis.intersection(row['iso_edges']):raise ValueError('existing_member_context_owns_this_main')
                qualify(plan,axis,row,scope['plan_drawn_nominal_mm'],None,manifest['isometric_horizontal_directions_degrees'])
                pe=next(e for e in plan['edges']if e['edge_id']==row['plan_edges'][0])
                if pe.get('source_flexible_joints'):raise ValueError('inline assemblies retain their original metric owner')
            except ValueError as exc:
                pending.append(dict(mapping_id=row['mapping_id'],axis_edges=row['iso_edges'],reason=str(exc)));continue
            eligible.append((row,scope))
        if not eligible:continue
        if axis_doc is None:axis_doc,preflight['iso']=read_source(paths['axis_source'])
        units=unit_evidence(doc,load(paths['unit_policy_'+floor]));sh=sha(paths['plan_source_'+floor]);gh=sha(paths['plan_graph_'+floor]);reader=make_reader(load(paths['current_T_source_config']),sh,gh)
        hashes=dict(plan=dict(source_sha256=sh,graph_sha256=gh),iso=dict(source_sha256=sha(paths['axis_source']),graph_sha256=sha(paths['axis_graph'])))
        for row,scope in eligible:
            native={}
            for view,native_doc,g in(('plan',doc,plan),('iso',axis_doc,axis)):
                snapshot=selected_snapshot(g,row[view+'_edges'])
                if snapshot!=row[view+'_snapshot']:raise ValueError('existing mapped native snapshot changed')
                h=hashes[view];path=coverage(native_doc,g,row[view+'_edges'],h['source_sha256'],h['graph_sha256'])
                if any(s['status']!='single_source_line_covers'for e in path['edges']for s in e['segments']):raise ValueError('existing main lacks unique native LINE coverage')
                tee_reader=reader if view=='plan'else native_tee
                junctions={nid:tee_reader(native_doc,g,nid,h['source_sha256'],h['graph_sha256'])for nid in(row[view+'_start'],row[view+'_end'])}
                native[view]=dict(snapshot=snapshot,junctions=junctions,path_coverage=path,scope='existing_parent_mapping_rechecked_not_new_route_discovery',global_graph_route_uniqueness_asserted=False)
            eid=row['iso_edges'][0];raw_edge=raw_edges[eid];identity_edge=next(e for e in axis['edges']if e['edge_id']==eid)
            if any(raw_edge.get(k)!=identity_edge.get(k)for k in('edge_id','system','start_node_id','end_node_id','attribute_paths','equipment_inventory','source_insert_handle')):raise ValueError('qualified axis main geometry/components differ')
            dn=local[floor][row['plan_edges'][0]]
            if dn['nominal_mm']!=scope['plan_drawn_nominal_mm']or dn['system']!=row['system']or dn['scope_paths']!=native['plan']['snapshot']['edges'][0]['attribute_paths']:raise ValueError('qualified local DN source extent differs')
            projection=lengths(plan,native['plan']['path_coverage'],row,units)
            if scope['horizontal_projection']is None or abs(scope['horizontal_projection']['value_mm']-projection['value_mm'])>.0001:raise ValueError('replayed native plan metric differs')
            result=qualify(plan,axis,row,dn['nominal_mm'],projection,manifest['isometric_horizontal_directions_degrees'])
            records.append(dict(result,native_source_evidence=native,source_hashes=copy.deepcopy(hashes),plan_DN_record=copy.deepcopy(dn),DN_status='exact_qualified_local_plan_DN_retained_not_fresh_global_DN_rebuild',old_scope=copy.deepcopy(scope),metric_reader='inherited_native_plan_projection_with_undirected_endpoint_qualification'))
        announce(f'{floor}F: {len(eligible)} source-witnessed undirected main extents requalified')
    if len({r['axis_edge_id']for r in records})!=len(records):raise ValueError('main extent writers repeat')
    checked();return dict(mode=MODE,records=records,pending=pending,compound_carrier_barriers=carrier_proofs,retained_member_axis_edges=sorted(member_axis),compound_parent_replayed=True,source_preflight=preflight,source_hashes={k:sha(p)for k,p in paths.items()},all_parent_mapping_records_screened=screened,counts=dict(requalified_main_edges=len(records),complete_horizontal_centerlines=sum(r['complete_horizontal_centerline_route_mm']is not None for r in records),unresolved_extent_scopes=len(pending)),existing_correspondences_unchanged=True,local_topology_changed=False,source_paths_mutated=False,installed_lengths_assigned=0,net_pipe_cut_lengths_assigned=0,local_DN_retained_not_fresh_global_DN=True,human_accepted=False)

def implementation_hashes():
    names=('noncompound_main_extent_guard','compound_carrier_members','compound_pipe_label_evidence','rebuild_compound_member_projections','native_main_endpoint_extent','rebuild_anchor_bounded_main_batch','ordered_anchor_branch_paths','native_current_junction_reader','crossview_equipment_branch_inventory','match_source_checked_crossview_paths','batch_native_path_coverage','native_plan_projection_lengths','source_readability','attach_anchored_floor_main_attributes')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    before=implementation_hashes();result=compute(load(manifest_path),lambda m:print(m,flush=True))
    if before!=implementation_hashes():raise ValueError('main extent implementation changed')
    output.mkdir(parents=True);target=output/'main-extents.json';target.write_bytes(encode(result));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=before,output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');spec=receipt['manifest'];target=output/'main-extents.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(spec['path'])!=spec['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('main extent receipt or source changed')
    result=compute(load(spec['path']))
    if encode(result)!=target.read_bytes():raise ValueError('native main extent replay differs')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:
            if a.manifest or a.output:p.error('verification uses original fixed inputs')
            result=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('fixed manifest and new output required')
            result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':main()
