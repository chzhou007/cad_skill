const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const hash=/^[0-9a-f]{64}$/;
const positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0;
export function checkedContactOwnerPath(edge,context){
 const c=context?.contact_owner_application,b=c?.source_bindings,bridge=context?.component_inventory_bridge,prior=context?.contact_owner_prior_component_bridge;
 if(c?.mode!=='qualified_native_contact_owner_path_attributes_v1'||c.native_mode!=='native_contact_owner_scope_and_path_attribute_application_v1'||c.complete_current_parent_replayed!==true||c.native_owner_inventory_replayed!==true||c.all_affected_old_scopes_requalified!==true||c.pipe_graph_restoration_exact!==true||c.source_graphs_mutated!==false||c.DN_used_for_mapping!==false||c.physical_pipe_count_inferred!==false||c.unknown_physical_parameters_filled!==0||c.human_accepted!==false||!b)return null;
 if(![c.source_proof_sha256,...Object.values(b)].every(v=>hash.test(v||''))||b.raw_axis_graph!==context.source_graph_sha256||b.native_axis_graph!==context.riser_header_application?.source_bindings?.axis_graph||b.current_rendered_graph!==context.current_rendered_graph_sha256||b.current_rendered_graph!==bridge?.current_rendered_graph_sha256||b.parent_rendered_graph!==prior?.current_rendered_graph_sha256||bridge?.native_proof_sha256!==c.source_proof_sha256)return null;
 if(!Array.isArray(c.records)||c.records.length!==c.counts?.new_axis_intervals||new Set(c.records.map(r=>r.axis_edge_id)).size!==c.records.length||new Set(c.records.map(r=>r.mapping_id)).size!==c.records.length)return null;
 const r=c.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r)return null;
 const m=r.native_mapping,dn=r.qualified_plan_DN_record;
 if(r.system!==edge.system||r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||r.source_paths_mutated!==false||r.DN_used_for_mapping!==false||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false||r.vertical_values_assigned!==0||r.installed_length_mm!==null||r.net_pipe_cut_length_mm!==null||!r.mapping_id?.startsWith('MEMBER-INTERVAL-')||m?.mapping_id!==r.mapping_id||!same(m.plan_edges,[r.plan_edge_id])||!same(m.iso_edges,[edge.edge_id])||m.system!==r.system||m.floor!==r.floor||m.human_accepted!==false||!same(m.incomplete_reasons,r.incomplete_reasons)||m.complete_horizontal_centerline_mm!==r.complete_horizontal_centerline_mm||m.drawn_plan_projection_mm!==r.drawn_plan_projection_mm||dn?.edge_id!==r.plan_edge_id||dn.system!==r.system||!same(dn.scope_paths,r.plan_attribute_paths)||dn.nominal_mm!==r.nominal_mm)return null;
 if(r.nominal_mm!==null&&(!positive(r.nominal_mm)||!['existing_qualified_native_plan_DN_retained','native_specific_plan_DN_reapplied'].includes(r.DN_status)||!r.native_extent_check))return null;
 if(r.nominal_mm===null&&!['native_plan_DN_conflict','existing_native_annotation_provider_application_pending'].includes(r.DN_status))return null;
 if(!positive(r.drawn_plan_projection_mm)||m.native_metric?.projection?.value_mm!==r.drawn_plan_projection_mm||!Array.isArray(r.incomplete_reasons)||r.complete_horizontal_centerline_mm!==null&&(!positive(r.complete_horizontal_centerline_mm)||r.complete_horizontal_centerline_mm!==r.drawn_plan_projection_mm||r.incomplete_reasons.length))return null;
 return r;
}
export function contactOwnerPathProperties(edge,zh=true,context){
 const r=checkedContactOwnerPath(edge,context);if(!r)return [];
 const label=(a,b)=>zh?a:b,complete=r.complete_horizontal_centerline_mm;
 return [[label('\u7ba1\u5f84','Pipe diameter'),r.nominal_mm===null?label('\u672a\u77e5\uff1b\u5e73\u9762\u6807\u6ce8\u6765\u6e90\u51b2\u7a81\u6216\u4f5c\u7528\u8303\u56f4\u672a\u9f50','Unknown; plan source conflict or incomplete scope'):`DN${r.nominal_mm}`],
 [label('\u697c\u5c42\u4f4d\u7f6e','Floor'),`${r.floor}F`],
 [label('\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\u957f\u5ea6','Complete horizontal centreline'),complete===null?label('\u672a\u77e5\uff1b\u8f6f\u63a5\u5185\u90e8\u6216\u6e90\u56fe\u7701\u7565\u957f\u5ea6\u672a\u8bc1\u660e','Unknown; inline or omitted extent unproved'):`${(complete/1000).toFixed(3)} m`],
 [label('\u5df2\u7ed8\u5e73\u9762\u8def\u5f84','Drawn plan path'),`${(r.drawn_plan_projection_mm/1000).toFixed(3)} m`],
 [label('\u5bf9\u5e94\u5e73\u9762\u8fb9','Matched plan edge'),`${String(r.floor+7).padStart(2,'0')} / ${r.plan_edge_id}`],
 [label('\u8fde\u63a5\u4f9d\u636e','Connection evidence'),label('\u5143\u4ef6\u7269\u7406\u5f52\u5c5e\u3001\u539f\u6709\u8bbe\u5907\u7aef\u53e3\u548c\u4e24\u56fe\u4e09\u901a\u8def\u5f84\u5171\u540c\u56de\u8bc1','Native component ownership, original equipment ports and two-view T paths')],
 [label('\u5b89\u88c5\uff0f\u51c0\u4e0b\u6599\u957f\u5ea6','Installed / net cut length'),label('\u672a\u77e5\uff1b\u672a\u628a\u56fe\u793a\u957f\u5ea6\u6216\u7f3a\u53e3\u586b\u96f6','Unknown; drawing lengths and gaps not zero-filled')]];
}
export const contactOwnerPathCsvFields=['contact_owner_mapping_id','contact_owner_plan_edge','contact_owner_plan_DN_mm','contact_owner_complete_centerline_mm','contact_owner_drawn_projection_mm','contact_owner_DN_status','contact_owner_length_status','contact_owner_plan_source_sha256','contact_owner_source_scope_ids','contact_owner_evidence_json'];
export function contactOwnerPathCsvValues(edge,context){
 const r=checkedContactOwnerPath(edge,context);if(!r)return {};
 const out={contact_owner_mapping_id:r.mapping_id,contact_owner_plan_edge:r.plan_edge_id,contact_owner_plan_DN_mm:r.nominal_mm??'',contact_owner_complete_centerline_mm:r.complete_horizontal_centerline_mm??'',contact_owner_drawn_projection_mm:r.drawn_plan_projection_mm,contact_owner_DN_status:r.DN_status,contact_owner_length_status:r.complete_horizontal_centerline_mm===null?'native_incomplete_source_extent':'native_complete_plan_T_to_T_centerline',contact_owner_plan_source_sha256:context.contact_owner_application.source_bindings.plan_source,contact_owner_source_scope_ids:r.source_member_observation_ids.join('; '),contact_owner_evidence_json:JSON.stringify(r)};
 if(r.nominal_mm!==null)Object.assign(out,{diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`,diameter_status:'native_contact_owner_plan_DN'});
 return out;
}
