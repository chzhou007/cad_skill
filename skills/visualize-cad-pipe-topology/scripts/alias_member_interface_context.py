"""Compose only source-qualified alias member directional attributes."""
import copy,math,sys
from pathlib import Path
owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(owner)not in sys.path:sys.path.insert(0,str(owner))
from confirm_crossview_paths import load,sha
from rebuild_alias_member_circle_interfaces import verify_output,MODE as SOURCE_MODE
from noncompound_main_extent_context import component_identities
MODE='qualified_confirmed_alias_member_interfaces_v1'

def collect(raw,rendered,proof,bindings,prior):
    if proof.get('mode')!=SOURCE_MODE or proof.get('original_local_graphs_mutated')is not False or proof.get('ordinary_junction_mapping_extended')is not False or proof.get('vertical_attributes_assigned_from_plan')!=0 or proof.get('human_accepted')is not False or proof.get('pending'):raise ValueError('unsupported alias member source proof')
    if prior.get('source_graph_sha256')!=bindings['axis_graph']or prior.get('rendered_graph_sha256')!=bindings['rendered_graph']or proof['inputs']['raw_axis_graph']['sha256']!=bindings['axis_graph']:raise ValueError('alias member source graph differs')
    for k in('plan_graph','axis_graph','plan_source','axis_source'):
        field='axis_local_graph'if k=='axis_graph'else k
        if proof['inputs'][k]['sha256']!=bindings[field]:raise ValueError('alias member native source binding differs')
    reserved={r['axis_edge_id']for key,value in prior.items()if key!='axis_vertical_segment_DN'and isinstance(value,dict)for r in value.get('records',[])if 'axis_edge_id'in r}
    by={e['edge_id']:e for e in raw['edges']};view={e['edge_id']:e for e in rendered['edges']};records=[];seen=set()
    for r in proof['records']:
        eid=r['axis_edge_id']
        if eid in reserved or eid in seen:raise ValueError('alias interface overlaps an existing owner')
        seen.add(eid);edge=by[eid];shown=view[eid]
        if any(edge.get(k)!=shown.get(k)for k in('edge_id','system','start_node_id','end_node_id','attribute_paths'))or r['axis_attribute_paths']!=edge['attribute_paths']or r['axis_nodes']!=[edge['start_node_id'],edge['end_node_id']]or r['system']!=edge['system']:raise ValueError('alias interface geometry or service changed')
        if any(edge.get(k)!=r['floor']for k in('floor_start','floor_end'))or r['original_plan_graph_sha256']!=bindings['plan_graph']:raise ValueError('alias interface floor or local plan version differs')
        domains=r['attribute_source_domains'];spans=domains['records'];points={(pi,si):[a,b]for pi,path in enumerate(edge['attribute_paths'])for si,(a,b)in enumerate(zip(path,path[1:]))}
        if len(spans)!=len(points)or any(points.get((s['path_index'],s['segment_index']))!=s['scope_points']or s['source_line_coverage_checked']is not True for s in spans):raise ValueError('alias directional scope identity differs')
        if any(s['DN_source_route']!=('axis_11_native_vertical'if s['direction_class']=='vertical'else'corresponding_floor_plan_horizontal')or s['length_source_route']!=s['DN_source_route']for s in spans):raise ValueError('alias vertical attributes incorrectly sourced from plan')
        value=domains['horizontal_complete_centerline_mm']
        if not isinstance(value,(int,float))or isinstance(value,bool)or not math.isfinite(value)or value<=0 or value!=r['plan_projection']['value_mm']or domains['horizontal_nominal_mm']!=r['nominal_mm']:raise ValueError('alias member metric or DN differs')
        kinds={s['direction_class']for s in spans}
        if r['kind']=='primary_member_main':
            if kinds!={'horizontal'}or domains['whole_edge_nominal_mm']!=r['nominal_mm']or domains['whole_edge_complete_centerline_mm']!=value:raise ValueError('primary alias member complete extent differs')
        elif r['kind']=='lower_member_approach_with_local_rise':
            if kinds!={'horizontal','vertical'}or domains['whole_edge_nominal_mm']is not None or domains['whole_edge_complete_centerline_mm']is not None:raise ValueError('mixed alias member promoted to whole value')
        else:raise ValueError('unknown alias member role')
        keys=('mapping_id','axis_edge_id','kind','floor','system','nominal_mm','source_alias_group_id','original_plan_graph_sha256','reading_projection_sha256','plan_LINE','plan_member_edge_id','member_scope_id','literal_level_key','axis_nodes','axis_attribute_paths','plan_attribute_paths','plan_projection','attribute_source_domains')
        record={k:copy.deepcopy(r[k])for k in keys};record.update(component_instance_identities=component_identities(edge,shown,rendered),related_HIL_confirmation_inherited=False,human_accepted=False);records.append(record)
    return dict(mode=MODE,records=records,source_bindings=bindings,source_sheet=Path(proof['inputs']['plan_source']['path']).name,original_local_topologies_unchanged=True,ordinary_member_namespaces_separate=True,vertical_attributes_assigned_from_plan=0,installed_lengths_assigned=0,net_pipe_lengths_assigned=0,human_accepted=False)

def from_artifact(raw_path,rendered_path,proof_path,prior):
    proof=verify_output(Path(proof_path).parent)
    bindings=dict(axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),native_proof=sha(proof_path),plan_graph=proof['inputs']['plan_graph']['sha256'],axis_local_graph=proof['inputs']['axis_graph']['sha256'],plan_source=proof['inputs']['plan_source']['sha256'],axis_source=proof['inputs']['axis_source']['sha256'])
    return collect(load(raw_path),load(rendered_path),proof,bindings,prior)
