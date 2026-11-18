import assert from 'node:assert/strict';
import {checkedReviewedRingDN,reviewedRingDNCsvValues,reviewedRingDNProperties} from '../assets/viewer/public/reviewed-ring-partition-DN.js';
import {crossViewAttributeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes-reviewed-ring.js';
import {edgeAttributeCsvFields as priorFields} from '../assets/viewer/public/edge-attributes-plan-crossover.js';
const h='a'.repeat(64),edge={edge_id:'A',system:'return',floor_start:2,floor_end:2,start_node_id:'T1',end_node_id:'T2',attribute_paths:[[[0,0],[10,10]]]};
const row={axis_edge_id:'A',plan_edge_id:'P',mapping_id:'M',floor:2,system:'return',axis_nodes:['T1','T2'],axis_attribute_paths:edge.attribute_paths,
classification:'horizontal_only',nominal_mm:300,whole_axis_nominal_mm:300,mixed_plan_value_scope:null,
plan_DN_record:{edge_id:'P',system:'return',nominal_mm:300},current_mapping:{floor:2,system:'return',plan_edges:['P'],iso_edges:['A'],kind:'native_cycle_gate_direct_interval'},
source_sha256:{plan:h,iso:h},graph_sha256:{plan:h,iso:h},DN_used_for_mapping:false,human_accepted:false,related_HIL_confirmation_inherited:false,
physical_length_mm:null,installed_whole_edge_length_mm:null,vertical_DN_assigned:false,per_axis_horizontal_subsegment_allocation_inferred:false};
const context={source_graph_sha256:h,current_rendered_graph_sha256:h,reviewed_ring_partition_DN:{mode:'qualified_reviewed_ring_partition_DN_v1',source_graphs_mutated:false,
new_correspondences_assigned:0,physical_lengths_assigned:0,vertical_values_assigned:0,human_accepted:false,count:1,records:[row],
source_bindings:{raw_axis_graph:h,rendered_graph:h,native_axis_graph:h,plan_graph:h,plan_source:h,axis_source:h,native_crossview_proof:h,native_partition_proof:h}}};
assert.equal(checkedReviewedRingDN(edge,context),row);
assert.equal(reviewedRingDNCsvValues(edge,context).diameter_nominal_mm,300);
assert.equal(crossViewAttributeCsvValues(edge,context).diameter_nominal_mm,300);
assert.deepEqual(edgeAttributeCsvFields.slice(0,priorFields.length),priorFields);
assert.equal(new Set(edgeAttributeCsvFields).size,edgeAttributeCsvFields.length);
assert.equal(edgeAttributeCsvFields.length,priorFields.length+6);
const props=reviewedRingDNProperties(edge,[['Current DN conflict','old'],['Complete centreline','10 m']],true,context);
assert.equal(props[0][1],'DN300');assert.ok(!props.some(([k])=>k==='Current DN conflict'));assert.ok(props.some(([k,v])=>k==='Complete centreline'&&v==='10 m'));
const mixed=structuredClone(context);Object.assign(mixed.reviewed_ring_partition_DN.records[0],{classification:'mixed_horizontal_vertical',whole_axis_nominal_mm:null,mixed_plan_value_scope:'corresponding_drawn_plan_branch_not_individual_axis_horizontal_subsegments'});mixed.reviewed_ring_partition_DN.records[0].current_mapping.kind='equipment_branch';
assert.ok(checkedReviewedRingDN(edge,mixed));const mv=reviewedRingDNCsvValues(edge,mixed);assert.equal(mv.reviewed_partition_plan_nominal_mm,300);assert.ok(!Object.hasOwn(mv,'diameter_nominal_mm'));assert.equal(mv.reviewed_partition_whole_axis_nominal_mm,'');
for(const mutate of [c=>c.reviewed_ring_partition_DN.records[0].floor=3,c=>c.reviewed_ring_partition_DN.records[0].system='supply',
c=>c.reviewed_ring_partition_DN.records[0].graph_sha256.plan='b'.repeat(64),c=>c.reviewed_ring_partition_DN.records[0].whole_axis_nominal_mm=200,
c=>c.reviewed_ring_partition_DN.records[0].vertical_DN_assigned=true,c=>c.reviewed_ring_partition_DN.records[0].physical_length_mm=600,
c=>c.reviewed_ring_partition_DN.records[0].per_axis_horizontal_subsegment_allocation_inferred=true]){
 const bad=structuredClone(context);mutate(bad);assert.equal(checkedReviewedRingDN(edge,bad),null);assert.deepEqual(reviewedRingDNCsvValues(edge,bad),{});
}
console.log('Reviewed ring DN source namespace, inherited facade prefix, mixed scope and old metric preservation passed');
