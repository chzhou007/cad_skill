const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
const rules=new Set(['same_original_attribute_path_and_two_arm_bends','same_original_LINE_through_T_and_native_two_arm_bends']);
export function checkedContinuousAxisVerticalDN(edge,context=null){
 const root=context?.continuous_axis_vertical_DN,b=root?.source_bindings;
 if(root?.mode!=='qualified_continuous_axis_vertical_DN_context_v1'||root.human_accepted!==false||root.raw_graph_changed!==false||root.physical_lengths_assigned!==0||root.whole_edge_DN_assigned!==0||!b)return [];
 if(![b.native_source,b.native_graph,b.native_proof,b.rendered_graph].every(hash)||b.rendered_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>`${r.edge_id}:${r.path_index}:${r.segment_index}`)).size!==root.count)return [];
 const rows=root.records.filter(r=>r.edge_id===edge.edge_id);
 if(rows.some(r=>r.system!==edge.system||!Number.isFinite(r.nominal_mm)||r.nominal_mm<=0||r.axis_source_sha256!==b.native_source||!Number.isInteger(r.path_index)||!Number.isInteger(r.segment_index)||!same(edge.attribute_paths?.[r.path_index]?.slice(r.segment_index,r.segment_index+2),r.scope_points)||Math.abs(r.scope_points[0][0]-r.scope_points[1][0])>.05||!Array.isArray(r.seed_text_handles)||!r.seed_text_handles.length||!Array.isArray(r.source_rules)||!r.source_rules.length||r.source_rules.some(v=>!rules.has(v))||!Array.isArray(r.seed_domains)||!r.seed_domains.length||r.seed_domains.some(s=>s.system!==r.system||s.nominal_mm!==r.nominal_mm)||!Array.isArray(r.through_T_nodes)||r.source_rules.includes('same_original_LINE_through_T_and_native_two_arm_bends')&&!r.through_T_nodes.length||r.branch_seed_used_for_main!==false||r.physical_length_mm!==null||r.whole_edge_DN_assigned!==false||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false))return [];
 return rows;
}
export function continuousAxisVerticalDNProperties(edge,zh=true,context=null){
 const rows=checkedContinuousAxisVerticalDN(edge,context),out=[];
 for(const r of rows){
  out.push([zh?`\u7ad6\u76f4\u6bb5\u7ba1\u5f84\uff0811\u56fe\u8fde\u7eed\u7ba1\u8def ${r.path_index}:${r.segment_index}\uff09`:`Vertical DN from axis continuity ${r.path_index}:${r.segment_index}`,`DN${r.nominal_mm}`]);
  out.push([zh?'\u539f\u6807\u6ce8\u4e0e\u7ee7\u627f\u8303\u56f4':'Native annotation and scope',`SH16 11 / ${r.seed_text_handles.join('; ')} / ${r.path_index}:${r.segment_index}`]);
  out.push([zh?'\u4e09\u901a\u4e0e\u5f2f\u5934\u4f9d\u636e':'Through-T and bend evidence',r.through_T_nodes.length?r.through_T_nodes.join('; '):(zh?'\u539f\u7ba1\u8def\u5185\u4e24\u81c2\u5f2f\u5934\u8fde\u7eed':'Native two-arm bend continuity')]);
 }
 if(rows.length)out.push([zh?'\u7ad6\u76f4\u6bb5\u7269\u7406\u957f\u5ea6':'Vertical physical length',zh?'\u672a\u77e5\uff1b\u7b49\u5f8511\u56fe\u7aef\u70b9\u6807\u9ad8\u6216\u5c3a\u5bf8\u8bc1\u636e':'Unknown; axis endpoint level or dimension evidence required']);
 return out;
}
export const continuousAxisVerticalDNCsvFields=['axis_continuous_vertical_DN_segment_count','axis_continuous_vertical_DN_segments_json','axis_continuous_vertical_DN_source_sha256'];
export function continuousAxisVerticalDNCsvValues(edge,context=null){const rows=checkedContinuousAxisVerticalDN(edge,context);return rows.length?{axis_continuous_vertical_DN_segment_count:rows.length,axis_continuous_vertical_DN_segments_json:JSON.stringify(rows),axis_continuous_vertical_DN_source_sha256:context.continuous_axis_vertical_DN.source_bindings.native_source}:{};}
