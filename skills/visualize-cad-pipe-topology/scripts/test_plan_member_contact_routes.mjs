import assert from'node:assert/strict';
import{checkedPlanMemberContact,planMemberContactCsvValues}from'../assets/viewer/public/plan-member-contact-routes.js';
const h='a'.repeat(64),e={edge_id:'E1',system:'supply',floor_start:2,floor_end:2,start_node_id:'A',end_node_id:'B',attribute_paths:[[[0,0],[1,2]]]};
const r={axis_edge_id:'E1',kind:'member_to_ordinary_external_route',system:'supply',floor:2,axis_nodes:['A','B'],axis_attribute_paths:e.attribute_paths,member_node_id:'MEMBER:x',plan_remote:'T1',member_axis_node:'A',axis_remote:'B',original_source_Z_preserved:true,axis_component_reader_3D_unchanged:true,plan_component_reading_mode:'qualified_member_floor_plan_XY_contact_reading_v1',whole_edge_DN_mm:null,whole_edge_physical_length_mm:null,physical_values_assigned:0,attribute_adoption_allowed:false,human_accepted:false,native_T:{plan:{graph_sha256:h},axis:{graph_sha256:h}},mapping_id:'M1',plan_source_edge_id:'P1'};
const c={plan_member_contact_routes:{mode:'qualified_plan_member_contact_viewer_v1',source_bindings:{plan_graph:h,native_axis_graph:h},records:[r],count:1,physical_values_assigned:0,axis_3D_reader_unchanged:true,human_accepted:false}};
assert.equal(checkedPlanMemberContact(e,c),r);assert.equal(planMemberContactCsvValues(e,c).plan_member_contact_mapping_id,'M1');
for(const patch of [{system:'return'},{start_node_id:'C'},{floor_end:3},{attribute_paths:[[[0,0],[9,9]]]}])assert.equal(checkedPlanMemberContact({...e,...patch},c),null);
for(const patch of [{whole_edge_physical_length_mm:0},{whole_edge_DN_mm:200},{original_source_Z_preserved:false},{axis_component_reader_3D_unchanged:false},{plan_remote:'MEMBER:other'},{human_accepted:true},{native_T:{plan:{graph_sha256:'b'.repeat(64)},axis:{graph_sha256:h}}}]){
 const changed=structuredClone(c);Object.assign(changed.plan_member_contact_routes.records[0],patch);assert.equal(checkedPlanMemberContact(e,changed),null);
}
assert.deepEqual(planMemberContactCsvValues({...e,edge_id:'E2'},c),{});
console.log('Exact native member scope, separate systems, raw-Z and unknown-metric controls passed');
