"""Compose checked source/member bridge attributes on unchanged axis edges."""
import copy,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from confirm_crossview_paths import load,sha
from rebuild_compound_member_bridges import verify_output,MODE as SOURCE_MODE
from noncompound_main_extent_context import component_identities
MODE='qualified_native_compound_member_inline_bridges_v1'
def collect(raw,rendered,proof,bindings,prior):
    if proof.get('mode')!=SOURCE_MODE or proof.get('DN_used_for_mapping')is not False or proof.get('source_drawing_graphs_unchanged')is not True or proof.get('installed_lengths_assigned')!=0 or proof.get('human_accepted')is not False:raise ValueError('unsupported native bridge result')
    if proof['source_hashes']['raw_axis_graph']!=bindings['axis_graph']or proof['source_hashes']['member_interfaces']!=prior.get('compound_member_interfaces',{}).get('source_bindings',{}).get('native_proof'):raise ValueError('native bridge parent or axis source differs')
    if prior.get('source_graph_sha256')!=bindings['axis_graph']or prior.get('rendered_graph_sha256')!=bindings['rendered_graph']:raise ValueError('bridge context graph identity differs')
    reserved={r['axis_edge_id']for root in prior.values()if isinstance(root,dict)for r in root.get('records',[])if r.get('axis_edge_id')};original={e['edge_id']:e for e in raw['edges']};display={e['edge_id']:e for e in rendered['edges']};records=[];seen=set()
    for r in proof['records']:
        eid=r['axis_edge_id']
        if eid in seen or eid in reserved:raise ValueError('bridge conflicts with an existing attribute owner')
        seen.add(eid);e,v=original[eid],display[eid]
        if any(e.get(k)!=v.get(k)for k in('edge_id','system','start_node_id','end_node_id','attribute_paths'))or r['axis_nodes']!=[e['start_node_id'],e['end_node_id']]or r['axis_attribute_paths']!=e['attribute_paths']or r['system']!=e['system']:raise ValueError('bridge raw/rendered source snapshot differs')
        if any(r.get(k)is not None for k in('whole_centerline_length_mm','installed_whole_length_mm','net_pipe_cut_length_mm','physical_elevation_mm'))or r['inline_graphic_spans_used_as_physical_length']is not False:raise ValueError('bridge inline graphic span promoted to physical length')
        if not math.isfinite(r['nominal_mm'])or r['nominal_mm']<=0 or any(r['floor']!=e.get(k)for k in('floor_start','floor_end')):raise ValueError('bridge DN/floor invalid')
        if not r['plan_pieces']or abs(sum(p['measured_plan_pipe_projection_mm']or 0 for p in r['plan_pieces'])-r['plan_pipe_projection_mm'])>.0001:raise ValueError('bridge source pipe projection differs')
        if any(p['kind']=='native_inline_joint'and p.get('physical_inline_length_mm')is not None for p in r['plan_pieces']):raise ValueError('inline component length must remain unknown')
        if any(r['source_hashes'].get(k)!=proof['source_hashes'].get(k)for k in proof['source_hashes']):raise ValueError('bridge native source bindings differ')
        if any(e.get(k)for k in('axis_riser_attributes','plan_segment_attributes','anchored_floor_main_attributes','external_feed_plan_attributes','cross_view_attributes','batch_plan_attribute_scopes')):raise ValueError('bridge needs explicit legacy owner reconciliation')
        identities=component_identities(e,v,rendered);names={i['source_device_name']for i in identities};paired={p['axis']['device_name']for p in r['component_correspondences']}
        if len(paired)!=len(r['component_correspondences'])or paired!=names:raise ValueError('bridge paired component instance identities differ')
        records.append(dict(copy.deepcopy(r),component_instance_identities=identities,related_HIL_confirmation_inherited=False))
    if len(records)!=proof['counts']['qualified_bridges']:raise ValueError('bridge count differs')
    return dict(mode=MODE,records=records,axis_edges=len(records),source_bindings=bindings,native_sources=proof['source_hashes'],member_topology_rebuilt=True,
        original_axis_geometry_unchanged=True,installed_lengths_assigned=0,existing_attribute_owners_preserved=True,remaining_external_ports=proof['member_local_graph']['external_ports'],
        member_graph_counts=dict(nodes=len(proof['member_local_graph']['nodes']),edges=len(proof['member_local_graph']['edges'])),human_accepted=False)
def from_artifact(raw_path,rendered_path,proof_path,prior):
    before={str(p):sha(p)for p in(raw_path,rendered_path,proof_path)};proof=verify_output(Path(proof_path).parent)
    result=collect(load(raw_path),load(rendered_path),proof,dict(axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path),member_interfaces=proof['source_hashes']['member_interfaces']),prior)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('bridge inputs changed during composition')
    return result
