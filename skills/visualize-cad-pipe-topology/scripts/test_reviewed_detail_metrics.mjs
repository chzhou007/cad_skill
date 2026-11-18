import assert from 'node:assert/strict';
import {checkedAnchoredNativeMetric, anchoredNativeMetricCsvValues, anchoredNativeMetricProperties} from '../assets/viewer/public/anchored-native-plan-metrics.js';
const h='a'.repeat(64), decision='平面省略，实物按轴测两阀';
const edge={edge_id:'E',system:'return',floor_start:3,floor_end:3,start_node_id:'A',end_node_id:'B',attribute_paths:[[[0,0],[10,0]]]};
const row={axis_edge_id:'E',source_scope_id:'REVIEWED',system:'return',floor:3,axis_nodes:['A','B'],axis_attribute_paths:edge.attribute_paths,
complete_horizontal_centerline_mm:10,projection:{value_mm:10,pieces:[{length_mm:10,source_line_handle:'LINE'}]},
human_accepted:false,related_HIL_confirmation_inherited:false,DN_evidence_changed:false,physical_installed_length_mm:null,
net_pipe_cut_length_mm:null,source_paths_mutated:false,unknown_length_filled_with_zero:false,DN_used_for_matching:false,
plan_source_sha256:h,plan_edge_id:'P',component_profiles:{plan:{ball_valve:1},iso:{ball_valve:2}},
source_detail_resolution:{question_id:'Q',answer_receipt_sha256:h,pair_sha256:h,answer:{decision,source_pair_sha256:h},
policy:'plan_omits_axis_component_detail',source_instances_retained:true,crossview_components_merged:false,plan_valve_positions_invented:false,physical_ball_valve_count:2}};
const context={current_rendered_graph_sha256:h,source_graph_sha256:h,anchored_plan_metrics:{mode:'qualified_anchored_native_plan_metrics_v1',
original_metric_readers_reused:true,source_graphs_mutated:false,component_owners_changed:false,DN_values_assigned:0,vertical_values_assigned:0,
installed_lengths_assigned:0,human_accepted:false,source_bindings:{rendered_graph:h,raw_axis_graph:h,native_axis_graph:h,native_metric_proof:h},
records:[row],count:1,reviewed_detail_extension:{mode:'version_bound_reviewed_plan_omission_metric_extension_v1',native_metric_proof_sha256:h,
answer_receipt_sha256:h,question_id:'Q',source_scope_ids:['REVIEWED'],count:1,human_accepted:false}}};
assert.equal(checkedAnchoredNativeMetric(edge,context),row);
assert.equal(anchoredNativeMetricCsvValues(edge,context).anchored_metric_complete_centerline_mm,10);
assert.ok(anchoredNativeMetricProperties(edge,[],true,context).some(([k,v])=>k==='元件表达核查'&&v.includes('管径另行核对')));
for(const mutate of [
c=>delete c.anchored_plan_metrics.reviewed_detail_extension,
c=>c.anchored_plan_metrics.reviewed_detail_extension.question_id='OTHER',
c=>c.anchored_plan_metrics.records[0].source_detail_resolution.answer.decision='暂不确定',
c=>c.anchored_plan_metrics.records[0].source_detail_resolution.answer.source_pair_sha256='b'.repeat(64),
c=>c.anchored_plan_metrics.records[0].source_detail_resolution.crossview_components_merged=true,
c=>c.anchored_plan_metrics.records[0].source_detail_resolution.plan_valve_positions_invented=true,
c=>c.anchored_plan_metrics.records[0].component_profiles.iso.ball_valve=3,
c=>c.anchored_plan_metrics.records[0].physical_installed_length_mm=10]){
 const bad=structuredClone(context);mutate(bad);assert.equal(checkedAnchoredNativeMetric(edge,bad),null);assert.deepEqual(anchoredNativeMetricCsvValues(edge,bad),{});
}
const old=structuredClone(context);delete old.anchored_plan_metrics.reviewed_detail_extension;delete old.anchored_plan_metrics.records[0].source_detail_resolution;
assert.ok(checkedAnchoredNativeMetric(edge,old),'historical metric owner still works');
console.log('Reviewed detail binding, independent metric, unknown physical length and inherited owner checks passed');
