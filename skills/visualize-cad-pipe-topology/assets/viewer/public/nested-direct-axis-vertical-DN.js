const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
const rules=new Set(['original_direct_reader_complete_nested_WCS_projection','original_nested_direct_DN_and_two_arm_bends','original_nested_direct_DN_and_omission_pair']);
export function checkedNestedDirectAxisVerticalDN(edge,context=null){
 const root=context?.nested_direct_axis_vertical_DN,b=root?.source_bindings;
 if(root?.mode!=='qualified_nested_direct_axis_vertical_DN_context_v1'||root.human_accepted!==false||root.raw_graph_changed!==false||root.physical_lengths_assigned!==0||root.whole_edge_DN_assigned!==0||!b)return [];
 if(![b.native_source,b.native_graph,b.native_proof,b.rendered_graph].every(hash)||b.rendered_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>`${r.edge_id}:${r.path_index}:${r.segment_index}`)).size!==root.count)return [];
 const rows=root.records.filter(r=>r.edge_id===edge.edge_id);
 if(rows.some(r=>r.system!==edge.system||!Number.isFinite(r.nominal_mm)||r.nominal_mm<=0||r.axis_source_sha256!==b.native_source||!Number.isInteger(r.path_index)||!Number.isInteger(r.segment_index)||!same(edge.attribute_paths?.[r.path_index]?.slice(r.segment_index,r.segment_index+2),r.scope_points)||Math.abs(r.scope_points[0][0]-r.scope_points[1][0])>.05||!Array.isArray(r.seed_text_handles)||!r.seed_text_handles.length||!Array.isArray(r.source_rules)||!r.source_rules.length||r.source_rules.some(v=>!rules.has(v))||!Array.isArray(r.seed_domains)||!r.seed_domains.length||r.seed_domains.some(s=>s.system!==r.system||s.nominal_mm!==r.nominal_mm)||!Array.isArray(r.source_chains)||!r.source_chains.length||r.source_chains.some(c=>!Array.isArray(c)||c.length!==2||c.some(v=>typeof v!=='string'||!v))||r.physical_length_mm!==null||r.whole_edge_DN_assigned!==false||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false))return [];
 return rows;
}
export function nestedDirectAxisVerticalDNProperties(edge,zh=true,context=null){
 const rows=checkedNestedDirectAxisVerticalDN(edge,context),out=[];
 for(const r of rows){
  out.push([zh?`\u7ad6\u76f4\u6bb5\u7ba1\u5f84\uff0811\u56fe\u76f4\u63a5\u6807\u6ce8 ${r.path_index}:${r.segment_index}\uff09`:`Vertical DN from axis direct caption ${r.path_index}:${r.segment_index}`,`DN${r.nominal_mm}`]);
  out.push([zh?'\u539f\u6807\u6ce8\u4e0e\u6e90\u5757\uff0f\u5b50\u7ebf':'Native caption and root/child',`SH16 11 / ${r.seed_text_handles.join('; ')} / ${r.source_chains.map(c=>c.join('/')).join('; ')}`]);
  const direct=r.source_rules.includes('original_direct_reader_complete_nested_WCS_projection'),omission=r.source_rules.includes('original_nested_direct_DN_and_omission_pair');
  out.push([zh?'\u7ba1\u5f84\u8bfb\u53d6\u4f9d\u636e':'Native DN evidence',direct?(zh?'\u5b8c\u6574\u539f\u751f\u7ba1\u7ebf\u7ade\u4e89\u4e0b\u7684\u76f4\u63a5\u6807\u6ce8':'Direct caption with complete native pipe competition'):omission?(zh?'\u76f4\u63a5\u6807\u6ce8\uff0b\u539f\u7701\u7565\u7b26\u4e24\u4fa7\u8fde\u7eed':'Direct caption and original omission continuity'):(zh?'\u76f4\u63a5\u6807\u6ce8\uff0b\u539f\u4e24\u81c2\u5f2f\u5934\u8fde\u7eed':'Direct caption and original two-arm bends')]);
 }
 if(rows.length)out.push([zh?'\u7ad6\u76f4\u6bb5\u7269\u7406\u957f\u5ea6':'Vertical physical length',zh?'\u672a\u77e5\uff1b\u4ec5\u91c7\u752811\u56fe\u660e\u786e\u5bf9\u5e94\u7ad6\u6bb5\u7684\u957f\u5ea6\u4f9d\u636e\uff0c\u4e0d\u4ece\u6c34\u5e73\u6807\u6ce8\u63a8\u7b97':'Unknown; explicit drawing11 vertical length evidence required, no horizontal-label inference']);
 return out;
}
export const nestedDirectAxisVerticalDNCsvFields=['axis_nested_direct_vertical_DN_segment_count','axis_nested_direct_vertical_DN_segments_json','axis_nested_direct_vertical_DN_source_sha256'];
export function nestedDirectAxisVerticalDNCsvValues(edge,context=null){const rows=checkedNestedDirectAxisVerticalDN(edge,context);return rows.length?{axis_nested_direct_vertical_DN_segment_count:rows.length,axis_nested_direct_vertical_DN_segments_json:JSON.stringify(rows),axis_nested_direct_vertical_DN_source_sha256:context.nested_direct_axis_vertical_DN.source_bindings.native_source}:{};}
