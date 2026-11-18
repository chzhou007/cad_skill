import assert from 'node:assert/strict';
import {checkedNoncompoundMainExtent,noncompoundMainExtentCsvValues} from '../assets/viewer/public/full-batch-plan-attributes.js';
import {crossViewAttributeCsvValues,edgeAttributeProperties} from '../assets/viewer/public/edge-attributes.js';
const h='a'.repeat(64),paths=[[[0,0],[1000,0]]];
const edge={edge_id:'E',system:'supply',start_node_id:'A',end_node_id:'B',floor_start:3,floor_end:3,attribute_paths:paths};
edge.batch_plan_attribute_scopes={system:'supply',floor:3,mapping_id:'M',kind:'same_floor_T_to_T_main',iso_edges:['E'],plan_edges:['PE'],source_sha256:{plan:h,iso:h},graph_sha256:{plan:h,iso:h},mapping_receipt_sha256:h,plan_DN_receipt_sha256:h,human_accepted:false,related_HIL_confirmation_inherited:false,whole_installed_length_mm:null,plan_DN_records:[{edge_id:'PE',system:'supply',human_accepted:false,scope_paths:paths,nominal_mm:250,lineage:[{evidence:[{evidence_id:'source:DN250'}]}]}],plan_drawn_nominal_mm:250,group_scope_not_allocated_to_child_edges:false,whole_axis_nominal_mm:null,complete_horizontal_centerline_route_mm:null,horizontal_projection:null};
const row={axis_edge_id:'E',plan_edge_id:'PE',mapping_id:'M',floor:3,system:'supply',nominal_mm:250,axis_start_node:'A',axis_end_node:'B',axis_attribute_paths:paths,complete_horizontal_centerline_route_mm:1000,whole_installed_length_mm:null,net_pipe_cut_length_mm:null,human_accepted:false,related_HIL_confirmation_inherited:false,source_paths_mutated:false,source_hashes:{plan:{source_sha256:h,graph_sha256:h},iso:{source_sha256:h,graph_sha256:h}},source_projection:{value_mm:1000,installed_whole_edge_length_mm:null,pieces:[{length_mm:1000}]},endpoint_relations:Object.fromEntries(['plan','iso'].map(k=>[k,{path_orientation:k==='plan'?'end_to_start':'start_to_end',source_path_unchanged:true,flow_direction_inferred:false}]))};
const context={source_graph_sha256:h,rendered_graph_sha256:h,compound_member_mains:{source_bindings:{native_proof:h},records:[]},noncompound_main_extents:{mode:'qualified_native_noncompound_main_extents_v1',records:[row],axis_edges:1,source_bindings:{axis_graph:h,rendered_graph:h,native_proof:h,member_proof:h},existing_attribute_owners_preserved:true,compound_carriers_excluded:true,source_paths_mutated:false,local_topology_changed:false,installed_lengths_assigned:0,human_accepted:false}};
assert.equal(checkedNoncompoundMainExtent(edge,context),row);
assert.equal(noncompoundMainExtentCsvValues(edge,context).batch_complete_horizontal_centerline_mm,1000);
const before=crossViewAttributeCsvValues(edge,null),after=crossViewAttributeCsvValues(edge,context);
assert.equal(after.diameter_nominal_mm,before.diameter_nominal_mm);
assert.equal(after.batch_complete_horizontal_centerline_mm,1000);
assert.ok(edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'},attribute_value_context:context}).some(r=>r[1]==='1.000 m'));
for(const mutate of [r=>r.nominal_mm=300,r=>r.axis_end_node='OTHER',r=>r.whole_installed_length_mm=0,r=>r.source_projection.pieces[0].length_mm=900,r=>r.endpoint_relations.plan.flow_direction_inferred=true]){
 const bad=structuredClone(context);mutate(bad.noncompound_main_extents.records[0]);assert.equal(checkedNoncompoundMainExtent(edge,bad),null);
 const rejected=crossViewAttributeCsvValues(edge,bad);assert.equal(rejected.diameter_nominal_mm,before.diameter_nominal_mm);assert.equal(rejected.batch_complete_horizontal_centerline_mm,'');
}
const overlap=structuredClone(context);overlap.ordered_anchor_branches={records:[{axis_edge_id:'E'}]};assert.equal(checkedNoncompoundMainExtent(edge,overlap),null);
assert.deepEqual(noncompoundMainExtentCsvValues({...edge,edge_id:'OTHER'},context),{});
console.log('Noncompound main lengths: orientation, native bindings, preserved DN, ownership and unknown installed lengths passed');
