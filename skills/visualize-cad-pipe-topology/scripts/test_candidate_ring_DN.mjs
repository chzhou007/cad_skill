import assert from 'node:assert/strict';
import {checkedCandidateRingDN,candidateRingDNCsvValues,candidateRingDNProperties} from '../assets/viewer/public/reviewed-candidate-ring-DN.js';
import {crossViewAttributeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes-candidate-ring.js';
import {edgeAttributeCsvFields as priorFields} from '../assets/viewer/public/edge-attributes-effective-provider.js';
const h='a'.repeat(64),edge={edge_id:'A',system:'return',floor_start:3,floor_end:3,start_node_id:'T1',end_node_id:'T2',attribute_paths:[[[0,0],[10,0]]]};
const row={axis_edge_id:'A',plan_edge_id:'P',mapping_id:'M',floor:3,system:'return',axis_nodes:['T1','T2'],axis_attribute_paths:edge.attribute_paths,
 classification:'horizontal_only',nominal_mm:250,whole_axis_nominal_mm:250,mixed_plan_value_scope:null,
 plan_DN_record:{edge_id:'P',system:'return',nominal_mm:250},current_mapping:{floor:3,system:'return',plan_edges:['P'],iso_edges:['A'],kind:'native_endpoint_bounded_existing_interval'},
 source_sha256:{plan:h,iso:h},graph_sha256:{plan:h,iso:h},DN_used_for_mapping:false,human_accepted:false,related_HIL_confirmation_inherited:false,
 physical_length_mm:null,installed_whole_edge_length_mm:null,vertical_DN_assigned:false,per_axis_horizontal_subsegment_allocation_inferred:false};
const root={mode:'qualified_reviewed_candidate_ring_partition_DN_v1',source_graphs_mutated:false,new_correspondences_assigned:0,
 physical_lengths_assigned:0,vertical_values_assigned:0,human_accepted:false,count:1,records:[row],source_bindings:{raw_axis_graph:h,rendered_graph:h,
 native_axis_graph:h,plan_graph:h,plan_source:h,axis_source:h,native_crossview_proof:h,native_partition_proof:h}};
const context={source_graph_sha256:h,current_rendered_graph_sha256:h,reviewed_candidate_ring_partition_DN:root};
assert.equal(checkedCandidateRingDN(edge,context),row);
assert.equal(crossViewAttributeCsvValues(edge,context).diameter_nominal_mm,250);
assert.equal(candidateRingDNCsvValues(edge,context).candidate_ring_partition_plan_nominal_mm,250);
assert.ok(!Object.keys(candidateRingDNCsvValues(edge,context)).some(k=>k.startsWith('reviewed_partition_')));
assert.deepEqual(edgeAttributeCsvFields.slice(0,priorFields.length),priorFields);assert.equal(edgeAttributeCsvFields.length,priorFields.length+6);
assert.equal(new Set(edgeAttributeCsvFields).size,edgeAttributeCsvFields.length);
const props=candidateRingDNProperties(edge,[['Current DN conflict','old'],['Length','5.0 m']],true,context);
assert.equal(props[0][1],'DN250');assert.ok(props.some(([k,v])=>k==='Length'&&v==='5.0 m'));
for(const mutate of [c=>c.reviewed_candidate_ring_partition_DN.records[0].floor=2,c=>c.reviewed_candidate_ring_partition_DN.records[0].system='supply',
 c=>c.reviewed_candidate_ring_partition_DN.records[0].vertical_DN_assigned=true,c=>c.reviewed_candidate_ring_partition_DN.records[0].physical_length_mm=5,
 c=>c.reviewed_candidate_ring_partition_DN.records[0].graph_sha256.plan='b'.repeat(64)]){
 const bad=structuredClone(context);mutate(bad);assert.equal(checkedCandidateRingDN(edge,bad),null);assert.deepEqual(candidateRingDNCsvValues(edge,bad),{});
}
const known=structuredClone(context);known.reviewed_ring_partition_DN={...structuredClone(root),mode:'qualified_reviewed_ring_partition_DN_v1'};
Object.assign(known.reviewed_ring_partition_DN.records[0],{nominal_mm:300,whole_axis_nominal_mm:300});known.reviewed_ring_partition_DN.records[0].plan_DN_record.nominal_mm=300;
assert.equal(crossViewAttributeCsvValues(edge,known).diameter_nominal_mm,300);
assert.equal(crossViewAttributeCsvValues(edge,known).candidate_ring_partition_mapping_id,undefined);
console.log('Candidate ring source, original guard, old DN/CSV prefix, length and vertical boundaries passed');
