import test from'node:test';import assert from'node:assert/strict';import fs from'node:fs';
import{checkedBoundedMain,boundedMainCsvValues,boundedMainProperties}from'../assets/viewer/public/anchor-bounded-main-attributes.js';
import{edgeAttributeProperties,crossViewAttributeCsvValues,edgeAttributeCsvFields}from'../assets/viewer/public/edge-attributes.js';
function fixture(){
 const h='a'.repeat(64),v='b'.repeat(64),edge={edge_id:'A',system:'supply',start_node_id:'T1',end_node_id:'T2',floor_start:2,floor_end:2,attribute_paths:[[[0,0],[100,0]]]};
 const row={axis_edge_id:'A',mapping_id:'M',floor:2,system:'supply',axis_start_node:'T1',axis_end_node:'T2',axis_attribute_paths:structuredClone(edge.attribute_paths),plan_edges:['P'],plan_Ts:['P1','P2'],axis_Ts:['T1','T2'],nominal_mm:300,plan_DN_record:{nominal_mm:300,system:'supply',human_accepted:false,lineage:[]},plan_horizontal_projection:{value_mm:20000,pieces:[{plan_edge:'P',length_mm:20000}],installed_whole_edge_length_mm:null},metric_reader:'inherited_native_plan_projection',whole_axis_DN_selected:true,whole_axis_physical_length_mm:null,net_pipe_cut_length_mm:null,related_HIL_confirmation_inherited:false,human_accepted:false,source_sha256:{plan:h,iso:h},plan_graph_sha256:h,DN_status:'exact_qualified_local_plan_DN_retained_not_fresh_global_DN_rebuild'};
 const context={source_graph_sha256:h,rendered_graph_sha256:v,anchor_bounded_mains:{mode:'qualified_native_anchor_bounded_main_attributes_v1',records:[row],axis_edges:1,source_bindings:{axis_graph:h,rendered_graph:v,native_proof:h,DN_receipt:h,DN_result:h},local_topology_mutated:false,physical_lengths_assigned:0,human_accepted:false}};
 return{edge,row,context};
}
test('native plan DN and XY enter actual common properties and CSV; installed length stays unknown',()=>{
 const{edge,row,context}=fixture();assert.equal(checkedBoundedMain(edge,context),row);const csv=crossViewAttributeCsvValues(edge,context);assert.equal(csv.diameter_nominal_mm,300);assert.equal(csv.bounded_main_plan_pipe_XY_mm,20000);assert.equal(csv.bounded_main_whole_installed_length_mm,'');assert.equal(csv.crossview_whole_edge_length_mm,'');
 const props=Object.fromEntries(edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'},attribute_value_context:context}));assert.equal(props['管径'],'DN300');assert.equal(props['平面已绘管线长度'],'20.000 m');assert(props['平面属性来源'].includes('SH16 09'));assert(props['整边安装长度'].startsWith('未知'));assert(!props['计量规则'].includes('inherited_'));
 assert(edgeAttributeCsvFields.includes('bounded_main_evidence_json'));assert.equal(new Set(edgeAttributeCsvFields).size,edgeAttributeCsvFields.length);
});
test('source, domain, metric and prior-owner mutations disable the new overlay',()=>{
 for(const mode of['system','path','floor','source','metric','owner','duplicate','physical']){
  const{edge,row,context}=fixture();if(mode==='system')row.system='return';if(mode==='path')row.axis_attribute_paths[0][1][0]=99;if(mode==='floor')row.floor=3;if(mode==='source')context.anchor_bounded_mains.source_bindings.native_proof='bad';if(mode==='metric')row.plan_horizontal_projection.value_mm=1;if(mode==='owner')edge.cross_view_attributes={existing:true};if(mode==='duplicate')context.anchor_bounded_mains.records.push(structuredClone(row));if(mode==='physical')row.whole_axis_physical_length_mm=0;
  assert.equal(checkedBoundedMain(edge,context),null,mode);assert.deepEqual(boundedMainCsvValues(edge,context),{},mode);
 }
});
test('unknown local DN or metric does not become zero',()=>{
 const{edge,row,context}=fixture();row.nominal_mm=null;row.plan_DN_record.nominal_mm=null;row.whole_axis_DN_selected=false;row.plan_horizontal_projection=null;row.metric_reader=null;
 const values=boundedMainCsvValues(edge,context);assert.equal(values.diameter_nominal_mm,'');assert.equal(values.bounded_main_plan_pipe_XY_mm,'');assert.equal(Object.fromEntries(boundedMainProperties(edge,true,context))['平面已绘管线长度'],'未知');
});
test('unrelated edges retain old behavior and shipped implementation keeps escaped Chinese',()=>{
 const{edge,context}=fixture();edge.edge_id='unrelated';assert.deepEqual(boundedMainCsvValues(edge,context),{});assert(fs.readFileSync(new URL('../assets/viewer/public/anchor-bounded-main-attributes.js',import.meta.url),'utf8').split('').every(c=>c.charCodeAt(0)<128));
});
