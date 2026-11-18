const hash=/^[0-9a-f]{64}$/;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function checkedCurrentPlanScope(edge){
 const c=edge.cross_view_attributes,s=c?.current_plan_scope_evidence;
 if(!s||c.human_accepted!==false||s.human_accepted!==false||s.related_HIL_confirmation_inherited!==false||s.equal_plan_axis_segment_extents_proved!==false||s.edge_id!==edge.edge_id||s.system!==edge.system||s.floor!==c.floor||!same(s.plan_edges,c.plan_edges)||!same(s.iso_edges,c.iso_edges))return null;
 if(![s.plan_graph_sha256,s.iso_graph_sha256,s.mapping_sha256,s.attribute_scope_sha256,s.comparison_sha256,s.source_sha256?.plan,s.source_sha256?.iso].every(v=>hash.test(v||'')))return null;
 if(s.source_sha256.plan!==c.source_hashes?.plan||s.source_sha256.iso!==c.source_hashes?.isometric||s.iso_graph_sha256!==c.source_hashes?.local_iso_graph||c.mapping_id!==(s.historical_mapping_id??s.current_mapping_id))return null;
 if(!Number.isFinite(s.diameter?.nominal_mm)||s.diameter.nominal_mm<=0||s.diameter.nominal_mm!==c.diameter?.plan_drawn_nominal_mm||!Number.isFinite(s.horizontal_projection?.value_mm)||!Number.isFinite(c.horizontal_projection?.value_mm)||s.horizontal_projection.value_mm<=0||Math.abs(s.horizontal_projection.value_mm-c.horizontal_projection.value_mm)>1e-8)return null;
 const domains=s.native_axis_annotation_domains;if(!Array.isArray(domains)||new Set(domains.map(r=>r.text_handle)).size!==domains.length)return null;
 const proofs=(s.DN_extent_comparison?.axis_native_observations||[]).filter(r=>r.current_edge_id===edge.edge_id);
 if(!same([...domains.map(r=>r.text_handle)].sort(),[...proofs.map(r=>r.source_text?.handle)].sort()))return null;
 for(const d of domains){
  const seg=d.segment,points=edge.attribute_paths?.[seg?.path_index]?.slice(seg?.segment_index,seg?.segment_index+2);
  const native=proofs.find(p=>p.source_text?.handle===d.text_handle);if(!native||native.nominal_mm_candidate!==d.nominal_mm||!same(native.source_chain,d.source_chain))return null;
  if(d.edge_id!==edge.edge_id||d.source_sha256!==s.source_sha256.iso||d.graph_sha256!==s.iso_graph_sha256||d.human_accepted!==false||d.physical_vertical_length_mm!==null||d.inter_floor_riser_proved!==false||d.equal_plan_axis_segment_extents_proved!==false||!Number.isFinite(d.nominal_mm)||d.nominal_mm<=0||!Array.isArray(d.source_chain)||d.source_chain.length!==2||!Number.isInteger(seg?.path_index)||!Number.isInteger(seg?.segment_index)||seg.path_index<0||seg.segment_index<0||!same(points,d.segment.scope_points)||!['vertical_stroke_in_CAD_WCS','horizontal_stroke_in_CAD_WCS','oblique_stroke_in_CAD_WCS'].includes(seg.drawing_direction))return null;
 }
 return s;
}
export function currentPlanScopeProperties(edge,zh=true){
 const s=checkedCurrentPlanScope(edge);if(!s)return [];
 const rows=[[zh?'\u5f53\u524d\u5e73\u9762\u56de\u8bc1':'Current plan verification',s.current_mapping_id]];
 if(s.historical_mapping_id)rows.push([zh?'\u4fdd\u7559\u7684\u5386\u53f2\u5bf9\u5e94':'Retained historical mapping',s.historical_mapping_id]);
 if(s.native_axis_annotation_domains.length){
  rows.push([zh?'\u8f74\u6d4b\u5c40\u90e8\u539f\u56fe\u6807\u6ce8':'Local axis source annotations',s.native_axis_annotation_domains.map(d=>`DN${d.nominal_mm} [11:${d.text_handle}]`).join('; ')],
   [zh?'\u6807\u6ce8\u6240\u5728\u753b\u6bb5':'Annotation drawing segments',s.native_axis_annotation_domains.map(d=>`${d.floor_start??'?'}F -> ${d.floor_end??'?'}F; path ${d.segment.path_index}, segment ${d.segment.segment_index}; ${d.source_chain.join(' / ')}`).join('; ')],
   [zh?'\u7ba1\u6bb5\u8303\u56f4':'Segment extents',zh?'\u5e73\u9762\u5df2\u7ed8\u7247\u6bb5\u4e0e\u8f74\u6d4b\u5c40\u90e8\u6807\u6ce8\u5206\u522b\u4fdd\u7559\uff1b\u5c1a\u672a\u8bc1\u660e\u8303\u56f4\u76f8\u540c':'Plan fragments and local axis labels retained separately; equal extents unproved'],
   [zh?'\u8de8\u5c42\u7acb\u7ba1\u5224\u5b9a':'Inter-floor riser evidence',zh?'\u8be5\u753b\u6bb5\u8bc1\u636e\u672a\u8bc1\u660e\u8de8\u5c42\u7acb\u7ba1\uff1b\u672a\u7528\u4e8e\u63a8\u7b97\u5b9e\u9645\u957f\u5ea6':'This drawing-segment evidence does not establish an inter-floor riser or actual length']);
 }
 return rows;
}
export const currentPlanScopeCsvFields=['current_plan_mapping_id','historical_plan_mapping_id','current_plan_graph_sha256','current_plan_attribute_scope_sha256','current_plan_DN_comparison_sha256','axis_local_DN_annotation_domains_json'];
export function currentPlanScopeCsvValues(edge){
 const s=checkedCurrentPlanScope(edge);if(!s)return {};
 return {current_plan_mapping_id:s.current_mapping_id,historical_plan_mapping_id:s.historical_mapping_id??'',current_plan_graph_sha256:s.plan_graph_sha256,current_plan_attribute_scope_sha256:s.attribute_scope_sha256,current_plan_DN_comparison_sha256:s.comparison_sha256,axis_local_DN_annotation_domains_json:JSON.stringify(s.native_axis_annotation_domains)};
}
