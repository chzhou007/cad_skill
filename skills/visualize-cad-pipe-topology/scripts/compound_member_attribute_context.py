"""Compose member-qualified plan DN/run evidence onto unchanged axis identities."""
import copy,hashlib,sys
from pathlib import Path
owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(owner)not in sys.path:sys.path.insert(0,str(owner))
from confirm_crossview_paths import load,sha,encode
from rebuild_compound_member_projections import verify_output
from native_replay_session import verify_once
MODE='qualified_native_compound_member_attributes_v1'

def collect(raw,rendered,proof,bindings):
    if proof['mode']!='native_compound_carrier_member_projection_v1'or not proof['source_drawing_graphs_unchanged']or proof['DN_selected_from_axis_value']or proof['human_accepted']:raise ValueError('unsupported native member proof')
    if raw['sourceFullPlanBatchAttributes']['source_hashes']['identity_graph']!=proof['source_hashes']['axis_graph']:raise ValueError('member axis source identity differs')
    raw_edges={e['edge_id']:e for e in raw['edges']};view={e['edge_id']:e for e in rendered['edges']};rows=[];seen=set()
    for r in proof['records']:
        eid=r['axis_edge_id'];edge=raw_edges[eid];snapshot=r['native_evidence']['iso']['snapshot']['edges'][0]
        if eid in seen or any(edge.get(k)!=snapshot.get(k)or view[eid].get(k)!=edge.get(k)for k in('edge_id','system','start_node_id','end_node_id','attribute_paths')):raise ValueError('member axis endpoint/geometry differs')
        if any(edge.get(k)for k in('axis_riser_attributes','plan_segment_attributes','anchored_floor_main_attributes','external_feed_plan_attributes','source_dimensioned_segments','source_straight_crossover_evidence','source_normalized_crossovers')):raise ValueError('member cannot replace an unrelated attribute owner')
        if any(edge.get(k)!=r['floor']for k in('floor_start','floor_end')if k in edge):raise ValueError('member floor differs')
        if r['DN_used_for_mapping']or r['physical_elevation_mm']is not None or r['installed_whole_length_mm']is not None or r['net_pipe_cut_length_mm']is not None or r['other_member_connections_inferred']:raise ValueError('member source values promoted or inferred')
        seen.add(eid);rows.append(dict(axis_edge_id=eid,axis_start_node=edge['start_node_id'],axis_end_node=edge['end_node_id'],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),floor=r['floor'],system=r['system'],
            mapping_id=r['mapping_id'],plan_edge_id=r['plan_edge_id'],member_edge_id=r['member_edge_id'],member_node_ids=r['member_node_ids'],member_scope_id=r['member_scope_id'],
            nominal_mm=r['nominal_mm'],plan_declarations=copy.deepcopy(r['plan_declarations']),source_level_literal=r['source_level_literal'],physical_elevation_mm=None,
            plan_run_centerline_mm=r['plan_run_centerline_mm'],plan_projection=copy.deepcopy(r['plan_projection']),plan_LINE=r['plan_LINE'],axis_LINE=r['axis_LINE'],
            axis_caption_crosscheck=copy.deepcopy(r['axis_caption_crosscheck']),anchors=copy.deepcopy(r['anchors']),superseded_scalar_observation=copy.deepcopy(r['superseded_scalar_observation']),
            source_plan_sha256=proof['source_hashes']['plan_source'],source_axis_sha256=proof['source_hashes']['axis_source'],source_plan_graph_sha256=proof['source_hashes']['plan_graph'],
            DN_selected_from_axis_value=False,whole_installed_length_mm=None,net_pipe_cut_length_mm=None,component_member_allocation='unresolved',related_HIL_confirmation_inherited=False,human_accepted=False))
    return dict(mode=MODE,records=rows,axis_edges=len(rows),source_bindings=bindings,member_graph_sha256=hashlib.sha256(encode(proof['member_local_graph'])).hexdigest(),
        source_drawing_graphs_unchanged=True,global_plan_topology_complete=False,component_assignments_mutated=False,human_accepted=False)

def from_artifact(raw_path,rendered_path,proof_path):
    paths=list(map(Path,(raw_path,rendered_path,proof_path)));before={str(p):sha(p)for p in paths}
    proof=verify_once(Path(proof_path).parent,verify_output)
    context=collect(load(raw_path),load(rendered_path),proof,dict(axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path)))
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('member context inputs changed')
    return context
