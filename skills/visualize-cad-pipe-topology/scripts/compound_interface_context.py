"""Expose checked member topology values on unchanged original axis identities."""
import copy,sys,math
from pathlib import Path
owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(owner) not in sys.path:sys.path.insert(0,str(owner))
from confirm_crossview_paths import load,sha
from rebuild_compound_member_interfaces import verify_output,MODE as SOURCE_MODE
from noncompound_main_extent_context import component_identities
MODE='qualified_circle_bracketed_compound_member_interfaces_v1'

def collect(raw,rendered,proof,bindings,prior):
    if (proof.get('mode')!=SOURCE_MODE or proof.get('member_topology_rebuilt')is not True or proof.get('source_drawing_graphs_unchanged')is not True
        or proof.get('DN_used_for_mapping')is not False or proof.get('installed_lengths_assigned')!=0 or proof.get('human_accepted')is not False):raise ValueError('unsupported native compound interface proof')
    if proof['source_hashes']['raw_axis_graph']!=bindings['axis_graph'] or proof['source_hashes']['member_proof']!=prior.get('compound_member_mains',{}).get('source_bindings',{}).get('native_proof'):raise ValueError('member interface source version differs')
    if prior.get('source_graph_sha256')!=bindings['axis_graph'] or prior.get('rendered_graph_sha256')!=bindings['rendered_graph']:raise ValueError('prior attribute context belongs to another graph')
    reserved=set()
    for key in ('compound_member_mains','member_plan_runs','ordered_group_plan_runs','ordered_anchor_branches','anchor_bounded_mains','noncompound_main_extents'):
        reserved.update(r['axis_edge_id'] for r in prior.get(key,{}).get('records',[]) if r.get('axis_edge_id'))
    original={e['edge_id']:e for e in raw['edges']};display={e['edge_id']:e for e in rendered['edges']};records=[];seen=set()
    for r in proof['records']:
        eid=r['axis_edge_id']
        if eid in reserved or eid in seen:raise ValueError('compound interface writer overlaps an inherited owner')
        seen.add(eid);source,edge=original[eid],display[eid]
        if any(r['source_hashes'].get(k)!=proof['source_hashes'].get(k) for k in ('plan_source','axis_source','plan_graph','axis_graph')):raise ValueError('member native source binding differs')
        if any(source.get(k)!=edge.get(k) for k in ('edge_id','system','start_node_id','end_node_id','attribute_paths')):raise ValueError('rendered interface geometry differs from original')
        if r['system']!=source['system'] or r['axis_nodes']!=[source['start_node_id'],source['end_node_id']] or r['axis_attribute_paths']!=source['attribute_paths']:raise ValueError('native interface snapshot differs')
        if r['floor']!=source.get('floor_start',source.get('start_floor')) or r['floor']!=source.get('floor_end',source.get('end_floor')):raise ValueError('member interface floor differs')
        if not math.isfinite(r['nominal_mm']) or r['nominal_mm']<=0 or any(r.get(k)is not None for k in ('installed_whole_length_mm','net_pipe_cut_length_mm','physical_elevation_mm')):raise ValueError('unsupported member value or physical metric promotion')
        p=r['plan_projection']
        if p['installed_whole_edge_length_mm']is not None or not p['pieces'] or abs(sum(x['length_mm'] for x in p['pieces'])-p['value_mm'])>.0001:raise ValueError('incomplete native plan metric')
        if r['kind']=='primary_member_main':
            if r['complete_horizontal_centerline_route_mm']!=p['value_mm']:raise ValueError('primary member complete extent differs')
        elif r['kind']=='lower_member_approach_with_local_rise':
            if r['complete_horizontal_centerline_route_mm']is not None or r['local_rise_length_mm']is not None or r['level_difference_used_as_length']is not False:raise ValueError('mixed local rise promoted to complete physical length')
        else:raise ValueError('unknown member interface role')
        if any(source.get(k) for k in ('axis_riser_attributes','plan_segment_attributes','anchored_floor_main_attributes','external_feed_plan_attributes','cross_view_attributes','batch_plan_attribute_scopes')):raise ValueError('new member mapping needs reconciliation with an existing source owner')
        record=copy.deepcopy(r);record.update(component_instance_identities=component_identities(source,edge,rendered),related_HIL_confirmation_inherited=False)
        records.append(record)
    if len(records)!=proof['counts']['new_axis_correspondences']:raise ValueError('member interface inventory differs')
    return dict(mode=MODE,records=records,axis_edges=len(records),source_bindings=bindings,existing_attribute_owners_preserved=True,
        native_sources={k:proof['source_hashes'][k] for k in ('plan_source','axis_source','plan_graph','axis_graph')},
        member_topology_rebuilt=True,original_axis_geometry_unchanged=True,installed_lengths_assigned=0,human_accepted=False,
        member_graph_counts=dict(nodes=len(proof['member_local_graph']['nodes']),edges=len(proof['member_local_graph']['edges'])),
        unresolved_external_ports=proof['member_local_graph']['external_ports'],global_plan_topology_complete=False)

def from_artifact(raw_path,rendered_path,proof_path,prior):
    before={str(p):sha(p) for p in (raw_path,rendered_path,proof_path)};proof=verify_output(Path(proof_path).parent)
    result=collect(load(raw_path),load(rendered_path),proof,dict(axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path),member_proof=proof['source_hashes']['member_proof']),prior)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('interface context inputs changed')
    return result
