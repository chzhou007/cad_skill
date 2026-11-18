import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedPlanSegments,planSegmentProperties,planSegmentCsvValues} from '../assets/viewer/public/upper-floor-plan-segments.js';
import {edgeAttributeProperties,crossViewAttributeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';

function fixture(whole=false){
 const edge={edge_id:'A',system:'supply',floor_start:1,floor_end:whole?1:2,attribute_paths:whole?[[[0,0],[2,2],[4,2]]]:[[[0,0],[3,0],[3,10]]]};
 if(!whole)edge.axis_riser_attributes=[{path_index:0,segment_index:1,nominal_mm:450,scope_points:[[3,0],[3,10]],floor_pair:[1,2]}];
 const r={mapping_id:'M',mapping_kind:'named_riser_lower_floor_segment_'+(whole?'network_link':'approach'),floor:1,system:'supply',edge_id:'A',path_index:0,
  segment_indices:whole?[0,1]:[0],scope_points:whole?[[0,0],[2,2],[4,2]]:[[0,0],[3,0]],scope:'native_plan_matched_lower_floor_axis_segments_only',
  whole_local_edge:whole,plan_edges:['P'],identifier:'CHWS1',equipment_anchor:'D',plan_riser_interface:'R',plan_network_T:'PT',axis_network_T:'AT',plan_equipment_T:'PE',axis_equipment_T:'AE',
  nominal_mm:200,whole_edge_nominal_mm:whole?200:null,whole_edge_centerline_route_mm:whole?10:null,
  length_scope:whole?'complete_mapped_T_to_T_centerline_route_not_pipe_net_cut_length':'mapped_plan_drawn_approach_only',
  pipe_net_cut_length_mm:null,unshown_connection_length_mm:null,physical_port_verified:false,human_accepted:false,
  source_scope_sha256:'a'.repeat(64),mapping_sha256:'b'.repeat(64),attribute_parent_graph_sha256:'c'.repeat(64),
  source_sha256:{plan:'d'.repeat(64),iso:'e'.repeat(64)},local_graph_sha256:{plan:'f'.repeat(64),iso:'1'.repeat(64)}};
 r.diameter_evidence={edge_id:'P',system:'supply',nominal_mm:r.nominal_mm,scope:'native_plan_drawn_pipe_paths_only',human_accepted:false,
  scope_paths:[[[0,0],[10,0]]],lineage:[{nominal_mm:r.nominal_mm,evidence:[{evidence_id:'source:DN',edge_path:['P']}]}]};
 r.horizontal_projection={value_mm:10,installed_whole_edge_length_mm:null,unshown_connection_length_mm:null,
  pieces:[{plan_edge:'P',path_index:0,segment_index:0,points:[[0,0],[10,0]],source_line_handle:'L',length_mm:10}]};
 edge.plan_segment_attributes=[r];return edge;
}

test('lower-prefix values preserve the separate vertical450 tail and mixed unknowns',()=>{
 const e=fixture(),before=structuredClone(e),r=checkedPlanSegments(e);assert.equal(r.length,1);
 const p=planSegmentProperties(e);assert.match(JSON.stringify(p),/DN200/);assert.deepEqual(e,before);
 const csv=crossViewAttributeCsvValues(e);assert.equal(csv.plan_segment_nominal_mm,200);assert.equal(csv.diameter_nominal_mm,'');
 assert.equal(csv.plan_segment_whole_main_centerline_mm,'');assert.equal(e.axis_riser_attributes[0].nominal_mm,450);
});
test('lower full bent main exports DN200 and exact plan route without net cut value',()=>{
 const e=fixture(true),csv=crossViewAttributeCsvValues(e);
 assert.equal(checkedPlanSegments(e).length,1);assert.equal(csv.diameter_nominal_mm,200);
 assert.equal(csv.plan_segment_whole_main_centerline_mm,10);assert.equal(csv.plan_segment_net_cut_length_mm,'');
 const p=Object.fromEntries(edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'}}));
 assert.equal(p['\u7ba1\u5f84'],'DN200');assert.equal(p['\u697c\u5c42\u4f4d\u7f6e'],'1F');
});
test('lower suffix floor reversal missing vertical points or repeated physical claims fail',()=>{
 for(const change of [
  (e,r)=>{r.segment_indices=[1]},(e,r)=>{r.mapping_kind='named_riser_floor_segment_approach'},
  (e,r)=>{e.floor_end=1},(e,r)=>{e.axis_riser_attributes[0].floor_pair=[2,3]},
  (e,r)=>{e.axis_riser_attributes[0].scope_points[0][0]+=1},(e,r)=>{e.axis_riser_attributes.push(structuredClone(e.axis_riser_attributes[0]))},
  (e,r)=>{r.whole_edge_nominal_mm=200},(e,r)=>{r.horizontal_projection.installed_whole_edge_length_mm=10},
  (e,r)=>{r.scope='unknown'},(e,r)=>{r.diameter_evidence.lineage=[]},(e,r)=>{r.human_accepted=true},
 ]){const e=fixture();change(e,e.plan_segment_attributes[0]);assert.equal(checkedPlanSegments(e),null);assert.deepEqual(planSegmentCsvValues(e),{});}
});

function networkFixture(){
 const e=fixture(),r=e.plan_segment_attributes[0],v=e.axis_riser_attributes[0];
 v.edge_id=e.edge_id;v.source_line_handle='native-vertical';
 r.scope='native_network_named_lower_floor_prefix_only';r.mapping_kind='network_anchored_named_lower_floor_approach';
 r.independent_adjoining_main_mapping_id='MAIN';r.retained_vertical_scope=structuredClone(v);
 r.whole_edge_physical_length_mm=null;r.related_HIL_confirmation_inherited=false;
 for(const k of ['equipment_anchor','plan_equipment_T','axis_equipment_T'])delete r[k];
 delete e.plan_segment_attributes;e.network_named_lower_plan_attributes=r;return e;
}
test('network-named prefix uses whole-network main evidence without inventing equipment anchors',()=>{
 const e=networkFixture(),before=structuredClone(e);
 assert.equal(checkedPlanSegments(e).length,1);assert.deepEqual(e,before);
 const csv=crossViewAttributeCsvValues(e);assert.equal(csv.plan_segment_nominal_mm,200);
 assert.equal(csv.plan_segment_projection_mm,10);assert.equal(csv.diameter_nominal_mm,'');
 assert.match(JSON.stringify(edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'}})),/MAIN/);
 assert.equal(e.axis_riser_attributes[0].nominal_mm,450);
});
test('network prefix rejects overlapping writers and changed vertical or network evidence',()=>{
 for(const change of [
  (e,r)=>{e.plan_segment_attributes=[structuredClone(r)]},(e,r)=>{r.independent_adjoining_main_mapping_id=''},
  (e,r)=>{r.retained_vertical_scope.source_line_handle='changed'},(e,r)=>{r.retained_vertical_scope.scope_points[0][0]+=1},
  (e,r)=>{r.related_HIL_confirmation_inherited=true},(e,r)=>{r.whole_edge_physical_length_mm=10},
  (e,r)=>{r.mapping_kind='named_riser_lower_floor_segment_approach'},
 ]){const e=networkFixture();change(e,e.network_named_lower_plan_attributes);assert.equal(checkedPlanSegments(e),null);assert.deepEqual(planSegmentCsvValues(e),{});}
});
