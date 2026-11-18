const hash=/^[0-9a-f]{64}$/,same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0;
export function checkedReviewedRingDN(edge,context){
 const root=context?.reviewed_ring_partition_DN,b=root?.source_bindings;
 if(root?.mode!=='qualified_reviewed_ring_partition_DN_v1'||root.source_graphs_mutated!==false||root.new_correspondences_assigned!==0||root.physical_lengths_assigned!==0||root.vertical_values_assigned!==0||root.human_accepted!==false||!b||!Object.values(b).every(v=>hash.test(v||''))||b.rendered_graph!==context.current_rendered_graph_sha256||b.raw_axis_graph!==context.source_graph_sha256)return null;
 if(!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.count)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r)return null;
 if(r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||r.system!==edge.system||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||!positive(r.nominal_mm)||r.plan_DN_record?.nominal_mm!==r.nominal_mm||r.plan_DN_record?.system!==r.system||r.plan_DN_record?.edge_id!==r.plan_edge_id||r.DN_used_for_mapping!==false||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||r.physical_length_mm!==null||r.installed_whole_edge_length_mm!==null||r.vertical_DN_assigned!==false||r.per_axis_horizontal_subsegment_allocation_inferred!==false)return null;
 if(r.graph_sha256?.plan!==b.plan_graph||r.graph_sha256?.iso!==b.native_axis_graph||r.source_sha256?.plan!==b.plan_source||r.source_sha256?.iso!==b.axis_source||r.current_mapping?.floor!==r.floor||r.current_mapping?.system!==r.system||!same(r.current_mapping?.plan_edges,[r.plan_edge_id])||!same(r.current_mapping?.iso_edges,[edge.edge_id]))return null;
 if(r.classification==='horizontal_only'){
  if(r.whole_axis_nominal_mm!==r.nominal_mm||r.mixed_plan_value_scope!==null)return null;
 }else if(r.classification==='mixed_horizontal_vertical'){
  if(r.whole_axis_nominal_mm!==null||r.current_mapping?.kind!=='equipment_branch'||r.mixed_plan_value_scope!=='corresponding_drawn_plan_branch_not_individual_axis_horizontal_subsegments')return null;
 }else return null;
 return r;
}
export function reviewedRingDNProperties(edge,prior,zh,context){
 const r=checkedReviewedRingDN(edge,context);if(!r)return prior;
 const whole=r.whole_axis_nominal_mm!==null,label=(a,b)=>zh?a:b;
 const obsolete=new Set(['Current plan DN','Current DN conflict','DN source','\u672c\u8f6e\u5e73\u9762\u7ba1\u5f84','\u5f53\u524d\u7ba1\u5f84\u51b2\u7a81','\u7ba1\u5f84\u6765\u6e90']);
 if(whole)for(const key of ['Diameter','\u7ba1\u5f84'])obsolete.add(key);
 const rows=prior.filter(([k])=>!obsolete.has(k));
 rows.unshift([label('\u672c\u8f6e\u5e73\u9762\u7ba1\u5f84','Current plan DN'),`DN${r.nominal_mm} [${r.floor}F / ${String(r.floor+7).padStart(2,'0')}]`]);
 if(whole)rows.unshift([label('\u7ba1\u5f84','Diameter'),`DN${r.nominal_mm}`]);
 rows.push(
 [label('\u7ba1\u5f84\u5206\u533a\u6765\u6e90','DN partition evidence'),`${String(r.floor+7).padStart(2,'0')} / ${r.plan_edge_id}; ${r.mapping_id}`],
 [label('\u7ba1\u5f84\u7ee7\u627f\u4f9d\u636e','DN inheritance evidence'),label('\u4e13\u5bb6\u786e\u8ba4\u4e3b\u7ba1\u5206\u533a\uff1b\u539f\u751f\u4e09\u901a\u3001\u6e90\u7ebf\u548c\u5df2\u6709\u6620\u5c04\u5df2\u590d\u6838\uff1b\u5386\u53f2\u51b2\u7a81\u8bc1\u636e\u4fdd\u7559','Expert-confirmed main partition; native Ts, LINEs and existing mapping rechecked; historical conflicts retained')]);
 if(!whole)rows.push([label('\u5e73\u9762\u652f\u8def\u53d6\u503c\u8303\u56f4','Plan branch value extent'),label('\u4ec5\u5bf9\u5e94\u5e73\u9762\u5df2\u7ed8\u652f\u8def\uff1b\u672a\u9010\u6bb5\u5206\u914d\u8f74\u6d4b\u6c34\u5e73\u5b50\u6bb5\uff0c\u7ad6\u6bb5\u4ecd\u53d611\u56fe\uff0c\u6574\u8fb9\u7ba1\u5f84\u672a\u77e5','Corresponding drawn plan branch only; individual axis horizontal subsegments remain unallocated; vertical values still use drawing 11; whole DN unknown')]);
 return rows;
}
export const reviewedRingDNCsvFields=['reviewed_partition_mapping_id','reviewed_partition_plan_edge','reviewed_partition_plan_nominal_mm','reviewed_partition_whole_axis_nominal_mm','reviewed_partition_source_sha256','reviewed_partition_evidence_json'];
export function reviewedRingDNCsvValues(edge,context){
 const r=checkedReviewedRingDN(edge,context);if(!r)return {};
 const result={reviewed_partition_mapping_id:r.mapping_id,reviewed_partition_plan_edge:r.plan_edge_id,reviewed_partition_plan_nominal_mm:r.nominal_mm,reviewed_partition_whole_axis_nominal_mm:r.whole_axis_nominal_mm??'',reviewed_partition_source_sha256:r.source_sha256.plan,reviewed_partition_evidence_json:JSON.stringify(r),diameter_status:r.whole_axis_nominal_mm===null?'reviewed_plan_branch_DN_whole_axis_unknown':'expert_reviewed_whole_horizontal_main_partition_DN'};
 if(r.whole_axis_nominal_mm!==null)Object.assign(result,{diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`});
 return result;
}
