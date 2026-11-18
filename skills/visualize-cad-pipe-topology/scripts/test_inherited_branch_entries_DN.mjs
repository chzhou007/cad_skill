import assert from 'node:assert/strict';
import {checkedInheritedEntryDN,inheritedEntryDNCsvValues,inheritedEntryDNFields,inheritedEntryDNProperties} from '../assets/viewer/public/inherited-branch-entries-DN.js';
import {localConnectionDescription,localConnectionProperties} from '../assets/viewer/public/checked-source-connection-display.js';
const h='a'.repeat(64),g='b'.repeat(64),edge={edge_id:'E',system:'supply',floor_start:2,floor_end:2,start_node_id:'T',end_node_id:'V',attribute_paths:[[[0,0],[0,-10],[20,-30],[21,-31]]]};
const normalization={source_hash:h,graph_hash:g,edge_id:'E',raw_source_coverage_unchanged:true,raw_source_graph_route_items_unchanged:true,private_schema_not_raw_LINE_evidence:true,physical_gap_length_mm:null,physical_lengths_assigned:0};
const vertical={edge_id:'E',path_index:0,segment_index:0,scope_points:[[0,0],[0,-10]],system:'supply',direction_class:'vertical',nominal_mm:200,axis_source_sha256:h,native_proof_sha256:h,source_field:'inherited_entry_vertical_DN_segments_json',new_vertical_value_assigned:true,source:'axis11_original_native_caption_T_and_replayed_normalization',raw_source_coverage_not_promoted:true,physical_length_mm:null,human_accepted:false,semantic_source_normalization:normalization};
const row={kind:'branch',axis_edge_id:'E',axis_nodes:['T','V'],axis_attribute_paths:structuredClone(edge.attribute_paths),system:'supply',floor:2,nominal_mm:200,axis_T:'T',main_arms:['L','R'],source_scope_id:'PLAN',horizontal_segment_domains:[{edge_id:'E',system:'supply',path_index:0,segment_index:1,scope_points:[[0,-10],[20,-30]],direction_class:'horizontal',native_source_status:'single_source_line_covers'}],excluded_marker_display_segment:2,retained_vertical_domains:[],new_axis11_vertical_domains:[vertical],excluded_other_direction_domains:[],whole_physical_DN_complete:true,plan_source_sha256:h,axis_source_sha256:h,axis_labels_validation_only:true,individual_device_correspondence_assigned:false,physical_length_mm:null,related_HIL_confirmation_inherited:false,human_accepted:false};
const root={mode:'qualified_inherited_branch_attribute_entries_current_viewer_v1',records:[row],count:1,source_bindings:{native_proof:h,parent_provider:h,native_axis_graph:g,native_axis_source:h,rendered_graph:g,attribute_context_graph:g,plan_source:h,plan_graph:g},complete_original_native_replay:true,all_previous_source_branch_payloads_exact:true,graph_mutated:false,components_changed:false,new_axis11_vertical_domains:1,physical_lengths_assigned:0,individual_device_mappings_assigned:0,human_accepted:false};
const context={current_rendered_graph_sha256:g,inherited_branch_attribute_entries:root};
assert.equal(checkedInheritedEntryDN(edge,context,{}).nominal_mm,200);
assert.equal(Object.keys(inheritedEntryDNCsvValues(edge,context,{})).length,9);assert.equal(inheritedEntryDNFields.length,9);
assert.ok(inheritedEntryDNProperties(edge,true,context,{}).some(([k,v])=>k==='竖段管径来源'&&v.includes('11图')));
assert.ok(localConnectionDescription(edge,context,{},true,'raw missing').includes('个体对应和人工验收分别记录'));
assert.equal(localConnectionDescription({...edge,system:'return'},context,{},true,'raw missing'),'raw missing');
const oldRows=[['局部证据状态','old raw incomplete'],['unrelated','unchanged']];
const rewritten=localConnectionProperties(edge,context,{},true,oldRows);
assert.equal(rewritten[0][0],'原始LINE覆盖状态');assert.ok(rewritten[0][1].includes('物理长度仍未知'));assert.deepEqual(rewritten[1],oldRows[1]);
assert.deepEqual(oldRows,[['局部证据状态','old raw incomplete'],['unrelated','unchanged']]);
for(const mutate of [
 c=>c.inherited_branch_attribute_entries.records[0].new_axis11_vertical_domains=[],
 c=>c.inherited_branch_attribute_entries.records[0].new_axis11_vertical_domains[0].axis_source_sha256=g,
 c=>c.inherited_branch_attribute_entries.records[0].new_axis11_vertical_domains[0].nominal_mm=80,
 c=>c.inherited_branch_attribute_entries.records[0].new_axis11_vertical_domains[0].source_field='axis_rule_vertical_DN_segments_json',
 c=>c.inherited_branch_attribute_entries.records[0].new_axis11_vertical_domains[0].semantic_source_normalization.physical_gap_length_mm=2.35,
 c=>c.inherited_branch_attribute_entries.records[0].new_axis11_vertical_domains[0].raw_source_coverage_not_promoted=false,
 c=>c.inherited_branch_attribute_entries.records[0].horizontal_segment_domains[0].direction_class='undetermined',
 c=>c.inherited_branch_attribute_entries.records[0].horizontal_segment_domains[0].segment_index=2,
 c=>c.inherited_branch_attribute_entries.records[0].physical_length_mm=0,
 c=>c.inherited_branch_attribute_entries.records[0].related_HIL_confirmation_inherited=true,
 c=>c.inherited_branch_attribute_entries.records.push(structuredClone(row)),
 c=>c.inherited_branch_attribute_entries.source_bindings.attribute_context_graph=h,
]){const c=structuredClone(context);mutate(c);assert.equal(checkedInheritedEntryDN(edge,c,{}),null);assert.deepEqual(inheritedEntryDNCsvValues(edge,c,{}),{});}
assert.equal(checkedInheritedEntryDN(edge,context,{diameter_nominal_mm:80}),null);
assert.equal(checkedInheritedEntryDN({...edge,system:'return'},context,{}),null);
const retained=structuredClone(context),r=retained.inherited_branch_attribute_entries.records[0];
r.new_axis11_vertical_domains=[];r.retained_vertical_domains=[{...vertical,source_field:'axis_rule_vertical_DN_segments_json',new_vertical_value_assigned:false}];
assert.equal(checkedInheritedEntryDN(edge,retained,{}),null);
const old={axis_rule_vertical_DN_segments_json:JSON.stringify([{...vertical,human_accepted:false}])};
assert.equal(checkedInheritedEntryDN(edge,retained,old).whole_physical_DN_complete,true);
const legacyRow={...structuredClone(row),native_axis_source_sha256:h,new_vertical_values_assigned:0,retained_vertical_domains:[{...vertical,source_field:'axis_rule_vertical_DN_segments_json',new_vertical_value_assigned:false}]};
const legacyContext={current_rendered_graph_sha256:g,plan_seeded_axis_branch_DN:{mode:'qualified_plan_seeded_axis_branch_DN_current_viewer_v1',records:[legacyRow],count:1,source_bindings:structuredClone(root.source_bindings),complete_original_native_replay:true,graph_mutated:false,vertical_values_assigned:0,physical_lengths_assigned:0,individual_device_correspondences_assigned:0,human_accepted:false}};
assert.ok(localConnectionDescription(edge,legacyContext,old,true,'raw missing').includes('已提供源图回证'));
assert.equal(localConnectionProperties(edge,legacyContext,old,true,oldRows)[0][0],'原始LINE覆盖状态');
assert.equal(localConnectionDescription(edge,legacyContext,{},true,'raw missing'),'raw missing');
assert.equal(localConnectionDescription({...edge,system:'return'},legacyContext,old,true,'raw missing'),'raw missing');
const partial=structuredClone(context),p=partial.inherited_branch_attribute_entries.records[0];
p.kind='partial_main';p.axis_T=null;p.main_arms=[];p.excluded_marker_display_segment=null;p.whole_physical_DN_complete=false;p.new_axis11_vertical_domains=[];
p.excluded_other_direction_domains=[{edge_id:'E',system:'supply',path_index:0,segment_index:0,scope_points:[[0,0],[0,-10]],direction_class:'undetermined',new_DN_assigned:null,physical_length_mm:null},{edge_id:'E',system:'supply',path_index:0,segment_index:2,scope_points:[[20,-30],[21,-31]],direction_class:'vertical',new_DN_assigned:null,physical_length_mm:null}];
assert.equal(checkedInheritedEntryDN(edge,partial,{}).whole_physical_DN_complete,false);
assert.equal(Object.keys(inheritedEntryDNCsvValues(edge,partial,{})).length,6);
assert.equal(localConnectionDescription(edge,partial,{},true,'raw missing'),'raw missing');
for(const mutate of [c=>c.inherited_branch_attribute_entries.records[0].whole_physical_DN_complete=true,c=>c.inherited_branch_attribute_entries.records[0].excluded_other_direction_domains.pop(),c=>c.inherited_branch_attribute_entries.records[0].excluded_other_direction_domains[0].new_DN_assigned=200]){const c=structuredClone(partial);mutate(c);assert.equal(checkedInheritedEntryDN(edge,c,{}),null);}
console.log('Independent drawing11 vertical DN, retained old sources, exact physical partitions, partial main and null gap-length guards passed');
