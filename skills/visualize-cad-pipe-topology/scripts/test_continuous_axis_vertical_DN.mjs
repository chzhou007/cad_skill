import assert from 'node:assert/strict';
import {checkedContinuousAxisVerticalDN,continuousAxisVerticalDNProperties,continuousAxisVerticalDNCsvValues,continuousAxisVerticalDNCsvFields} from '../assets/viewer/public/continuous-axis-vertical-DN.js';
import {edgeAttributeCsvFields as fields} from '../assets/viewer/public/edge-attributes-continuous-axis.js';
import {edgeAttributeCsvFields as old} from '../assets/viewer/public/edge-attributes-omission-vertical.js';
assert.deepEqual(fields.slice(0,-3),old);assert.deepEqual(fields.slice(-3),continuousAxisVerticalDNCsvFields);
const h='a'.repeat(64),e={edge_id:'E',system:'supply',attribute_paths:[[[0,0],[0,10]]]};
const r={edge_id:'E',path_index:0,segment_index:0,scope_points:[[0,0],[0,10]],system:'supply',nominal_mm:300,axis_source_sha256:h,seed_domains:[{edge_id:'MAIN',path_index:0,segment_index:0,system:'supply',nominal_mm:300}],seed_text_handles:['DN01'],source_rules:['same_original_LINE_through_T_and_native_two_arm_bends'],through_T_nodes:['T1'],branch_seed_used_for_main:false,physical_length_mm:null,whole_edge_DN_assigned:false,related_HIL_confirmation_inherited:false,human_accepted:false};
const c={current_rendered_graph_sha256:h,continuous_axis_vertical_DN:{mode:'qualified_continuous_axis_vertical_DN_context_v1',records:[r],count:1,raw_graph_changed:false,physical_lengths_assigned:0,whole_edge_DN_assigned:0,human_accepted:false,source_bindings:{native_source:h,native_graph:h,native_proof:h,rendered_graph:h}}};
assert.equal(checkedContinuousAxisVerticalDN(e,c).length,1);
assert.equal(continuousAxisVerticalDNCsvValues(e,c).axis_continuous_vertical_DN_segment_count,1);
assert(continuousAxisVerticalDNProperties(e,true,c).some(p=>p[0].includes('管径')&&p[1]==='DN300'));
for(const mutate of [x=>x.records[0].system='return',x=>x.records[0].seed_domains[0].nominal_mm=200,x=>x.records[0].branch_seed_used_for_main=true,x=>x.records[0].through_T_nodes=[],x=>x.records[0].through_T_nodes=null,x=>x.records[0].physical_length_mm=0,x=>x.records[0].human_accepted=true,x=>x.records[0].scope_points[0][0]=1,x=>x.source_bindings.rendered_graph='b'.repeat(64),x=>{x.records.push(structuredClone(x.records[0]));x.count=2;}]){
 const copy=structuredClone(c);mutate(copy.continuous_axis_vertical_DN);assert.deepEqual(checkedContinuousAxisVerticalDN(e,copy),[]);assert.deepEqual(continuousAxisVerticalDNCsvValues(e,copy),{});
}
console.log('Continuous axis DN UI/export positive and ten source/invalidation controls passed');
