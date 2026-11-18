import test from'node:test';import assert from'node:assert/strict';
import {checkedOrderedBranch,orderedBranchCsvValues}from'../assets/viewer/public/ordered-branch-plan-attributes.js';
import {edgeAttributeProperties,crossViewAttributeCsvValues,edgeAttributeCsvFields}from'../assets/viewer/public/edge-attributes.js';
function fixture(){
 const h='a'.repeat(64),edge={edge_id:'E',system:'supply',start_node_id:'V',end_node_id:'T',start_port_id:'VP',end_port_id:null,source_insert_handle:'M',floor_start:3,floor_end:3,attribute_paths:[[[0,0],[1,0],[5,0]]]};
 const row={axis_edge_id:'E',system:'supply',floor:3,mapping_id:'MAP',parent_mapping_id:'GROUP',axis_start_node:'V',axis_end_node:'T',axis_port_id:'VP',axis_marker_handle:'M',axis_attribute_paths:structuredClone(edge.attribute_paths),axis_display_segment_index:0,
 plan_edges:['P'],plan_boundary_id:'B',main_anchor:{plan_node:'PT',axis_node:'T'},known_plan_pipe_XY_mm:812.278,plan_horizontal_projection:{value_mm:812.278,pieces:[{plan_edge:'P',length_mm:812.278}],installed_whole_edge_length_mm:null},
 plan_drawn_nominal_mm:250,plan_DN_records:[{nominal_mm:250,system:'supply',human_accepted:false,lineage:[{evidence:[{evidence_id:'source:DN'}]}]}],local_DN_evidence_status:'exact_qualified_local_plan_DN_retained_not_fresh_global_DN_rebuild',source_sha256:{plan:h,iso:h},plan_graph_sha256:h,
 whole_axis_DN_selected:false,whole_axis_physical_length_mm:null,physical_port_verified:false,remote_equipment_identity_inferred:false,circle_radius_added_to_metric:false,axis_marker_centre_span_added_to_metric:false,related_HIL_confirmation_inherited:false,human_accepted:false};
 const context={source_graph_sha256:h,rendered_graph_sha256:h,ordered_anchor_branches:{mode:'qualified_ordered_anchor_drawn_branch_attributes_v1',records:[row],axis_edges:1,source_bindings:{axis_graph:h,rendered_graph:h,branch_proof:h},local_topology_mutated:false,whole_axis_values_assigned:0,physical_ports_created:0,human_accepted:false}};
 return{edge,row,context};
}
test('drawn branch plan DN/XY is visible while every old CSV value and source graph remain unchanged',()=>{
 const{edge,row,context}=fixture(),before=structuredClone(edge),old=crossViewAttributeCsvValues(edge),current=crossViewAttributeCsvValues(edge,context);assert.ok(checkedOrderedBranch(edge,context));for(const[k,v]of Object.entries(old))assert.deepEqual(current[k],v,k);
 assert.equal(current.ordered_branch_plan_DN_mm,250);assert.equal(current.ordered_branch_plan_pipe_XY_mm,812.278);assert.equal(current.ordered_branch_whole_axis_DN_mm,'');assert.equal(current.ordered_branch_whole_axis_length_mm,'');assert.ok(edgeAttributeCsvFields.includes('ordered_branch_mapping_id'));
 const rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'},attribute_value_context:context});assert.equal(rows[0][1],'DN250（平面已绘支路）');assert.ok(rows.some(r=>r[0]==='平面已绘支路线长'&&r[1]==='0.812 m'));assert.ok(rows.some(r=>r[0]==='整条轴测边管径与长度'&&r[1].startsWith('未知')));assert.deepEqual(edge,before);
});
test('wrong source/path/port, duplicate writer and physical promotions cannot export drawing values',()=>{
 for(const defect of['source','path','port','writer','physical','whole','radius','metric','duplicate','floor']){
  const{edge,row,context}=fixture();
  if(defect==='source')context.source_graph_sha256='b'.repeat(64);
  if(defect==='path')edge.attribute_paths=[[[0,0],[2,0],[5,0]]];
  if(defect==='port')edge.start_port_id='wrong';
  if(defect==='writer')edge.batch_plan_attribute_scopes={prior:true};
  if(defect==='physical')row.physical_port_verified=true;
  if(defect==='whole')row.whole_axis_DN_selected=true;
  if(defect==='radius')row.circle_radius_added_to_metric=true;
  if(defect==='metric')row.plan_horizontal_projection.pieces[0].length_mm=900;
  if(defect==='duplicate')context.ordered_anchor_branches.records.push(structuredClone(row));
  if(defect==='floor')edge.floor_end=2;
  assert.equal(checkedOrderedBranch(edge,context),null,defect);assert.deepEqual(orderedBranchCsvValues(edge,context),{});
 }
});
