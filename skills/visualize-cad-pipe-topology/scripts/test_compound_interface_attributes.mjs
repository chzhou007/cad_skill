import test from 'node:test';
import assert from 'node:assert/strict';
import{checkedCompoundInterface,compoundInterfaceProperties,compoundInterfaceCsvValues}from'../assets/viewer/public/full-batch-plan-attributes.js';
import{crossViewAttributeCsvValues,edgeAttributeProperties}from'../assets/viewer/public/edge-attributes.js';
function fixture(mixed=false){
 const edge={edge_id:'E',system:'supply',start_node_id:'A',end_node_id:'B',floor_start:3,floor_end:3,attribute_paths:[[[0,0],[100,0]]]},hash=c=>c.repeat(64);
 const sources={plan_source:hash('1'),axis_source:hash('2'),plan_graph:hash('3'),axis_graph:hash('4')};
 const r={axis_edge_id:'E',axis_nodes:['A','B'],axis_attribute_paths:edge.attribute_paths,floor:3,system:'supply',nominal_mm:mixed?200:300,kind:mixed?'lower_member_approach_with_local_rise':'primary_member_main',mapping_id:'M',plan_member_edge_id:'PM',plan_LINE:'L',plan_declarations:[{text_handle:'TEXT'}],
  DN_used_for_mapping:false,human_accepted:false,related_HIL_confirmation_inherited:false,installed_whole_length_mm:null,net_pipe_cut_length_mm:null,physical_elevation_mm:null,plan_component_member_allocation:'unresolved',literal_level_key:mixed?'3':'3.6',source_hashes:sources,
  plan_projection:{value_mm:4000,installed_whole_edge_length_mm:null,pieces:[{plan_edge:'PM',source_line_handle:'L',length_mm:4000}]},complete_horizontal_centerline_route_mm:mixed?null:4000,local_rise_length_mm:null,level_difference_used_as_length:false};
 const context={source_graph_sha256:hash('a'),rendered_graph_sha256:hash('b'),compound_member_mains:{source_bindings:{native_proof:hash('d')},records:[]},compound_member_interfaces:{mode:'qualified_circle_bracketed_compound_member_interfaces_v1',existing_attribute_owners_preserved:true,member_topology_rebuilt:true,original_axis_geometry_unchanged:true,installed_lengths_assigned:0,human_accepted:false,
  source_bindings:{axis_graph:hash('a'),rendered_graph:hash('b'),native_proof:hash('c'),member_proof:hash('d')},native_sources:sources,records:[r],axis_edges:1}};
 return {edge,r,context};
}
test('primary member DN and complete plan centreline reach actual canonical CSV and properties',()=>{
 const{edge,r,context}=fixture();assert.equal(checkedCompoundInterface(edge,context),r);
 const values=crossViewAttributeCsvValues(edge,context);assert.equal(values.diameter_nominal_mm,300);assert.equal(values.batch_complete_horizontal_centerline_mm,4000);
 const props=edgeAttributeProperties(edge,{attribute_value_context:context,display:{edge_attribute_language:'zh-CN'}});assert.ok(props.some(([k,v])=>k==='管径'&&v==='DN300'));assert.ok(props.some(([k,v])=>k.includes('中心线')&&v==='4.000 m'));
});
test('mixed member approach inherits DN but local rise and whole installed length stay unknown',()=>{
 const{edge,context}=fixture(true);const values=compoundInterfaceCsvValues(edge,context);assert.equal(values.diameter_nominal_mm,200);assert.equal(values.circle_member_plan_projection_mm,4000);assert.equal(values.circle_member_complete_centerline_mm,'');assert.equal(values.batch_complete_horizontal_centerline_mm,undefined);
 const props=compoundInterfaceProperties(edge,true,context);assert.ok(props.some(([k,v])=>k==='局部升降长度'&&v==='未知'));assert.ok(props.some(([k,v])=>k.includes('实际安装全长')&&v==='未知'));
});
test('wrong sources, altered endpoints, old writers and fabricated mixed length fail closed',()=>{
 for(const mutate of [x=>x.r.source_hashes={...x.r.source_hashes,plan_source:'f'.repeat(64)},x=>x.edge.end_node_id='OTHER',x=>x.context.member_plan_runs={records:[{axis_edge_id:'E'}]},x=>x.r.complete_horizontal_centerline_route_mm=4000,x=>x.r.local_rise_length_mm=600]){
  const x=fixture(true);mutate(x);assert.equal(checkedCompoundInterface(x.edge,x.context),null);assert.deepEqual(compoundInterfaceCsvValues(x.edge,x.context),{});
 }
});
