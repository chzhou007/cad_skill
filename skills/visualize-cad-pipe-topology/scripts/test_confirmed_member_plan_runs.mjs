import test from 'node:test';import assert from 'node:assert/strict';
import {checkedMemberPlanRun,memberPlanRunProperties,memberPlanRunCsvValues} from '../assets/viewer/public/full-batch-plan-attributes.js';
import {crossViewAttributeCsvValues,edgeAttributeProperties} from '../assets/viewer/public/edge-attributes.js';
function fixture(){
 const h='a'.repeat(64),s={mapping_id:'M',kind:'same_floor_T_to_T_main',floor:2,system:'supply',plan_edges:['P'],iso_edges:['E'],plan_drawn_nominal_mm:200,
 plan_DN_records:[{edge_id:'P',system:'supply',nominal_mm:200,status:'direct_plan_DN',lineage:[{evidence:[{evidence_id:'source:T'}]}],scope_paths:[[[0,0],[10000,0]]],human_accepted:false}],
 horizontal_projection:null,complete_horizontal_centerline_route_mm:null,whole_axis_nominal_mm:null,whole_installed_length_mm:null,group_scope_not_allocated_to_child_edges:false,
 source_sha256:{plan:h,iso:h},graph_sha256:{plan:h,iso:h},mapping_receipt_sha256:h,plan_DN_receipt_sha256:h,human_accepted:false,related_HIL_confirmation_inherited:false};
 const edge={edge_id:'E',system:'supply',start_node_id:'A',end_node_id:'B',start_floor:2,end_floor:2,attribute_paths:[[[0,0],[100,0]]],batch_plan_attribute_scopes:s};
 const r={axis_edge_id:'E',axis_start_node:'A',axis_end_node:'B',axis_mapping_id:'M',axis_attribute_paths:structuredClone(edge.attribute_paths),plan_edge_id:'P',floor:2,system:'supply',nominal_mm:200,plan_graph_sha256:h,source_sha256:{plan:h,iso:h},mapping_receipt_sha256:h,
 horizontal_plan_run_centerline_mm:4000,net_pipe_cut_length_mm:null,installed_whole_edge_length_mm:null,detail_inline_positions_scaled_to_plan:false,run_centerline_includes_inline_assembly_extents:true,human_accepted:false,related_HIL_confirmation_inherited:false,shared_projected_source_LINE:'LINE',compound_text_handle:'TEXT'};
 const context={source_graph_sha256:h,rendered_graph_sha256:h,member_plan_runs:{mode:'qualified_axis_confirmed_member_plan_runs_v1',original_local_topology_unchanged:true,original_axis_correspondences_unchanged:true,human_accepted:false,net_pipe_cut_lengths_assigned:0,source_bindings:{axis_graph:h,rendered_graph:h,member_proof:h},records:[r]}};
 return{edge,context,r};
}
test('member native plan run is visible and exportable without counting detail span or net pipe length',()=>{
 const{edge,context}=fixture(),before=structuredClone(edge);assert.ok(checkedMemberPlanRun(edge,context));
 const rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'},attribute_value_context:context});
 assert.ok(rows.some(r=>r[0]==='平面三通间路由中心线'&&r[1]==='4.000 m（含边上元件区间）'));
 const csv=crossViewAttributeCsvValues(edge,context);assert.equal(csv.member_plan_run_centerline_mm,4000);assert.equal(csv.member_plan_run_DN_mm,200);assert.equal(csv.member_plan_net_pipe_cut_length_mm,'');assert.equal(csv.batch_complete_horizontal_centerline_mm,'');assert.deepEqual(edge,before);
});
test('stale versions, changed geometry, mixed systems, merged groups and promoted net lengths do not leak',()=>{
 for(const defect of ['source','geometry','system','group','length','review','duplicate']){
  const{edge,context,r}=fixture();
  if(defect==='source')context.source_graph_sha256='b'.repeat(64);
  if(defect==='geometry')edge.attribute_paths=[[[0,0],[90,0]]];
  if(defect==='system')r.system='return';
  if(defect==='group')edge.batch_plan_attribute_scopes.iso_edges.push('OTHER');
  if(defect==='length')r.net_pipe_cut_length_mm=4000;
  if(defect==='review')r.related_HIL_confirmation_inherited=true;
  if(defect==='duplicate')context.member_plan_runs.records.push(structuredClone(r));
  assert.equal(checkedMemberPlanRun(edge,context),null,defect);assert.deepEqual(memberPlanRunCsvValues(edge,context),{});assert.deepEqual(memberPlanRunProperties(edge,true,context),[]);
 }
});

test('canonical manifest key sorting preserves member source identity',()=>{
 const {edge,context}=fixture();
 const sorted=o=>Array.isArray(o)?o.map(sorted):o&&typeof o==='object'?Object.fromEntries(Object.keys(o).sort().map(k=>[k,sorted(o[k])])):o;
 const roundtrip=JSON.parse(JSON.stringify(sorted(context)));
 assert.notEqual(JSON.stringify(edge.batch_plan_attribute_scopes.source_sha256),JSON.stringify(roundtrip.member_plan_runs.records[0].source_sha256));
 assert.ok(checkedMemberPlanRun(edge,roundtrip));assert.equal(crossViewAttributeCsvValues(edge,roundtrip).member_plan_run_centerline_mm,4000);
});
