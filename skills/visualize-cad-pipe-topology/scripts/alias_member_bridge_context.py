"""Publish original native alias bridges without changing local topology."""
import copy,math,sys
from pathlib import Path
for name in('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha
from rebuild_alias_member_inline_bridges import verify_output,MODE as SOURCE_MODE
from noncompound_main_extent_context import component_identities
MODE='qualified_confirmed_alias_member_inline_bridges_v1'

def collect(raw,rendered,proof,bindings,prior):
    if proof.get('mode')!=SOURCE_MODE or proof.get('parent_alias_interfaces_independently_replayed')is not True or proof.get('DN_used_for_mapping')is not False or proof.get('source_drawing_graphs_unchanged')is not True or proof.get('all_vertical_attributes_from11')is not True or proof.get('whole_centerline_lengths_assigned')!=0 or proof.get('installed_lengths_assigned')!=0 or proof.get('human_accepted')is not False:raise ValueError('unsupported native alias bridge proof')
    source=proof['source_hashes'];parent=prior.get('alias_member_interfaces',{}).get('source_bindings',{})
    if source['raw_axis_graph']!=bindings['axis_graph']or source['member_interfaces']!=parent.get('native_proof')or source['plan_graph']!=parent.get('plan_graph')or source['axis_graph']!=parent.get('axis_local_graph'):raise ValueError('alias bridge parent or graph source differs')
    if prior.get('source_graph_sha256')!=bindings['axis_graph']or prior.get('rendered_graph_sha256')!=bindings['rendered_graph']:raise ValueError('alias bridge graph context differs')
    reserved={r['axis_edge_id']for root in prior.values()if isinstance(root,dict)for r in root.get('records',[])if r.get('axis_edge_id')}
    original={e['edge_id']:e for e in raw['edges']};display={e['edge_id']:e for e in rendered['edges']};records=[];seen=set()
    for row in proof['records']:
        eid=row['axis_edge_id']
        if eid in seen or eid in reserved:raise ValueError('alias bridge conflicts with prior owner')
        seen.add(eid);e,v=original[eid],display[eid]
        if any(e.get(k)!=v.get(k)for k in('edge_id','system','start_node_id','end_node_id','attribute_paths'))or row['axis_nodes']!=[e['start_node_id'],e['end_node_id']]or row['axis_attribute_paths']!=e['attribute_paths']or row['system']!=e['system']:raise ValueError('alias bridge raw/rendered identity differs')
        if any(row.get(k)is not None for k in('whole_centerline_length_mm','installed_whole_length_mm','net_pipe_cut_length_mm','physical_elevation_mm'))or row['inline_graphic_spans_used_as_physical_length']is not False:raise ValueError('inline graphic spans cannot become complete physical length')
        if not isinstance(row['nominal_mm'],(int,float))or isinstance(row['nominal_mm'],bool)or not math.isfinite(row['nominal_mm'])or row['nominal_mm']<=0 or any(e.get(k)!=row['floor']for k in('floor_start','floor_end')):raise ValueError('alias bridge DN or floor invalid')
        if row['source_hashes']['original_plan_graph']!=source['plan_graph']or row['source_hashes']['plan_graph']!=proof['reading_projection_sha256']:raise ValueError('private/original reading domain provenance differs')
        if not row['plan_pieces']or abs(sum(p['measured_plan_pipe_projection_mm']or 0 for p in row['plan_pieces'])-row['plan_pipe_projection_mm'])>.0001:raise ValueError('alias bridge pipe-only projection differs')
        if any(p['kind']=='native_inline_joint'and p.get('physical_inline_length_mm')is not None for p in row['plan_pieces']):raise ValueError('inline physical length must remain unknown')
        if any(e.get(k)for k in('axis_riser_attributes','plan_segment_attributes','anchored_floor_main_attributes','external_feed_plan_attributes','cross_view_attributes','batch_plan_attribute_scopes')):raise ValueError('legacy attribute owner needs explicit reconciliation')
        identities=component_identities(e,v,rendered);paired={p['axis']['device_name']for p in row['component_correspondences']}
        if len(paired)!=len(row['component_correspondences'])or paired!={i['source_device_name']for i in identities}:raise ValueError('alias bridge component identities differ')
        records.append(dict(copy.deepcopy(row),component_instance_identities=identities,related_HIL_confirmation_inherited=False))
    if len(records)!=proof['counts']['qualified_bridges']:raise ValueError('alias bridge population differs')
    return dict(mode=MODE,records=records,source_bindings=bindings,source_sheet='09-二层顶部水管平面图.dxf',source_hashes=source,
        reading_projection_sha256=proof['reading_projection_sha256'],member_topology_rebuilt=True,original_axis_geometry_unchanged=True,prior_owners_preserved=True,
        all_vertical_attributes_from11=True,complete_lengths_assigned=0,installed_lengths_assigned=0,
        remaining_external_ports=proof['member_local_graph']['external_ports'],human_accepted=False)

def from_artifact(raw_path,rendered_path,proof_path,prior):
    before={str(p):sha(p)for p in(raw_path,rendered_path,proof_path)};proof=verify_output(Path(proof_path).parent)
    result=collect(load(raw_path),load(rendered_path),proof,dict(axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path)),prior)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('alias bridge inputs changed during composition')
    return result
