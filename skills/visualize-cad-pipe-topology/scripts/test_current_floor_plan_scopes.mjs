import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedCurrentFloorPlanScope,currentFloorPlanScopeProperties,currentFloorPlanScopeCsvValues} from '../assets/viewer/public/current-floor-plan-scopes.js';
import {crossViewAttributeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';

function fixture(detail=false){
 const source='a'.repeat(64),axisSource='b'.repeat(64),oldGraph='c'.repeat(64),currentGraph='d'.repeat(64),axisGraph='e'.repeat(64);
 const metric={value_mm:detail?null:1000,pieces:[{plan_edge:'P',points:[[0,0],[1000,0]]}],installed_whole_edge_length_mm:null,unshown_connection_length_mm:null};
 if(detail)Object.assign(metric,{status:'source_confirmed_detail_topology_physical_length_unknown',detail_context:{physical_units_applied:false,plan_graph_sha256:currentGraph,plan_source_sha256:source,human_accepted:false,plan_edges:['P']}});
 const c={status:'partial_plan_attributes_source_checked',mapping_id:'OLD',mapping_kind:'equipment_branch',floor:2,system:'supply',plan_edges:['P'],iso_edges:['E'],human_accepted:false,
  source_hashes:{plan:source,isometric:axisSource,plan_graph:oldGraph,local_iso_graph:axisGraph},diameter:{nominal_mm:null,plan_candidate:{nominal_mm:300}},horizontal_projection:structuredClone(metric)};
 const scope={current_mapping_id:'CURRENT',historical_mapping_id:'OLD',edge_id:'E',floor:2,system:'supply',plan_edges:['P'],iso_edges:['E'],
  source_sha256:{plan:source,iso:axisSource},plan_graph_sha256:currentGraph,iso_graph_sha256:axisGraph,prior_plan_graph_sha256:oldGraph,source_scope_sha256:'f'.repeat(64),historical_attribute_sha256:'1'.repeat(64),
  diameter:{edge_id:'P',system:'supply',nominal_mm:300,lineage:[{}],human_accepted:false},horizontal_projection:metric,axis_local_DN_candidates:[],
  whole_axis_DN_selected:false,whole_axis_physical_length_mm:null,physical_ports_verified:false,equal_plan_axis_segment_extents_proved:false,related_HIL_confirmation_inherited:false,human_accepted:false};
 return {edge_id:'E',system:'supply',attribute_paths:[[[0,0],[0,10]]],cross_view_attributes:c,current_floor_plan_scope_evidence:scope};
}

test('current source DN is separate from historical whole unknown and CSV retains scope',()=>{
 const edge=fixture();assert.ok(checkedCurrentFloorPlanScope(edge));
 assert.ok(currentFloorPlanScopeProperties(edge).some(r=>r[0]==='当前平面已绘片段管径'&&r[1]==='DN300 [2F]'));
 const csv=currentFloorPlanScopeCsvValues(edge);assert.equal(csv.current_floor_scope_DN_mm,300);assert.equal(csv.current_floor_scope_XY_mm,1000);
 assert.equal(edge.cross_view_attributes.diameter.nominal_mm,null);assert.ok(edgeAttributeCsvFields.includes('current_floor_scope_DN_mm'));
 assert.equal(crossViewAttributeCsvValues(edge).current_floor_scope_mapping_id,'CURRENT');
});
test('detail drawing length stays unknown and exports blank instead of zero',()=>{
 const edge=fixture(true);assert.ok(checkedCurrentFloorPlanScope(edge));
 assert.equal(currentFloorPlanScopeCsvValues(edge).current_floor_scope_XY_mm,'');
 assert.ok(currentFloorPlanScopeProperties(edge).some(r=>r[1].includes('详图跨度不计物理长度')));
});
test('local axis DN candidate binds only original segment without whole or inter-floor claim',()=>{
 const edge=fixture(),s=edge.current_floor_plan_scope_evidence;
 s.axis_local_DN_candidates=[{edge_id:'E',system:'supply',status:'segment_dn_candidate_not_accepted',source_text:{handle:'LABEL',source_sha256:s.source_sha256.iso},nominal_mm_candidate:65,source_line_handle:'LINE',path_index:0,segment_index:0,scope_points:[[0,0],[0,10]],whole_axis_DN_selected:false,inter_floor_riser_proved:false,physical_length_mm:null,human_accepted:false}];
 assert.ok(checkedCurrentFloorPlanScope(edge));assert.ok(currentFloorPlanScopeProperties(edge).some(r=>r[1].includes('DN65')));
 s.axis_local_DN_candidates[0].inter_floor_riser_proved=true;assert.equal(checkedCurrentFloorPlanScope(edge),null);
});
test('stale source graph wrong DN or changed metric cannot display verified current data',()=>{
 for(const change of [e=>e.current_floor_plan_scope_evidence.prior_plan_graph_sha256='0'.repeat(64),e=>e.current_floor_plan_scope_evidence.diameter.nominal_mm=65,
  e=>e.current_floor_plan_scope_evidence.horizontal_projection.value_mm=0,e=>e.current_floor_plan_scope_evidence.whole_axis_DN_selected=true,
  e=>e.current_floor_plan_scope_evidence.related_HIL_confirmation_inherited=true]){
  const edge=fixture();change(edge);assert.equal(checkedCurrentFloorPlanScope(edge),null);assert.deepEqual(currentFloorPlanScopeCsvValues(edge),{});
 }
});
