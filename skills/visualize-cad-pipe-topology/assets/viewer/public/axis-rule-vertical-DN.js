const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
const rule='original_native_main_T_and_unlabelled_branch_continuity';
const multiline='original_native_multiline_main_through_T_and_branch_continuity';
const typedDirect='original_direct_reader_with_typed_inline_body_evidence',typedBend='original_direct_DN_and_inherited_normalized_two_arm_bends';
const layoutDirect='original_repeated_layout_owner_for_ambiguous_caption',layoutBend='original_repeated_layout_DN_and_source_two_arm_bends';
const expandedBend='original_source_LINE_expanded_main_seed_and_two_arm_bends';
function expandedBendEvidence(r){
 if(!same(r.source_rules,[expandedBend])||r.original_caption_owner_rules_replayed!==true||r.source_LINE_scope_expansion_replayed!==true||r.native_two_arm_continuity_replayed!==true||r.same_original_path_seed!==true||r.branch_DN_used_as_main_seed!==false||r.annotation_barriers_checked!==true)return false;
 if(!Array.isArray(r.main_line_handles)||!r.main_line_handles.length||!Array.isArray(r.expanded_main_seed_owners)||!r.expanded_main_seed_owners.length||r.expanded_main_seed_owners.some(o=>!r.seed_text_handles.includes(o.text_handle)||!r.main_line_handles.includes(o.source_LINE)||o.nominal_mm!==r.nominal_mm||o.system!==r.system||o.source_LINE_scope_native_replayed!==true||!Number.isFinite(o.source_Z)||!Array.isArray(o.through_T_node_ids)))return false;
 if(!Array.isArray(r.source_chains)||r.source_chains.length<2||r.source_chains.some(p=>!Array.isArray(p)||p.length!==2||(p[0]!==null&&typeof p[0]!=='string')||typeof p[1]!=='string'||!p[1]))return false;
 if(!Array.isArray(r.two_arm_bends)||!r.two_arm_bends.length||r.two_arm_bends.some(b=>b.source_arms!==2||b.physical_T_crossed!==false||!Number.isFinite(b.source_Z)||!Array.isArray(b.point_xy)||b.point_xy.length!==2||b.point_xy.some(v=>!Number.isFinite(v))))return false;
 return r.seed_domains.every(s=>s.edge_id===r.edge_id&&s.path_index===r.path_index)&&r.expanded_main_seed_owners.every(o=>r.source_chains.some(p=>p[1]===o.source_LINE));
}
function layoutEvidence(r){
 if(!same(r.source_rules,[layoutDirect])&&!same(r.source_rules,[layoutBend]))return false;
 if(r.original_layout_reader_and_thresholds_unchanged!==true||r.target_texts_used_as_controls!==false||r.annotation_barriers_checked!==true||!Array.isArray(r.source_chains)||!r.source_chains.length||!Array.isArray(r.layout_ownership)||!r.layout_ownership.length)return false;
 if(r.layout_ownership.some(o=>!r.seed_text_handles.includes(o.text_handle)||!Array.isArray(o.source_chain)||o.source_chain.length!==2||!r.source_chains.some(p=>same(p,o.source_chain))||!Array.isArray(o.independent_control_roots)||new Set(o.independent_control_roots).size<4||o.independent_control_roots.includes(o.source_chain[0])||o.source_Z_checked!==true))return false;
 return !same(r.source_rules,[layoutBend])||r.native_two_arm_continuity_replayed===true;
}
function typedEvidence(r){
 if(!same(r.source_rules,[typedDirect])&&!same(r.source_rules,[typedBend]))return false;
 if(r.original_direct_reader_and_margin_unchanged!==true||r.unknown_neutral_geometry_excluded!==false||r.physical_ports_inferred!==false||!Array.isArray(r.source_chains)||!r.source_chains.length||r.source_chains.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>typeof v!=='string'||!v)))return false;
 const a=r.typed_component_body_instances;
 if(!Array.isArray(a)||!a.length||a.some(b=>b.type_code!=='YS'||!b.device_name||!hash(b.block_signature_sha256)||!Array.isArray(b.source_chain)||b.source_chain.length<2||!r.source_chains.some(p=>p[0]===b.source_chain[0])||b.physical_ports_verified!==false||!Number.isInteger(b.primitive_count)||b.primitive_count<3))return false;
 return !same(r.source_rules,[typedBend])||r.inherited_elbow_normalization_replayed===true;
}
export function checkedAxisRuleVerticalDN(edge,context=null){
 const root=context?.axis_rule_vertical_DN,b=root?.source_bindings;
 if(root?.mode!=='qualified_axis_rule_vertical_DN_context_v1'||root.human_accepted!==false||root.raw_graph_changed!==false||root.physical_lengths_assigned!==0||root.whole_edge_DN_assigned!==0||!b)return [];
 if(![b.native_source,b.native_graph,b.native_proof,b.rendered_graph].every(hash)||b.rendered_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>`${r.edge_id}:${r.path_index}:${r.segment_index}`)).size!==root.count)return [];
 const rows=root.records.filter(r=>r.edge_id===edge.edge_id),nonempty=a=>Array.isArray(a)&&a.length>0&&a.every(v=>typeof v==='string'&&v.length>0);
 const ownership=root.modelspace_pair_seed_ownership;
 if(ownership&&(ownership.mode!=='original_native_pair_and_direct_source_LINE_scope_v1'||!Array.isArray(ownership.keys)||ownership.keys.length!==ownership.count||new Set(ownership.keys).size!==ownership.count||ownership.keys.some(k=>!root.records.some(r=>`${r.edge_id}:${r.path_index}:${r.segment_index}`===k))||!Number.isInteger(ownership.existing_main_T_requalified)||ownership.existing_main_T_requalified<1||ownership.old_values_changed!==false))return [];
 const sourceOwners=r=>!(ownership?.keys.includes(`${r.edge_id}:${r.path_index}:${r.segment_index}`)||r.seed_annotation_owners!==undefined)||(r.same_LINE_seed_priority_checked===true&&r.original_caption_owner_rules_replayed===true&&Array.isArray(r.seed_annotation_owners)&&r.seed_annotation_owners.length>0&&r.seed_annotation_owners.every(o=>r.seed_text_handles.includes(o.text_handle)&&r.main_line_handles.includes(o.source_LINE)&&['native_pair','native_direct'].includes(o.geometry_family)&&o.source_LINE_scope_native_replayed===true));
 const mainEvidence=r=>(same(r.source_rules,[rule])||same(r.source_rules,[multiline]))&&nonempty(r.main_line_handles)&&nonempty(r.root_T_nodes)&&r.whole_branch_annotation_barriers_checked===true&&(!same(r.source_rules,[multiline])||(r.multiline_main_source_chain_replayed===true&&r.source_roots_from_native_witnesses===true&&r.root_main_annotation_extents_checked===true&&r.conflicting_source_connected_seeds_blocked===true&&r.branch_DN_used_as_main_seed===false&&Array.isArray(r.main_source_chains)&&r.main_source_chains.length>0&&r.main_source_chains.every(s=>typeof s.edge_id==='string'&&Number.isInteger(s.path_index)&&Number.isInteger(s.segment_index)&&typeof s.child_handle==='string'&&r.main_line_handles.includes(s.child_handle)&&(s.root_handle===null||typeof s.root_handle==='string'))));
 if(rows.some(r=>r.system!==edge.system||!Number.isFinite(r.nominal_mm)||r.nominal_mm<=0||r.axis_source_sha256!==b.native_source||!Number.isInteger(r.path_index)||r.path_index<0||!Number.isInteger(r.segment_index)||r.segment_index<0||!Array.isArray(r.scope_points)||r.scope_points.length!==2||!same(edge.attribute_paths?.[r.path_index]?.slice(r.segment_index,r.segment_index+2),r.scope_points)||Math.abs(r.scope_points[0][0]-r.scope_points[1][0])>.05||!nonempty(r.seed_text_handles)||!Array.isArray(r.seed_domains)||!r.seed_domains.length||!(mainEvidence(r)||typedEvidence(r)||layoutEvidence(r)||expandedBendEvidence(r))||r.seed_domains.some(s=>s.system!==r.system||s.nominal_mm!==r.nominal_mm)||r.physical_length_mm!==null||r.whole_edge_DN_assigned!==false||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false))return [];
 if(rows.some(r=>!sourceOwners(r)))return [];
 return rows;
}
export function axisRuleVerticalDNProperties(edge,zh=true,context=null){
 const rows=checkedAxisRuleVerticalDN(edge,context),out=[];
 for(const r of rows){
  if(same(r.source_rules,[expandedBend])){
   out.push([zh?`\u7ad6\u6bb5\u7ba1\u5f84（\u4e3b\u7ba1\u5ef6\u4f38\u540e\u5f2f\u5934\u7ee7\u627f ${r.path_index}:${r.segment_index}）`:`Vertical DN via expanded main and bends ${r.path_index}:${r.segment_index}`,`DN${r.nominal_mm}`]);
   out.push([zh?'11\u56fe\u6807\u6ce8\u4e0e\u6e90\u7ebf':'Drawing11 caption and source lines',`TEXT ${r.seed_text_handles.join('; ')} / LINE ${r.source_chains.map(p=>p[1]).join(' → ')}`]);
   out.push([zh?'\u7ee7\u627f\u8fb9\u754c':'Inheritance boundary',zh?'\u539f\u4e3b\u7ba1\u6807\u6ce8\u5ef6\u4f38\u4e0e\u540c\u8def\u5f84\u4e24\u81c2\u5f2f\u5934\u5df2\u56de\u8bc1；\u771f\u5b9e\u5206\u652f、\u65b0\u7ba1\u5f84\u53caF\u6807\u6ce8\u4ecd\u963b\u65ad':'Original source-LINE scope and same-path two-arm bends replayed; true branches, new DN and F leaders still block']);
   continue;
  }
  if(same(r.source_rules,[layoutDirect])||same(r.source_rules,[layoutBend])){
   out.push([zh?`\u7ad6\u6bb5\u7ba1\u5f84\uff08\u65e7\u6a21\u677f\u89c4\u5219\u590d\u7528 ${r.path_index}:${r.segment_index}\uff09`:`Vertical DN via inherited layout ${r.path_index}:${r.segment_index}`,`DN${r.nominal_mm}`]);
   out.push([zh?'\u6807\u6ce8\u5f52\u5c5e\u6765\u6e90':'Caption ownership source',`SH16 11 / TEXT ${r.seed_text_handles.join('; ')} / ${r.source_chains.map(p=>p.join('/')).join('; ')}`]);
   out.push([zh?'\u72ec\u7acb\u5bf9\u7167\u6837\u672c':'Independent source controls',r.layout_ownership.map(o=>`${o.independent_control_roots.length}`).join('; ')]);
   out.push([zh?'\u53d6\u503c\u8fb9\u754c':'Value scope',zh?'\u539f\u91cd\u590d\u6a21\u677f\u3001\u6e90Z\u548c\u65b0\u7ba1\u5f84\u5c4f\u969c\u4fdd\u7559\uff1b\u4ec5\u5bf9\u5e94\u7ad6\u6bb5\uff0c\u6574\u8fb9\u53ca\u672a\u77e5\u957f\u5ea6\u4e0d\u8d4b\u503c':'Original layout, source Z and transition guards retained; segment only, no whole-edge or unknown length value']);
   continue;
  }
  if(same(r.source_rules,[multiline])){
   out.push([zh?`\u7ad6\u6bb5\u7ba1\u5f84\uff08\u5206\u6bb5\u4e3b\u7ba1\u4e09\u901a\u7ee7\u627f ${r.path_index}:${r.segment_index}\uff09`:`Vertical DN via segmented main T ${r.path_index}:${r.segment_index}`,`DN${r.nominal_mm}`]);
   out.push([zh?'\u4e3b\u7ba1\u6807\u6ce8\u53ca\u539f\u751f\u8fde\u7eed\u8bc1\u636e':'Main caption and native continuity',`SH16 11 / TEXT ${r.seed_text_handles.join('; ')} / LINE ${r.main_line_handles.join('; ')} / T ${r.root_T_nodes.join('; ')}`]);
   if(r.seed_annotation_owners)out.push([zh?'\u6807\u6ce8\u5f52\u5c5e\u89c4\u5219':'Caption ownership rules',zh?'\u539f\u751f\u6210\u5bf9\u51e0\u4f55\u4e0e\u76f4\u63a5\u6807\u6ce8\u540c\u7b49\u5904\u7406\uff1b\u6309\u4e09\u901a\u5b9e\u9645\u63a5\u5165\u7684LINE\u53d6\u503c':'Native paired and direct captions have equal priority; use the actual LINE entering the T']);
   out.push([zh?'\u7ee7\u627f\u8fb9\u754c':'Inheritance boundary',zh?'\u4e3b\u7ba1\u8f6c\u5f2f\u548c\u4e09\u901a\u76f4\u901a\u81c2\u5df2\u56de\u8bc1\uff1b\u6574\u6761\u652f\u8def\u7684\u65b0\u7ba1\u5f84\u53caF\u6807\u6ce8\u4ecd\u963b\u65ad\u7ee7\u627f':'Native main bends and through-T arms replayed; complete branch new-DN and F barriers retained']);
   continue;
  }
  if(!same(r.source_rules,[rule])){
   const bend=same(r.source_rules,[typedBend]);
   out.push([zh?`\u7ad6\u6bb5\u7ba1\u5f84\uff08${bend?'\u65e7\u5f2f\u5934\u89c4\u5219\u7ee7\u627f':'\u539f\u751f\u76f4\u63a5\u6807\u6ce8'} ${r.path_index}:${r.segment_index}\uff09`:`Vertical DN via ${bend?'inherited bend':'native caption'} ${r.path_index}:${r.segment_index}`,`DN${r.nominal_mm}`]);
   out.push([zh?'\u6807\u6ce8\u4e0e\u5143\u4ef6\u4f9d\u636e':'Caption and typed component evidence',`SH16 11 / TEXT ${r.seed_text_handles.join('; ')} / ${r.source_chains.map(p=>p.join('/')).join('; ')} / ${r.typed_component_body_instances.map(b=>b.device_name).join('; ')}`]);
   out.push([zh?'\u65e7\u89c4\u5219\u590d\u7528\u8fb9\u754c':'Inherited rule boundary',zh?'\u5df2\u6838\u9a8c\u8fc7\u6ee4\u5668\u56fe\u5f62\u4e0d\u4f5c\u7ba1\u7ebf\u7ade\u4e89\uff1b\u5176\u4ed6\u56fe\u5f62\u53ca\u771f\u5b9e\u5206\u652f\u4ecd\u4fdd\u7559':'Verified filter body excluded from pipe competition; other geometry and real branches retained']);
   continue;
  }
  out.push([zh?`\u7ad6\u6bb5\u7ba1\u5f84\uff08\u4e3b\u7ba1\u4e09\u901a\u7ee7\u627f ${r.path_index}:${r.segment_index}\uff09`:`Vertical DN via native main T ${r.path_index}:${r.segment_index}`,`DN${r.nominal_mm}`]);
  out.push([zh?'\u4e3b\u7ba1\u6807\u6ce8\u4e0e\u8fde\u63a5\u4f9d\u636e':'Main caption and native connection',`SH16 11 / TEXT ${r.seed_text_handles.join('; ')} / LINE ${r.main_line_handles.join('; ')} / T ${r.root_T_nodes.join('; ')}`]);
  out.push([zh?'\u7ee7\u627f\u8fb9\u754c':'Inheritance boundary',zh?'\u540c\u7cfb\u7edf\u771f\u5b9e\u4e09\u901a\uff1b\u5df2\u68c0\u67e5\u6574\u6761\u652f\u8def\u7684\u65b0\u7ba1\u5f84\u4e0eF\u6807\u6ce8':'Same-system native T; entire branch checked for new DN and F labels']);
 }
 if(rows.length)out.push([zh?'\u7ad6\u76f4\u6bb5\u7269\u7406\u957f\u5ea6':'Vertical physical length',zh?'\u672a\u77e5\uff1b\u4ec511\u56fe\u660e\u786e\u7ad6\u6bb5\u957f\u5ea6\u53ef\u7528\uff0c\u4e0d\u4ece\u6c34\u5e73\u6807\u6ce8\u63a8\u7b97':'Unknown; explicit drawing11 vertical length required; no horizontal-label inference']);
 return out;
}
export const axisRuleVerticalDNCsvFields=['axis_rule_vertical_DN_segment_count','axis_rule_vertical_DN_segments_json','axis_rule_vertical_DN_source_sha256'];
export function axisRuleVerticalDNCsvValues(edge,context=null){const rows=checkedAxisRuleVerticalDN(edge,context);return rows.length?{axis_rule_vertical_DN_segment_count:rows.length,axis_rule_vertical_DN_segments_json:JSON.stringify(rows),axis_rule_vertical_DN_source_sha256:context.axis_rule_vertical_DN.source_bindings.native_source}:{};}
