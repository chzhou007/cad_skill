"""Prefer a freshly reconstructed specific provider over generic unknown DN."""
import copy,sys
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/name/'scripts'))
from confirm_crossview_paths import load,sha
from rebuild_qualified_plan_scope_extension import verify_output,MODE as SOURCE_MODE
from native_replay_session import verify_once
from noncompound_main_extent_context import component_identities
from native_main_endpoint_extent import qualify
MODE='qualified_source_provider_plan_runs_v1'

def collect(raw,rendered,axis,plan,proof,bindings,prior):
    if proof.get('mode')!=SOURCE_MODE or proof.get('specific_provider_reconstructed')is not True or proof.get('source_graphs_mutated')is not False or proof.get('DN_used_for_mapping')is not False or proof.get('physical_pipe_count_inferred')is not False or proof.get('human_accepted')is not False:raise ValueError('fresh specific native provider required')
    if proof['native_provider'].get('old_provider_receipt_accepted')is not False or proof['native_provider'].get('current_native_provider_recomputed')is not True:raise ValueError('historical receipt cannot qualify current source')
    if prior.get('source_graph_sha256')!=bindings['axis_graph']or prior.get('rendered_graph_sha256')!=bindings['rendered_graph']or proof['inputs']['plan_graph']['sha256']!=bindings['plan_graph']or proof['inputs']['axis_graph']['sha256']!=bindings['axis_local_graph']:raise ValueError('specific source graph binding differs')
    raw_edges={e['edge_id']:e for e in raw['edges']};views={e['edge_id']:e for e in rendered['edges']};native={e['edge_id']:e for e in axis['edges']};reserved={r['axis_edge_id']for root in prior.values()if isinstance(root,dict)for r in root.get('records',[])if r.get('axis_edge_id')};records=[];seen=set()
    for row in proof['records']:
        eid=row['axis_edge_id'];edge=raw_edges[eid];view=views[eid];mapping=row['current_mapping'];scope=edge.get('batch_plan_attribute_scopes')
        if eid in seen or eid in reserved or scope!=row['generic_scope_retained_as_superseded']or scope['plan_drawn_nominal_mm']is not None or any(d['status']=='conflict'for d in scope['plan_DN_records']):raise ValueError('specific provider collides or tries to overwrite a conflict')
        seen.add(eid)
        for other in(view,native[eid]):
            if any(edge.get(k)!=other.get(k)for k in('system','start_node_id','end_node_id','attribute_paths','floor_start','floor_end')):raise ValueError('current axis source geometry differs')
        check=qualify(plan,axis,mapping,row['nominal_mm'],row['provider_metric'],prior['horizontal_directions_degrees'])
        if check['complete_horizontal_centerline_route_mm']!=row['complete_horizontal_centerline_route_mm']or row['physical_source_identity_resolved']is not False:raise ValueError('specific metric or physical identity was broadened')
        pieces=row['provider_metric']['pieces'];handles={p['source_line_handle']for p in pieces};labels={e['evidence_id'][7:]for group in row['provider_DN_record']['lineage']for e in group['evidence']if e['evidence_id'].startswith('source:')}
        if len(handles)!=1 or not labels:raise ValueError('source LINE or DN lineage is missing')
        records.append(dict(copy.deepcopy(row),mapping=copy.deepcopy(mapping),plan_graph_sha256=bindings['plan_graph'],horizontal_plan_run_centerline_mm=row['complete_horizontal_centerline_route_mm'],axis_nodes=[edge['start_node_id'],edge['end_node_id']],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),shared_projected_source_LINE=next(iter(handles)),compound_text_handle=';'.join(sorted(labels)),source_sha256={k:proof['inputs'][k+'_source']['sha256']for k in('plan','axis')},component_instance_identities=component_identities(edge,view,rendered),net_pipe_cut_length_mm=None,installed_whole_edge_length_mm=None,unshown_branch_connector_length_mm=None,run_centerline_includes_inline_assembly_extents=True,detail_inline_positions_scaled_to_plan=False,DN_used_for_mapping=False,related_HIL_confirmation_inherited=False))
    return dict(mode=MODE,records=records,axis_edges=len(records),source_bindings=bindings,old_mapping_IDs_preserved=True,historical_contexts_preserved=True,new_mixed_or_vertical_lengths=0,installed_lengths_assigned=0,physical_pipe_count_inferred=False,source_provider_precedence='fresh_specific_native_scope_over_generic_unknown_never_over_conflict',human_accepted=False)

def from_artifact(raw_path,rendered_path,proof_path,prior):
    paths=[Path(p)for p in(raw_path,rendered_path,proof_path)];before={str(p):sha(p)for p in paths};proof=verify_once(Path(proof_path).parent,verify_output);ap=Path(proof['inputs']['axis_graph']['path']);pp=Path(proof['inputs']['plan_graph']['path']);bindings=dict(axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path),axis_local_graph=sha(ap),plan_graph=sha(pp))
    result=collect(load(raw_path),load(rendered_path),load(ap),load(pp),proof,bindings,prior)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('specific source input changed during composition')
    return result
