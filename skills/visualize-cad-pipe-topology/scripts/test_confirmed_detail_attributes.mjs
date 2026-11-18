import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedDetailTopology,checkedPlanDiameterScope,crossViewAttributeProperties,crossViewAttributeCsvValues,edgeAttributeProperties} from '../assets/viewer/public/edge-attributes.js';

function fixture(){
 const role={kind:'confirmed_detail_view',coordinate_domain:'native_detail_drawing',source_sha256:'a'.repeat(64),input_graph_sha256:'b'.repeat(64),confirmed_alias_root_sha256:'c'.repeat(64),physical_length_from_drawing_span:false,metric_verified_by_this_stage:false};
 const context={plan_graph_sha256:'d'.repeat(64),plan_source_sha256:'a'.repeat(64),confirmed_alias_root_sha256:'c'.repeat(64),native_coverage_sha256:'e'.repeat(64),plan_edges:['P'],source_view_roles:[{edge_id:'P',source_view_context:role}],physical_units_applied:false,human_accepted:false};
 const c={status:'partial_plan_attributes_source_checked',mapping_id:'SC1',mapping_kind:'main_between_equipment_branches',plan_edges:['P'],iso_edges:['I'],system:'supply',human_accepted:false,physical_ports_verified:false,source_hashes:{plan:'a'.repeat(64),plan_graph:'d'.repeat(64)},whole_edge_physical_length_mm:null,whole_axis_main_scope:'source_checked_plan_native_T_to_T_horizontal_main',plan_DN_scope_evidence_sha256:'f'.repeat(64),
  horizontal_projection:{status:'source_confirmed_detail_topology_physical_length_unknown',value_mm:null,edge_value_mm:null,allocation:'unmeasured_confirmed_detail_view_not_floor_plan_metric',detail_context:context,pieces:[{plan_edge:'P',source_line_handle:'LINE',drawing_span_native_units:1000,physical_length_mm:null}]},
  diameter:{plan_scope_evidence_sha256:'f'.repeat(64),plan_drawn_status:'source_checked_plan_DN_scope_human_pending',plan_drawn_nominal_mm:200,nominal_mm:200,selected_physical_diameter:true,status:'source_checked_whole_horizontal_main_DN_length_unknown',plan_drawn_values:[{edge_id:'P',system:'supply',nominal_mm:200,scope:'native_plan_drawn_pipe_paths_only',human_accepted:false}]}};
 return {edge_id:'I',pipe_diameter:{display:'DN65'},cross_view_attributes:c};
}

test('checked same-floor detail main exposes DN while physical length and projection remain blank',()=>{
 const edge=fixture(),before=structuredClone(edge),c=edge.cross_view_attributes;
 assert.equal(checkedDetailTopology(c),true);const scope=checkedPlanDiameterScope(c);assert.equal(scope.whole,true);assert.equal(scope.length,null);
 const csv=crossViewAttributeCsvValues(edge);assert.equal(csv.diameter_nominal_mm,200);assert.equal(csv.crossview_plan_horizontal_projection_mm,'');assert.equal(csv.crossview_whole_edge_length_mm,'');
 assert.equal(csv.crossview_metric_status,'source_confirmed_detail_topology_physical_length_unknown');assert.ok(csv.crossview_detail_context_json.includes('physical_units_applied'));
 const rows=crossViewAttributeProperties(edge,true);assert.ok(rows.some(([k,v])=>k==='\u8de8\u56fe\u5c5e\u6027\u72b6\u6001'&&v.includes('\u5b9e\u9645\u957f\u5ea6\u672a\u77e5')));
 assert.ok(rows.some(([k,v])=>k==='\u5e73\u9762\u6c34\u5e73\u6295\u5f71\u957f\u5ea6'&&v.includes('\u8be6\u56fe')));
 assert.equal(edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}})[0][1],'DN200');assert.deepEqual(edge,before);
});

test('stale or promoted detail contexts cannot select whole DN or a numerical length',()=>{
 for(const change of [c=>c.horizontal_projection.edge_value_mm=0,c=>c.horizontal_projection.value_mm=1000,c=>c.whole_edge_physical_length_mm=1000,
  c=>c.horizontal_projection.detail_context.plan_graph_sha256='x'.repeat(64),c=>c.horizontal_projection.detail_context.source_view_roles=[],
  c=>c.horizontal_projection.detail_context.source_view_roles[0].source_view_context.metric_verified_by_this_stage=true,
  c=>c.horizontal_projection.detail_context.physical_units_applied=true,c=>c.horizontal_projection.detail_context.human_accepted=true]){
  const edge=fixture(),c=edge.cross_view_attributes;change(c);assert.equal(checkedDetailTopology(c),false);const row=crossViewAttributeCsvValues(edge);
  assert.equal(row.diameter_nominal_mm,'');assert.equal(row.crossview_whole_edge_length_mm,'');
 }
});

test('detail branch never acquires whole-edge DN from the same visible label',()=>{
 const edge=fixture(),c=edge.cross_view_attributes;c.mapping_kind='equipment_branch';c.whole_axis_main_scope=null;
 Object.assign(c.diameter,{nominal_mm:null,selected_physical_diameter:false,status:'source_checked_plan_DN_axis_extent_partial'});
 const row=crossViewAttributeCsvValues(edge);assert.equal(row.crossview_plan_drawn_nominal_mm,200);assert.equal(row.diameter_nominal_mm,'');assert.equal(row.crossview_whole_edge_length_mm,'');
});
