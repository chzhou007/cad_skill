import test from 'node:test';import assert from 'node:assert/strict';
import {checkedOrderedGroupRun,orderedGroupRunCsvValues} from '../assets/viewer/public/full-batch-plan-attributes.js';
import {edgeAttributeProperties,crossViewAttributeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';
function fixture(partial=false){
 const h='a'.repeat(64),s={mapping_id:'M',kind:'native_main_chain_between_independent_junctions',floor:3,system:'return',plan_edges:['P1','P2'],iso_edges:['E1','E2'],plan_drawn_nominal_mm:250,
 plan_DN_records:['P1','P2'].map(edge_id=>({edge_id,system:'return',nominal_mm:250,status:'direct_plan_DN',lineage:[{evidence:[{evidence_id:'LINE:TEXT'}]}],scope_paths:[[[0,0],[2500,0]]],human_accepted:false})),
 horizontal_projection:{status:'native_plan_horizontal_projection_partial_length',value_mm:10000,pieces:[{plan_edge:'P1',path_index:0,segment_index:0,length_mm:10000}]},
 complete_horizontal_centerline_route_mm:null,whole_axis_nominal_mm:null,whole_installed_length_mm:null,group_scope_not_allocated_to_child_edges:true,
 source_sha256:{plan:h,iso:h},graph_sha256:{plan:h,iso:h},mapping_receipt_sha256:h,plan_DN_receipt_sha256:h,human_accepted:false,related_HIL_confirmation_inherited:false};
 const edge={edge_id:'E1',system:'return',start_node_id:'T1',end_node_id:'T2',start_floor:3,end_floor:3,attribute_paths:[[[0,0],[100,0]]],batch_plan_attribute_scopes:s};
 const g={mapping_id:'M',floor:3,system:'return',nominal_mm:250,plan_edges:s.plan_edges,iso_edges:s.iso_edges,source_sha256:s.source_sha256,graph_sha256:s.graph_sha256,
 mapping_receipt_sha256:h,plan_DN_receipt_sha256:h,domains:[{edge_id:'E1',start_node_id:'T1',end_node_id:'T2',scope_paths:structuredClone(edge.attribute_paths)},{edge_id:'E2',start_node_id:'T2',end_node_id:'T3',scope_paths:[[[100,0],[200,0]]]}],child_length_allocation_known:false,physical_child_lengths_mm:null,human_accepted:false};
 const r={axis_edge_id:'E1',axis_start_node:'T1',axis_end_node:'T2',mapping_id:'M',axis_attribute_paths:structuredClone(edge.attribute_paths),axis_Ts:['T1','T2'],plan_Ts:['PT1','PT2'],plan_edge_id:'P1',index_in_group:0,floor:3,system:'return',nominal_mm:250,
 plan_graph_sha256:h,source_sha256:{plan:h,iso:h},mapping_receipt_sha256:h,known_plan_pipe_XY_mm:2500,complete_horizontal_run_centerline_mm:partial?null:2500,
 source_projection:{value_mm:2500,pieces:[{plan_edge:'P1',path_index:0,segment_index:0,source_line_handle:'LINE',length_mm:2500}],installed_whole_edge_length_mm:null,inline_joint_interior_length_mm:null,joint_graphic_spans_added:false},
 unknown_inline_joint_handles:partial?['J1','J2']:[],physical_installed_length_mm:null,net_pipe_cut_length_mm:null,human_accepted:false,related_HIL_confirmation_inherited:false,
 length_allocation_method:'native_T_order_between_two_independent_anchors',axis_drawn_lengths_or_ratios_used:false,child_equipment_or_external_interface_identity_inferred:false,metric_reader:partial?'inherited_native_inline_pipe_XY':'inherited_native_plan_projection'};
 const context={mode:'source_checked_uniform_path_group_DN_child_domains_v1',source_graph_sha256:h,rendered_graph_sha256:h,source_policy_sha256:h,horizontal_directions_degrees:[0,45,135],groups:[g],scalar_physical_lengths_assigned:0,topology_mutated:false,human_accepted:false,
 ordered_group_plan_runs:{mode:'qualified_ordered_group_child_plan_metrics_v1',records:[r],axis_edges:1,source_bindings:{axis_graph:h,rendered_graph:h,length_proof:h},group_totals_copied_to_children:false,unknown_inline_lengths_assigned:0,human_accepted:false}};
 return {edge,context,r};
}
test('native child route replaces unallocated UI text while original effective CSV and graph remain exact',()=>{
 const {edge,context}=fixture(),before=structuredClone(edge),oldContext=structuredClone(context);delete oldContext.ordered_group_plan_runs;
 const old=crossViewAttributeCsvValues(edge,oldContext),now=crossViewAttributeCsvValues(edge,context);assert.ok(checkedOrderedGroupRun(edge,context));
 for(const[k,v]of Object.entries(old))assert.deepEqual(now[k],v,k);
 assert.equal(now.ordered_group_plan_pipe_XY_mm,2500);assert.equal(now.ordered_group_complete_run_mm,2500);assert.equal(now.batch_group_pipe_XY_total_mm,10000);assert.equal(now.ordered_group_net_pipe_cut_length_mm,'');assert.equal(now.diameter_nominal_mm,250);
 const properties=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'},attribute_value_context:context});assert.ok(properties.some(r=>r[0]==='三通间完整中心线'&&r[1]==='2.500 m（含阀件区间）'));assert.ok(properties.some(r=>r[0]==='路径组内分配'&&r[1].startsWith('已按原生三通区间')));assert.ok(properties.every(r=>!r[1].includes('长度分配仍未知')));assert.ok(edgeAttributeProperties(edge,{display:{edge_attribute_language:'en'},attribute_value_context:context}).every(r=>!r[1].includes('child length allocation remains unknown')));assert.ok(edgeAttributeCsvFields.includes('ordered_group_complete_run_mm'));assert.deepEqual(edge,before);
});
test('partial inline source pipe XY never gains graphic-span or complete installed length',()=>{
 const{edge,context}=fixture(true),values=crossViewAttributeCsvValues(edge,context);assert.ok(checkedOrderedGroupRun(edge,context));assert.equal(values.ordered_group_plan_pipe_XY_mm,2500);assert.equal(values.ordered_group_complete_run_mm,'');assert.equal(values.ordered_group_unknown_inline_handles,'J1;J2');
 const rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'},attribute_value_context:context});assert.ok(rows.some(r=>r[0]==='三通间完整中心线'&&r[1].startsWith('未知；软接内部长度未计入')));
});
test('source, order, geometry, system, duplicate and unjustified physical values fail closed',()=>{
 for(const defect of['source','order','geometry','system','duplicate','net','joint_complete','graphic_span','piece_total']){
  const{edge,context,r}=fixture(true);
  if(defect==='source')context.source_graph_sha256='b'.repeat(64);
  if(defect==='order')r.index_in_group=1;
  if(defect==='geometry')edge.attribute_paths=[[[0,0],[99,0]]];
  if(defect==='system')r.system='supply';
  if(defect==='duplicate')context.ordered_group_plan_runs.records.push(structuredClone(r));
  if(defect==='net')r.net_pipe_cut_length_mm=2500;
  if(defect==='joint_complete')r.complete_horizontal_run_centerline_mm=2500;
  if(defect==='graphic_span')r.source_projection.joint_graphic_spans_added=true;
  if(defect==='piece_total')r.source_projection.pieces[0].length_mm=2800;
  assert.equal(checkedOrderedGroupRun(edge,context),null,defect);assert.deepEqual(orderedGroupRunCsvValues(edge,context),{});
 }
 const{edge,context}=fixture();const sorted=value=>Array.isArray(value)?value.map(sorted):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,sorted(value[k])])):value;
 assert.ok(checkedOrderedGroupRun(edge,JSON.parse(JSON.stringify(sorted(context)))));
});
