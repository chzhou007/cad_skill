const hash=/^[0-9a-f]{64}$/;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0;
function root(context){
 const r=context?.equivalent_member_application,b=r?.source_bindings;
 if(r?.mode!=='qualified_equivalent_member_plan_attributes_v1'||r.native_mode!=='native_equivalent_member_plan_attribute_application_v1'||!b||r.complete_source_batch_replayed!==true||r.existing_complete_DN_provider_retained!==true||r.specific_calibrated_and_F_readers_reapplied!==true||r.all_horizontal_values_from_plan!==true||r.source_graphs_mutated!==false||r.DN_used_for_mapping!==false||r.physical_pipe_count_inferred!==false||r.unknown_length_filled_with_zero!==false||r.vertical_values_assigned!==0||r.installed_lengths_assigned!==0||r.human_accepted!==false)return null;
 if(![r.source_proof_sha256,...Object.values(b)].every(x=>hash.test(x||''))||b.raw_axis_graph!==context.source_graph_sha256||b.rendered_graph!==context.rendered_graph_sha256||b.native_axis_graph!==context.riser_header_application?.source_bindings?.axis_graph||!Array.isArray(r.records)||r.records.length!==r.counts?.new_correspondence_intervals||new Set(r.records.map(x=>x.axis_edge_id)).size!==r.records.length||new Set(r.records.map(x=>x.mapping_id)).size!==r.records.length)return null;
 return r;
}
export function checkedCohortMember(edge,context){
 const c=root(context);if(!c)return null;const r=c.records.find(x=>x.axis_edge_id===edge.edge_id);if(!r)return null;
 const m=r.native_mapping,dn=r.qualified_plan_DN_record;
 if(r.system!==edge.system||r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||r.source_paths_mutated!==false||r.DN_used_for_mapping!==false||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false||r.vertical_values_assigned!==0||r.installed_length_mm!==null||r.net_pipe_cut_length_mm!==null||!r.mapping_id?.startsWith('MEMBER-INTERVAL-')||m?.mapping_id!==r.mapping_id||!same(m.plan_edges,[r.plan_edge_id])||!same(m.iso_edges,[edge.edge_id])||m.system!==r.system||m.floor!==r.floor||m.human_accepted!==false||!same(m.incomplete_reasons,r.incomplete_reasons)||m.complete_horizontal_centerline_mm!==r.complete_horizontal_centerline_mm||m.drawn_plan_projection_mm!==r.drawn_plan_projection_mm||dn?.edge_id!==r.plan_edge_id||dn.system!==r.system||!same(dn.scope_paths,r.plan_attribute_paths)||dn.nominal_mm!==r.nominal_mm)return null;
 if(r.nominal_mm!==null&&(!positive(r.nominal_mm)||!['existing_qualified_native_plan_DN_retained','native_specific_plan_DN_reapplied'].includes(r.DN_status)||!r.native_extent_check))return null;
 if(r.nominal_mm===null&&!['native_plan_DN_conflict','existing_native_annotation_provider_application_pending'].includes(r.DN_status))return null;
 if(!positive(r.drawn_plan_projection_mm)||m.native_metric?.projection?.value_mm!==r.drawn_plan_projection_mm||!Array.isArray(r.incomplete_reasons)||r.complete_horizontal_centerline_mm!==null&&(!positive(r.complete_horizontal_centerline_mm)||r.complete_horizontal_centerline_mm!==r.drawn_plan_projection_mm||r.incomplete_reasons.length))return null;
 return r;
}
export function cohortMemberProperties(edge,zh=true,context){
 const r=checkedCohortMember(edge,context);if(!r)return [];
 const label=(a,b)=>zh?a:b;const known=r.nominal_mm!==null;const complete=r.complete_horizontal_centerline_mm!==null;
 const sources=[...new Set((r.qualified_plan_DN_record.lineage||[]).flatMap(l=>(l.evidence||[]).map(e=>e.evidence_id)).filter(Boolean))];
 return [[label('\u7ba1\u5f84','Pipe diameter'),known?`DN${r.nominal_mm}`:label(r.DN_status==='native_plan_DN_conflict'?'\u672a\u77e5\uff1b\u5e73\u9762\u56fe\u7ba1\u5f84\u6765\u6e90\u51b2\u7a81':'\u672a\u77e5\uff1b\u539f\u6807\u6ce8\u4f5c\u7528\u533a\u95f4\u5f85\u6838\u9a8c','Unknown; native plan DN unresolved')],
 [label('\u697c\u5c42\u4f4d\u7f6e','Floor'),`${r.floor}F`],
 [label('\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\u957f\u5ea6','Complete horizontal centreline'),complete?`${(r.complete_horizontal_centerline_mm/1000).toFixed(3)} m`:label('\u672a\u77e5\uff1b\u8f6f\u63a5\u6216\u8de8\u7ba1\u7701\u7565\u7684\u5b8c\u6574\u957f\u5ea6\u5c1a\u672a\u8bc1\u660e','Unknown; inline or crossing omission extent incomplete')],
 [label('\u5df2\u7ed8\u5e73\u9762\u8def\u5f84\u957f\u5ea6','Drawn plan path'),`${(r.drawn_plan_projection_mm/1000).toFixed(3)} m`],
 [label('\u5bf9\u5e94\u5e73\u9762\u8fb9','Matched plan edge'),`10 / ${r.plan_edge_id}`],
 [label('\u7ba1\u5f84\u6765\u6e90','DN source'),sources.length?sources.join('; '):label('\u4fdd\u7559\u539f\u56fe\u51b2\u7a81\u8bc1\u636e','Original conflicting evidence retained')],
 [label('\u8fde\u63a5\u4f9d\u636e','Connection evidence'),label('\u5b8c\u6574\u8bbe\u5907\u652f\u8def\u3001\u539f\u751fT\u8282\u70b9\u53ca\u4e24\u56fe\u4e3b\u7ba1\u987a\u5e8f\u5171\u540c\u6838\u9a8c','Complete equipment branches, native Ts and two-view main order')],
 [label('\u5b89\u88c5\uff0f\u51c0\u4e0b\u6599\u957f\u5ea6','Installed / net cut length'),label('\u672a\u77e5\uff1b\u672a\u5c06\u56fe\u793a\u7701\u7565\u6216\u672a\u89c1\u63a5\u7ba1\u586b\u96f6','Unknown; no zero-filled omissions or connectors')]];
}
export const cohortMemberCsvFields=['cohort_member_mapping_id','cohort_member_plan_edge','cohort_member_plan_DN_mm','cohort_member_complete_centerline_mm','cohort_member_drawn_projection_mm','cohort_member_DN_status','cohort_member_length_status','cohort_member_plan_source_sha256','cohort_member_source_scope_ids','cohort_member_evidence_json'];
export function cohortMemberCsvValues(edge,context){
 const r=checkedCohortMember(edge,context);if(!r)return {};
 const out={cohort_member_mapping_id:r.mapping_id,cohort_member_plan_edge:r.plan_edge_id,cohort_member_plan_DN_mm:r.nominal_mm??'',cohort_member_complete_centerline_mm:r.complete_horizontal_centerline_mm??'',cohort_member_drawn_projection_mm:r.drawn_plan_projection_mm,cohort_member_DN_status:r.DN_status,cohort_member_length_status:r.complete_horizontal_centerline_mm===null?'native_incomplete_source_extent':'native_complete_plan_T_to_T_centerline',cohort_member_plan_source_sha256:context.equivalent_member_application.source_bindings.plan_source,cohort_member_source_scope_ids:r.source_member_observation_ids.join('; '),cohort_member_evidence_json:JSON.stringify(r)};
 if(r.nominal_mm!==null)Object.assign(out,{diameter_nominal_mm:r.nominal_mm,diameter_text:`DN${r.nominal_mm}`,diameter_status:'cohort_member_native_plan_DN'});
 return out;
}
