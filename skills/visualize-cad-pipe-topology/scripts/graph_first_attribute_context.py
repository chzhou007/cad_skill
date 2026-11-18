"""Publish checked cycle centreline and unbranched vertical DN as new scopes.

All old contexts and CSV values remain intact. New horizontal lengths do not
select a conflicting DN; inherited vertical values do not become whole-edge DN.
"""
import copy,json,math,sys
from pathlib import Path
for name in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha
from cycle_gate_plan_lengths import MODE as METRIC_MODE,verify_output as verify_metrics
from rebuild_axis_unbranched_vertical_DN import MODE as VERTICAL_MODE,verify_output as verify_vertical
from noncompound_main_extent_context import component_identities
from native_replay_session import verify_once
MODE='qualified_graph_first_attribute_extensions_v1'

def positive(v):return isinstance(v,(int,float))and not isinstance(v,bool)and math.isfinite(v)and v>0
def key(r):return(r['edge_id'],r['path_index'],r['segment_index'])

def collect(raw,rendered,metrics,vertical,bindings,prior):
    if metrics.get('mode')!=METRIC_MODE or metrics.get('cycle_correspondences_independently_replayed')is not True or metrics.get('original_metric_readers_reused')is not True or metrics.get('local_graphs_changed')is not False or metrics.get('human_accepted')is not False or any(metrics.get(k)!=0 for k in('DN_values_assigned','vertical_values_assigned','installed_lengths_assigned')):raise ValueError('unsupported native cycle metrics')
    if vertical.get('mode')!=VERTICAL_MODE or vertical.get('original_native_annotations_independently_replayed')is not True or vertical.get('original_direction_routing_independently_replayed')is not True or vertical.get('original_axis_graphs_unchanged')is not True or vertical.get('all_vertical_values_from11')is not True or vertical.get('horizontal_plan_attributes_changed')is not False or vertical.get('human_accepted')is not False or any(vertical.get(k)!=0 for k in('crossed_physical_Ts','whole_edge_DN_assigned','physical_lengths_assigned')):raise ValueError('unsupported inherited vertical source')
    if prior.get('source_graph_sha256')!=bindings['raw_axis_graph']or prior.get('rendered_graph_sha256')!=bindings['rendered_graph']:raise ValueError('extension uses another raw/rendered axis graph')
    vi=vertical['inputs'];mi=metrics['inputs']
    if vi['raw_axis_graph']['sha256']!=bindings['raw_axis_graph']or vi['graph']['sha256']!=mi['axis_graph']['sha256']or raw['metadata']['source_sha256']!=vi['source']['sha256']:raise ValueError('extension source ancestry differs')
    oldroot=prior['axis_vertical_segment_DN']
    if vi['annotations']['sha256']!=oldroot['source_bindings']['native_vertical_DN_proof']:raise ValueError('original vertical seed provider differs')
    old={key(r):r for r in oldroot['records']};occupied=set(old)
    for e in raw['edges']:
        for r in e.get('axis_riser_attributes',[]):occupied.add((e['edge_id'],r['path_index'],r['segment_index']))
    original={e['edge_id']:e for e in raw['edges']};view={e['edge_id']:e for e in rendered['edges']}
    if original.keys()!=view.keys():raise ValueError('axis edge populations differ')
    def unchanged(eid):
        e,v=original[eid],view[eid]
        if any(e.get(k)!=v.get(k)for k in('edge_id','system','start_node_id','end_node_id','attribute_paths')):raise ValueError('axis source identity changed')
        return e
    reserved={r['axis_edge_id']for root in prior.values()if isinstance(root,dict)for r in root.get('records',[])if r.get('axis_edge_id')}
    cycles=[];seen=set()
    for r in metrics['records']:
        eid=r['axis_edge_id'];e=unchanged(eid)
        if eid in seen or eid in reserved:raise ValueError('cycle interval competes with existing owner')
        seen.add(eid)
        if [e['start_node_id'],e['end_node_id']]!=r['axis_nodes']or e['attribute_paths']!=r['axis_attribute_paths']or e['system']!=r['system']or any(e.get(k)!=r['floor']for k in('floor_start','floor_end')):raise ValueError('cycle interval source extent differs')
        value=r['complete_horizontal_centerline_mm'];projection=r['projection']
        if not positive(value)or projection['value_mm']!=value or abs(sum(p['length_mm']for p in projection['pieces'])-value)>.0001 or r.get('nominal_mm')is not None or any(r.get(k)is not None for k in('physical_installed_length_mm','net_pipe_cut_length_mm'))or r.get('human_accepted')is not False:raise ValueError('cycle metric assigned an unsupported DN or installed length')
        identities=component_identities(e,view[eid],rendered)
        cycles.append(dict(copy.deepcopy(r),component_instance_identities=identities,related_HIL_confirmation_inherited=False))
    inherited=[];newkeys=set()
    for r in vertical['records']:
        k=key(r);e=unchanged(r['edge_id']);seed=r['seed_record'];sk=key(seed);pi,si=r['path_index'],r['segment_index']
        if k in occupied or k in newkeys or sk not in old:raise ValueError('vertical target repeats or seed is not an old qualified domain')
        if old[sk]['nominal_mm']!=seed['nominal_mm']or seed['nominal_mm']!=r['nominal_mm']or old[sk]['observations']!=seed['observations']or not positive(r['nominal_mm']):raise ValueError('vertical seed lineage changed')
        if e['attribute_paths'][pi][si:si+2]!=r['scope_points']or e['system']!=r['system']or seed['system']!=r['system']or seed['edge_id']!=r['edge_id']or seed['path_index']!=pi:raise ValueError('vertical inheritance changed native path or system')
        bends=r['continuity_evidence']['bends'];guard=r['annotation_guard']
        if not bends or any(b['source_arms']!=2 or b['physical_T_crossed']is not False for b in bends)or guard['other_in_scope_DN_annotations']or guard['F_crossings']or r['whole_edge_DN_assigned']is not False or r['physical_length_mm']is not None or r['whole_edge_physical_length_mm']is not None or r.get('human_accepted')is not False:raise ValueError('vertical local value crossed a barrier or became whole-edge')
        inherited.append(dict(copy.deepcopy(r),axis_source_sha256=vi['source']['sha256'],related_HIL_confirmation_inherited=False));newkeys.add(k)
    if len(cycles)!=metrics['counts']['complete_horizontal_centerlines']or len(inherited)!=vertical['counts']['new_inherited_vertical_domains']:raise ValueError('extension source population differs')
    result=dict(mode=MODE,cycle_records=cycles,vertical_records=inherited,cycle_intervals=len(cycles),new_vertical_DN_domains=len(inherited),source_bindings=bindings,axis_source_sha256=vi['source']['sha256'],plan_source_sha256=mi['plan_source']['sha256'],
        cycle_new_junction_mapping_source=mi['cycle_proof'],old_vertical_record_count=len(old),old_all_vertical_domain_count=len(occupied),all_current_vertical_domain_count=len(occupied|newkeys),
        old_contexts_preserved=True,raw_axis_graph_unchanged=True,DN_values_assigned_to_horizontal=0,whole_edge_vertical_DN_assigned=0,physical_installed_lengths_assigned=0,human_accepted=False)
    # Native metric readers use tuple index pairs. The viewer contract is JSON;
    # normalize at this boundary so fresh replay and persisted evidence agree.
    return json.loads(json.dumps(result,ensure_ascii=False,allow_nan=False))

def from_artifacts(raw_path,rendered_path,metric_path,vertical_path,prior):
    before={str(p):sha(p)for p in(raw_path,rendered_path,metric_path,vertical_path)}
    metrics=verify_once(Path(metric_path).parent,verify_metrics);vertical=verify_once(Path(vertical_path).parent,verify_vertical)
    result=collect(load(raw_path),load(rendered_path),metrics,vertical,
        dict(raw_axis_graph=sha(raw_path),rendered_graph=sha(rendered_path),cycle_metric_proof=sha(metric_path),vertical_inheritance_proof=sha(vertical_path)),prior)
    if any(sha(p)!=h for p,h in before.items()):raise ValueError('attribute extension inputs changed')
    return result
