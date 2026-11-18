const hash=/^[0-9a-f]{64}$/,same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function checkedCappedBranch(edge,context){
 const root=context?.capped_branch_correspondence,b=root?.source_bindings;
 if(root?.mode!=='qualified_native_capped_branch_drawing_context_v1'||root.graph_mutated!==false||root.other_system_ports_assigned!==0||root.remote_equipment_identities_assigned!==0||root.physical_lengths_assigned!==0||root.whole_axis_DN_assigned!==0||root.vertical_values_assigned!==0||root.human_accepted!==false||!b||!Object.values(b).every(v=>hash.test(v||''))||b.raw_axis_graph!==context.source_graph_sha256||b.attribute_context_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.count)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r)return null;
 const axis=r.native_checks?.iso?.snapshot?.edges?.[0],cap=r.plan_cap,port=r.axis_cap_port;
 if(!axis||axis.edge_id!==edge.edge_id||r.system!==edge.system||r.floor!==edge.floor_start||r.floor!==edge.floor_end||!same(axis.attribute_paths,edge.attribute_paths)||!same([axis.start_node_id,axis.end_node_id],[edge.start_node_id,edge.end_node_id])||r.scope!=='native_capped_third_arm_drawing_correspondence_only'||r.other_system_port_assigned!==false||r.remote_equipment_identity_assigned!==false||r.whole_axis_DN_selected!==false||r.whole_axis_physical_length_mm!==null||r.vertical_values_assigned!==0||r.human_accepted!==false||cap?.qualifier?.text!=='\u76f2\u677f\u5c01\u5835'||r.axis_cap?.qualifier_text!==cap.qualifier.text||cap.caption?.declared_group_quantity!==r.axis_cap?.declared_quantity||cap.system!==edge.system||port?.system!==edge.system||port?.edge_id!==edge.edge_id||![edge.start_port_id,edge.end_port_id].includes(port.port_id)||r.axis_drawing_port?.port_id!==port.port_id)return null;
 return r;
}
export function cappedBranchProperties(edge,context,zh){
 const r=checkedCappedBranch(edge,context);if(!r)return[];
 return [[zh?'\u9884\u7559\u5c01\u5835\u652f\u8def\u5bf9\u5e94':'Capped branch correspondence',`${String(r.floor+7).padStart(2,'0')} / ${r.plan_edge_id} \u2192 11 / ${r.axis_edge_id}`],
 [zh?'\u5c01\u5835\u6807\u6ce8':'Cap declaration',`${r.plan_cap.caption.text}\uff1b${r.plan_cap.qualifier.text}`],
 [zh?'\u5bf9\u5e94\u4f9d\u636e':'Correspondence evidence',zh?'\u4e3b\u7ba1\u4e24\u4fa7\u8fde\u63a5\u3001\u4e2d\u6587\u5c01\u5835\u6807\u6ce8\u53ca\u72ec\u7acb\u7aef\u53e3\u5747\u5df2\u6838\u5bf9':'Independent main arms, native capped captions and separate marker port checked'],
 [zh?'\u5bf9\u5e94\u8303\u56f4':'Correspondence scope',zh?'\u4ec5\u672c\u7cfb\u7edf\u652f\u8def\uff1b\u672a\u6807\u957f\u5ea6\u4e0e\u8fdc\u7aef\u8bbe\u5907\u4fdd\u6301\u672a\u77e5':'This system branch only; unlabelled length and remote equipment remain unknown']];
}
export const cappedBranchFields=['capped_branch_mapping_id','capped_branch_plan_edge','capped_branch_plan_node','capped_branch_axis_port','capped_branch_scope','capped_branch_evidence_json'];
export function cappedBranchCsvValues(edge,context){const r=checkedCappedBranch(edge,context);return r?{capped_branch_mapping_id:r.mapping_id,capped_branch_plan_edge:r.plan_edge_id,capped_branch_plan_node:r.plan_cap.node_id,capped_branch_axis_port:r.axis_cap_port.port_id,capped_branch_scope:r.scope,capped_branch_evidence_json:JSON.stringify(r)}:{};}
