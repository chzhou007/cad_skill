const hash=/^[a-f0-9]{64}$/;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function checkedRoot(edge,context,rootKey,mode){
 const root=context?.[rootKey],h=root?.source_bindings;
 if(root?.mode!==mode||root.human_accepted!==false||root.old_mapping_IDs_preserved!==true||root.historical_contexts_preserved!==true||root.new_mixed_or_vertical_lengths!==0||root.installed_lengths_assigned!==0)return null;
 if(!h||![h.axis_graph,h.rendered_graph,h.native_proof,h.axis_local_graph,h.plan_graph].every(v=>hash.test(v||''))||h.axis_graph!==context.source_graph_sha256||h.rendered_graph!==context.rendered_graph_sha256)return null;
 const rows=root.records?.filter(r=>r.axis_edge_id===edge.edge_id);if(rows?.length!==1)return null;const r=rows[0],m=r.mapping;
 if(r.system!==edge.system||r.plan_graph_sha256!==h.plan_graph||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||r.DN_used_for_mapping!==false||r.human_accepted!==false||r.related_HIL_confirmation_inherited!==false)return null;
 if(!m||m.kind!=='same_floor_T_to_T_main'||m.mapping_id!==r.mapping_id||m.status!=='native_path_correspondence_independently_source_checked'||m.DN_used_for_mapping!==false||m.system!==r.system||m.floor!==r.floor||!same(m.plan_edges,[r.plan_edge_id])||!same(m.iso_edges,[edge.edge_id]))return null;
 if(![edge.floor_start??edge.start_floor,edge.floor_end??edge.end_floor].every(f=>f===r.floor)||![r.nominal_mm,r.horizontal_plan_run_centerline_mm].every(v=>Number.isFinite(v)&&v>0)||r.net_pipe_cut_length_mm!==null||r.installed_whole_edge_length_mm!==null||r.unshown_branch_connector_length_mm!==null||r.run_centerline_includes_inline_assembly_extents!==true||r.detail_inline_positions_scaled_to_plan!==false)return null;
 const angles=context.horizontal_directions_degrees;if(!Array.isArray(angles)||angles.some(v=>Math.abs(v-90)<.1))return null;
 for(const path of edge.attribute_paths??[])for(let i=1;i<path.length;i++){const a=path[i-1],b=path[i],d=(Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI+180)%180;if(!angles.some(v=>Math.min(Math.abs(d-v),180-Math.abs(d-v))<.1))return null;}
 for(const [key,other]of Object.entries(context))if(key!==rootKey&&other?.records?.some(v=>v.axis_edge_id===edge.edge_id))return null;
 return r;
}
function resolvedRun(edge,context=null){
 const roots=[['ordered_owner_plan_runs','qualified_ordered_owner_crossview_plan_runs_v1'],['qualified_plan_scope_runs','qualified_source_provider_plan_runs_v1']];
 const matches=roots.map(([key,mode])=>({root:context?.[key],record:checkedRoot(edge,context,key,mode)})).filter(x=>x.record);
 return matches.length===1?matches[0]:null;
}
export function checkedOrderedOwnerRun(edge,context=null){return resolvedRun(edge,context)?.record??null;}
export function orderedOwnerRunProperties(edge,zh=true,context=null){
 const r=checkedOrderedOwnerRun(edge,context);if(!r)return [];
 return [[zh?'\u7ba1\u5f84':'DN',`DN${r.nominal_mm}`],[zh?'\u697c\u5c42\u4f4d\u7f6e':'Floor',`${r.floor}F`],[zh?'\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\u8def\u7531':'Complete horizontal centerline',`${(r.horizontal_plan_run_centerline_mm/1000).toFixed(3)} m`],[zh?'\u7ba1\u5f84\u4e0e\u957f\u5ea6\u6765\u6e90':'Plan source',`SH16 ${String(r.floor+7).padStart(2,'0')} / ${r.plan_edge_id} / LINE ${r.shared_projected_source_LINE} / TEXT ${r.compound_text_handle}`],[zh?'\u5bf9\u5e94\u4f9d\u636e':'Correspondence',zh?'\u539f\u8bbe\u5907\u5f52\u5c5e\u3001\u4e24\u4fa7\u4e09\u901a\u53ca\u540c\u7cfb\u7edf\u8def\u5f84\u72ec\u7acb\u6838\u5bf9\uff1b\u672a\u7528\u7ba1\u5f84\u9009\u62e9\u6620\u5c04':'Independent device, T and same-service paths; DN not used to match'],[zh?'\u6620\u5c04\u7f16\u53f7':'Mapping',r.mapping_id],[zh?'\u957f\u5ea6\u53e3\u5f84':'Length scope',zh?'\u4e09\u901a\u95f4\u4e2d\u5fc3\u7ebf\u542b\u8fb9\u4e0a\u5143\u4ef6\u533a\u95f4\uff1b\u5b9e\u9645\u5b89\u88c5\u5168\u957f\u3001\u51c0\u622a\u7ba1\u957f\u672a\u77e5':'T-to-T centreline includes inline extents; installed and net cut length unknown']];
}
export const orderedOwnerRunCsvFields=['ordered_owner_mapping_id','ordered_owner_plan_graph_sha256','ordered_owner_plan_run_evidence_json'];
export function orderedOwnerRunCsvValues(edge,context=null){
 const resolved=resolvedRun(edge,context);if(!resolved)return {};const {record:r,root}=resolved;
 return {diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`,diameter_status:'native_ordered_owner_member_plan_DN',physical_edge_length_status:'native_member_plan_run_centerline',crossview_mapping_id:r.mapping_id,crossview_plan_edges:r.plan_edge_id,crossview_plan_horizontal_projection_mm:r.horizontal_plan_run_centerline_mm,crossview_projection_allocation:'native_member_T_to_T_run',crossview_metric_status:'native_member_plan_run_centerline',crossview_plan_drawn_nominal_mm:r.nominal_mm,crossview_plan_DN_scope_status:'source_checked_physical_member',crossview_plan_DN_scope_sha256:root.source_bindings.native_proof,crossview_plan_source_sha256:r.source_sha256.plan,member_plan_run_centerline_mm:r.horizontal_plan_run_centerline_mm,member_plan_run_DN_mm:r.nominal_mm,member_plan_run_source_LINE:r.shared_projected_source_LINE,member_plan_run_source_TEXT:r.compound_text_handle,member_plan_run_edge:r.plan_edge_id,member_plan_run_includes_inline_extents:true,member_plan_net_pipe_cut_length_mm:'',member_plan_run_evidence_json:JSON.stringify(r),ordered_owner_mapping_id:r.mapping_id,ordered_owner_plan_graph_sha256:r.plan_graph_sha256,ordered_owner_plan_run_evidence_json:JSON.stringify(r)};
}
