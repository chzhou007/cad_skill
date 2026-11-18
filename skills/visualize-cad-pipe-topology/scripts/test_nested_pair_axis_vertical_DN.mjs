import assert from 'node:assert/strict';
import {checkedNestedPairAxisVerticalDN,nestedPairAxisVerticalDNProperties,nestedPairAxisVerticalDNCsvValues,nestedPairAxisVerticalDNCsvFields} from '../assets/viewer/public/nested-pair-axis-vertical-DN.js';
import {edgeAttributeCsvFields as fields} from '../assets/viewer/public/edge-attributes-nested-pair-axis.js';
import {edgeAttributeCsvFields as old} from '../assets/viewer/public/edge-attributes-continuous-axis.js';
assert.deepEqual(fields.slice(0,-3),old);assert.deepEqual(fields.slice(-3),nestedPairAxisVerticalDNCsvFields);
const h='a'.repeat(64),e={edge_id:'E',system:'supply',attribute_paths:[[[0,0],[0,10]]]};
const r={edge_id:'E',path_index:0,segment_index:0,scope_points:[[0,0],[0,10]],system:'supply',nominal_mm:300,axis_source_sha256:h,seed_domains:[{edge_id:'MAIN',path_index:0,segment_index:0,system:'supply',nominal_mm:300}],seed_text_handles:['DN01'],source_rules:['original_nested_pair_and_omission_continuity'],source_chains:[['ROOT','CHILD']],physical_length_mm:null,whole_edge_DN_assigned:false,related_HIL_confirmation_inherited:false,human_accepted:false};
const c={current_rendered_graph_sha256:h,nested_pair_axis_vertical_DN:{mode:'qualified_nested_pair_axis_vertical_DN_context_v1',records:[r],count:1,raw_graph_changed:false,physical_lengths_assigned:0,whole_edge_DN_assigned:0,human_accepted:false,source_bindings:{native_source:h,native_graph:h,native_proof:h,rendered_graph:h}}};
assert.equal(checkedNestedPairAxisVerticalDN(e,c).length,1);
assert.equal(nestedPairAxisVerticalDNCsvValues(e,c).axis_nested_pair_vertical_DN_segment_count,1);
assert(nestedPairAxisVerticalDNProperties(e,true,c).some(p=>p[0].includes('管径')&&p[1]==='DN300'));
for(const mutate of [x=>x.records[0].system='return',x=>x.records[0].seed_domains[0].nominal_mm=200,x=>x.records[0].source_chains=[],x=>x.records[0].source_chains=[['ROOT']],x=>x.records[0].source_chains=null,x=>x.records[0].physical_length_mm=0,x=>x.records[0].human_accepted=true,x=>x.records[0].scope_points[0][0]=1,x=>x.source_bindings.rendered_graph='b'.repeat(64),x=>{x.records.push(structuredClone(x.records[0]));x.count=2;}]){
 const copy=structuredClone(c);mutate(copy.nested_pair_axis_vertical_DN);assert.deepEqual(checkedNestedPairAxisVerticalDN(e,copy),[]);assert.deepEqual(nestedPairAxisVerticalDNCsvValues(e,copy),{});
}
console.log('Continuous axis DN UI/export positive and ten source/invalidation controls passed');
