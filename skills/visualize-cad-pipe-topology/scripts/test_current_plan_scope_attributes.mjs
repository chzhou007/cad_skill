import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedCurrentPlanScope,currentPlanScopeProperties,currentPlanScopeCsvValues} from '../assets/viewer/public/current-plan-scope-attributes.js';
import {crossViewAttributeCsvValues,edgeAttributeProperties,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';
function fixture(historical=false){
 const hash='a'.repeat(64),points=[[10,0],[10,100]],domain={edge_id:'E',text_handle:'DN-TEXT',nominal_mm:80,source_chain:['ROOT','LINE'],source_sha256:hash,graph_sha256:hash,
  segment:{path_index:0,segment_index:0,scope_points:points,drawing_direction:'vertical_stroke_in_CAD_WCS'},floor_start:3,floor_end:3,graph_floor_relation:'same_floor_graph_scope',
  human_accepted:false,physical_vertical_length_mm:null,inter_floor_riser_proved:false,equal_plan_axis_segment_extents_proved:false};
 const row={edge_id:'P',system:'supply',nominal_mm:150,scope:'native_plan_drawn_pipe_paths_only',human_accepted:false};
 const c={status:'partial_plan_attributes_source_checked',mapping_id:historical?'OLD':'CURRENT',floor:3,system:'supply',plan_edges:['P'],iso_edges:['E'],human_accepted:false,
  source_hashes:{plan:hash,isometric:hash,local_iso_graph:hash},plan_DN_scope_evidence_sha256:hash,
  horizontal_projection:{value_mm:520,edge_value_mm:520,pieces:[],allocation:'whole_mapped_axis_edge_projection'},whole_edge_physical_length_mm:null,
  diameter:{nominal_mm:null,status:'source_checked_plan_DN_axis_extent_partial',selected_physical_diameter:false,plan_drawn_nominal_mm:150,plan_drawn_values:[row],plan_scope_evidence_sha256:hash,plan_drawn_status:'source_checked_plan_DN_scope_human_pending'}};
 c.current_plan_scope_evidence={current_mapping_id:'CURRENT',historical_mapping_id:historical?'OLD':null,edge_id:'E',system:'supply',floor:3,plan_edges:['P'],iso_edges:['E'],
  plan_graph_sha256:hash,iso_graph_sha256:hash,mapping_sha256:hash,attribute_scope_sha256:hash,comparison_sha256:hash,source_sha256:{plan:hash,iso:hash},
  diameter:{nominal_mm:150},horizontal_projection:{value_mm:520},native_axis_annotation_domains:[domain],
  DN_extent_comparison:{axis_native_observations:[{current_edge_id:'E',source_text:{handle:'DN-TEXT'},nominal_mm_candidate:80,source_chain:['ROOT','LINE']}]},
  human_accepted:false,related_HIL_confirmation_inherited:false,equal_plan_axis_segment_extents_proved:false};
 return {edge_id:'E',system:'supply',attribute_paths:[structuredClone(points)],cross_view_attributes:c};
}
test('separate plan DN150 and axis local DN80 appear without whole DN or physical length',()=>{
 const edge=fixture(),rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}}),values=crossViewAttributeCsvValues(edge);
 assert.ok(checkedCurrentPlanScope(edge));assert.ok(rows.some(([,v])=>v.includes('DN80 [11:DN-TEXT]')));
 assert.ok(rows.some(([,v])=>v.includes('DN150')));assert.equal(values.diameter_nominal_mm,'');assert.equal(values.crossview_whole_edge_length_mm,'');
 assert.equal(values.crossview_plan_drawn_nominal_mm,150);assert.equal(values.crossview_plan_horizontal_projection_mm,520);
 assert.equal(values.current_plan_mapping_id,'CURRENT');assert.equal(JSON.parse(values.axis_local_DN_annotation_domains_json)[0].nominal_mm,80);
 assert.ok(edgeAttributeCsvFields.includes('current_plan_mapping_id'));
});
test('historical IDs remain historical while the current source evidence uses its own identity',()=>{
 const edge=fixture(true),values=currentPlanScopeCsvValues(edge);
 assert.equal(values.current_plan_mapping_id,'CURRENT');assert.equal(values.historical_plan_mapping_id,'OLD');assert.equal(edge.cross_view_attributes.mapping_id,'OLD');
 assert.ok(currentPlanScopeProperties(edge,false).some(([,v])=>v==='OLD'));
});
test('stale source, changed original segment, mixed annotations and physical claims fail closed',()=>{
 const changes=[e=>e.cross_view_attributes.current_plan_scope_evidence.plan_graph_sha256='old',e=>e.attribute_paths[0][0][0]+=1,
  e=>e.cross_view_attributes.current_plan_scope_evidence.native_axis_annotation_domains[0].nominal_mm=65,
  e=>e.cross_view_attributes.current_plan_scope_evidence.native_axis_annotation_domains[0].physical_vertical_length_mm=100,
  e=>e.cross_view_attributes.current_plan_scope_evidence.native_axis_annotation_domains[0].inter_floor_riser_proved=true,
  e=>e.cross_view_attributes.current_plan_scope_evidence.historical_mapping_id='other',e=>delete e.cross_view_attributes.horizontal_projection.value_mm,
  e=>e.cross_view_attributes.current_plan_scope_evidence.related_HIL_confirmation_inherited=true];
 for(const change of changes){const edge=fixture();change(edge);assert.equal(checkedCurrentPlanScope(edge),null);assert.deepEqual(currentPlanScopeProperties(edge),[]);assert.deepEqual(currentPlanScopeCsvValues(edge),{});}
});
test('legacy data without the versioned proof gains no new annotation claim',()=>{
 const edge=fixture();delete edge.cross_view_attributes.current_plan_scope_evidence;
 assert.deepEqual(currentPlanScopeProperties(edge),[]);assert.deepEqual(currentPlanScopeCsvValues(edge),{});
});
