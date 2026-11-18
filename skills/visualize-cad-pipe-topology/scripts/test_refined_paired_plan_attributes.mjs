import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedPlanDiameterScope,crossViewAttributeProperties,crossViewAttributeCsvValues} from '../assets/viewer/public/edge-attributes.js';
const fixture=()=>({cross_view_attributes:{status:'partial_plan_attributes_source_checked',human_accepted:false,
 mapping_basis:'native_paired_service_junction_correspondence',mapping_kind:'main_between_matched_junctions',junction_correspondence_ids:['PJ1'],
 mapping_id:'LINK-PJ1',system:'supply',plan_edges:['P'],iso_edges:['I'],source_hashes:{plan:'b'.repeat(64)},plan_DN_scope_evidence_sha256:'a'.repeat(64),
 whole_axis_main_scope:'source_checked_plan_native_T_to_T_horizontal_main',whole_edge_physical_length_mm:1700,
 whole_edge_length_kind:'floor_plan_horizontal_main_centerline_route',whole_edge_length_scope:'complete_mapped_T_to_T_centerline_route_not_pipe_net_cut_length',pipe_net_cut_length_mm:null,
 horizontal_projection:{edge_value_mm:1700,route_scope_status:'complete_mapped_horizontal_main_centerline',pieces:[]},
 diameter:{status:'source_checked_whole_horizontal_main_DN',nominal_mm:200,plan_drawn_nominal_mm:200,selected_physical_diameter:true,
 plan_scope_evidence_sha256:'a'.repeat(64),plan_drawn_status:'source_checked_plan_DN_scope_human_pending',
 plan_drawn_values:[{edge_id:'P',system:'supply',nominal_mm:200,scope:'native_plan_drawn_pipe_paths_only',human_accepted:false}]},equipment_connector_length_mm:null}});
test('matched physical network Ts display actual plan DN and length without fake equipment kind',()=>{
 const edge=fixture(),before=structuredClone(edge);assert.equal(checkedPlanDiameterScope(edge.cross_view_attributes).whole,true);
 const row=crossViewAttributeCsvValues(edge);assert.equal(row.diameter_nominal_mm,200);assert.equal(row.crossview_whole_edge_length_mm,1700);
 const properties=crossViewAttributeProperties(edge,true);assert.ok(properties.some(([k,v])=>k==='\u5bf9\u5e94\u4f9d\u636e'&&v.includes('\u4e09\u901a')));
 assert.ok(properties.some(([k,v])=>k==='\u5df2\u5bf9\u5e94\u4e09\u901a'&&v==='PJ1'));assert.deepEqual(edge,before);
});
test('generic main kind cannot bypass native junction proof and unique identities',()=>{
 for(const mutation of [c=>c.mapping_basis='OTHER',c=>delete c.junction_correspondence_ids,c=>c.junction_correspondence_ids=[],c=>c.junction_correspondence_ids=['PJ1','PJ1'],c=>c.junction_correspondence_ids=[null]]){
  const edge=fixture();mutation(edge.cross_view_attributes);assert.equal(checkedPlanDiameterScope(edge.cross_view_attributes).whole,false);
  assert.equal(crossViewAttributeCsvValues(edge).diameter_nominal_mm,'');assert.equal(crossViewAttributeCsvValues(edge).crossview_whole_edge_length_mm,'');
 }
});
test('a remaining multi-edge interval does not receive a repeated whole length',()=>{
 const edge=fixture();edge.cross_view_attributes.iso_edges.push('I2');edge.cross_view_attributes.horizontal_projection.edge_value_mm=null;
 assert.equal(checkedPlanDiameterScope(edge.cross_view_attributes).whole,false);assert.equal(crossViewAttributeCsvValues(edge).crossview_whole_edge_length_mm,'');
});
