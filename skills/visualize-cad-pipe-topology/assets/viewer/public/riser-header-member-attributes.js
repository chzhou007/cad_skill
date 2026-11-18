const hash=/^[0-9a-f]{64}$/;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0;
function checkedRoot(context){
 const r=context?.riser_header_application,b=r?.source_bindings,g=context?.cycle_carrier_guards;
 if(r?.mode!=='qualified_riser_header_interval_application_v1'||r.native_mode!=='native_reanchored_riser_header_interval_application_v1'||r.independent_gate_ancestry_replayed!==true||r.member_and_origin_native_sources_replayed!==true||r.old_graphs_unchanged!==true||r.all_horizontal_values_from_plan!==true||r.vertical_values_assigned!==0||r.installed_lengths_assigned!==0||r.lower_terminal_identities_assigned!==0||r.human_accepted!==false||!b)return null;
 if(![r.source_proof_sha256,r.prior_guard_proof_sha256,...Object.values(b)].every(x=>hash.test(x||''))||b.raw_axis_graph!==context.source_graph_sha256||b.rendered_graph!==context.rendered_graph_sha256||r.prior_guard_proof_sha256!==g?.source_proof_sha256||b.cycle_metric!==context.graph_first_extensions?.source_bindings?.cycle_metric_proof)return null;
 if(g.mode!=='native_cycle_compound_carrier_guards_v1'||g.old_graphs_and_source_values_unchanged!==true||g.original_compound_carrier_reader_reused!==true||g.original_provider_and_riser_sources_independently_replayed!==true||g.physical_lengths_assigned!==0||g.physical_member_ids_assigned!==0||g.human_accepted!==false||g.source_graph_sha256!==context.source_graph_sha256||g.rendered_graph_sha256!==context.rendered_graph_sha256||!Array.isArray(g.records)||g.records.length!==g.held_cycle_lengths)return null;
 if(!Array.isArray(r.member_records)||r.member_records.length!==r.counts?.member_intervals||new Set(r.member_records.map(x=>x.axis_edge_id)).size!==r.member_records.length||!Array.isArray(r.cycle_clearances)||r.cycle_clearances.length!==r.counts?.cleared_cycle_metrics||new Set([...r.member_records,...r.cycle_clearances].map(x=>x.axis_edge_id)).size!==r.member_records.length+r.cycle_clearances.length)return null;
 return r;
}
export function checkedCycleCarrierClearance(edge,context){
 const root=checkedRoot(context);if(!root)return null;const r=root.cycle_clearances.find(x=>x.axis_edge_id===edge.edge_id),old=context.cycle_carrier_guards?.records?.find(x=>x.axis_edge_id===edge.edge_id),metric=context.graph_first_extensions?.cycle_records?.find(x=>x.axis_edge_id===edge.edge_id);
 if(!r||!old||!metric||r.system!==edge.system||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||r.mapping_id!==old.mapping_id||r.mapping_id!==metric.mapping_id||r.plan_edge_id!==old.plan_edge_id||r.complete_horizontal_centerline_mm!==metric.complete_horizontal_centerline_mm||!positive(r.complete_horizontal_centerline_mm)||r.source_plan_scope_no_remaining_compound_barrier!==true||r.physical_metric_native_replayed!==true||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false||!r.excluded_native_origins?.length||r.excluded_native_origins.some(x=>x.reason!=='coarse_composite_edge_other_arm_not_this_native_LINE'||x.physical_member_identity_inferred!==false||!x.native_atom_origins?.length||x.native_atom_origins.some(a=>a.unique_modelspace_LINE!==true||!a.source_LINE||a.source_LINE===x.source_LINE)))return null;
 return r;
}
export function checkedRiserHeaderMember(edge,context){
 const root=checkedRoot(context);if(!root)return null;const r=root.member_records.find(x=>x.axis_edge_id===edge.edge_id);if(!r)return null;
 if(r.system!==edge.system||r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||!['approach','riser'].includes(r.member_kind)||!r.member_scope_id?.startsWith('MEMBER-RISER:')||r.plan_member_edge_id!==r.member_scope_id+':'+r.member_kind||r.source_paths_mutated!==false||r.lower_terminal_identity_selected!==false||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false||r.unshown_connection_length_mm!==null||r.installed_length_mm!==null||r.net_pipe_cut_length_mm!==null)return null;
 const dn=r.nominal_mm,complete=r.complete_horizontal_centerline_mm,p=r.projection;
 if(dn!==null&&(!positive(dn)||r.DN_status!=='native_plan_member_declaration_and_direct_labels_checked'||r.native_DN_guard?.F_precedence_preserved!==true))return null;
 if(dn===null&&(r.DN_status!=='native_plan_member_DN_conflict'||!r.native_DN_guard?.conflict))return null;
 if(complete!==null&&(!positive(complete)||r.member_kind!=='approach'||complete!==r.drawn_plan_projection_mm))return null;
 if(!positive(r.drawn_plan_projection_mm)||p?.value_mm!==r.drawn_plan_projection_mm||p.installed_whole_edge_length_mm!==null||!p.pieces?.length||p.pieces.some(x=>!positive(x.length_mm))||Math.abs(p.pieces.reduce((s,x)=>s+x.length_mm,0)-p.value_mm)>.0001||r.endpoint_evidence?.riser_symbol_offset_added_to_length!==false||!Array.isArray(r.source_component_ids)||new Set(r.source_component_ids).size!==r.source_component_ids.length)return null;
 return r;
}
export function riserHeaderMemberProperties(edge,zh=true,context){
 const r=checkedRiserHeaderMember(edge,context);if(!r)return [];
 return [[zh?'\u7ba1\u5f84':'Pipe diameter',r.nominal_mm===null?(zh?'\u672a\u77e5\uff1b\u5e73\u9762\u6210\u5458\u7ba1\u5f84\u51b2\u7a81':'Unknown; plan member DN conflict'):`DN${r.nominal_mm}`],[zh?'\u697c\u5c42\u4f4d\u7f6e':'Floor',`${r.floor}F`],
 [zh?'\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\u957f\u5ea6':'Complete horizontal centreline',r.complete_horizontal_centerline_mm===null?(zh?'\u672a\u77e5\uff1b\u7acb\u7ba1\u7b26\u53f7\u5904\u63a5\u7ba1\u957f\u5ea6\u5c1a\u672a\u8bc1\u660e':'Unknown; riser-symbol connector unproved'):`${(r.complete_horizontal_centerline_mm/1000).toFixed(3)} m`],
 [zh?'\u5df2\u7ed8\u5e73\u9762\u8def\u5f84\u957f\u5ea6':'Drawn plan path',`${(r.drawn_plan_projection_mm/1000).toFixed(3)} m`],[zh?'\u5bf9\u5e94\u5e73\u9762\u6210\u5458':'Matched plan member',`09 / ${r.plan_member_edge_id}`],
 [zh?'\u8fde\u63a5\u4f9d\u636e':'Connection evidence',zh?'\u5b64\u7acb\u5706\u5708\u3001\u4e09\u652f\u8def\u539f\u751f\u62d3\u6251\u3001\u4e3b\u7ba1\u951a\u70b9\u53ca\u5143\u4ef6\u552f\u4e00\u5f52\u5c5e\u5171\u540c\u6838\u9a8c':'Native circle, three branches, independent gate and unique component allocation'],
 [zh?'\u7ba1\u5f84\u6765\u6e90':'DN source',`${context.riser_header_application.source_bindings.plan_source}; ${r.member_declaration.plan_declarations.map(x=>x.text_handle).join('; ')}`],
 [zh?'\u539f\u56fe\u5143\u4ef6\u8bc1\u636e':'Native component evidence',r.source_component_ids.join('; ')],[zh?'\u5b89\u88c5\uff0f\u51c0\u4e0b\u6599\u957f\u5ea6':'Installed / net cut length',zh?'\u672a\u77e5\uff1b\u4e0d\u589e\u52a0\u5706\u5708\u534a\u5f84\uff0c\u4e0d\u628a\u672a\u89c1\u63a5\u7ba1\u586b\u96f6':'Unknown; no circle-radius addition or zero-filled connector']];
}
export const riserHeaderCsvFields=['riser_header_mapping_id','riser_header_member_scope','riser_header_plan_edge','riser_header_plan_DN_mm','riser_header_complete_centerline_mm','riser_header_drawn_projection_mm','riser_header_plan_source_sha256','riser_header_evidence_json','cycle_carrier_clearance_status','cycle_carrier_clearance_evidence_json'];
export function riserHeaderCsvValues(edge,context){
 const r=checkedRiserHeaderMember(edge,context),c=checkedCycleCarrierClearance(edge,context),out={};
 if(r)Object.assign(out,{riser_header_mapping_id:r.mapping_id,riser_header_member_scope:r.member_scope_id,riser_header_plan_edge:r.plan_member_edge_id,riser_header_plan_DN_mm:r.nominal_mm??'',riser_header_complete_centerline_mm:r.complete_horizontal_centerline_mm??'',riser_header_drawn_projection_mm:r.drawn_plan_projection_mm,riser_header_plan_source_sha256:context.riser_header_application.source_bindings.plan_source,riser_header_evidence_json:JSON.stringify(r)});
 if(c)Object.assign(out,{cycle_carrier_clearance_status:'native_atom_origin_replayed_scope_cleared',cycle_carrier_clearance_evidence_json:JSON.stringify(c)});return out;
}
