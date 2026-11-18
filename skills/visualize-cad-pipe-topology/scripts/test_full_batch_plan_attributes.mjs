import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedBatchPlanScope,batchPlanProperties,batchPlanCsvValues,reconcileBatchPlanCsvValues,uniformGroupChildDN} from '../assets/viewer/public/full-batch-plan-attributes.js';
import {edgeAttributeProperties,crossViewAttributeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';

function fixture(){
 const s={mapping_id:'CURRENT',kind:'same_floor_T_to_T_main',floor:1,system:'supply',plan_edges:['P'],iso_edges:['E'],
  plan_drawn_nominal_mm:100,plan_DN_records:[{edge_id:'P',system:'supply',nominal_mm:100,status:'direct_plan_DN',lineage:[{evidence:[{evidence_id:'source:TEXT'}]}],scope_paths:[[[0,0],[1000,0]]],human_accepted:false}],
  horizontal_projection:{status:'native_plan_horizontal_projection_partial_length',value_mm:1000,pieces:[{plan_edge:'P',path_index:0,segment_index:0,length_mm:1000}]},
  complete_horizontal_centerline_route_mm:1000,whole_axis_nominal_mm:100,whole_installed_length_mm:null,group_scope_not_allocated_to_child_edges:false,
  axis_horizontal_scope_paths:[[[0,0],[10,0]]],source_sha256:{plan:'a'.repeat(64),iso:'b'.repeat(64)},graph_sha256:{plan:'c'.repeat(64),iso:'d'.repeat(64)},
  mapping_receipt_sha256:'e'.repeat(64),plan_DN_receipt_sha256:'f'.repeat(64),human_accepted:false,related_HIL_confirmation_inherited:false};
 return {edge_id:'E',system:'supply',floor_start:1,floor_end:1,attribute_paths:[[[0,0],[10,0]]],batch_plan_attribute_scopes:s};
}
test('verified current plan source, whole horizontal route and CSV are integrated',()=>{
 const e=fixture();assert.ok(checkedBatchPlanScope(e));const rows=edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'}});
 assert.equal(rows[0][1],'DN100');assert.ok(rows.some(r=>r[0]==='完整水平中心线路由'&&r[1]==='1.000 m'));
 const csv=crossViewAttributeCsvValues(e);assert.equal(csv.batch_plan_DN_mm,100);assert.equal(csv.batch_plan_pipe_XY_mm,1000);
 assert.equal(csv.diameter_nominal_mm,100);assert.ok(edgeAttributeCsvFields.includes('batch_mapping_id'));assert.equal(e.batch_plan_attribute_scopes.whole_installed_length_mm,null);
});
test('equipment plan DN remains partial and cannot overwrite a distinct axis drop',()=>{
 const e=fixture(),s=e.batch_plan_attribute_scopes;s.kind='equipment_branch';s.plan_drawn_nominal_mm=150;s.plan_DN_records[0].nominal_mm=150;
 s.whole_axis_nominal_mm=null;s.complete_horizontal_centerline_route_mm=null;delete s.axis_horizontal_scope_paths;
 e.pipe_diameter={display:'DN80'};const before=structuredClone(e.pipe_diameter);
 const rows=edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'}});
 assert.equal(rows[0][1],'DN150（平面已绘区段）');assert.deepEqual(e.pipe_diameter,before);assert.equal(batchPlanCsvValues(e).diameter_nominal_mm,'');
});
test('group route totals are kept separate and never allocated to individual edges',()=>{
 const e=fixture(),s=e.batch_plan_attribute_scopes;s.kind='native_main_chain_between_independent_junctions';s.iso_edges=['E','E2'];
 s.group_scope_not_allocated_to_child_edges=true;s.whole_axis_nominal_mm=null;s.complete_horizontal_centerline_route_mm=null;delete s.axis_horizontal_scope_paths;
 assert.ok(checkedBatchPlanScope(e));const csv=batchPlanCsvValues(e);assert.equal(csv.batch_plan_pipe_XY_mm,'');assert.equal(csv.batch_group_pipe_XY_total_mm,1000);
 assert.ok(batchPlanProperties(e).some(r=>r[1].includes('不能重复累加组总长')));
});
test('conflicts and missing metrics export blank numeric values instead of zero or old values',()=>{
 const e=fixture(),s=e.batch_plan_attribute_scopes;s.kind='equipment_branch';s.plan_drawn_nominal_mm=null;s.plan_DN_records[0].nominal_mm=null;s.plan_DN_records[0].status='conflict';
 s.horizontal_projection=null;s.whole_axis_nominal_mm=null;s.complete_horizontal_centerline_route_mm=null;delete s.axis_horizontal_scope_paths;
 assert.ok(checkedBatchPlanScope(e));const csv=crossViewAttributeCsvValues(e);assert.equal(csv.batch_plan_DN_mm,'');assert.equal(csv.batch_plan_pipe_XY_mm,'');assert.equal(csv.diameter_nominal_mm,'');assert.equal(csv.diameter_status,'current_plan_DN_conflict');
});
test('wrong source, service, scope, metric, human or child allocation claims fail closed',()=>{
 for(const change of [s=>s.source_sha256.plan='stale',s=>s.system='return',s=>s.plan_drawn_nominal_mm=200,s=>s.horizontal_projection.value_mm=0,
  s=>s.related_HIL_confirmation_inherited=true,s=>s.iso_edges=['E','E2'],s=>s.axis_horizontal_scope_paths=[[[0,0],[0,10]]]]){
  const e=fixture();change(e.batch_plan_attribute_scopes);assert.equal(checkedBatchPlanScope(e),null);assert.deepEqual(batchPlanCsvValues(e),{});
 }
});
test('independent prior whole-edge DN survives an incomplete current metric when the current known main DN agrees',()=>{
 const e=fixture(),s=e.batch_plan_attribute_scopes;s.whole_axis_nominal_mm=null;s.complete_horizontal_centerline_route_mm=null;s.horizontal_projection=null;delete s.axis_horizontal_scope_paths;
 const before=structuredClone(e),prior={diameter_nominal_mm:100,diameter_text:'DN100',diameter_status:'prior_source_checked',crossview_whole_edge_length_mm:1234};
 const csv=reconcileBatchPlanCsvValues(e,prior);
 assert.equal(csv.diameter_nominal_mm,100);assert.equal(csv.batch_retained_prior_whole_DN_mm,100);assert.equal(csv.batch_whole_axis_DN_mm,'');assert.equal(csv.batch_complete_horizontal_centerline_mm,'');
 assert.equal(csv.crossview_whole_edge_length_mm,1234);assert.equal(csv.batch_plan_pipe_XY_mm,'');assert.equal(csv.batch_DN_resolution_basis,'prior_whole_edge_source_scope_agrees_with_current_plan');assert.deepEqual(e,before);
});
test('current DN conflicts, unknown source, changed value, equipment drops, groups and different floors never reuse old whole DN',()=>{
 for(const mode of['conflict','unknown','changed','equipment','group','floor','prior-unknown']){
  const e=fixture(),s=e.batch_plan_attribute_scopes;s.whole_axis_nominal_mm=null;s.complete_horizontal_centerline_route_mm=null;delete s.axis_horizontal_scope_paths;
  if(mode==='conflict'||mode==='unknown'){s.plan_drawn_nominal_mm=null;s.plan_DN_records[0].nominal_mm=null;s.plan_DN_records[0].status=mode==='conflict'?'conflict':'unresolved';s.plan_DN_records[0].lineage=[]}
  if(mode==='changed'){s.plan_drawn_nominal_mm=200;s.plan_DN_records[0].nominal_mm=200}
  if(mode==='equipment')s.kind='equipment_branch';
  if(mode==='group'){s.iso_edges=['E','E2'];s.group_scope_not_allocated_to_child_edges=true}
  if(mode==='floor')e.floor_end=2;
  const csv=reconcileBatchPlanCsvValues(e,{diameter_nominal_mm:mode==='prior-unknown'?'':100});
  assert.equal(csv.diameter_nominal_mm,'',mode);assert.equal(csv.batch_retained_prior_whole_DN_mm,'',mode);
 }
 const e=fixture();delete e.batch_plan_attribute_scopes;const prior={diameter_nominal_mm:100,diameter_status:'source_checked'};assert.deepEqual(reconcileBatchPlanCsvValues(e,prior),prior);
});

function groupFixture(){
 const e=fixture(),s=e.batch_plan_attribute_scopes;e.start_node_id='T1';e.end_node_id='T2';
 s.kind='native_main_chain_between_independent_junctions';s.iso_edges=['E','E2'];s.group_scope_not_allocated_to_child_edges=true;
 s.whole_axis_nominal_mm=null;s.complete_horizontal_centerline_route_mm=null;delete s.axis_horizontal_scope_paths;
 const g={mapping_id:s.mapping_id,floor:s.floor,system:s.system,nominal_mm:100,plan_edges:s.plan_edges,iso_edges:s.iso_edges,
 source_sha256:s.source_sha256,graph_sha256:s.graph_sha256,plan_DN_receipt_sha256:s.plan_DN_receipt_sha256,mapping_receipt_sha256:s.mapping_receipt_sha256,
 domains:[{edge_id:'E',start_node_id:'T1',end_node_id:'T2',scope_paths:structuredClone(e.attribute_paths)},
 {edge_id:'E2',start_node_id:'T2',end_node_id:'T3',scope_paths:[[[10,0],[20,0]]]}],
 child_length_allocation_known:false,physical_child_lengths_mm:null,human_accepted:false};
 return {e,c:{mode:'source_checked_uniform_path_group_DN_child_domains_v1',source_graph_sha256:'1'.repeat(64),rendered_graph_sha256:'2'.repeat(64),source_policy_sha256:'3'.repeat(64),horizontal_directions_degrees:[0,45,135],groups:[g],scalar_physical_lengths_assigned:0,topology_mutated:false,human_accepted:false}};
}
test('a source-bound uniform path DN applies to each complete horizontal child without allocating group length',()=>{
 const {e,c}=groupFixture(),before=structuredClone(e);assert.equal(uniformGroupChildDN(e,c).nominal_mm,100);
 const csv=crossViewAttributeCsvValues(e,c);assert.equal(csv.diameter_nominal_mm,100);assert.equal(csv.batch_uniform_group_child_DN_mm,100);
 assert.equal(csv.batch_group_pipe_XY_total_mm,1000);assert.equal(csv.batch_plan_pipe_XY_mm,'');assert.equal(csv.batch_complete_horizontal_centerline_mm,'');
 assert.equal(csv.crossview_whole_edge_length_mm??'','');assert.equal(csv.batch_whole_axis_DN_mm,'');
 const rows=edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'},attribute_value_context:c});
 assert.ok(rows[0][1].startsWith('DN100'));assert.ok(rows.some(r=>r[1].includes('长度尚未逐边分配')));assert.deepEqual(e,before);
 assert.equal(crossViewAttributeCsvValues(e).diameter_nominal_mm,'');
});
test('uniform child DN fails closed on changed source, path, service, floor, identity, conflict or length allocation',()=>{
 const mutations=[({c})=>c.source_graph_sha256='stale',({c})=>c.groups[0].source_sha256={...c.groups[0].source_sha256,plan:'9'.repeat(64)},
  ({c})=>c.groups.push(structuredClone(c.groups[0])),({c})=>c.groups[0].domains.pop(),({c})=>c.groups[0].physical_child_lengths_mm=[500,500],
  ({c})=>c.groups[0].child_length_allocation_known=true,({c})=>c.horizontal_directions_degrees=[90],({e})=>e.start_node_id='',
  ({e})=>e.floor_end=2,({e})=>e.axis_riser_attributes={},({e})=>e.plan_segment_attributes={},({e})=>e.attribute_paths=[[[0,0],[0,10]]],
  ({e})=>e.batch_plan_attribute_scopes.plan_DN_records[0].status='conflict',({c})=>c.groups[0].nominal_mm=200,
  ({c})=>c.groups[0].system='return',({c})=>c.groups[0].mapping_receipt_sha256='8'.repeat(64)];
 for(const mutate of mutations){const pair=groupFixture();mutate(pair);assert.equal(uniformGroupChildDN(pair.e,pair.c),null,String(mutate));
  assert.equal(crossViewAttributeCsvValues(pair.e,pair.c).diameter_nominal_mm,'');}
});
