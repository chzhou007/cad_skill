"""Qualified one-to-one native mains; plan DN and drawn XY remain distinct."""
import copy,math,sys
from pathlib import Path
for owner in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/owner/'scripts'))
from confirm_crossview_paths import load,sha
from rebuild_anchor_bounded_main_batch import verify_output
from ordered_anchor_branch_paths import qualified_local_DN
from native_replay_session import verify_once
MODE='qualified_native_anchor_bounded_main_attributes_v1'

def collect(graph,rendered,proof,local_DN,hashes):
    if proof.get('local_topology_changed')is not False or proof.get('axis_graph_changed')is not False or proof.get('component_assignments_changed')is not False or proof.get('DN_used_for_mapping')is not False:raise ValueError('bounded main source changed protected roles')
    root=graph['sourceFullPlanBatchAttributes'];sources=proof['source_hashes']
    if root['source_hashes']['identity_graph']!=sources['axis_graph']or root['source_hashes']['axis_source']!=sources['axis_source']:raise ValueError('bounded main axis source identity differs')
    raw={e['edge_id']:e for e in graph['edges']};view={e['edge_id']:e for e in rendered['edges']};records=[];seen=set()
    for floor,result in sorted(proof['floors'].items()):
        for row in result['records']:
            if len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1:raise ValueError('bounded main child must be one-to-one')
            pe,eid=row['plan_edges'][0],row['iso_edges'][0];edge=raw[eid];group=next(g for g in result['groups']if g['mapping_id']in row['source_group_ids']);snap=next(e for e in group['native']['iso']['snapshot']['edges']if e['edge_id']==eid)
            if eid in seen or any(edge.get(k)!=snap.get(k)or view[eid].get(k)!=edge.get(k)for k in('edge_id','system','start_node_id','end_node_id','attribute_paths')):raise ValueError('bounded main child geometry changed')
            if any(edge.get(k)for k in('batch_plan_attribute_scopes','cross_view_attributes','axis_riser_attributes','plan_segment_attributes','anchored_floor_main_attributes')):raise ValueError('bounded main cannot overwrite another attribute owner')
            floor_values=[[edge[k]for k in keys if k in edge]for keys in(('floor_start','start_floor'),('floor_end','end_floor'))]
            if {edge['start_node_id'],edge['end_node_id']}!={row['iso_start'],row['iso_end']}or edge['system']!=row['system']or any(not v or any(x!=row['floor']for x in v)for v in floor_values):raise ValueError('bounded main child service/floor differs')
            metric=next(m for m in result['metrics']if m['mapping_id']==row['mapping_id']);projection=metric['projection']
            if projection is not None:
                value=projection['value_mm'];pieces=projection['pieces']
                if isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value)or value<=0 or not pieces or abs(sum(p['length_mm']for p in pieces)-value)>.0001 or projection['installed_whole_edge_length_mm']is not None:raise ValueError('bounded main metric invalid or promoted')
            dn=copy.deepcopy(local_DN[floor][pe]);scope=next(e for e in group['native']['plan']['snapshot']['edges']if e['edge_id']==pe)['attribute_paths']
            if dn['scope_paths']!=scope or dn['system']!=row['system']:raise ValueError('retained plan DN no longer covers native child')
            nominal=dn['nominal_mm']
            if nominal is not None and(isinstance(nominal,bool)or not isinstance(nominal,(int,float))or not math.isfinite(nominal)or nominal<=0):raise ValueError('invalid native plan DN')
            seen.add(eid);records.append(dict(axis_edge_id=eid,mapping_id=row['mapping_id'],floor=row['floor'],system=row['system'],axis_start_node=edge['start_node_id'],axis_end_node=edge['end_node_id'],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),plan_edges=[pe],plan_Ts=[row['plan_start'],row['plan_end']],axis_Ts=[row['iso_start'],row['iso_end']],nominal_mm=nominal,plan_DN_record=dn,plan_scope_paths=copy.deepcopy(scope),plan_horizontal_projection=copy.deepcopy(projection),metric_reader=metric.get('reader'),metric_attempts=copy.deepcopy(metric.get('attempts',[])),whole_axis_DN_selected=nominal is not None,whole_axis_physical_length_mm=None,net_pipe_cut_length_mm=None,related_HIL_confirmation_inherited=False,human_accepted=False,source_sha256=dict(plan=sources['plan_source_'+floor],iso=sources['axis_source']),plan_graph_sha256=sources['plan_graph_'+floor],DN_status='exact_qualified_local_plan_DN_retained_not_fresh_global_DN_rebuild'))
    return dict(mode=MODE,records=records,axis_edges=len(records),source_bindings=hashes,local_topology_mutated=False,physical_lengths_assigned=0,human_accepted=False)

def from_artifact(graph_path,rendered_path,proof_path,DN_result,DN_receipt,parent_manifest,context):
    files=[Path(p)for p in(graph_path,rendered_path,proof_path,DN_result,DN_receipt,parent_manifest)];before={str(p):sha(p)for p in files}
    fresh=verify_once(Path(proof_path).parent,verify_output);receipt=load(Path(proof_path).parent/'receipt.json');manifest=load(receipt['manifest']['path']);inputs=manifest['inputs'];raw=load(graph_path);rendered=load(rendered_path)
    if load(parent_manifest)['sourceHashes']['graph']!=sha(graph_path):raise ValueError('qualified parent raw graph identity differs')
    original_batch=Path(inputs['batch_result']['path']).parent/'main-chain-batch-receipt.json'
    if raw['sourceFullPlanBatchAttributes']['source_hashes']['mapping_receipt']!=sha(original_batch):raise ValueError('qualified parent has another complete source batch')
    floors=sorted(fresh['floors']);plans={f:load(inputs['plan_graph_'+f]['path'])for f in floors}
    local=qualified_local_DN(raw,load(DN_result),DN_receipt,DN_result,plans,{f:fresh['source_hashes']['plan_source_'+f]for f in floors},{f:fresh['source_hashes']['plan_graph_'+f]for f in floors})
    # This exact ordered-main owner was freshly replayed by the new producer.
    from ordered_group_metric_context import collect as ordered_context
    ordered=inputs['ordered_proof']['path'];expected=ordered_context(raw,rendered,load(ordered),context,dict(axis_graph=sha(graph_path),rendered_graph=sha(rendered_path),length_proof=sha(ordered)))
    if context.get('ordered_group_plan_runs')!=expected:raise ValueError('prior ordered-main context differs from current native proof')
    result=collect(raw,rendered,fresh,local,dict(axis_graph=sha(graph_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path),DN_receipt=sha(DN_receipt),DN_result=sha(DN_result)))
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('bounded main attribute input changed')
    return result

def retained_branches(proof_path,graph_path,rendered_path,context):
    from ordered_anchor_branch_paths import implementation_hashes
    from ordered_branch_attribute_context import collect as branch_context
    proof_path=Path(proof_path);receipt=load(proof_path.parent/'receipt.json');spec=receipt['manifest'];proof=load(proof_path)
    if sha(proof_path)!=receipt['output_sha256']or receipt['implementation_sha256']!=implementation_hashes()or sha(spec['path'])!=spec['sha256']:raise ValueError('retained drawn-branch source owner changed')
    source=load(spec['path'])['inputs']
    if any(sha(v['path'])!=v['sha256']for v in source.values()):raise ValueError('retained drawn-branch native dependency changed')
    expected=branch_context(load(graph_path),load(rendered_path),proof,dict(axis_graph=sha(graph_path),rendered_graph=sha(rendered_path),branch_proof=sha(proof_path)))
    if context.get('ordered_anchor_branches')!=expected:raise ValueError('retained8 branch context differs')
    return dict(status='exact_source_bound_branch_context_retained_not_fresh_branch_reconstruction',axis_edges=expected['axis_edges'],proof_sha256=sha(proof_path))
