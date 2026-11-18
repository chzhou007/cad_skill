import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedAxisRiserSegments,axisRiserAttributeProperties,axisRiserAttributeCsvValues} from '../assets/viewer/public/axis-riser-attributes.js';
import {crossViewAttributeCsvValues,edgeAttributeProperties,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';
function fixture(){
 const hash='a'.repeat(64);return {edge_id:'E1',system:'supply',floor_start:1,floor_end:2,attribute_paths:[[[10,0],[0,0],[0,20]]],
  axis_riser_attributes:[{edge_id:'E1',path_index:0,segment_index:1,system:'supply',scope_points:[[0,0],[0,20]],floor_pair:[1,2],nominal_mm:450,
   status:'T_inherited_axis_segment_DN',scope:'native_axis_vertical_segment_DN_only',horizontal_values_source:'floor_plan_correspondence',
   source_scope_sha256:hash,source_sha256:hash,local_graph_sha256:hash,attribute_parent_graph_sha256:hash,source_line_handle:'A1',
   lineage:[{nominal_mm:450,evidence:[{evidence_id:'source:TEXT1',edge_path:['DN-SEG:E2:0','DN-SEG:E1:1']}]}],
   whole_edge_nominal_mm:null,physical_length_mm:null,whole_edge_physical_length_mm:null,human_accepted:false}]};
}
test('source checked DN450 appears as segment properties and CSV while mixed edge values stay blank',()=>{
 const edge=fixture(),before=structuredClone(edge);assert.equal(checkedAxisRiserSegments(edge).length,1);
 const props=axisRiserAttributeProperties(edge);assert.ok(props.some(([k,v])=>k==='竖向分段管径'&&v.includes('DN450')&&v.includes('1F')));
 assert.ok(props.some(([k,v])=>k==='竖管管径来源'&&v.includes('SH16 11')&&v.includes('TEXT1')));
 assert.ok(edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}}).some(([k])=>k==='竖管实际长度'));
 const values=crossViewAttributeCsvValues(edge);assert.equal(values.axis_riser_segment_nominal_mm,'450');assert.equal(values.axis_riser_physical_length_mm,'');
 assert.equal(values.diameter_nominal_mm,undefined);assert.equal(values.crossview_whole_edge_length_mm,undefined);
 assert.ok(edgeAttributeCsvFields.includes('axis_riser_segments_json'));assert.deepEqual(edge,before);
});
test('stale shape/system/floor/hash/lineage or whole-edge claims cannot display checked segment DN',()=>{
 for(const mutate of [e=>e.attribute_paths[0][1][0]=1,e=>e.system='return',e=>e.floor_end=3,e=>e.axis_riser_attributes[0].source_scope_sha256='bad',
  e=>e.axis_riser_attributes[0].lineage[0].evidence[0].edge_path=['OTHER'],e=>e.axis_riser_attributes[0].nominal_mm=0,
  e=>e.axis_riser_attributes[0].physical_length_mm=0,e=>e.axis_riser_attributes[0].whole_edge_nominal_mm=450,
  e=>e.axis_riser_attributes[0].human_accepted=true,e=>e.axis_riser_attributes.push(structuredClone(e.axis_riser_attributes[0]))]){
  const edge=fixture();mutate(edge);assert.equal(checkedAxisRiserSegments(edge),null);assert.deepEqual(axisRiserAttributeCsvValues(edge),{});
 }
});
test('an unrelated ordinary edge preserves legacy empty output',()=>{
 const edge={edge_id:'ordinary'};assert.equal(checkedAxisRiserSegments(edge),null);assert.deepEqual(axisRiserAttributeCsvValues(edge),{});assert.deepEqual(crossViewAttributeCsvValues(edge),{});
});
