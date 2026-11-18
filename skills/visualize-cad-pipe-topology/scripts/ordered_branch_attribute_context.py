"""Source-bound drawn branch context; never whole axis DN or pipe length."""
import copy,math,sys
from pathlib import Path
for owner in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/owner/'scripts'))
from confirm_crossview_paths import load,sha
from ordered_anchor_branch_paths import verify_output
from native_replay_session import verify_once
MODE='qualified_ordered_anchor_drawn_branch_attributes_v1'

def collect(graph,rendered,proof,hashes):
    if proof['original_local_graphs_mutated']is not False or proof['original_axis_graph_mutated']is not False or proof['whole_axis_DN_assigned']!=0 or proof['physical_whole_edge_lengths_assigned']!=0 or proof['anchor_feedback_into_its_own_parent']is not False:raise ValueError('ordered branch producer changed protected scope')
    if proof['source_hashes']['parent_graph']!=hashes['axis_graph']or proof['source_hashes']['axis_graph']!=graph['sourceFullPlanBatchAttributes']['source_hashes']['identity_graph']:raise ValueError('ordered branch identity/qualified graph differs')
    raw={e['edge_id']:e for e in graph['edges']};view={e['edge_id']:e for e in rendered['edges']};records=[];pending=copy.deepcopy(proof['pending']);used=set()
    for source in proof['records']:
        routes=source['routes'];ids=routes['iso']['edges']
        if len(ids)!=1:
            pending.append(dict(mapping_id=source['mapping_id'],reason='multi_edge_branch_context_keeps_group_metric_unallocated'));continue
        eid=ids[0];edge=raw[eid];snapshot=source['iso_snapshot']['edges'][0]
        if eid in used or any(edge.get(k)!=snapshot.get(k)or view[eid].get(k)!=edge.get(k)for k in('edge_id','start_node_id','end_node_id','system','attribute_paths','start_port_id','end_port_id','source_insert_handle')):raise ValueError('ordered branch actual source path/port identity changed')
        if edge.get('batch_plan_attribute_scopes')or edge.get('cross_view_attributes')or edge.get('axis_riser_attributes')or edge.get('plan_segment_attributes'):raise ValueError('ordered drawing branch cannot overwrite another attribute owner')
        if source['system']!=edge['system']or source['physical_port_verified']is not False or source['whole_axis_DN_selected']is not False or source['whole_axis_physical_length_mm']is not None or source['remote_equipment_identity_inferred']is not False:raise ValueError('ordered branch role was promoted')
        metric=source['plan_horizontal_projection'];pieces=metric['pieces'];value=metric['value_mm']
        if not math.isfinite(value)or value<=0 or abs(sum(p['length_mm']for p in pieces)-value)>.0001 or metric['installed_whole_edge_length_mm']is not None or source['whole_horizontal_plan_route_mm']is not None or source['circle_radius_added_to_metric']is not False or source['axis_marker_centre_span_added_to_metric']is not False:raise ValueError('ordered branch metric has unsupported whole/display extents')
        used.add(eid);records.append(dict(axis_edge_id=eid,mapping_id=source['mapping_id'],parent_mapping_id=source['parent_mapping_id'],floor=source['floor'],system=source['system'],
            axis_start_node=edge['start_node_id'],axis_end_node=edge['end_node_id'],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),axis_port_id=source['axis_drawing_port']['port_id'],axis_marker_handle=edge['source_insert_handle'],axis_display_segment_index=source['axis_drawing_port']['display_segment_index'],
            main_anchor=copy.deepcopy(source['main_anchor']),plan_edges=copy.deepcopy(routes['plan']['edges']),plan_scope_paths=[path for e in source['plan_snapshot']['edges']for path in copy.deepcopy(e['attribute_paths'])],plan_boundary_id=routes['plan']['terminal_id'],
            known_plan_pipe_XY_mm=value,plan_horizontal_projection=copy.deepcopy(metric),plan_drawn_nominal_mm=source['plan_drawn_nominal_mm'],plan_DN_records=copy.deepcopy(source['plan_DN_records']),
            local_DN_evidence_status=source['local_DN_evidence_status'],whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,physical_port_verified=False,remote_equipment_identity_inferred=False,
            circle_radius_added_to_metric=False,axis_marker_centre_span_added_to_metric=False,related_HIL_confirmation_inherited=False,human_accepted=False,
            source_sha256=dict(plan=proof['source_hashes']['plan_source_'+str(source['floor'])],iso=proof['source_hashes']['axis_source']),plan_graph_sha256=proof['source_hashes']['plan_graph_'+str(source['floor'])]))
    return dict(mode=MODE,records=records,pending=pending,source_bindings=hashes,axis_edges=len(records),local_topology_mutated=False,whole_axis_values_assigned=0,physical_ports_created=0,human_accepted=False)

def from_artifact(graph_path,rendered_path,branch_proof,parent_manifest,context):
    paths=[Path(p)for p in(graph_path,rendered_path,branch_proof,parent_manifest)];before={str(p):sha(p)for p in paths};fresh=verify_once(Path(branch_proof).parent,verify_output)
    if fresh['source_hashes']['parent_manifest']!=sha(parent_manifest)or fresh['source_hashes']['parent_graph']!=sha(graph_path):raise ValueError('branch source proof belongs to another qualified parent')
    receipt=load(Path(branch_proof).parent/'receipt.json');manifest=load(receipt['manifest']['path']);ordered_path=manifest['inputs']['ordered_proof']['path']
    if sha(ordered_path)!=fresh['source_hashes']['ordered_proof']:raise ValueError('original ordered source proof changed')
    # The native branch verifier just replayed this exact main proof. Re-derive
    # prior context values instead of trusting saved UI values or pass flags.
    from ordered_group_metric_context import collect as main_context
    expected=main_context(load(graph_path),load(rendered_path),load(ordered_path),context,dict(axis_graph=sha(graph_path),rendered_graph=sha(rendered_path),length_proof=sha(ordered_path)))
    if context.get('ordered_group_plan_runs')!=expected:raise ValueError('retained ordered main context differs from freshly replayed source')
    result=collect(load(graph_path),load(rendered_path),fresh,dict(axis_graph=sha(graph_path),rendered_graph=sha(rendered_path),branch_proof=sha(branch_proof)))
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('branch context inputs changed during native replay')
    return result
