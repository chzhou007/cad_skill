"""Bind fresh member plan paths to unchanged, qualified axis correspondences.

The caller qualifies the complete cached artifact and its source comparison.
This layer changes effective attributes and review identity, not local topology
or correspondence. Native member paths are independently replayed on each call.
"""
import copy,math,re,sys
from pathlib import Path
for p in (Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts',Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'):
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha
from confirmed_member_plan_paths import verify_output
from native_replay_session import verify_once
from attach_anchored_floor_main_attributes import horizontal_domain
MODE='qualified_axis_confirmed_member_plan_runs_v1'

def collect(graph,rendered,members,hashes,angles):
    if any(not isinstance(h,str)or not re.fullmatch('[0-9a-f]{64}',h)for h in hashes.values()):raise ValueError('qualified member source hashes required')
    root=graph['sourceFullPlanBatchAttributes'];raw={e['edge_id']:e for e in graph['edges']};view={e['edge_id']:e for e in rendered['edges']}
    if root['source_verification_pending']is not False or root['human_accepted']is not False:raise ValueError('unqualified parent source scopes')
    if members['local_connectivity_changed']is not False or members['detail_drawing_span_used_as_length']is not False:raise ValueError('member topology or metric domain changed')
    records=[];pending=[];used=set()
    for row in members['records']:
        candidates=[s for s in root['records']if s['floor']==row['floor']and row['plan_edge_id']in s['plan_edges']]
        if len(candidates)!=1:pending.append(dict(plan_edge_id=row['plan_edge_id'],reason='no_unique_existing_axis_correspondence'));continue
        s=candidates[0]
        if (s['kind']!='same_floor_T_to_T_main'or s['plan_edges']!=[row['plan_edge_id']]or len(s['iso_edges'])!=1
            or s['group_scope_not_allocated_to_child_edges']is not False):pending.append(dict(plan_edge_id=row['plan_edge_id'],reason='existing_mapping_is_not_one_to_one_same_floor_main'));continue
        eid=s['iso_edges'][0];edge=raw[eid]
        if (s['system']!=row['system']or s['plan_drawn_nominal_mm']!=row['nominal_mm']or s['graph_sha256']['plan']!=members['graph_sha256']
            or s['source_sha256']['plan']!=members['source_sha256']or edge['batch_plan_attribute_scopes']!=s):raise ValueError('member scope conflicts with qualified current mapping or DN')
        if eid in used:raise ValueError('member axis edge claimed twice')
        for key in ('start_node_id','end_node_id','attribute_paths','system'):
            if view[eid].get(key)!=edge.get(key):raise ValueError('rendered axis geometry differs from qualified canonical graph')
        local=dict(iso_edges=[eid],iso_start=edge['start_node_id'],iso_end=edge['end_node_id'],floor=row['floor'],system=row['system'])
        try:axis_path=horizontal_domain(graph,local,angles)
        except ValueError as exc:pending.append(dict(plan_edge_id=row['plan_edge_id'],reason=str(exc)));continue
        value=row['horizontal_plan_run_centerline_mm']
        if (isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value)or value<=0
            or row['net_pipe_cut_length_mm']is not None or row['installed_whole_edge_length_mm']is not None
            or row['detail_inline_positions_scaled_to_plan']is not False or row['run_centerline_includes_inline_assembly_extents']is not True):raise ValueError('member run was promoted to an unsupported pipe length')
        used.add(eid);records.append(dict(row,axis_edge_id=eid,axis_mapping_id=s['mapping_id'],axis_start_node=edge['start_node_id'],axis_end_node=edge['end_node_id'],
            axis_attribute_paths=[copy.deepcopy(axis_path)],source_sha256=copy.deepcopy(s['source_sha256']),plan_graph_sha256=members['graph_sha256'],
            mapping_receipt_sha256=s['mapping_receipt_sha256'],human_accepted=False,related_HIL_confirmation_inherited=False))
    return dict(mode=MODE,records=records,pending=pending,axis_edges=len(records),source_bindings=copy.deepcopy(hashes),
        original_local_topology_unchanged=True,original_axis_correspondences_unchanged=True,net_pipe_cut_lengths_assigned=0,human_accepted=False)

def from_artifact(graph_path,rendered_path,member_proof,expected_graph_hash,angles):
    if sha(graph_path)!=expected_graph_hash:raise ValueError('qualified member axis parent changed')
    proof=Path(member_proof);before={str(p):sha(p)for p in(graph_path,rendered_path,proof)};members=verify_once(proof.parent,verify_output)
    result=collect(load(graph_path),load(rendered_path),members,dict(axis_graph=expected_graph_hash,rendered_graph=sha(rendered_path),member_proof=sha(proof)),angles)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('qualified member inputs changed during source replay')
    return result
