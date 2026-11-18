const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
const rules=new Set(['original_nested_straddling_pair_geometry','original_nested_pair_and_omission_continuity']);
export function checkedNestedPairAxisVerticalDN(edge,context=null){
 const root=context?.nested_pair_axis_vertical_DN,b=root?.source_bindings;
 if(root?.mode!=='qualified_nested_pair_axis_vertical_DN_context_v1'||root.human_accepted!==false||root.raw_graph_changed!==false||root.physical_lengths_assigned!==0||root.whole_edge_DN_assigned!==0||!b)return [];
 if(![b.native_source,b.native_graph,b.native_proof,b.rendered_graph].every(hash)||b.rendered_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>`${r.edge_id}:${r.path_index}:${r.segment_index}`)).size!==root.count)return [];
 const rows=root.records.filter(r=>r.edge_id===edge.edge_id);
 if(rows.some(r=>r.system!==edge.system||!Number.isFinite(r.nominal_mm)||r.nominal_mm<=0||r.axis_source_sha256!==b.native_source||!Number.isInteger(r.path_index)||!Number.isInteger(r.segment_index)||!same(edge.attribute_paths?.[r.path_index]?.slice(r.segment_index,r.segment_index+2),r.scope_points)||Math.abs(r.scope_points[0][0]-r.scope_points[1][0])>.05||!Array.isArray(r.seed_text_handles)||!r.seed_text_handles.length||!Array.isArray(r.source_rules)||!r.source_rules.length||r.source_rules.some(v=>!rules.has(v))||!Array.isArray(r.seed_domains)||!r.seed_domains.length||r.seed_domains.some(s=>s.system!==r.system||s.nominal_mm!==r.nominal_mm)||!Array.isArray(r.source_chains)||!r.source_chains.length||r.source_chains.some(c=>!Array.isArray(c)||c.length!==2||c.some(v=>typeof v!=='string'||!v))||r.physical_length_mm!==null||r.whole_edge_DN_assigned!==false||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false))return [];
 return rows;
}
export function nestedPairAxisVerticalDNProperties(edge,zh=true,context=null){
 const rows=checkedNestedPairAxisVerticalDN(edge,context),out=[];
 for(const r of rows){
  out.push([zh?`\u7ad6\u76f4\u6bb5\u7ba1\u5f84\uff0811\u56fe\u6210\u5bf9\u6807\u6ce8 ${r.path_index}:${r.segment_index}\uff09`:`Vertical DN from axis caption pair ${r.path_index}:${r.segment_index}`,`DN${r.nominal_mm}`]);
  out.push([zh?'\u539f\u6807\u6ce8\u4e0e\u6e90\u5757\uff0f\u5b50\u7ebf':'Native caption and root/child',`SH16 11 / ${r.seed_text_handles.join('; ')} / ${r.source_chains.map(c=>c.join('/')).join('; ')}`]);
  out.push([zh?'\u7ba1\u5f84\u8bfb\u53d6\u4f9d\u636e':'Native DN evidence',r.source_rules.includes('original_nested_pair_and_omission_continuity')?(zh?'\u6210\u5bf9\u6807\u6ce8\uff0b\u539f\u7701\u7565\u7b26\u4e24\u4fa7\u8fde\u7eed':'Native pair and omission continuity'):(zh?'\u539f\u751f\u4e24\u7ba1\u5939\u6301\u5f0f\u6210\u5bf9\u6807\u6ce8':'Native straddling caption geometry')]);
 }
 if(rows.length)out.push([zh?'\u7ad6\u76f4\u6bb5\u7269\u7406\u957f\u5ea6':'Vertical physical length',zh?'\u672a\u77e5\uff1b\u4ec5\u91c7\u752811\u56fe\u660e\u786e\u5bf9\u5e94\u7ad6\u6bb5\u7684\u957f\u5ea6\u4f9d\u636e\uff0c\u7701\u7565\u957f\u5ea6\u4e0d\u8865\u503c':'Unknown; explicit vertical length evidence from drawing11 required']);
 return out;
}
export const nestedPairAxisVerticalDNCsvFields=['axis_nested_pair_vertical_DN_segment_count','axis_nested_pair_vertical_DN_segments_json','axis_nested_pair_vertical_DN_source_sha256'];
export function nestedPairAxisVerticalDNCsvValues(edge,context=null){const rows=checkedNestedPairAxisVerticalDN(edge,context);return rows.length?{axis_nested_pair_vertical_DN_segment_count:rows.length,axis_nested_pair_vertical_DN_segments_json:JSON.stringify(rows),axis_nested_pair_vertical_DN_source_sha256:context.nested_pair_axis_vertical_DN.source_bindings.native_source}:{};}
