const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
export function checkedPlanBranchDN(edge,context=null,old={}){
 const root=context?.plan_seeded_axis_branch_DN,b=root?.source_bindings;
 if(root?.mode!=='qualified_plan_seeded_axis_branch_DN_current_viewer_v1'||root.complete_original_native_replay!==true||root.graph_mutated!==false||root.vertical_values_assigned!==0||root.physical_lengths_assigned!==0||root.individual_device_correspondences_assigned!==0||root.human_accepted!==false||!b||!Object.values(b).every(hash)||b.attribute_context_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.count)return null;
 const r=root.records.find(x=>x.axis_edge_id===edge.edge_id);if(!r)return null;
 if(r.system!==edge.system||r.floor!==edge.floor_start||r.floor!==edge.floor_end||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||!(typeof r.nominal_mm==='number'&&Number.isFinite(r.nominal_mm)&&r.nominal_mm>0)||r.plan_source_sha256!==b.plan_source||r.native_axis_source_sha256!==b.native_axis_source||r.axis_labels_validation_only!==true||r.individual_device_correspondence_assigned!==false||r.new_vertical_values_assigned!==0||r.physical_length_mm!==null||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false||typeof r.whole_physical_DN_complete!=='boolean'||!Array.isArray(r.horizontal_segment_domains)||!r.horizontal_segment_domains.length||!Array.isArray(r.retained_vertical_domains)||edge.attribute_paths.length!==1)return null;
 const all=new Set(edge.attribute_paths[0].slice(1).map((_,i)=>`0:${i}`)),display=`0:${r.excluded_marker_display_segment}`,seen=new Set();
 if(!all.has(display))return null;all.delete(display);
 for(const s of r.horizontal_segment_domains){const key=`${s.path_index}:${s.segment_index}`;
  if(!all.has(key)||seen.has(key)||s.direction_class!=='horizontal'||s.native_source_status!=='single_source_line_covers'||s.edge_id!==edge.edge_id||s.system!==edge.system||!same(edge.attribute_paths[s.path_index]?.slice(s.segment_index,s.segment_index+2),s.scope_points))return null;seen.add(key);
 }
 let previous;try{previous=JSON.parse(old.axis_rule_vertical_DN_segments_json||'[]');}catch{return null;}
 if(!Array.isArray(previous))return null;
 for(const s of r.retained_vertical_domains){const key=`${s.path_index}:${s.segment_index}`,matches=previous.filter(v=>v.edge_id===edge.edge_id&&v.path_index===s.path_index&&v.segment_index===s.segment_index);
  if(!all.has(key)||seen.has(key)||s.source_field!=='axis_rule_vertical_DN_segments_json'||s.new_vertical_value_assigned!==false||s.nominal_mm!==r.nominal_mm||s.system!==edge.system||s.axis_source_sha256!==b.native_axis_source||!same(edge.attribute_paths[s.path_index]?.slice(s.segment_index,s.segment_index+2),s.scope_points)||matches.length!==1)return null;
  const v=matches[0];if(v.nominal_mm!==s.nominal_mm||v.system!==s.system||v.axis_source_sha256!==s.axis_source_sha256||v.human_accepted!==false||!same(v.scope_points,s.scope_points))return null;seen.add(key);
 }
 if(r.whole_physical_DN_complete&&seen.size!==all.size)return null;
 if(typeof old.diameter_nominal_mm==='number'&&old.diameter_nominal_mm>0&&old.diameter_nominal_mm!==r.nominal_mm)return null;
 return r;
}
export function planBranchDNProperties(edge,zh,context,old){const r=checkedPlanBranchDN(edge,context,old);if(!r)return [];
 return [[zh?'\u7ba1\u5f84\uff08\u5e73\u9762\u4e3b\u7ba1\u7ecf\u4e09\u901a\u7ee7\u627f\uff09':'DN inherited from floor-plan main',`DN${r.nominal_mm}`],
  [zh?'\u6c34\u5e73\u7ba1\u5f84\u6765\u6e90':'Horizontal DN source',`${r.source_scope_id} \u2192 ${r.main_arms.join(' / ')} \u2192 ${r.axis_T}`],
  [zh?'\u7ad6\u6bb5\u7ba1\u5f84\u6765\u6e90':'Vertical DN source',r.whole_physical_DN_complete?(zh?'\u4fdd\u755911\u56fe\u5df2\u6838\u9a8c\u7684\u7ad6\u6bb5\u7ba1\u5f84\uff1b\u5404\u7269\u7406\u533a\u6bb5\u7ba1\u5f84\u4e00\u81f4':'Retained drawing11 vertical DN; all physical domains agree'):(zh?'\u4ecd\u753111\u56fe\u72ec\u7acb\u63d0\u4f9b\uff0c\u5c1a\u672a\u8986\u76d6\u5168\u90e8\u533a\u6bb5':'Drawing11 remains independent; complete domain coverage pending')],
  [zh?'\u8bbe\u5907\u5bf9\u5e94\u4e0e\u957f\u5ea6':'Device correspondence and length',zh?'\u672c\u6b21\u672a\u5206\u914d\u8bbe\u5907\u4e2a\u4f53\u5bf9\u5e94\u6216\u8865\u586b\u957f\u5ea6':'No individual device mapping or length assigned']];
}
export const planBranchDNFields=['plan_branch_DN_scope_id','plan_branch_DN_T','plan_branch_DN_domains_json','plan_branch_DN_plan_source_sha256','plan_branch_DN_native_proof_sha256','plan_branch_DN_whole_physical_complete'];
export function planBranchDNCsvValues(edge,context,old){const r=checkedPlanBranchDN(edge,context,old);return r?{
 plan_branch_DN_scope_id:r.source_scope_id,plan_branch_DN_T:r.axis_T,plan_branch_DN_domains_json:JSON.stringify(r),
 plan_branch_DN_plan_source_sha256:r.plan_source_sha256,plan_branch_DN_native_proof_sha256:context.plan_seeded_axis_branch_DN.source_bindings.native_proof,
 plan_branch_DN_whole_physical_complete:r.whole_physical_DN_complete}:{};}
