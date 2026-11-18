const hash=/^[0-9a-f]{64}$/;
const positive=v=>Number.isFinite(v)&&v>0;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function checkedOrderedBranch(edge,context=null){
 const root=context?.ordered_anchor_branches;if(!root||root.mode!=='qualified_ordered_anchor_drawn_branch_attributes_v1'||root.local_topology_mutated!==false||root.whole_axis_values_assigned!==0||root.physical_ports_created!==0||root.human_accepted!==false)return null;
 const h=root.source_bindings;if(!h||![h.axis_graph,h.rendered_graph,h.branch_proof].every(v=>hash.test(v||''))||h.axis_graph!==context.source_graph_sha256||h.rendered_graph!==context.rendered_graph_sha256)return null;
 if(!Array.isArray(root.records)||root.records.length!==root.axis_edges||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.records.length)return null;
 const rows=root.records.filter(r=>r.axis_edge_id===edge.edge_id);if(rows.length!==1)return null;const r=rows[0];
 if(r.system!==edge.system||r.axis_start_node!==edge.start_node_id||r.axis_end_node!==edge.end_node_id||r.axis_marker_handle!==edge.source_insert_handle||![edge.start_port_id,edge.end_port_id].includes(r.axis_port_id)||!same(r.axis_attribute_paths,edge.attribute_paths)||![edge.floor_start??edge.start_floor,edge.floor_end??edge.end_floor].every(f=>f===r.floor))return null;
 if(edge.batch_plan_attribute_scopes||edge.cross_view_attributes||edge.axis_riser_attributes||edge.plan_segment_attributes||r.whole_axis_DN_selected!==false||r.whole_axis_physical_length_mm!==null||r.physical_port_verified!==false||r.remote_equipment_identity_inferred!==false||r.circle_radius_added_to_metric!==false||r.axis_marker_centre_span_added_to_metric!==false||r.related_HIL_confirmation_inherited!==false||r.human_accepted!==false)return null;
 const p=r.plan_horizontal_projection;if(!positive(r.known_plan_pipe_XY_mm)||p?.value_mm!==r.known_plan_pipe_XY_mm||p.installed_whole_edge_length_mm!==null||!p.pieces?.length||Math.abs(p.pieces.reduce((s,v)=>s+v.length_mm,0)-p.value_mm)>.0001||p.pieces.some(v=>!r.plan_edges.includes(v.plan_edge)||!positive(v.length_mm)))return null;
 if(![r.source_sha256?.plan,r.source_sha256?.iso,r.plan_graph_sha256].every(v=>hash.test(v||''))||r.local_DN_evidence_status!=='exact_qualified_local_plan_DN_retained_not_fresh_global_DN_rebuild'||!r.plan_boundary_id||!r.main_anchor?.plan_node||!r.main_anchor?.axis_node)return null;
 if(r.plan_drawn_nominal_mm!==null&&(!positive(r.plan_drawn_nominal_mm)||!r.plan_DN_records?.length||r.plan_DN_records.some(d=>d.nominal_mm!==r.plan_drawn_nominal_mm||d.system!==r.system||d.human_accepted!==false)))return null;
 return r;
}
export function orderedBranchProperties(edge,zh=true,context=null){
 const r=checkedOrderedBranch(edge,context);if(!r)return [];
 return [[zh?'\u5e73\u9762\u5df2\u7ed8\u652f\u8def\u7ba1\u5f84':'Drawn plan branch DN',r.plan_drawn_nominal_mm===null?(zh?'\u672a\u77e5':'Unknown'):`DN${r.plan_drawn_nominal_mm}`],
 [zh?'\u5e73\u9762\u5df2\u7ed8\u652f\u8def\u7ebf\u957f':'Drawn plan branch pipe XY',`${(r.known_plan_pipe_XY_mm/1000).toFixed(3)} m`],
 [zh?'\u652f\u8def\u5bf9\u5e94\u4f9d\u636e':'Branch correspondence basis',`${r.main_anchor.plan_node} \u2194 ${r.main_anchor.axis_node}${zh?'\uff1b\u53cc\u56fe\u540c\u7cfb\u7edf\u4e3b\u7ba1\u4e09\u901a\u7684\u552f\u4e00\u652f\u8def':' ; unique same-system off-main branch'}`],
 [zh?'\u5e73\u9762\u5c5e\u6027\u6765\u6e90':'Plan attribute source',`SH16 ${String(r.floor+7).padStart(2,'0')} / ${r.plan_edges.join(' / ')} / ${r.plan_boundary_id}`],
 [zh?'\u7ed8\u56fe\u63a5\u53e3':'Drawing interface',`${r.axis_port_id}${zh?'\uff1b\u4fdd\u7559\u539f\u7ed8\u56fe\u7aef\u53e3\uff0c\u4e0d\u4ee3\u8868\u771f\u5b9e\u8bbe\u5907\u63a5\u53e3':' ; existing drawing port, not a verified physical equipment port'}`],
 [zh?'\u6574\u6761\u8f74\u6d4b\u8fb9\u7ba1\u5f84\u4e0e\u957f\u5ea6':'Whole axis-edge DN and length',zh?'\u672a\u77e5\uff1b\u8fd9\u91cc\u53ea\u5bf9\u5e94\u5e73\u9762\u5df2\u7ed8\u8303\u56f4\uff0c\u672a\u753b\u63a5\u7ba1\u4e0e\u5c40\u90e8\u7ad6\u5411\u8303\u56f4\u672a\u8865\u503c':'Unknown; matched drawn plan scope only; unshown connectors and local vertical extents remain unknown'],
 [zh?'\u91cf\u6d4b\u6392\u9664\u9879':'Metric exclusions',zh?'\u672a\u52a0\u5165\u8fde\u63a5\u5708\u56fe\u5f62\u534a\u5f84\u3001\u63a5\u53e3\u4e2d\u5fc3\u663e\u793a\u7ebf\u6bb5\u6216\u672a\u753b\u63a5\u7ba1':'Circle radii, marker-centre display spans and unshown connectors excluded']];
}
export const orderedBranchCsvFields=['ordered_branch_mapping_id','ordered_branch_plan_edges','ordered_branch_plan_DN_mm','ordered_branch_plan_pipe_XY_mm','ordered_branch_plan_boundary_id','ordered_branch_axis_drawing_port','ordered_branch_DN_evidence_status','ordered_branch_whole_axis_DN_mm','ordered_branch_whole_axis_length_mm','ordered_branch_evidence_json'];
export function orderedBranchCsvValues(edge,context=null){
 const r=checkedOrderedBranch(edge,context);if(!r)return {};
 return {ordered_branch_mapping_id:r.mapping_id,ordered_branch_plan_edges:r.plan_edges.join(';'),ordered_branch_plan_DN_mm:r.plan_drawn_nominal_mm??'',ordered_branch_plan_pipe_XY_mm:r.known_plan_pipe_XY_mm,ordered_branch_plan_boundary_id:r.plan_boundary_id,ordered_branch_axis_drawing_port:r.axis_port_id,ordered_branch_DN_evidence_status:r.local_DN_evidence_status,ordered_branch_whole_axis_DN_mm:'',ordered_branch_whole_axis_length_mm:'',ordered_branch_evidence_json:JSON.stringify(r)};
}
