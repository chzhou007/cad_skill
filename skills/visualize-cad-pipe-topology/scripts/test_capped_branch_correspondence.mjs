import assert from 'node:assert/strict';
import {checkedCappedBranch,cappedBranchCsvValues,cappedBranchProperties} from '../assets/viewer/public/capped-branch-correspondence.js';
const h='a'.repeat(64),edge={edge_id:'E',system:'supply',floor_start:3,floor_end:3,start_node_id:'T',end_node_id:'V',end_port_id:'V-S',attribute_paths:[[[0,0],[1,0],[1,1]]]};
const record={axis_edge_id:'E',plan_edge_id:'P',mapping_id:'CAP',floor:3,system:'supply',native_checks:{iso:{snapshot:{edges:[structuredClone(edge)]}}},scope:'native_capped_third_arm_drawing_correspondence_only',other_system_port_assigned:false,remote_equipment_identity_assigned:false,whole_axis_DN_selected:false,whole_axis_physical_length_mm:null,vertical_values_assigned:0,human_accepted:false,plan_cap:{node_id:'U',system:'supply',qualifier:{text:'盲板封堵'},caption:{text:'预留支管接口/共2处',declared_group_quantity:2}},axis_cap:{qualifier_text:'盲板封堵',declared_quantity:2},axis_cap_port:{system:'supply',edge_id:'E',port_id:'V-S'},axis_drawing_port:{port_id:'V-S'}};
const root={mode:'qualified_native_capped_branch_drawing_context_v1',records:[record],count:1,graph_mutated:false,other_system_ports_assigned:0,remote_equipment_identities_assigned:0,physical_lengths_assigned:0,whole_axis_DN_assigned:0,vertical_values_assigned:0,human_accepted:false,source_bindings:{raw_axis_graph:h,attribute_context_graph:h,native_axis_graph:h,native_proof:h}};
const context={source_graph_sha256:h,current_rendered_graph_sha256:h,capped_branch_correspondence:root};
assert.equal(checkedCappedBranch(edge,context).mapping_id,'CAP');assert.equal(Object.keys(cappedBranchCsvValues(edge,context)).length,6);assert.ok(cappedBranchProperties(edge,context,true).some(([k])=>k==='封堵标注'));
assert.ok(!Object.keys(cappedBranchCsvValues(edge,context)).some(k=>k==='diameter_nominal_mm'||k==='physical_length_mm'));
for(const mutate of [c=>c.capped_branch_correspondence.physical_lengths_assigned=1,c=>c.capped_branch_correspondence.records[0].axis_cap_port.system='return',c=>c.capped_branch_correspondence.records[0].axis_cap.declared_quantity=4,c=>c.capped_branch_correspondence.records[0].axis_cap_port.port_id='V-R',c=>c.capped_branch_correspondence.records[0].native_checks.iso.snapshot.edges[0].attribute_paths=[],c=>c.capped_branch_correspondence.records.push(structuredClone(record)),c=>c.source_graph_sha256='b'.repeat(64)]){
 const bad=structuredClone(context);mutate(bad);assert.equal(checkedCappedBranch(edge,bad),null);assert.deepEqual(cappedBranchCsvValues(edge,bad),{});
}
assert.equal(checkedCappedBranch({...edge,system:'return'},context),null);
assert.equal(checkedCappedBranch({...edge,floor_start:2},context),null);
console.log('Capped context source/port/system/quantity/geometry guards and no physical scalar writer passed');
