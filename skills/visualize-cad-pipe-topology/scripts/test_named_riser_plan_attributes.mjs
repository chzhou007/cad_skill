import test from 'node:test';
import assert from 'node:assert/strict';
import {namedRiserApproachProperties,crossViewAttributeCsvValues,checkedPlanDiameterScope} from '../assets/viewer/public/edge-attributes.js';
function fixture(){
 const hash='a'.repeat(64),row={edge_id:'P',system:'supply',nominal_mm:300,scope:'native_plan_drawn_pipe_paths_only',human_accepted:false};
 return {status:'partial_plan_attributes_source_checked',human_accepted:false,physical_ports_verified:false,equipment_connector_length_mm:null,
  mapping_basis:'native_named_riser_and_independent_equipment_service',mapping_kind:'named_riser_floor_approach',floor:2,system:'supply',
  plan_edges:['P'],iso_edges:['A'],plan_DN_scope_evidence_sha256:hash,source_hashes:{plan:hash},whole_edge_physical_length_mm:null,
  horizontal_projection:{edge_value_mm:5128.08,value_mm:5128.08},diameter:{nominal_mm:null,status:'source_checked_plan_DN_axis_extent_partial',
   plan_scope_evidence_sha256:hash,plan_drawn_status:'source_checked_plan_DN_scope_human_pending',plan_drawn_values:[row],plan_drawn_nominal_mm:300},
  named_riser_interface_context:{identifier:'CHWS1',floor:2,physical_port_verified:false,graphic_circle_radius_added_to_length:false,
   whole_installed_length_mm:null,plan_riser_interface:'RIF001',iso_riser_junction:'T123',equipment_anchor:'CRAH2-2',plan_equipment_main_T:'T062',iso_equipment_main_T:'T121'}};
}
test('checked named interface properties retain DN300 and plan projection without whole DN/length',()=>{
 const c=fixture(),rows=namedRiserApproachProperties(c),values=crossViewAttributeCsvValues({cross_view_attributes:c});
 assert.ok(rows.some(([,v])=>v.includes('CHWS1')));assert.ok(rows.some(([,v])=>v.includes('RIF001')));assert.equal(checkedPlanDiameterScope(c).whole,false);
 assert.equal(values.crossview_plan_drawn_nominal_mm,300);assert.equal(values.crossview_plan_horizontal_projection_mm,5128.08);
 assert.equal(values.diameter_nominal_mm,'');assert.equal(values.crossview_whole_edge_length_mm,'');
});
test('wrong system, floor, radius, port and whole-length claims cannot display checked correspondence',()=>{
 for(const change of [c=>delete c.named_riser_interface_context,c=>delete c.floor,c=>c.named_riser_interface_context.identifier='CHWR1',
  c=>c.named_riser_interface_context.floor=3,c=>c.named_riser_interface_context.graphic_circle_radius_added_to_length=true,
  c=>c.named_riser_interface_context.physical_port_verified=true,c=>c.physical_ports_verified=true,c=>c.whole_edge_physical_length_mm=5128.08,
  c=>c.diameter.nominal_mm=300,c=>c.human_accepted=true]){
  const c=fixture();change(c);assert.deepEqual(namedRiserApproachProperties(c),[]);
 }
});
test('legacy mappings and incomplete records do not gain named-interface claims',()=>{
 assert.deepEqual(namedRiserApproachProperties(null),[]);
 const c=fixture();c.mapping_basis='native_source_and_main_branch_order';assert.deepEqual(namedRiserApproachProperties(c),[]);
});
