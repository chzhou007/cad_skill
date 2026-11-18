import assert from 'node:assert/strict';
import {checkedAxisRuleVerticalDN,axisRuleVerticalDNProperties,axisRuleVerticalDNCsvValues,axisRuleVerticalDNCsvFields} from '../assets/viewer/public/axis-rule-vertical-DN.js';
import {edgeAttributeCsvFields as fields} from '../assets/viewer/public/edge-attributes-axis-rule.js';
import {edgeAttributeCsvFields as old} from '../assets/viewer/public/edge-attributes-nested-direct-axis.js';
assert.deepEqual(fields.slice(0,-3),old);assert.deepEqual(fields.slice(-3),axisRuleVerticalDNCsvFields);
const h='a'.repeat(64),e={edge_id:'E',system:'supply',attribute_paths:[[[0,0],[0,10]]]};
const r={edge_id:'E',path_index:0,segment_index:0,scope_points:[[0,0],[0,10]],system:'supply',nominal_mm:300,axis_source_sha256:h,seed_domains:[{edge_id:'MAIN',path_index:0,segment_index:2,system:'supply',nominal_mm:300}],seed_text_handles:['DN01'],source_rules:['original_native_main_T_and_unlabelled_branch_continuity'],main_line_handles:['LINE'],root_T_nodes:['T1'],whole_branch_annotation_barriers_checked:true,physical_length_mm:null,whole_edge_DN_assigned:false,related_HIL_confirmation_inherited:false,human_accepted:false};
const c={current_rendered_graph_sha256:h,axis_rule_vertical_DN:{mode:'qualified_axis_rule_vertical_DN_context_v1',records:[r],count:1,raw_graph_changed:false,physical_lengths_assigned:0,whole_edge_DN_assigned:0,human_accepted:false,source_bindings:{native_source:h,native_graph:h,native_proof:h,rendered_graph:h}}};
assert.equal(checkedAxisRuleVerticalDN(e,c).length,1);assert.equal(axisRuleVerticalDNCsvValues(e,c).axis_rule_vertical_DN_segment_count,1);assert(axisRuleVerticalDNProperties(e,true,c).some(p=>p[0].includes('\u4e09\u901a')&&p[1]==='DN300'));
assert(axisRuleVerticalDNProperties(e,true,c).some(p=>p[1].includes('\u6574\u6761\u652f\u8def')));
for(const mutate of [x=>x.records[0].system='return',x=>x.records[0].seed_domains[0].nominal_mm=200,x=>x.records[0].main_line_handles=[],x=>x.records[0].root_T_nodes=[],x=>x.records[0].whole_branch_annotation_barriers_checked=false,x=>x.records[0].physical_length_mm=0,x=>x.records[0].human_accepted=true,x=>x.records[0].scope_points[0][0]=1,x=>x.source_bindings.rendered_graph='b'.repeat(64),x=>{x.records.push(structuredClone(x.records[0]));x.count=2;},x=>x.records[0].source_rules=['unproved_same_edge'],x=>x.records[0].related_HIL_confirmation_inherited=true]){
 const copy=structuredClone(c);mutate(copy.axis_rule_vertical_DN);assert.deepEqual(checkedAxisRuleVerticalDN(e,copy),[]);assert.deepEqual(axisRuleVerticalDNCsvValues(e,copy),{});
}
console.log('Native main/T DN UI, whole-branch guards, old CSV prefix and invalidation passed');
