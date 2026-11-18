const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=/^[0-9a-f]{64}$/;
const positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0;
export function checkedAnchoredNativeMetric(edge,context){
 const root=context?.anchored_plan_metrics,b=root?.source_bindings;
 if(root?.mode!=='qualified_anchored_native_plan_metrics_v1'||root.original_metric_readers_reused!==true||root.source_graphs_mutated!==false||root.component_owners_changed!==false||root.DN_values_assigned!==0||root.vertical_values_assigned!==0||root.installed_lengths_assigned!==0||root.human_accepted!==false||!b)return null;
 if(!Object.values(b).every(v=>hash.test(v||''))||b.rendered_graph!==context.current_rendered_graph_sha256||b.raw_axis_graph!==context.source_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.count)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r)return null;
 const extension=root.reviewed_detail_extension;
 if(r.source_detail_resolution||extension?.source_scope_ids?.includes(r.source_scope_id)){
  const d=r.source_detail_resolution;
  if(extension?.mode!=='version_bound_reviewed_plan_omission_metric_extension_v1'||!hash.test(extension.native_metric_proof_sha256||'')||!hash.test(extension.answer_receipt_sha256||'')||!Array.isArray(extension.source_scope_ids)||new Set(extension.source_scope_ids).size!==extension.count||extension.source_scope_ids.length!==extension.count||!extension.source_scope_ids.includes(r.source_scope_id)||extension.human_accepted!==false||!d||d.question_id!==extension.question_id||d.answer_receipt_sha256!==extension.answer_receipt_sha256||!hash.test(d.pair_sha256||'')||d.answer?.source_pair_sha256!==d.pair_sha256||d.answer?.decision!=='\u5e73\u9762\u7701\u7565\uff0c\u5b9e\u7269\u6309\u8f74\u6d4b\u4e24\u9600'||d.policy!=='plan_omits_axis_component_detail'||d.source_instances_retained!==true||d.crossview_components_merged!==false||d.plan_valve_positions_invented!==false||d.physical_ball_valve_count!==2||r.component_profiles?.plan?.ball_valve!==1||r.component_profiles?.iso?.ball_valve!==2)return null;
 }
 if(r.system!==edge.system||r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||!positive(r.complete_horizontal_centerline_mm)||r.projection?.value_mm!==r.complete_horizontal_centerline_mm||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||r.DN_evidence_changed!==false||r.physical_installed_length_mm!==null||r.net_pipe_cut_length_mm!==null||r.source_paths_mutated!==false||r.unknown_length_filled_with_zero!==false||r.DN_used_for_matching!==false||!hash.test(r.plan_source_sha256||''))return null;
 if(!r.projection.pieces?.length||r.projection.pieces.some(p=>!positive(p.length_mm))||Math.abs(r.projection.pieces.reduce((s,p)=>s+p.length_mm,0)-r.complete_horizontal_centerline_mm)>.0001)return null;
 if(r.original_incomplete_holds?.length){const x=r.coarse_joint_hold_exclusion;if(x?.status!=='all_original_native_joint_origins_outside_current_child_scope'||x.source_metadata_unchanged!==true||x.physical_joint_lengths_assigned!==0||x.relevant_joint_origins?.length!==0||!x.excluded_joint_origins?.length)return null;}
 return r;
}
export function anchoredNativeMetricProperties(edge,prior,zh,context){
 const r=checkedAnchoredNativeMetric(edge,context);if(!r)return prior;
 const label=(a,b)=>zh?a:b,key=label('\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\u957f\u5ea6','Complete horizontal centreline');
 const rows=prior.filter(([k])=>k!==key);
 rows.push([key,`${(r.complete_horizontal_centerline_mm/1000).toFixed(3)} m`],
 [label('\u672c\u6b21\u957f\u5ea6\u6765\u6e90','Current length evidence'),`${String(r.floor+7).padStart(2,'0')} / ${r.plan_edge_id}: ${r.projection.pieces.map(p=>p.source_line_handle).join(' / ')}`],
 [label('\u957f\u5ea6\u8303\u56f4\u6838\u9a8c','Length scope check'),label('\u4e24\u7aef\u771f\u5b9e\u4e09\u901a\u4e0e\u539f\u751f\u7ebf\u6bb5\u5df2\u6838\u5bf9\uff1b\u5b89\u88c5\u53ca\u51c0\u4e0b\u6599\u957f\u5ea6\u4ecd\u672a\u77e5','Native Ts and pipe intervals checked; installed and net cut lengths remain unknown')]);
 if(r.coarse_joint_hold_exclusion)rows.push([label('\u7236\u7ba1\u8def\u8f6f\u63a5\u6807\u8bb0\u590d\u6838','Ancestor joint hold review'),label('\u539f\u751f\u8f6f\u63a5\u63a5\u89e6\u8303\u56f4\u5747\u5728\u8be5\u5b50\u6bb5\u4e4b\u5916\uff1b\u65e7\u8bb0\u5f55\u4fdd\u7559','Original native joints lie outside this child scope; historical evidence retained')]);
 if(r.source_detail_resolution)rows.push([label('\u5143\u4ef6\u8868\u8fbe\u6838\u67e5','Component expression review'),label('\u4e13\u5bb6\u786e\u8ba4\u5e73\u9762\u7701\u7565\uff0c\u5b9e\u7269\u4fdd\u7559\u8f74\u6d4b\u4e24\u9600\uff1b\u4e24\u56fe\u539f\u59cb\u5b9e\u4f8b\u5747\u4fdd\u7559\uff0c\u7ba1\u5f84\u53e6\u884c\u6838\u5bf9','Expert confirmed plan omission; retain two axis valves and both source inventories; DN checked separately')]);
 return rows;
}
export const anchoredNativeMetricCsvFields=['anchored_metric_mapping_id','anchored_metric_plan_edge','anchored_metric_floor','anchored_metric_complete_centerline_mm','anchored_metric_plan_source_sha256','anchored_metric_evidence_json'];
export function anchoredNativeMetricCsvValues(edge,context){const r=checkedAnchoredNativeMetric(edge,context);return r?{anchored_metric_mapping_id:r.source_scope_id,anchored_metric_plan_edge:r.plan_edge_id,anchored_metric_floor:r.floor,anchored_metric_complete_centerline_mm:r.complete_horizontal_centerline_mm,anchored_metric_plan_source_sha256:r.plan_source_sha256,anchored_metric_evidence_json:JSON.stringify(r)}:{};}
