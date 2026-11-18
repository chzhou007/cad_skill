"""Compose newly source-qualified mappings without rewriting historical roots."""
import copy,math,sys
from pathlib import Path
for name in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/name/'scripts'))
from confirm_crossview_paths import load,sha
from rebuild_ordered_owner_crossview import verify_output,MODE as SOURCE_MODE
from native_replay_session import verify_once
from attach_anchored_floor_main_attributes import horizontal_domain
from noncompound_main_extent_context import component_identities
MODE='qualified_ordered_owner_crossview_plan_runs_v1'

def collect(raw,rendered,local_axis,proof,bindings,prior):
    if proof.get('mode')!=SOURCE_MODE or proof.get('DN_used_for_mapping')is not False or proof.get('local_graphs_mutated')is not False or proof.get('attributes_fused')is not False or proof.get('human_accepted')is not False:raise ValueError('unsupported new owner correspondence evidence')
    if prior.get('source_graph_sha256')!=bindings['axis_graph']or prior.get('rendered_graph_sha256')!=bindings['rendered_graph']:raise ValueError('qualified axis context identity differs')
    if proof['inputs']['axis_graph']['sha256']!=bindings['axis_local_graph']or proof['inputs']['plan_graph']['sha256']!=bindings['plan_graph']:raise ValueError('local mapping graph identity differs')
    reserved={r['axis_edge_id']for root in prior.values()if isinstance(root,dict)for r in root.get('records',[])if r.get('axis_edge_id')}
    indexes=[{e['edge_id']:e for e in g['edges']}for g in (raw,rendered,local_axis)];records=[];seen=set()
    members={r['plan_edge_id']:r for r in proof['member_plan_paths']['records']}
    for mapping in proof['new_records']:
        if mapping['kind']!='same_floor_T_to_T_main':continue
        if len(mapping['plan_edges'])!=1 or len(mapping['iso_edges'])!=1:raise ValueError('new owner metric requires one-to-one main mapping')
        pid,eid=mapping['plan_edges'][0],mapping['iso_edges'][0]
        if eid in seen or eid in reserved or pid not in proof['new_member_plan_edges']:raise ValueError('new owner metric collides with existing scope')
        seen.add(eid);edges=[i[eid]for i in indexes];edge=edges[0];row=members[pid]
        for e in edges[1:]:
            if any(e.get(k)!=edge.get(k)for k in('system','start_node_id','end_node_id','attribute_paths','floor_start','floor_end')):raise ValueError('raw/rendered/local axis topology differs')
        if edges[2].get('equipment_inventory')!=edge.get('equipment_inventory'):raise ValueError('native axis component inventory changed')
        component_instances=component_identities(edge,edges[1],rendered)
        if edge.get('batch_plan_attribute_scopes')or edge.get('axis_riser_attributes')or edge.get('cross_view_attributes'):raise ValueError('legacy axis owner needs explicit reconciliation')
        if row['system']!=mapping['system']or row['floor']!=mapping['floor']or row['net_pipe_cut_length_mm']is not None or row['installed_whole_edge_length_mm']is not None or row['detail_inline_positions_scaled_to_plan']is not False:raise ValueError('member service or metric interpretation differs')
        horizontal_domain(raw,mapping,prior['horizontal_directions_degrees'])
        if not math.isfinite(row['horizontal_plan_run_centerline_mm'])or row['horizontal_plan_run_centerline_mm']<=0:raise ValueError('invalid native plan length')
        records.append(dict(copy.deepcopy(row),axis_edge_id=eid,mapping_id=mapping['mapping_id'],mapping=copy.deepcopy(mapping),axis_nodes=[edge['start_node_id'],edge['end_node_id']],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),component_instance_identities=component_instances,plan_graph_sha256=bindings['plan_graph'],source_sha256={v:proof['inputs'][v+'_source']['sha256']for v in('plan','axis')},DN_used_for_mapping=False,related_HIL_confirmation_inherited=False))
    if len(records)!=proof['counts']['new_member_runs']:raise ValueError('new mapped member run population differs')
    return dict(mode=MODE,records=records,new_correspondences=copy.deepcopy(proof['new_records']),source_bindings=bindings,axis_edges=len(records),old_mapping_IDs_preserved=True,historical_contexts_preserved=True,new_mixed_or_vertical_lengths=0,installed_lengths_assigned=0,human_accepted=False)

def from_artifact(raw_path,rendered_path,proof_path,prior):
    paths=[Path(p)for p in(raw_path,rendered_path,proof_path)];before={str(p):sha(p)for p in paths};proof=verify_once(Path(proof_path).parent,verify_output)
    local=Path(proof['inputs']['axis_graph']['path']);bindings=dict(axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path),axis_local_graph=sha(local),plan_graph=proof['inputs']['plan_graph']['sha256'])
    result=collect(load(raw_path),load(rendered_path),load(local),proof,bindings,prior)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('new mapping input changed during native composition')
    return result
