const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
export function checkedOmissionVerticalDN(edge,context=null){
 const root=context?.omission_vertical_DN,b=root?.source_bindings;
 if(root?.mode!=='qualified_native_omission_vertical_DN_context_v1'||root.human_accepted!==false||root.raw_graph_changed!==false||root.physical_lengths_assigned!==0||root.whole_edge_DN_assigned!==0||!b)return [];
 if(![b.native_source,b.native_graph,b.native_proof,b.rendered_graph].every(hash)||b.rendered_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>`${r.edge_id}:${r.path_index}:${r.segment_index}`)).size!==root.count)return [];
 const rows=root.records.filter(r=>r.edge_id===edge.edge_id);
 if(rows.some(r=>r.system!==edge.system||!Number.isFinite(r.nominal_mm)||r.nominal_mm<=0||r.axis_source_sha256!==b.native_source||!Number.isInteger(r.path_index)||!Number.isInteger(r.segment_index)||!same(edge.attribute_paths?.[r.path_index]?.slice(r.segment_index,r.segment_index+2),r.scope_points)||Math.abs(r.scope_points[0][0]-r.scope_points[1][0])>.05||r.seed_domain?.edge_id!==r.edge_id||r.seed_domain.path_index===r.path_index||r.seed_domain.nominal_mm!==r.nominal_mm||!r.seed_text_handles?.length||r.physical_length_mm!==null||r.whole_edge_DN_assigned!==false||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false||r.omission?.source!=='original_native_omission_pair_replayed'||r.omission.physical_T_crossed!==false||r.omission.inline_joint_crossed!==false||r.omission.physical_length_mm!==null||r.omission.marker_chains?.length!==2||same(r.omission.marker_chains[0],r.omission.marker_chains[1])))return [];
 return rows;
}
export function omissionVerticalDNProperties(edge,zh=true,context=null){
 const rows=checkedOmissionVerticalDN(edge,context),out=[];
 for(const r of rows){
  out.push([zh?`\u7ad6\u76f4\u6bb5\u7ba1\u5f84\uff08\u7701\u7565\u4e24\u4fa7\u7ee7\u627f ${r.path_index}:${r.segment_index}\uff09`:`Vertical DN across omission ${r.path_index}:${r.segment_index}`,`DN${r.nominal_mm}`]);
  out.push([zh?'\u7ba1\u5f84\u6e90\u56fe\u4e0e\u7ee7\u627f\u4f9d\u636e':'Native DN evidence',`SH16 11 / ${r.seed_text_handles.join('; ')} / ${r.seed_domain.path_index}:${r.seed_domain.segment_index} \u2192 ${r.path_index}:${r.segment_index}`]);
 }
 if(rows.length)out.push([zh?'\u7701\u7565\u6bb5\u53ca\u7ad6\u76f4\u6bb5\u7269\u7406\u957f\u5ea6':'Omitted and vertical physical lengths',zh?'\u672a\u77e5\uff1b\u7701\u7565\u7b26\u4ec5\u8bc1\u660e\u8fde\u63a5':'Unknown; omission proves connectivity only']);
 return out;
}
export const omissionVerticalDNCsvFields=['axis_omission_vertical_DN_segment_count','axis_omission_vertical_DN_segments_json','axis_omission_vertical_DN_source_sha256'];
export function omissionVerticalDNCsvValues(edge,context=null){
 const rows=checkedOmissionVerticalDN(edge,context);
 return rows.length?{axis_omission_vertical_DN_segment_count:rows.length,axis_omission_vertical_DN_segments_json:JSON.stringify(rows),axis_omission_vertical_DN_source_sha256:context.omission_vertical_DN.source_bindings.native_source}:{};
}
