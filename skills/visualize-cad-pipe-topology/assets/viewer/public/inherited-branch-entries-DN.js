const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
const positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0;
export const inheritedEntryDNFields=['inherited_entry_DN_scope_id','inherited_entry_DN_T','inherited_entry_DN_domains_json','inherited_entry_DN_plan_source_sha256','inherited_entry_DN_native_proof_sha256','inherited_entry_DN_whole_physical_complete','inherited_entry_vertical_DN_segments_json','inherited_entry_vertical_DN_axis_source_sha256','inherited_entry_vertical_DN_native_proof_sha256'];
export function checkedInheritedEntryDN(edge,context=null,old={}){
 const root=context?.inherited_branch_attribute_entries,b=root?.source_bindings;
 if(root?.mode!=='qualified_inherited_branch_attribute_entries_current_viewer_v1'||root.complete_original_native_replay!==true||root.all_previous_source_branch_payloads_exact!==true||root.graph_mutated!==false||root.components_changed!==false||root.physical_lengths_assigned!==0||root.individual_device_mappings_assigned!==0||root.human_accepted!==false||!b||!Object.values(b).every(hash)||b.attribute_context_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.count)return null;
 const r=root.records.find(x=>x.axis_edge_id===edge.edge_id);if(!r)return null;
 if(!['branch','partial_main'].includes(r.kind)||r.system!==edge.system||r.floor!==edge.floor_start||r.floor!==edge.floor_end||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||!positive(r.nominal_mm)||r.plan_source_sha256!==b.plan_source||r.axis_source_sha256!==b.native_axis_source||r.axis_labels_validation_only!==true||r.individual_device_correspondence_assigned!==false||r.physical_length_mm!==null||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||typeof r.whole_physical_DN_complete!=='boolean'||!Array.isArray(r.horizontal_segment_domains)||!r.horizontal_segment_domains.length||!Array.isArray(r.retained_vertical_domains)||!Array.isArray(r.new_axis11_vertical_domains)||!Array.isArray(r.excluded_other_direction_domains)||!r.source_scope_id)return null;
 const all=new Set(edge.attribute_paths.flatMap((p,pi)=>p.slice(1).map((_,si)=>`${pi}:${si}`))),seen=new Set();
 const domain=s=>{const k=`${s.path_index}:${s.segment_index}`;return all.has(k)&&!seen.has(k)&&s.edge_id===edge.edge_id&&s.system===edge.system&&same(edge.attribute_paths[s.path_index]?.slice(s.segment_index,s.segment_index+2),s.scope_points)?k:null;};
 if(r.kind==='branch'){
  const display=`0:${r.excluded_marker_display_segment}`;
  if(edge.attribute_paths.length!==1||!all.has(display)||!r.axis_T||!Array.isArray(r.main_arms)||r.main_arms.length!==2||new Set(r.main_arms).size!==2||r.excluded_other_direction_domains.length)return null;
  all.delete(display);
 }else if(r.whole_physical_DN_complete||r.excluded_marker_display_segment!==null||r.axis_T!==null||r.retained_vertical_domains.length||r.new_axis11_vertical_domains.length||!r.excluded_other_direction_domains.length)return null;
 for(const s of r.horizontal_segment_domains){const k=domain(s);if(!k||s.direction_class!=='horizontal'||s.native_source_status!=='single_source_line_covers')return null;seen.add(k);}
 let prior;try{prior=JSON.parse(old.axis_rule_vertical_DN_segments_json||'[]');}catch{return null;}if(!Array.isArray(prior))return null;
 for(const s of r.retained_vertical_domains){const k=domain(s),matches=prior.filter(v=>v.edge_id===edge.edge_id&&v.path_index===s.path_index&&v.segment_index===s.segment_index);
  if(!k||s.source_field!=='axis_rule_vertical_DN_segments_json'||s.new_vertical_value_assigned!==false||s.nominal_mm!==r.nominal_mm||s.axis_source_sha256!==b.native_axis_source||matches.length!==1)return null;
  const v=matches[0];if(v.nominal_mm!==s.nominal_mm||v.system!==s.system||v.axis_source_sha256!==s.axis_source_sha256||v.human_accepted!==false||!same(v.scope_points,s.scope_points))return null;seen.add(k);
 }
 for(const s of r.new_axis11_vertical_domains){const k=domain(s),n=s.semantic_source_normalization;
  if(!k||s.direction_class!=='vertical'||s.nominal_mm!==r.nominal_mm||s.axis_source_sha256!==b.native_axis_source||s.native_proof_sha256!==b.native_proof||s.source!=='axis11_original_native_caption_T_and_replayed_normalization'||s.source_field!=='inherited_entry_vertical_DN_segments_json'||s.new_vertical_value_assigned!==true||s.raw_source_coverage_not_promoted!==true||s.physical_length_mm!==null||s.human_accepted!==false||!n||n.source_hash!==b.native_axis_source||n.graph_hash!==b.native_axis_graph||n.edge_id!==edge.edge_id||n.raw_source_coverage_unchanged!==true||n.raw_source_graph_route_items_unchanged!==true||n.private_schema_not_raw_LINE_evidence!==true||n.physical_gap_length_mm!==null||n.physical_lengths_assigned!==0)return null;seen.add(k);
 }
 for(const s of r.excluded_other_direction_domains){const k=domain(s);if(!k||!['vertical','undetermined'].includes(s.direction_class)||s.new_DN_assigned!==null||s.physical_length_mm!==null)return null;seen.add(k);}
 if(r.kind==='partial_main'&&seen.size!==all.size||r.whole_physical_DN_complete&&seen.size!==all.size)return null;
 if(positive(old.diameter_nominal_mm)&&old.diameter_nominal_mm!==r.nominal_mm)return null;
 return r;
}
export function inheritedEntryDNCsvValues(edge,context,old){const r=checkedInheritedEntryDN(edge,context,old);if(!r)return {};
 return {inherited_entry_DN_scope_id:r.source_scope_id,inherited_entry_DN_T:r.axis_T,inherited_entry_DN_domains_json:JSON.stringify(r),inherited_entry_DN_plan_source_sha256:r.plan_source_sha256,inherited_entry_DN_native_proof_sha256:context.inherited_branch_attribute_entries.source_bindings.native_proof,inherited_entry_DN_whole_physical_complete:r.whole_physical_DN_complete,
 ...(r.new_axis11_vertical_domains.length?{inherited_entry_vertical_DN_segments_json:JSON.stringify(r.new_axis11_vertical_domains),inherited_entry_vertical_DN_axis_source_sha256:r.axis_source_sha256,inherited_entry_vertical_DN_native_proof_sha256:context.inherited_branch_attribute_entries.source_bindings.native_proof}:{})};
}
export function inheritedEntryDNProperties(edge,zh,context,old){const r=checkedInheritedEntryDN(edge,context,old);if(!r)return [];
 return [[zh?(r.kind==='branch'?'\u7ba1\u5f84\uff08\u65e2\u6709\u8fde\u63a5\u89c4\u5219\u7ee7\u627f\uff09':'\u6c34\u5e73\u533a\u6bb5\u7ba1\u5f84'):'Inherited source-domain DN',`DN${r.nominal_mm}`],
 [zh?'\u6c34\u5e73\u7ba1\u5f84\u6765\u6e90':'Horizontal DN source',r.source_scope_id+(r.axis_T?` \u2192 ${r.main_arms.join(' / ')} \u2192 ${r.axis_T}`:'')],
 [zh?'\u7ad6\u6bb5\u7ba1\u5f84\u6765\u6e90':'Vertical DN source',r.new_axis11_vertical_domains.length?(zh?'11\u56fe\u539f\u751f\u7ba1\u5f84\u4e0e\u8fde\u63a5\u8bc1\u636e\uff0c\u72ec\u7acb\u4e8e\u5e73\u9762\u56fe':'Independent drawing11 source DN and connectivity'):(r.kind==='partial_main'?(zh?'\u5176\u4ed6\u65b9\u5411\u533a\u6bb5\u4fdd\u6301\u539f\u72b6\uff0c\u4e0d\u586b\u6574\u8fb9\u7ba1\u5f84':'Other direction domains retained; no whole-edge DN'):(zh?'\u4fdd\u755911\u56fe\u65e2\u6709\u7ad6\u6bb5\u8bc1\u636e':'Retained drawing11 vertical evidence'))],
 [zh?'\u957f\u5ea6\u4e0e\u8bbe\u5907\u5bf9\u5e94':'Length and equipment correspondence',zh?'\u672c\u6b21\u672a\u586b\u957f\u5ea6\u6216\u65b0\u589e\u4e2a\u4f53\u5bf9\u5e94\uff1b\u5f52\u4e00\u5316\u65ad\u53e3\u7684\u7269\u7406\u957f\u5ea6\u4ecd\u672a\u77e5':'No lengths or individual mappings assigned; normalized physical gap length remains unknown']];
}
