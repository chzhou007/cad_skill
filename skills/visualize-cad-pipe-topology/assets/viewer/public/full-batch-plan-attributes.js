const hash=/^[0-9a-f]{64}$/;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const positive=v=>Number.isFinite(v)&&v>0;
export function checkedMemberPlanRun(edge,context=null){
 const root=context?.member_plan_runs,s=checkedBatchPlanScope(edge);if(!root||!s)return null;
 if(root.mode!=='qualified_axis_confirmed_member_plan_runs_v1'||root.original_local_topology_unchanged!==true||root.original_axis_correspondences_unchanged!==true||root.human_accepted!==false||root.net_pipe_cut_lengths_assigned!==0)return null;
 const h=root.source_bindings;if(!h||![h.axis_graph,h.rendered_graph,h.member_proof].every(v=>hash.test(v||''))||h.axis_graph!==context.source_graph_sha256||h.rendered_graph!==context.rendered_graph_sha256)return null;
 const rows=root.records?.filter(r=>r.axis_edge_id===edge.edge_id);if(rows?.length!==1)return null;const r=rows[0];
 if(r.system!==edge.system||r.floor!==s.floor||r.axis_mapping_id!==s.mapping_id||s.kind!=='same_floor_T_to_T_main'||s.iso_edges.length!==1||s.plan_edges.length!==1||s.plan_edges[0]!==r.plan_edge_id||r.nominal_mm!==s.plan_drawn_nominal_mm)return null;
 if(r.axis_start_node!==edge.start_node_id||r.axis_end_node!==edge.end_node_id||!same(r.axis_attribute_paths,edge.attribute_paths)||r.plan_graph_sha256!==s.graph_sha256.plan||(r.source_sha256?.plan!==s.source_sha256.plan||r.source_sha256?.iso!==s.source_sha256.iso)||r.mapping_receipt_sha256!==s.mapping_receipt_sha256)return null;
 if(![edge.floor_start??edge.start_floor,edge.floor_end??edge.end_floor].every(f=>f===r.floor)||!positive(r.horizontal_plan_run_centerline_mm)||r.net_pipe_cut_length_mm!==null||r.installed_whole_edge_length_mm!==null||r.detail_inline_positions_scaled_to_plan!==false||r.run_centerline_includes_inline_assembly_extents!==true||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false)return null;
 return r;
}
export function memberPlanRunProperties(edge,zh=true,context=null){
 const r=checkedMemberPlanRun(edge,context);if(!r)return [];
 return [[zh?'\u5e73\u9762\u4e09\u901a\u95f4\u8def\u7531\u4e2d\u5fc3\u7ebf':'Plan T-to-T run centerline',`${(r.horizontal_plan_run_centerline_mm/1000).toFixed(3)} m${zh?'\uff08\u542b\u8fb9\u4e0a\u5143\u4ef6\u533a\u95f4\uff09':' (including inline assembly extents)'}`],
 [zh?'\u8def\u7531\u957f\u5ea6\u6765\u6e90':'Run length source',`SH16 ${String(r.floor+7).padStart(2,'0')} / LINE ${r.shared_projected_source_LINE} / ${r.plan_edge_id}`],
 [zh?'\u53e0\u7ba1\u6210\u5458\u7ba1\u5f84':'Overlapping member DN',`DN${r.nominal_mm} / ${zh?'\u590d\u5408\u6807\u6ce8':'compound label'} ${r.compound_text_handle}`],
 [zh?'\u51c0\u7ba1\u6750\u957f\u5ea6':'Net pipe cut length',zh?'\u672a\u77e5\uff1b\u672a\u4ece\u8def\u7531\u957f\u5ea6\u4e2d\u6263\u9664\u5143\u4ef6\u5b9e\u4f53\u957f\u5ea6':'Unknown; component body lengths have not been deducted'],
 [zh?'\u4fa7\u89c6\u4f7f\u7528\u8303\u56f4':'Detail-view extent',zh?'\u4fdd\u7559\u62d3\u6251\u4e0e\u5143\u4ef6\u5f52\u5c5e\uff1b\u4f4d\u7f6e\u548c\u957f\u5ea6\u6765\u81ea\u5e73\u9762\u5bf9\u5e94\uff0c\u672a\u6309\u4fa7\u89c6\u6bd4\u4f8b\u6362\u7b97':'Topology and components retained; route extent comes from matched plan anchors, not scaled detail geometry']];
}
export const memberPlanRunCsvFields=['member_plan_run_centerline_mm','member_plan_run_DN_mm','member_plan_run_source_LINE','member_plan_run_source_TEXT','member_plan_run_edge','member_plan_run_includes_inline_extents','member_plan_net_pipe_cut_length_mm','member_plan_run_evidence_json'];
export function memberPlanRunCsvValues(edge,context=null){
 const r=checkedMemberPlanRun(edge,context);if(!r)return {};
 return {member_plan_run_centerline_mm:r.horizontal_plan_run_centerline_mm,member_plan_run_DN_mm:r.nominal_mm,member_plan_run_source_LINE:r.shared_projected_source_LINE,member_plan_run_source_TEXT:r.compound_text_handle,member_plan_run_edge:r.plan_edge_id,member_plan_run_includes_inline_extents:true,member_plan_net_pipe_cut_length_mm:'',member_plan_run_evidence_json:JSON.stringify(r)};
}
export function checkedBatchPlanScope(edge){
 const s=edge.batch_plan_attribute_scopes;if(!s)return null;
 if(s.system!==edge.system||!Number.isInteger(s.floor)||!s.mapping_id||!Array.isArray(s.iso_edges)||!s.iso_edges.includes(edge.edge_id)||new Set(s.iso_edges).size!==s.iso_edges.length||!s.plan_edges?.length||new Set(s.plan_edges).size!==s.plan_edges.length)return null;
 if(![s.source_sha256?.plan,s.source_sha256?.iso,s.graph_sha256?.plan,s.graph_sha256?.iso,s.mapping_receipt_sha256,s.plan_DN_receipt_sha256].every(v=>hash.test(v||''))||s.human_accepted!==false||s.related_HIL_confirmation_inherited!==false||s.whole_installed_length_mm!==null)return null;
 const DN=s.plan_DN_records;if(!Array.isArray(DN)||DN.length!==s.plan_edges.length||new Set(DN.map(r=>r.edge_id)).size!==DN.length||DN.some(r=>!s.plan_edges.includes(r.edge_id)||r.system!==s.system||r.human_accepted!==false||!r.scope_paths?.length||(r.nominal_mm!==null&&(!positive(r.nominal_mm)||!r.lineage?.length))))return null;
 const values=new Set(DN.map(r=>r.nominal_mm)),expected=values.size===1&&!values.has(null)?[...values][0]:null;if(s.plan_drawn_nominal_mm!==expected)return null;
 const group=s.iso_edges.length>1;if(s.group_scope_not_allocated_to_child_edges!==group)return null;
 const metric=s.horizontal_projection;
 if(metric){const p=metric.pieces;if(!positive(metric.value_mm)||!Array.isArray(p)||!p.length||new Set(p.map(v=>`${v.plan_edge}/${v.path_index}/${v.segment_index}`)).size!==p.length||p.some(v=>!s.plan_edges.includes(v.plan_edge)||!positive(v.length_mm))||Math.abs(p.reduce((sum,v)=>sum+v.length_mm,0)-metric.value_mm)>.0001)return null;}
 if(group&&(s.whole_axis_nominal_mm!==null||s.complete_horizontal_centerline_route_mm!==null))return null;
 if(s.axis_horizontal_scope_paths){
  const floors=[edge.floor_start??edge.start_floor,edge.floor_end??edge.end_floor];
  if(group||s.kind!=='same_floor_T_to_T_main'||!same(s.axis_horizontal_scope_paths,edge.attribute_paths)||floors.some(f=>f!==s.floor)||s.whole_axis_nominal_mm!==s.plan_drawn_nominal_mm)return null;
  if(s.complete_horizontal_centerline_route_mm!==null&&(!positive(s.complete_horizontal_centerline_route_mm)||metric?.status!=='native_plan_horizontal_projection_partial_length'||s.complete_horizontal_centerline_route_mm!==metric.value_mm))return null;
 }else if(s.whole_axis_nominal_mm!==null||s.complete_horizontal_centerline_route_mm!==null)return null;
 return s;
}
function sourceLabels(s){return [...new Set(s.plan_DN_records.flatMap(r=>(r.lineage||[]).flatMap(c=>(c.evidence||[]).map(e=>e.evidence_id))))].join('; ');}
export function batchPlanProperties(edge,zh=true,context=null){
 const s=checkedBatchPlanScope(edge);if(!s)return [];
 const group=s.group_scope_not_allocated_to_child_edges,metric=s.horizontal_projection;
 const child=checkedOrderedGroupRun(edge,context);
 const source=String(7+s.floor).padStart(2,'0'),value=s.plan_drawn_nominal_mm;
 const rows=[[zh?'\u672c\u8f6e\u5e73\u9762\u7ba1\u5f84':'Current plan DN',value===null?(zh?'\u672a\u77e5\uff1b\u4fdd\u7559\u51b2\u7a81\u6216\u7f3a\u5931\u6765\u6e90':'Unknown; conflicting or missing source'):`DN${value} [${s.floor}F / SH16 ${source}]`],
  [zh?'\u672c\u8f6e\u5e73\u9762\u7ba1\u957f':'Current plan pipe XY',metric?`${(metric.value_mm/1000).toFixed(3)} m${group?(zh?'\uff08\u8def\u5f84\u7ec4\u603b\u91cf\uff0c\u672a\u5206\u914d\u5230\u672c\u8fb9\uff09':' (group total, not allocated)'):(zh?'\uff08\u5df2\u7ed8\u533a\u6bb5\uff09':' (drawn scope)')}`:(zh?'\u672a\u77e5\uff1b\u672c\u8f6e\u672a\u53d6\u5f97\u53ef\u9760\u7269\u7406\u91cf\u6d4b\u8303\u56f4':'Unknown; no proved current metric scope')],
  [zh?'\u7ba1\u5f84\u6765\u6e90':'DN source',sourceLabels(s)||(zh?'\u672a\u786e\u5b9a':'Unresolved')],
  [zh?'\u5e73\u9762\u56fe\u5bf9\u5e94\u7ba1\u6bb5':'Corresponding plan edges',s.plan_edges.join(' / ')],
  [zh?'\u672c\u8f6e\u6620\u5c04':'Current correspondence',s.mapping_id],
  [zh?'\u53d6\u503c\u8303\u56f4':'Attribute extent',zh?'\u5e73\u9762\u5df2\u7ed8\u6c34\u5e73\u7ba1\u6bb5\uff1b\u8bbe\u5907\u7acb\u7ba1\u3001\u8f6f\u63a5\u5185\u90e8\u53ca\u672a\u7ed8\u63a5\u7ba1\u5206\u522b\u4fdd\u7559':'Drawn plan horizontal scope; axis drops, joint interiors and unshown connectors remain separate']];
 if(s.complete_horizontal_centerline_route_mm!==null)rows.push([zh?'\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\u8def\u7531':'Complete horizontal centerline route',`${(s.complete_horizontal_centerline_route_mm/1000).toFixed(3)} m`]);
 if(s.plan_DN_records.some(r=>r.status==='conflict'))rows.push([zh?'\u5f53\u524d\u7ba1\u5f84\u51b2\u7a81':'Current DN conflict',zh?'\u672c\u8f6e\u4e0d\u9009\u53d6\u6574\u8fb9\u7ba1\u5f84\uff1b\u65e7\u5c5e\u6027\u4fdd\u7559\u4f9b\u8ffd\u6eaf':'No current whole-edge DN selected; prior attributes retained for history']);
 if(child){rows[1]=[zh?'\u672c\u8fb9\u5e73\u9762\u5df2\u77e5\u4e2d\u5fc3\u7ebf':'Known plan centerline for this edge',`${(child.known_plan_pipe_XY_mm/1000).toFixed(3)} m`];rows.push([zh?'\u8def\u5f84\u7ec4\u5185\u5206\u914d':'Group allocation',zh?'\u5df2\u6309\u539f\u751f\u4e09\u901a\u533a\u95f4\u9010\u8fb9\u8bfb\u53d6\uff1b\u672a\u91cd\u590d\u4f7f\u7528\u7ec4\u603b\u957f':'Read each native T interval; no group total copied to children']);}
 else if(group)rows.push([zh?'\u8def\u5f84\u7ec4\u5185\u5206\u914d':'Group allocation',uniformGroupChildDN(edge,context)?(zh?'\u7ba1\u5f84\u9002\u7528\u672c\u8fb9\uff1b\u957f\u5ea6\u5c1a\u672a\u9010\u8fb9\u5206\u914d\uff0c\u4e0d\u80fd\u91cd\u590d\u7d2f\u52a0\u7ec4\u603b\u957f':'DN applies to this child; length remains unallocated; do not repeat the group total'):(zh?'\u5c1a\u672a\u9010\u8fb9\u5206\u914d\uff0c\u4e0d\u80fd\u91cd\u590d\u7d2f\u52a0\u7ec4\u603b\u957f':'No child allocation; do not sum the repeated group total')]);
 return rows;
}
export const batchPlanCsvFields=['batch_mapping_id','batch_plan_edges','batch_plan_DN_mm','batch_plan_pipe_XY_mm','batch_group_pipe_XY_total_mm','batch_complete_horizontal_centerline_mm','batch_whole_axis_DN_mm','batch_plan_source_sha256','batch_plan_graph_sha256','batch_plan_DN_lineage_json','batch_scope_status','batch_retained_prior_whole_DN_mm','batch_DN_resolution_basis','batch_uniform_group_child_DN_mm','batch_uniform_group_DN_basis'];
export function batchPlanCsvValues(edge){
 const s=checkedBatchPlanScope(edge);if(!s)return {};
 const conflict=s.plan_DN_records.some(r=>r.status==='conflict'),group=s.group_scope_not_allocated_to_child_edges;
 return {batch_mapping_id:s.mapping_id,batch_plan_edges:s.plan_edges.join(';'),batch_plan_DN_mm:s.plan_drawn_nominal_mm??'',
  batch_plan_pipe_XY_mm:group?'':s.horizontal_projection?.value_mm??'',batch_group_pipe_XY_total_mm:group?s.horizontal_projection?.value_mm??'':'',
  batch_complete_horizontal_centerline_mm:s.complete_horizontal_centerline_route_mm??'',batch_whole_axis_DN_mm:s.whole_axis_nominal_mm??'',
  batch_plan_source_sha256:s.source_sha256.plan,batch_plan_graph_sha256:s.graph_sha256.plan,batch_plan_DN_lineage_json:JSON.stringify(s.plan_DN_records),
  batch_scope_status:conflict?'current_plan_DN_conflict':group?'path_group_child_allocation_unknown':'source_checked_drawn_plan_scope',
  diameter_nominal_mm:s.whole_axis_nominal_mm??'',diameter_text:s.whole_axis_nominal_mm===null?'':`DN${s.whole_axis_nominal_mm}`,
  diameter_status:conflict?'current_plan_DN_conflict':s.whole_axis_nominal_mm===null?'current_plan_DN_partial_or_unknown':'current_whole_horizontal_main_DN'};
}
export function reconcileBatchPlanCsvValues(edge,prior,context=null){
 const s=checkedBatchPlanScope(edge),batch=batchPlanCsvValues(edge),result={...prior,...batch};
 if(!s)return result;
 result.batch_retained_prior_whole_DN_mm='';result.batch_DN_resolution_basis='current_batch_scope';result.batch_uniform_group_child_DN_mm='';result.batch_uniform_group_DN_basis='';
 // A missing metric or a smaller drawn scope is not new contradictory DN
 // evidence. Preserve an independently source-checked prior whole-edge DN
 // only on a one-to-one same-floor main when the current known value agrees.
 // Conflicts, unknown values, equipment drops and group allocations do not
 // qualify; no prior value is promoted into the current source scope itself.
 const value=Number(prior.diameter_nominal_mm),floors=[edge.floor_start??edge.start_floor,edge.floor_end??edge.end_floor];
 if(s.whole_axis_nominal_mm===null&&s.kind==='same_floor_T_to_T_main'&&!s.group_scope_not_allocated_to_child_edges
   &&floors.every(f=>f===s.floor)&&positive(value)&&s.plan_drawn_nominal_mm===value
   &&!s.plan_DN_records.some(r=>r.status==='conflict')){
  result.diameter_nominal_mm=value;result.diameter_text=`DN${value}`;
  result.diameter_status='retained_prior_source_checked_whole_DN_agrees_with_current_plan';
  result.batch_retained_prior_whole_DN_mm=value;
  result.batch_DN_resolution_basis='prior_whole_edge_source_scope_agrees_with_current_plan';
 }
 const uniform=uniformGroupChildDN(edge,context);
 if(uniform){result.diameter_nominal_mm=uniform.nominal_mm;result.diameter_text=`DN${uniform.nominal_mm}`;
  result.diameter_status='source_checked_uniform_DN_on_complete_horizontal_group_child';
  result.batch_uniform_group_child_DN_mm=uniform.nominal_mm;result.batch_uniform_group_DN_basis='uniform_known_source_path_DN_complete_horizontal_child';
  result.batch_DN_resolution_basis=result.batch_uniform_group_DN_basis;
  result.batch_scope_status='uniform_group_DN_known_child_length_allocation_unknown';}
 return result;
}

export function uniformGroupChildDN(edge,context){
 const s=checkedBatchPlanScope(edge);
 if(!s||!context||context.mode!=='source_checked_uniform_path_group_DN_child_domains_v1'||context.human_accepted!==false||context.topology_mutated!==false||context.scalar_physical_lengths_assigned!==0)return null;
 if(![context.source_graph_sha256,context.rendered_graph_sha256,context.source_policy_sha256].every(v=>hash.test(v||'')))return null;
 if(s.kind!=='native_main_chain_between_independent_junctions'||!s.group_scope_not_allocated_to_child_edges||!positive(s.plan_drawn_nominal_mm)||s.plan_DN_records.some(r=>r.nominal_mm!==s.plan_drawn_nominal_mm||['conflict','unresolved','annotation_blocked','source_scope_unverified'].includes(r.status)))return null;
 const matches=(context.groups||[]).filter(g=>g.mapping_id===s.mapping_id);if(matches.length!==1)return null;const g=matches[0];
 if(g.nominal_mm!==s.plan_drawn_nominal_mm||g.floor!==s.floor||g.system!==s.system||g.child_length_allocation_known!==false||g.physical_child_lengths_mm!==null||g.human_accepted!==false||!same(g.plan_edges,s.plan_edges)||!same(g.iso_edges,s.iso_edges)||g.mapping_receipt_sha256!==s.mapping_receipt_sha256||g.plan_DN_receipt_sha256!==s.plan_DN_receipt_sha256)return null;
 for(const v of ['plan','iso'])if(g.source_sha256?.[v]!==s.source_sha256[v]||g.graph_sha256?.[v]!==s.graph_sha256[v])return null;
 if(!Array.isArray(g.domains)||g.domains.length!==s.iso_edges.length||new Set(g.domains.map(d=>d.edge_id)).size!==g.domains.length||g.domains.some(d=>!s.iso_edges.includes(d.edge_id)))return null;
 const ds=g.domains.filter(d=>d.edge_id===edge.edge_id);if(ds.length!==1)return null;const d=ds[0],angles=context.horizontal_directions_degrees;
 if(typeof edge.start_node_id!=='string'||!edge.start_node_id||typeof edge.end_node_id!=='string'||!edge.end_node_id||edge.start_node_id===edge.end_node_id||!angles?.length||angles.some(a=>!Number.isFinite(a)||Math.abs((a%180+180)%180-90)<.5)||d.start_node_id!==edge.start_node_id||d.end_node_id!==edge.end_node_id||!same(d.scope_paths,edge.attribute_paths)||d.scope_paths.length!==1||d.scope_paths[0].length<2||[edge.floor_start??edge.start_floor,edge.floor_end??edge.end_floor].some(f=>f!==s.floor)||edge.axis_riser_attributes||edge.plan_segment_attributes||edge.source_wave_omission||edge.source_view_context)return null;
 for(let i=1;i<d.scope_paths[0].length;i++){const a=d.scope_paths[0][i-1],b=d.scope_paths[0][i];if(![...a,...b].every(Number.isFinite)||Math.hypot(b[0]-a[0],b[1]-a[1])<=.05)return null;const angle=(Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI+180)%180;if(!angles.some(v=>{const delta=Math.abs(angle-(v%180+180)%180);return Math.min(delta,180-delta)<=.1}))return null;}
 return g;
}

export function checkedOrderedGroupRun(edge,context=null){
 const root=context?.ordered_group_plan_runs,s=checkedBatchPlanScope(edge),uniform=uniformGroupChildDN(edge,context);
 if(!root||!s||!uniform||root.mode!=='qualified_ordered_group_child_plan_metrics_v1'||root.human_accepted!==false||root.group_totals_copied_to_children!==false||root.unknown_inline_lengths_assigned!==0)return null;
 const h=root.source_bindings;if(!h||![h.axis_graph,h.rendered_graph,h.length_proof].every(v=>hash.test(v||''))||h.axis_graph!==context.source_graph_sha256||h.rendered_graph!==context.rendered_graph_sha256)return null;
 if(!Array.isArray(root.records)||root.records.length!==root.axis_edges||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.records.length)return null;
 const matches=root.records.filter(r=>r.axis_edge_id===edge.edge_id);if(matches.length!==1)return null;const r=matches[0],i=r.index_in_group;
 if(!Number.isInteger(i)||i<0||i>=s.iso_edges.length||r.mapping_id!==s.mapping_id||s.iso_edges[i]!==edge.edge_id||s.plan_edges[i]!==r.plan_edge_id||r.floor!==s.floor||r.system!==s.system||r.nominal_mm!==uniform.nominal_mm)return null;
 if(r.axis_start_node!==edge.start_node_id||r.axis_end_node!==edge.end_node_id||!same(r.axis_attribute_paths,edge.attribute_paths)||r.plan_graph_sha256!==s.graph_sha256.plan||r.source_sha256?.plan!==s.source_sha256.plan||r.source_sha256?.iso!==s.source_sha256.iso||r.mapping_receipt_sha256!==s.mapping_receipt_sha256)return null;
 if(r.length_allocation_method!=='native_T_order_between_two_independent_anchors'||r.axis_drawn_lengths_or_ratios_used!==false||r.child_equipment_or_external_interface_identity_inferred!==false||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||r.physical_installed_length_mm!==null||r.net_pipe_cut_length_mm!==null)return null;
 if(!Array.isArray(r.axis_Ts)||r.axis_Ts.length!==2||new Set(r.axis_Ts).size!==2||![edge.start_node_id,edge.end_node_id].every(id=>r.axis_Ts.includes(id))||!Array.isArray(r.plan_Ts)||r.plan_Ts.length!==2||new Set(r.plan_Ts).size!==2)return null;
 const p=r.source_projection,pieces=p?.pieces,unknown=r.unknown_inline_joint_handles;
 if(!positive(r.known_plan_pipe_XY_mm)||p?.value_mm!==r.known_plan_pipe_XY_mm||p.installed_whole_edge_length_mm!==null||!pieces?.length||new Set(pieces.map(v=>`${v.path_index}/${v.segment_index}`)).size!==pieces.length||pieces.some(v=>v.plan_edge!==r.plan_edge_id||!v.source_line_handle||!positive(v.length_mm))||Math.abs(pieces.reduce((a,v)=>a+v.length_mm,0)-p.value_mm)>.0001)return null;
 if(!Array.isArray(unknown)||new Set(unknown).size!==unknown.length||unknown.some(v=>typeof v!=='string'||!v))return null;
 if(r.complete_horizontal_run_centerline_mm!==null&&(!positive(r.complete_horizontal_run_centerline_mm)||r.complete_horizontal_run_centerline_mm!==p.value_mm||unknown.length))return null;
 if(unknown.length&&(r.metric_reader!=='inherited_native_inline_pipe_XY'||p.joint_graphic_spans_added!==false||p.inline_joint_interior_length_mm!==null))return null;
 return r;
}
export function orderedGroupRunProperties(edge,zh=true,context=null){
 const r=checkedOrderedGroupRun(edge,context);if(!r)return [];
 const complete=r.complete_horizontal_run_centerline_mm!==null;
 return [[zh?'\u672c\u8fb9\u5e73\u9762\u5df2\u77e5\u4e2d\u5fc3\u7ebf':'Known plan centerline for this edge',`${(r.known_plan_pipe_XY_mm/1000).toFixed(3)} m`],
 [zh?'\u4e09\u901a\u95f4\u5b8c\u6574\u4e2d\u5fc3\u7ebf':'Complete T-to-T run centerline',complete?`${(r.complete_horizontal_run_centerline_mm/1000).toFixed(3)} m${zh?'\uff08\u542b\u9600\u4ef6\u533a\u95f4\uff09':' (including valve extents)'}`:(zh?'\u672a\u77e5\uff1b\u8f6f\u63a5\u5185\u90e8\u957f\u5ea6\u672a\u8ba1\u5165':'Unknown; flexible-joint interiors are not included')],
 [zh?'\u9010\u8fb9\u957f\u5ea6\u6765\u6e90':'Child length source',`SH16 ${String(r.floor+7).padStart(2,'0')} / ${r.plan_edge_id} / LINE ${[...new Set(r.source_projection.pieces.map(p=>p.source_line_handle))].join(', ')}`],
 [zh?'\u4e09\u901a\u5bf9\u5e94\u4f9d\u636e':'Junction correspondence basis',zh?'\u4e24\u7aef\u72ec\u7acb\u951a\u70b9\u4e4b\u95f4\uff0c\u53cc\u56fe\u539f\u751f\u4e09\u901a\u987a\u5e8f\u4e00\u81f4\uff1b\u672a\u6309\u8f74\u6d4b\u6bd4\u4f8b\u5206\u644a':'Matching native T order between independent outer anchors; no axis ratios'],
 [zh?'\u672a\u8ba1\u5165\u7684\u8f6f\u63a5':'Excluded flexible-joint interiors',r.unknown_inline_joint_handles.join(' / ')||(zh?'\u65e0':'None')],
 [zh?'\u51c0\u7ba1\u6750\u957f\u5ea6':'Net pipe cut length',zh?'\u672a\u77e5\uff1b\u672a\u6263\u9664\u9600\u4ef6\u5b9e\u4f53\u957f\u5ea6\uff0c\u4e5f\u672a\u8865\u5165\u672a\u77e5\u63a5\u7ba1':'Unknown; valve body lengths have not been deducted and unknown connectors have not been added']];
}
export const orderedGroupRunCsvFields=['ordered_group_plan_pipe_XY_mm','ordered_group_complete_run_mm','ordered_group_plan_edge','ordered_group_mapping_id','ordered_group_length_status','ordered_group_unknown_inline_handles','ordered_group_net_pipe_cut_length_mm','ordered_group_evidence_json'];
export function orderedGroupRunCsvValues(edge,context=null){
 const r=checkedOrderedGroupRun(edge,context);if(!r)return {};
 return {ordered_group_plan_pipe_XY_mm:r.known_plan_pipe_XY_mm,ordered_group_complete_run_mm:r.complete_horizontal_run_centerline_mm??'',ordered_group_plan_edge:r.plan_edge_id,ordered_group_mapping_id:r.mapping_id,
 ordered_group_length_status:r.complete_horizontal_run_centerline_mm===null?'native_child_pipe_XY_inline_interiors_unknown':'native_complete_child_T_to_T_run',ordered_group_unknown_inline_handles:r.unknown_inline_joint_handles.join(';'),ordered_group_net_pipe_cut_length_mm:'',ordered_group_evidence_json:JSON.stringify(r)};
}

// Native compound carrier member attributes.
const cmHash=/^[0-9a-f]{64}$/;
const cmSame=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const cmPositive=v=>Number.isFinite(v)&&v>0;
export function hasCompoundMemberScope(edge,context=null){return context?.compound_member_mains?.records?.some(r=>r.axis_edge_id===edge.edge_id)===true;}
export function checkedCompoundMember(edge,context=null){
 const root=context?.compound_member_mains,h=root?.source_bindings;
 if(!root||root.mode!=='qualified_native_compound_member_attributes_v1'||root.source_drawing_graphs_unchanged!==true||root.global_plan_topology_complete!==false||root.component_assignments_mutated!==false||root.human_accepted!==false||!cmHash.test(root.member_graph_sha256||''))return null;
 if(!h||![h.axis_graph,h.rendered_graph,h.native_proof].every(v=>cmHash.test(v||''))||h.axis_graph!==context.source_graph_sha256||h.rendered_graph!==context.rendered_graph_sha256)return null;
 if(!Array.isArray(root.records)||root.records.length!==root.axis_edges||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.axis_edges)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r)return null;
 if(r.system!==edge.system||r.axis_start_node!==edge.start_node_id||r.axis_end_node!==edge.end_node_id||!cmSame(r.axis_attribute_paths,edge.attribute_paths)||![edge.floor_start??edge.start_floor,edge.floor_end??edge.end_floor].every(v=>v===r.floor))return null;
 if(!cmPositive(r.nominal_mm)||!cmPositive(r.plan_run_centerline_mm)||!r.plan_declarations?.length||r.plan_declarations.some(d=>d.member?.nominal_mm!==r.nominal_mm)||r.axis_caption_crosscheck?.text?.nominal_mm!==r.nominal_mm)return null;
 if(r.DN_selected_from_axis_value!==false||r.physical_elevation_mm!==null||r.whole_installed_length_mm!==null||r.net_pipe_cut_length_mm!==null||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false||![r.source_plan_sha256,r.source_axis_sha256,r.source_plan_graph_sha256].every(v=>cmHash.test(v||'')))return null;
 if(r.anchors?.length!==2||new Set(r.anchors.map(a=>a.equipment_id)).size!==2||r.member_node_ids?.length!==2||r.plan_projection?.value_mm!==r.plan_run_centerline_mm||r.plan_projection?.installed_whole_edge_length_mm!==null)return null;
 const levels=[r.source_level_literal,r.axis_caption_crosscheck.text.source_level_text,...r.plan_declarations.map(d=>d.member.source_level_text)];
 if(levels.some(v=>typeof v!=='string'||!/^[-+]?\d+(?:\.\d+)?$/.test(v))||levels.some(v=>Number(v)!==Number(levels[0])))return null;
 const pieces=r.plan_projection.pieces;if(!pieces?.length||pieces.some(p=>p.plan_edge!==r.plan_edge_id||p.source_line_handle!==r.plan_LINE||!cmPositive(p.length_mm))||Math.abs(pieces.reduce((s,p)=>s+p.length_mm,0)-r.plan_run_centerline_mm)>.0001)return null;
 return r;
}
export function compoundMemberProperties(edge,zh=true,context=null){
 const r=checkedCompoundMember(edge,context);
 if(!r)return hasCompoundMemberScope(edge,context)?[[zh?'\u7ba1\u5f84':'Pipe diameter',zh?'\u672a\u77e5\uff1b\u6210\u5458\u8bc1\u636e\u6821\u9a8c\u5931\u8d25':'Unknown; member evidence invalid']]:[];
 const old=r.superseded_scalar_observation?.plan_nominal_mm;
 return [[zh?'\u7ba1\u5f84':'Pipe diameter',`DN${r.nominal_mm}`],[zh?'\u697c\u5c42\u4f4d\u7f6e':'Floor location',`${r.floor}F`],
 [zh?'\u539f\u56fe\u6807\u6ce8':'Source annotation',r.plan_declarations.map(d=>`SH16 ${String(r.floor+7).padStart(2,'0')} / ${d.text_handle} [${d.member.declaration_index+1}]`).join(' / ')],
 [zh?'\u5e73\u9762\u4e3b\u7ba1\u4e2d\u5fc3\u7ebf\u957f\u5ea6':'Plan main centreline',`${(r.plan_run_centerline_mm/1000).toFixed(3)} m`],
 [zh?'\u957f\u5ea6\u8303\u56f4':'Length scope',zh?'\u4e24\u7aef\u4e09\u901a\u4e4b\u95f4\u7684\u5e73\u9762\u4e2d\u5fc3\u7ebf\uff0c\u5305\u542b\u5143\u4ef6\u5360\u636e\u8303\u56f4\uff1b\u51c0\u88c1\u7ba1\u957f\u548c\u6574\u8fb9\u5b89\u88c5\u957f\u5ea6\u672a\u77e5':'Plan T-to-T centreline including assembly extents; net cut and installed length unknown'],
 [zh?'\u53e0\u7ba1\u6210\u5458\u5bf9\u5e94':'Overlapping pipe member',`${r.plan_LINE} \u2194 ${r.axis_LINE} / ${r.axis_caption_crosscheck.text.handle}`],
 [zh?'\u6807\u6ce8\u539f\u6587\u503c':'Literal source value',`${r.source_level_literal}${zh?'\uff1b\u4ec5\u7528\u4e8e\u533a\u5206\u6210\u5458\uff0c\u672a\u6362\u7b97\u7269\u7406\u6807\u9ad8':' ; member identity only, no physical elevation assigned'}`],
 [zh?'\u8bbe\u5907\u652f\u8def\u951a\u70b9':'Independent branch anchors',r.anchors.map(a=>`${a.equipment_id}: ${a.plan_T} \u2194 ${a.axis_T}`).join(' / ')],
 [zh?'\u65e7\u6807\u91cf\u89c2\u5bdf':'Superseded scalar observation',cmPositive(old)?`DN${old}${zh?'\uff1b\u672a\u533a\u5206\u53e0\u7ba1\u6210\u5458\uff0c\u5df2\u7531\u5f53\u524d\u6210\u5458\u8bc1\u636e\u53d6\u4ee3':' ; member-unspecific scalar superseded'}`:(zh?'\u672a\u77e5':'Unknown')],
 [zh?'\u7ba1\u5f84\u53d6\u503c\u6765\u6e90':'DN source',zh?'\u5e73\u9762\u590d\u5408\u6807\u6ce8\u4e2d\u5df2\u5bf9\u5e94\u7684\u6210\u5458\uff1b\u8f74\u6d4b\u6807\u6ce8\u53c2\u4e0e\u6838\u5bf9':'Matched plan declaration; axis caption is a cross-check'],
 [zh?'\u6574\u8fb9\u5b89\u88c5\u957f\u5ea6':'Whole installed length',zh?'\u672a\u77e5':'Unknown']];
}
export const compoundMemberCsvFields=['compound_member_mapping_id','compound_member_plan_edge','compound_member_scope_id','compound_member_plan_LINE','compound_member_axis_LINE','compound_member_plan_DN_mm','compound_member_plan_run_centerline_mm','compound_member_literal_level','compound_member_prior_scalar_DN_mm','compound_member_evidence_json'];
export function compoundMemberCsvValues(edge,context=null){
 const r=checkedCompoundMember(edge,context);
 if(!r)return hasCompoundMemberScope(edge,context)?{diameter_nominal_mm:'',diameter_text:'',diameter_status:'compound_member_evidence_invalid',batch_plan_DN_mm:'',batch_whole_axis_DN_mm:'',batch_retained_prior_whole_DN_mm:'',batch_uniform_group_child_DN_mm:''}:{};
 const lineage=JSON.stringify(r.plan_declarations),proof=context.compound_member_mains.source_bindings.native_proof;
 return {diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`,diameter_status:'native_compound_member_plan_DN',
 crossview_mapping_id:r.mapping_id,crossview_plan_edges:r.plan_edge_id,crossview_plan_horizontal_projection_mm:r.plan_run_centerline_mm,crossview_projection_allocation:'native_member_T_to_T_run',crossview_metric_status:'native_member_plan_run_centerline',crossview_whole_edge_length_mm:'',crossview_plan_drawn_nominal_mm:r.nominal_mm,crossview_plan_DN_scope_status:'source_checked_physical_member',crossview_plan_DN_scope_sha256:proof,crossview_axis_diameter_observation_mm:r.axis_caption_crosscheck.text.nominal_mm,crossview_plan_source_sha256:r.source_plan_sha256,
 batch_mapping_id:r.mapping_id,batch_plan_edges:r.plan_edge_id,batch_plan_DN_mm:r.nominal_mm,batch_plan_pipe_XY_mm:r.plan_run_centerline_mm,batch_complete_horizontal_centerline_mm:r.plan_run_centerline_mm,batch_whole_axis_DN_mm:r.nominal_mm,batch_plan_DN_lineage_json:lineage,batch_scope_status:'native_compound_member_source_scope',batch_retained_prior_whole_DN_mm:'',batch_uniform_group_child_DN_mm:'',batch_DN_resolution_basis:'plan_declaration_with_independent_member_identity',
 compound_member_mapping_id:r.mapping_id,compound_member_plan_edge:r.plan_edge_id,compound_member_scope_id:r.member_scope_id,compound_member_plan_LINE:r.plan_LINE,compound_member_axis_LINE:r.axis_LINE,compound_member_plan_DN_mm:r.nominal_mm,compound_member_plan_run_centerline_mm:r.plan_run_centerline_mm,compound_member_literal_level:r.source_level_literal,compound_member_prior_scalar_DN_mm:r.superseded_scalar_observation?.plan_nominal_mm??'',compound_member_evidence_json:JSON.stringify(r)};
}

export function hasNoncompoundMainExtent(edge,context=null){return context?.noncompound_main_extents?.records?.some(r=>r.axis_edge_id===edge.edge_id)===true;}
export function checkedNoncompoundMainExtent(edge,context=null){
 const root=context?.noncompound_main_extents,h=root?.source_bindings;
 if(root?.mode!=='qualified_native_noncompound_main_extents_v1'||root.existing_attribute_owners_preserved!==true||root.compound_carriers_excluded!==true||root.source_paths_mutated!==false||root.local_topology_changed!==false||root.installed_lengths_assigned!==0||root.human_accepted!==false)return null;
 if(!h||![h.axis_graph,h.rendered_graph,h.native_proof,h.member_proof].every(v=>cmHash.test(v||''))||h.axis_graph!==context.source_graph_sha256||h.rendered_graph!==context.rendered_graph_sha256||h.member_proof!==context.compound_member_mains?.source_bindings?.native_proof)return null;
 if(!Array.isArray(root.records)||root.records.length!==root.axis_edges||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.axis_edges)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id),s=checkedBatchPlanScope(edge);
 if(!r||!s||!cmPositive(r.nominal_mm)||!cmPositive(r.complete_horizontal_centerline_route_mm)||r.nominal_mm!==s.plan_drawn_nominal_mm||r.mapping_id!==s.mapping_id||!cmSame(s.plan_edges,[r.plan_edge_id]))return null;
 if(r.system!==edge.system||r.axis_start_node!==edge.start_node_id||r.axis_end_node!==edge.end_node_id||!cmSame(r.axis_attribute_paths,edge.attribute_paths)||r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor))return null;
 if(r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||r.source_paths_mutated!==false||r.whole_installed_length_mm!==null||r.net_pipe_cut_length_mm!==null)return null;
 for(const view of ['plan','iso'])for(const k of ['source','graph'])if(r.source_hashes?.[view]?.[`${k}_sha256`]!==s[`${k}_sha256`]?.[view])return null;
 const p=r.source_projection;
 if(!p||p.installed_whole_edge_length_mm!==null||p.value_mm!==r.complete_horizontal_centerline_route_mm||!Array.isArray(p.pieces)||!p.pieces.length||p.pieces.some(v=>!cmPositive(v.length_mm))||Math.abs(p.pieces.reduce((a,v)=>a+v.length_mm,0)-p.value_mm)>0.0001)return null;
 if(Object.entries(r.endpoint_relations||{}).length!==2||!['plan','iso'].every(k=>['start_to_end','end_to_start'].includes(r.endpoint_relations[k]?.path_orientation)&&r.endpoint_relations[k].source_path_unchanged===true&&r.endpoint_relations[k].flow_direction_inferred===false))return null;
 for(const key of ['compound_member_mains','member_plan_runs','ordered_group_plan_runs','ordered_anchor_branches','anchor_bounded_mains'])if(context[key]?.records?.some(v=>v.axis_edge_id===edge.edge_id))return null;
 return r;
}
export function noncompoundMainExtentProperties(edge,zh=true,context=null){
 const r=checkedNoncompoundMainExtent(edge,context);if(!r)return [];
 return [[zh?'\u7ba1\u5f84':'Pipe diameter',`DN${r.nominal_mm}`],[zh?'\u697c\u5c42\u4f4d\u7f6e':'Floor',`${r.floor}F`],
 [zh?'\u5e73\u9762 T\u2014T \u4e3b\u7ba1\u4e2d\u5fc3\u7ebf\uff08\u542b\u5143\u4ef6\u8303\u56f4\uff09':'Plan T-to-T main centreline',`${(r.complete_horizontal_centerline_route_mm/1000).toFixed(3)} m`],
 [zh?'\u957f\u5ea6\u6765\u6e90':'Length source',`SH16 ${String(7+r.floor).padStart(2,'0')} / ${r.plan_edge_id}`],
 [zh?'\u539f\u56fe\u7ba1\u5f84\u4f9d\u636e':'Plan DN evidence',(r.plan_DN_record?.lineage||[]).flatMap(c=>(c.evidence||[]).map(e=>e.evidence_id)).join('; ')||r.DN_status],
 [zh?'\u5b9e\u9645\u5b89\u88c5\u5168\u957f / \u51c0\u622a\u7ba1\u957f':'Installed whole / net cut length',zh?'\u672a\u77e5':'Unknown']];
}
export const noncompoundMainExtentCsvFields=['noncompound_main_mapping_id','noncompound_main_plan_edge','noncompound_main_DN_mm','noncompound_main_complete_centerline_mm','noncompound_main_plan_source_sha256','noncompound_main_source_order','noncompound_main_evidence_json'];
export function noncompoundMainExtentCsvValues(edge,context=null){
 const r=checkedNoncompoundMainExtent(edge,context);
 if(!r)return hasNoncompoundMainExtent(edge,context)?{batch_complete_horizontal_centerline_mm:''}:{};
 return {batch_complete_horizontal_centerline_mm:r.complete_horizontal_centerline_route_mm,
 noncompound_main_mapping_id:r.mapping_id,noncompound_main_plan_edge:r.plan_edge_id,noncompound_main_DN_mm:r.nominal_mm,noncompound_main_complete_centerline_mm:r.complete_horizontal_centerline_route_mm,
 noncompound_main_plan_source_sha256:r.source_hashes.plan.source_sha256,noncompound_main_source_order:r.endpoint_relations.plan.path_orientation,noncompound_main_evidence_json:JSON.stringify(r)};
}


export function checkedCompoundInterface(edge,context=null){
 const root=context?.compound_member_interfaces,h=root?.source_bindings;
 if(root?.mode!=='qualified_circle_bracketed_compound_member_interfaces_v1'||root.existing_attribute_owners_preserved!==true||root.member_topology_rebuilt!==true||root.original_axis_geometry_unchanged!==true||root.installed_lengths_assigned!==0||root.human_accepted!==false)return null;
 if(!h||![h.axis_graph,h.rendered_graph,h.native_proof,h.member_proof].every(v=>cmHash.test(v||''))||h.axis_graph!==context.source_graph_sha256||h.rendered_graph!==context.rendered_graph_sha256||h.member_proof!==context.compound_member_mains?.source_bindings?.native_proof)return null;
 if(!Array.isArray(root.records)||root.records.length!==root.axis_edges||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.axis_edges)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r||!cmPositive(r.nominal_mm)||r.system!==edge.system||!cmSame(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!cmSame(r.axis_attribute_paths,edge.attribute_paths))return null;
 if(r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||r.DN_used_for_mapping!==false||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||r.installed_whole_length_mm!==null||r.net_pipe_cut_length_mm!==null||r.physical_elevation_mm!==null||r.plan_component_member_allocation!=='unresolved')return null;
 if(!['plan_source','axis_source','plan_graph','axis_graph'].every(k=>cmHash.test(r.source_hashes?.[k]||'')&&r.source_hashes[k]===root.native_sources?.[k]))return null;
 const p=r.plan_projection;if(!p||!cmPositive(p.value_mm)||p.installed_whole_edge_length_mm!==null||!Array.isArray(p.pieces)||!p.pieces.length||p.pieces.some(v=>!cmPositive(v.length_mm)||v.plan_edge!==r.plan_member_edge_id||v.source_line_handle!==r.plan_LINE)||Math.abs(p.pieces.reduce((a,v)=>a+v.length_mm,0)-p.value_mm)>0.0001)return null;
 if(r.kind==='primary_member_main'){if(r.complete_horizontal_centerline_route_mm!==p.value_mm)return null;}
 else if(r.kind==='lower_member_approach_with_local_rise'){if(r.complete_horizontal_centerline_route_mm!==null||r.local_rise_length_mm!==null||r.level_difference_used_as_length!==false)return null;}
 else return null;
 for(const key of ['compound_member_mains','member_plan_runs','ordered_group_plan_runs','ordered_anchor_branches','anchor_bounded_mains','noncompound_main_extents'])if(context[key]?.records?.some(v=>v.axis_edge_id===edge.edge_id))return null;
 return r;
}
export function compoundInterfaceProperties(edge,zh=true,context=null){
 const r=checkedCompoundInterface(edge,context);if(!r)return [];
 const main=r.kind==='primary_member_main',unknown=zh?'\u672a\u77e5':'Unknown';
 return [[zh?'\u7ba1\u5f84':'Pipe diameter',`DN${r.nominal_mm}`],[zh?'\u697c\u5c42\u4f4d\u7f6e':'Floor',`${r.floor}F`],
 [zh?'\u7ba1\u8def\u6210\u5458':'Member',main?(zh?'\u4e0a\u5c42\u4e3b\u7ba1\u6210\u5458':'Primary member'):(zh?'\u4e0b\u5c42\u6210\u5458\u63a5\u5165\u4e3b\u7ba1\uff1b\u542b\u5c40\u90e8\u5347\u964d':'Lower-member approach with local rise')],
 [main?(zh?'\u5e73\u9762 T\u2014T \u4e3b\u7ba1\u4e2d\u5fc3\u7ebf\uff08\u542b\u5143\u4ef6\u8303\u56f4\uff09':'Plan T-to-T main centreline'):(zh?'\u5df2\u77e5\u5e73\u9762\u6295\u5f71\u957f\u5ea6':'Known floor-plan projection'),`${(r.plan_projection.value_mm/1000).toFixed(3)} m`],
 [zh?'\u7ba1\u5f84\u4e0e\u957f\u5ea6\u6765\u6e90':'Plan evidence',`SH16 ${String(7+r.floor).padStart(2,'0')} / LINE ${r.plan_LINE} / ${r.plan_declarations.map(v=>v.text_handle).join('; ')}`],
 [zh?'\u6210\u5458\u63a5\u53e3\u4f9d\u636e':'Interface evidence',r.mapping_id],
 [zh?'\u5c40\u90e8\u5347\u964d\u957f\u5ea6':'Local rise length',main?(zh?'\u672c\u6bb5\u4e3a\u6c34\u5e73\u4e3b\u7ba1':'Horizontal main'):unknown],
 [zh?'\u5b9e\u9645\u5b89\u88c5\u5168\u957f / \u51c0\u622a\u7ba1\u957f':'Installed / net cut length',unknown],
 [zh?'\u5e73\u9762\u5143\u4ef6\u6309\u6210\u5458\u5206\u914d':'Plan component member allocation',unknown]];
}
export const compoundInterfaceCsvFields=['circle_member_mapping_id','circle_member_role','circle_member_plan_LINE','circle_member_DN_mm','circle_member_plan_projection_mm','circle_member_complete_centerline_mm','circle_member_level_literal','circle_member_source_sha256','circle_member_evidence_json'];
export function compoundInterfaceCsvValues(edge,context=null){
 const r=checkedCompoundInterface(edge,context);if(!r)return {};
 const base={diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`,diameter_status:'source_checked_plan_compound_member',physical_edge_length_status:r.kind==='primary_member_main'?'plan_member_main_centerline_including_inline_extents':'partial_plan_projection_local_rise_unknown',
 circle_member_mapping_id:r.mapping_id,circle_member_role:r.kind,circle_member_plan_LINE:r.plan_LINE,circle_member_DN_mm:r.nominal_mm,circle_member_plan_projection_mm:r.plan_projection.value_mm,
 circle_member_complete_centerline_mm:r.complete_horizontal_centerline_route_mm??'',circle_member_level_literal:r.literal_level_key,circle_member_source_sha256:r.source_hashes.plan_source,circle_member_evidence_json:JSON.stringify(r)};
 if(r.complete_horizontal_centerline_route_mm!==null)base.batch_complete_horizontal_centerline_mm=r.complete_horizontal_centerline_route_mm;
 return base;
}

export function checkedAxisVerticalSegments(edge,context=null){
 const root=context?.axis_vertical_segment_DN,h=root?.source_bindings;
 if(root?.mode!=='qualified_axis_vertical_segment_DN_context_v1'||root.existing_axis_segment_values_preserved!==true||root.horizontal_plan_attributes_preserved!==true||root.raw_axis_graph_unchanged!==true||root.whole_edge_DN_assigned!==0||root.physical_lengths_assigned!==0||root.human_accepted!==false)return [];
 if(!h||![h.raw_axis_graph,h.rendered_graph,h.native_axis_graph,h.native_vertical_DN_proof,root.axis_source_sha256].every(v=>cmHash.test(v||''))||h.raw_axis_graph!==context.source_graph_sha256||h.rendered_graph!==context.rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.segments)return [];
 const rows=root.records.filter(r=>r.edge_id===edge.edge_id);if(new Set(rows.map(r=>`${r.path_index}:${r.segment_index}`)).size!==rows.length)return [];
 if(rows.some(r=>!cmPositive(r.nominal_mm)||r.system!==edge.system||!Number.isInteger(r.path_index)||!Number.isInteger(r.segment_index)||!cmSame(edge.attribute_paths?.[r.path_index]?.slice(r.segment_index,r.segment_index+2),r.scope_points)||r.axis_source_sha256!==root.axis_source_sha256||r.whole_edge_DN_assigned!==false||r.physical_length_mm!==null||r.whole_edge_physical_length_mm!==null||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false||!r.observations?.length||r.observations.some(o=>o.nominal_mm!==r.nominal_mm||o.source_text?.source_sha256!==root.axis_source_sha256)))return [];
 return rows;
}
export function axisVerticalSegmentProperties(edge,zh=true,context=null){
 const rows=checkedAxisVerticalSegments(edge,context);if(!rows.length)return [];const result=[];
 for(const [i,r]of rows.entries()){result.push([zh?`\u7ad6\u76f4\u6bb5 ${i+1} \u7ba1\u5f84\uff0811\u53f7\u56fe\uff09`:`Vertical segment ${i+1} DN (axis)`,`DN${r.nominal_mm}`]);result.push([zh?`\u7ad6\u76f4\u6bb5 ${i+1} \u6e90\u56fe\u6807\u6ce8`:`Vertical segment ${i+1} evidence`,`SH16 11 / ${r.observations.map(o=>o.source_text.handle).join('; ')} / ${r.path_index}:${r.segment_index}`]);}
 result.push([zh?'\u672c\u8f6e\u7ad6\u76f4\u6bb5\u7269\u7406\u957f\u5ea6':'New vertical physical lengths',zh?'\u672a\u77e5\uff1b\u4e0d\u4ece\u5e73\u9762\u56fe\u53d6\u503c':'Unknown; axis evidence required']);return result;
}
export const axisVerticalSegmentCsvFields=['axis_vertical_DN_segment_count','axis_vertical_DN_segments_json','axis_vertical_DN_source_sha256'];
export function axisVerticalSegmentCsvValues(edge,context=null){const rows=checkedAxisVerticalSegments(edge,context);return rows.length?{axis_vertical_DN_segment_count:rows.length,axis_vertical_DN_segments_json:JSON.stringify(rows),axis_vertical_DN_source_sha256:context.axis_vertical_segment_DN.axis_source_sha256}:{};}

export function checkedCompoundBridge(edge,context=null){
 const root=context?.compound_member_bridges,h=root?.source_bindings;
 if(root?.mode!=='qualified_native_compound_member_inline_bridges_v1'||root.existing_attribute_owners_preserved!==true||root.member_topology_rebuilt!==true||root.original_axis_geometry_unchanged!==true||root.installed_lengths_assigned!==0||root.human_accepted!==false)return null;
 if(!h||![h.axis_graph,h.rendered_graph,h.native_proof,h.member_interfaces].every(v=>cmHash.test(v||''))||h.axis_graph!==context.source_graph_sha256||h.rendered_graph!==context.rendered_graph_sha256||h.member_interfaces!==context.compound_member_interfaces?.source_bindings?.native_proof)return null;
 if(!Array.isArray(root.records)||root.records.length!==root.axis_edges||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.axis_edges)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r||!cmPositive(r.nominal_mm)||!cmPositive(r.plan_pipe_projection_mm)||r.system!==edge.system||!cmSame(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!cmSame(r.axis_attribute_paths,edge.attribute_paths))return null;
 if(r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||r.DN_used_for_mapping!==false||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false||r.whole_centerline_length_mm!==null||r.installed_whole_length_mm!==null||r.net_pipe_cut_length_mm!==null||r.physical_elevation_mm!==null||r.inline_graphic_spans_used_as_physical_length!==false)return null;
 if(!Object.entries(root.native_sources??{}).every(([k,v])=>cmHash.test(v||'')&&r.source_hashes?.[k]===v)||!Array.isArray(r.plan_pieces)||!r.plan_pieces.length||Math.abs(r.plan_pieces.reduce((n,p)=>n+(p.measured_plan_pipe_projection_mm??0),0)-r.plan_pipe_projection_mm)>.0001||r.plan_pieces.some(p=>p.physical_inline_length_mm!==null))return null;
 if(!Array.isArray(r.component_correspondences)||new Set(r.component_correspondences.map(p=>p.axis.device_name)).size!==r.component_correspondences.length||!cmSame(r.component_correspondences.map(p=>p.axis.device_name).sort(),r.component_instance_identities.map(p=>p.source_device_name).sort()))return null;
 for(const key of ['compound_member_interfaces','compound_member_mains','member_plan_runs','ordered_group_plan_runs','ordered_anchor_branches','anchor_bounded_mains','noncompound_main_extents'])if(context[key]?.records?.some(v=>v.axis_edge_id===edge.edge_id))return null;
 return r;
}
export function compoundBridgeProperties(edge,zh=true,context=null){
 const r=checkedCompoundBridge(edge,context);if(!r)return [];const unknown=zh?'\u672a\u77e5':'Unknown';
 return [[zh?'\u7ba1\u5f84':'Pipe diameter',`DN${r.nominal_mm}`],[zh?'\u697c\u5c42\u4f4d\u7f6e':'Floor',`${r.floor}F`],
 [zh?'\u5df2\u7ed8\u7ba1\u7ebf\u5e73\u9762\u6295\u5f71\uff08\u4e0d\u542b\u8f6f\u63a5\uff09':'Drawn plan pipe projection excluding inline joints',`${(r.plan_pipe_projection_mm/1000).toFixed(3)} m`],
 [zh?'\u5b8c\u6574\u4e2d\u5fc3\u7ebf\u957f\u5ea6':'Complete centreline length',unknown],[zh?'\u8f6f\u63a5\u5b9e\u9645\u957f\u5ea6':'Inline joint physical length',unknown],
 [zh?'\u7ba1\u5f84\u4e0e\u957f\u5ea6\u6765\u6e90':'Plan evidence',`SH16 ${String(7+r.floor).padStart(2,'0')} / ${r.source_parent_plan_edge} / ${r.plan_declarations.map(x=>x.text_handle).join('; ')}`],
 [zh?'\u7ba1\u5f84\u7ee7\u627f\u94fe':'DN inheritance',r.DN_inheritance_chain.join(' ; ')],
 [zh?'\u5143\u4ef6\u5b9e\u4f8b\u5bf9\u5e94':'Component instance correspondence',r.component_correspondences.map(x=>`${x.plan.source_handle} -> ${x.axis.source_handle}`).join('; ')],
 [zh?'\u5b9e\u9645\u5b89\u88c5\u5168\u957f / \u51c0\u622a\u7ba1\u957f':'Installed whole / net cut length',unknown]];
}
export const compoundBridgeCsvFields=['member_bridge_mapping_id','member_bridge_plan_edge','member_bridge_DN_mm','member_bridge_plan_pipe_projection_mm','member_bridge_component_pairs_json','member_bridge_evidence_json'];
export function compoundBridgeCsvValues(edge,context=null){
 const r=checkedCompoundBridge(edge,context);if(!r)return {};
 return {diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`,diameter_status:'source_checked_plan_member_bridge_inherited_DN',physical_edge_length_status:'partial_plan_pipe_projection_inline_joint_length_unknown',
 member_bridge_mapping_id:r.mapping_id,member_bridge_plan_edge:r.source_parent_plan_edge,member_bridge_DN_mm:r.nominal_mm,member_bridge_plan_pipe_projection_mm:r.plan_pipe_projection_mm,member_bridge_component_pairs_json:JSON.stringify(r.component_correspondences),member_bridge_evidence_json:JSON.stringify(r)};
}
