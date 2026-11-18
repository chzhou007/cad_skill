import test from 'node:test';
import assert from 'node:assert/strict';
import {checkedPlanSegments,planSegmentProperties,planSegmentCsvValues,planSegmentCsvFields} from '../assets/viewer/public/upper-floor-plan-segments.js';
import {edgeAttributeProperties,crossViewAttributeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';

function fixture(whole=false){
 const edge={edge_id:'A',system:'supply',floor_start:whole?3:2,floor_end:3,attribute_paths:whole?[[[0,0],[2,2],[4,2]]]:[[[0,0],[0,10],[3,10]]]};
 if(!whole)edge.axis_riser_attributes=[{path_index:0,segment_index:0,nominal_mm:450}];
 const r={mapping_id:'M',mapping_kind:'named_riser_floor_segment_'+(whole?'network_link':'approach'),floor:3,system:'supply',edge_id:'A',path_index:0,
  segment_indices:whole?[0,1]:[1],scope_points:whole?[[0,0],[2,2],[4,2]]:[[0,10],[3,10]],scope:'native_plan_matched_upper_floor_axis_segments_only',
  whole_local_edge:whole,plan_edges:['P'],identifier:'CHWS1',equipment_anchor:'D',plan_riser_interface:'R',plan_network_T:'PT',axis_network_T:'AT',plan_equipment_T:'PE',axis_equipment_T:'AE',
  nominal_mm:whole?250:300,whole_edge_nominal_mm:whole?250:null,whole_edge_centerline_route_mm:whole?10:null,
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
test('partial horizontal DN and measured plan path remain separate from vertical450 and whole values',()=>{
 const e=fixture(),before=structuredClone(e);assert.equal(checkedPlanSegments(e).length,1);
 const p=planSegmentProperties(e);assert.match(JSON.stringify(p),/DN300/);assert.ok(p.length>=8);assert.deepEqual(e,before);
 const csv=planSegmentCsvValues(e);assert.equal(csv.plan_segment_nominal_mm,300);assert.equal(csv.plan_segment_projection_mm,10);
 assert.equal(csv.plan_segment_whole_main_nominal_mm,'');assert.equal(csv.plan_segment_whole_main_centerline_mm,'');assert.equal(csv.plan_segment_net_cut_length_mm,'');
 assert.equal(e.axis_riser_attributes[0].nominal_mm,450);
});
test('complete bent horizontal main exports250 and one source route total',()=>{
 const e=fixture(true),r=planSegmentCsvValues(e);assert.equal(r.plan_segment_whole_main_nominal_mm,250);
 assert.equal(r.plan_segment_whole_main_centerline_mm,10);assert.equal(r.plan_segment_net_cut_length_mm,'');
 assert.equal(planSegmentProperties(e,false).find(([k])=>k==='Plan source path length')[1],'0.0100 m (10.0 mm)');
});
test('stale geometry scope system lineage hashes metrics or physical claims cannot display checked values',()=>{
 for(const mutate of [
  (e,r)=>{e.attribute_paths[0][2][0]+=1},(e,r)=>{r.system='return'},(e,r)=>{r.source_scope_sha256='bad'},
  (e,r)=>{r.segment_indices=[0]},(e,r)=>{r.whole_edge_nominal_mm=300},(e,r)=>{r.whole_edge_centerline_route_mm=10},
  (e,r)=>{r.horizontal_projection.value_mm=0},(e,r)=>{r.horizontal_projection.value_mm=11},(e,r)=>{r.diameter_evidence.lineage=[]},
  (e,r)=>{r.horizontal_projection.pieces[0].path_index=9},(e,r)=>{r.horizontal_projection.installed_whole_edge_length_mm=10},
  (e,r)=>{r.physical_port_verified=true},(e,r)=>{r.human_accepted=true},(e,r)=>{e.axis_riser_attributes[0].segment_index=1},
  (e,r)=>{r.plan_riser_interface=''},(e,r)=>{r.identifier='CHWR1'},
 ]){
  const e=fixture();mutate(e,e.plan_segment_attributes[0]);assert.equal(checkedPlanSegments(e),null);assert.deepEqual(planSegmentProperties(e),[]);assert.deepEqual(planSegmentCsvValues(e),{});
 }
 const old={edge_id:'OLD',attribute_paths:[[[0,0],[1,1]]]};assert.deepEqual(planSegmentCsvValues(old),{});
});
test('actual property and CSV entry points show scoped values and append fields without a whole mixed DN',()=>{
 const data={display:{edge_attribute_language:'zh-CN'}},partial=fixture(),main=fixture(true);
 const p=Object.fromEntries(edgeAttributeProperties(partial,data)),m=Object.fromEntries(edgeAttributeProperties(main,data));
 assert.equal(m['\u7ba1\u5f84'],'DN250');assert.equal(m['\u697c\u5c42\u4f4d\u7f6e'],'3F');
 assert.match(JSON.stringify(p),/DN300/);assert.notEqual(p['\u7ba1\u5f84'],'DN300');
 const pc=crossViewAttributeCsvValues(partial),mc=crossViewAttributeCsvValues(main);
 assert.equal(pc.diameter_nominal_mm,'');assert.equal(mc.diameter_nominal_mm,250);assert.equal(mc.plan_segment_whole_main_centerline_mm,10);
 assert.equal(edgeAttributeCsvFields.length,new Set(edgeAttributeCsvFields).size);
 const retainedStart=edgeAttributeCsvFields.indexOf(planSegmentCsvFields[0]);
 assert.ok(retainedStart>=0);
 assert.deepEqual(edgeAttributeCsvFields.slice(retainedStart,retainedStart+planSegmentCsvFields.length),planSegmentCsvFields);
 assert.deepEqual(edgeAttributeProperties({edge_id:'OLD'},data),[]);assert.deepEqual(crossViewAttributeCsvValues({edge_id:'OLD'}),{});
});
