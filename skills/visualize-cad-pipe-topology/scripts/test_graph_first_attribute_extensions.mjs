import test from 'node:test';import assert from 'node:assert/strict';
import {checkedCycleGateRun,checkedInheritedVerticalDN,graphFirstExtensionCsvValues,graphFirstExtensionCsvFields}from'../assets/viewer/public/graph-first-attribute-extensions.js';
import {crossViewAttributeCsvValues,edgeAttributeProperties,edgeAttributeCsvFields}from'../assets/viewer/public/edge-attributes.js';
function fixture(){
 const h='a'.repeat(64),e={edge_id:'H',system:'supply',start_node_id:'A',end_node_id:'B',floor_start:2,floor_end:2,attribute_paths:[[[0,0],[10,0]]]};
 const v={edge_id:'V',system:'return',start_node_id:'C',end_node_id:'D',floor_start:2,floor_end:2,attribute_paths:[[[0,0],[0,2],[2,4],[2,6]]]};
 const r={axis_edge_id:'H',mapping_id:'M',plan_edge_id:'P',system:'supply',floor:2,axis_nodes:['A','B'],axis_attribute_paths:e.attribute_paths,nominal_mm:null,DN_status:'unknown_pending_plan_DN_scope_resolution',complete_horizontal_centerline_mm:10000,projection:{value_mm:10000,pieces:[{length_mm:10000,plan_edge:'P',source_line_handle:'L'}],installed_whole_edge_length_mm:null},human_accepted:false,related_HIL_confirmation_inherited:false,physical_installed_length_mm:null,net_pipe_cut_length_mm:null,source_paths_mutated:false,unknown_length_filled_with_zero:false,DN_used_for_matching:false};
 const t={edge_id:'V',system:'return',nominal_mm:80,path_index:0,segment_index:0,scope_points:[[0,0],[0,2]],axis_source_sha256:h,whole_edge_DN_assigned:false,physical_length_mm:null,whole_edge_physical_length_mm:null,human_accepted:false,related_HIL_confirmation_inherited:false,seed_record:{edge_id:'V',path_index:0,segment_index:2,system:'return',nominal_mm:80,scope_points:[[2,4],[2,6]],observations:[{nominal_mm:80,source_text:{source_sha256:h,handle:'T'}}]},continuity_evidence:{bends:[{source_arms:2,physical_T_crossed:false}]},annotation_guard:{other_in_scope_DN_annotations:[],F_crossings:[]}};
 const root={mode:'qualified_graph_first_attribute_extensions_v1',old_contexts_preserved:true,raw_axis_graph_unchanged:true,DN_values_assigned_to_horizontal:0,whole_edge_vertical_DN_assigned:0,physical_installed_lengths_assigned:0,human_accepted:false,source_bindings:{raw_axis_graph:h,rendered_graph:h,cycle_metric_proof:h,vertical_inheritance_proof:h},axis_source_sha256:h,plan_source_sha256:h,cycle_records:[r],vertical_records:[t],cycle_intervals:1,new_vertical_DN_domains:1};
 return {e,v,r,t,context:{source_graph_sha256:h,rendered_graph_sha256:h,graph_first_extensions:root}};
}
test('actual UI and CSV show plan centreline independently of unresolved diameter',()=>{
 const a=fixture(),before=structuredClone(a);assert.ok(checkedCycleGateRun(a.e,a.context));
 const csv=crossViewAttributeCsvValues(a.e,a.context);assert.equal(csv.cycle_gate_complete_centerline_mm,10000);assert.ok(!csv.diameter_nominal_mm);
 const props=edgeAttributeProperties(a.e,{attribute_value_context:a.context,display:{edge_attribute_language:'zh-CN'}});assert.ok(props.some(r=>r[1]==='10.000 m'));assert.ok(props.some(r=>r[0]==='管径'&&r[1].includes('未知')));assert.deepEqual(a,before);
 assert.deepEqual(edgeAttributeCsvFields.slice(edgeAttributeCsvFields.indexOf(graphFirstExtensionCsvFields[0]),edgeAttributeCsvFields.indexOf(graphFirstExtensionCsvFields[0])+graphFirstExtensionCsvFields.length),graphFirstExtensionCsvFields);
});
test('vertical inheritance is a segment value, never whole DN or drawing length',()=>{
 const a=fixture();assert.equal(checkedInheritedVerticalDN(a.v,a.context).length,1);const csv=crossViewAttributeCsvValues(a.v,a.context);assert.equal(csv.unbranched_vertical_DN_segment_count,1);assert.ok(!csv.diameter_nominal_mm);
 const props=edgeAttributeProperties(a.v,{attribute_value_context:a.context,display:{edge_attribute_language:'zh-CN'}});assert.ok(props.some(r=>r[0].includes('11图继承')&&r[1].startsWith('DN80')));
});
test('stale graph, duplicate scope, cross service, real T, zero length and selected DN fail closed',()=>{
 for(const kind of ['graph','duplicate','system','T','zero','DN']){const a=fixture();if(kind==='graph')a.context.source_graph_sha256='b'.repeat(64);if(kind==='duplicate')a.context.graph_first_extensions.vertical_records.push(structuredClone(a.t));if(kind==='system')a.t.system='supply';if(kind==='T')a.t.continuity_evidence.bends[0].source_arms=3;if(kind==='zero')a.r.complete_horizontal_centerline_mm=0;if(kind==='DN')a.r.nominal_mm=300;
  if(['graph','duplicate','system','T'].includes(kind))assert.equal(checkedInheritedVerticalDN(a.v,a.context).length,0,kind);
  if(['graph','duplicate','zero','DN'].includes(kind))assert.equal(checkedCycleGateRun(a.e,a.context),null,kind);
 }
});
