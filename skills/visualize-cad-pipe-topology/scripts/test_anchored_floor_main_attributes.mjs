import test from 'node:test';import assert from 'node:assert/strict';
import {checkedAnchoredMain,anchoredMainCsvValues} from '../assets/viewer/public/anchored-floor-main-attributes.js';
import {crossViewAttributeCsvValues,edgeAttributeProperties,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';
function fixture(conflict=false,inline=false){
 const points=[[[0,0],[5,0]]],value=conflict?null:200,metric={value_mm:500,pieces:[{length_mm:500}],joint_graphic_spans_added:false,inline_joint_interior_length_mm:null};
 const a={axis_edge:'E',iso_edges:['E'],plan_edges:['P'],mapping_id:'M',floor:1,system:'supply',scope_paths:points,status:'source_checked_anchored_floor_main_attributes_human_pending',scope:'native_same_floor_T_to_T_main',
 nominal_mm:value,diameter_evidence:{edge_id:'P',system:'supply',nominal_mm:value,status:conflict?'conflict':'direct_plan_DN',lineage:conflict?[{nominal_mm:200,evidence:[]},{nominal_mm:450,evidence:[]}]:[{nominal_mm:200,evidence:[{evidence_id:'source:DN',edge_path:['P']}]}]},
 horizontal_projection:metric,inline_interiors_unknown:inline,complete_horizontal_centerline_route_mm:inline?null:500,installed_whole_edge_length_mm:null,pipe_net_cut_length_mm:null,human_accepted:false,physical_ports_verified:false,related_HIL_confirmation_inherited:false,
 mapping_sha256:'a'.repeat(64),attribute_scope_sha256:'b'.repeat(64),parent_graph_sha256:'c'.repeat(64),source_sha256:{plan:'source',iso:'axis'}};
 return {edge_id:'E',floor_start:1,floor_end:1,system:'supply',attribute_paths:points,anchored_floor_main_attributes:a};
}
test('known plan main DN and length appear in primary properties and CSV',()=>{
 const e=fixture(),before=structuredClone(e),csv=crossViewAttributeCsvValues(e),rows=edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(checkedAnchoredMain(e));assert.equal(rows[0][1],'DN200');assert.ok(rows[2][1].includes('source:DN'));assert.equal(csv.diameter_nominal_mm,200);assert.equal(csv.anchored_main_plan_XY_mm,500);assert.equal(csv.anchored_main_complete_centerline_mm,500);assert.ok(edgeAttributeCsvFields.includes('anchored_main_DN_evidence_json'));assert.deepEqual(e,before);
});
test('conflict and inline partial values stay blank for unknown whole quantities',()=>{
 const e=fixture(true,true),csv=crossViewAttributeCsvValues(e),rows=edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'}});
 assert.equal(csv.diameter_nominal_mm,'');assert.equal(csv.anchored_main_complete_centerline_mm,'');assert.equal(csv.anchored_main_plan_XY_mm,500);assert.match(rows[0][1],/\u51b2\u7a81/);assert.match(JSON.stringify(rows),/\u4e0d\u542b\u8f6f\u63a5/);assert.equal(JSON.parse(csv.anchored_main_DN_evidence_json).lineage.length,2);
});
test('forged source hashes, wrong paths, systems and physical claims are not displayed',()=>{
 for(const change of [e=>e.system='return',e=>e.floor_end=2,e=>e.attribute_paths=[[[0,0],[8,0]]],e=>e.anchored_floor_main_attributes.parent_graph_sha256='old',e=>e.anchored_floor_main_attributes.human_accepted=true,e=>e.anchored_floor_main_attributes.installed_whole_edge_length_mm=0]){
  const e=fixture();change(e);assert.equal(checkedAnchoredMain(e),null);assert.deepEqual(anchoredMainCsvValues(e),{});
 }
});
