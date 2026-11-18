const hash=/^[0-9a-f]{64}$/,same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function checkedAnchoredTerminalBranch(edge,context){
 const root=context?.anchored_terminal_branches,b=root?.source_bindings;
 if(root?.mode!=='qualified_anchored_terminal_drawing_branches_v1'||root.complete_published_parent_replayed!==true||root.all_current_independent_main_third_arms_screened!==true||root.graph_mutated!==false||root.old_providers_replaced!==false||root.remote_equipment_identities_assigned!==0||root.physical_ports_created!==0||root.whole_axis_DN_assigned!==0||root.whole_axis_lengths_assigned!==0||root.vertical_values_assigned!==0||root.human_accepted!==false||!b||!Object.values(b).every(v=>hash.test(v||''))||b.raw_axis_graph!==context.source_graph_sha256||b.rendered_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.count)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r)return null;
 const axis=r.native_checks?.iso?.snapshot?.edges?.[0],plan=r.native_checks?.plan?.snapshot?.edges?.[0];
 if(!axis||!plan||axis.edge_id!==edge.edge_id||r.system!==edge.system||r.floor!==edge.floor_start||r.floor!==edge.floor_end||!same(axis.attribute_paths,edge.attribute_paths)||!same([axis.start_node_id,axis.end_node_id],[edge.start_node_id,edge.end_node_id])||r.source_graphs_mutated!==false||r.physical_port_verified!==false||r.remote_equipment_identity_inferred!==false||r.whole_axis_DN_selected!==false||r.whole_axis_physical_length_mm!==null||r.vertical_values_assigned!==0||r.human_accepted!==false||r.source_scope!=='source_checked_third_arm_drawing_context_not_remote_identity')return null;
 const dn=r.plan_DN_record,metric=r.plan_horizontal_projection;
 if(dn?.edge_id!==r.plan_edge_id||(dn.nominal_mm!==null&&(typeof dn.nominal_mm!=='number'||!Number.isFinite(dn.nominal_mm)||dn.nominal_mm<=0))||dn.system!==r.system||!same(dn.scope_paths,plan.attribute_paths)||typeof metric?.value_mm!=='number'||!Number.isFinite(metric.value_mm)||metric.value_mm<=0||metric.installed_whole_edge_length_mm!==null||metric.unshown_connection_length_mm!==null||!metric.pieces?.length||Math.abs(metric.pieces.reduce((s,p)=>s+p.length_mm,0)-metric.value_mm)>.0001)return null;
 return r;
}
export function anchoredTerminalBranchProperties(edge,prior,zh,context){
 const r=checkedAnchoredTerminalBranch(edge,context);if(!r)return prior;const label=(a,b)=>zh?a:b;
 return [...prior,[label('\u65c1\u652f\u5e73\u9762\u5c40\u90e8\u7ba1\u5f84','Branch local plan diameter'),r.plan_DN_record.nominal_mm===null?label('\u672a\u77e5\uff1b\u4fdd\u7559\u539f\u6807\u6ce8\u51b2\u7a81\u6216\u8303\u56f4','Unknown; original source scope retained'):'DN'+r.plan_DN_record.nominal_mm],
 [label('\u65c1\u652f\u5e73\u9762\u5df2\u7ed8\u8def\u5f84','Branch drawn plan path'),(r.plan_horizontal_projection.value_mm/1000).toFixed(3)+' m'],
 [label('\u65c1\u652f\u5e73\u9762\u6765\u6e90','Branch plan source'),String(r.floor+7).padStart(2,'0')+' / '+r.plan_edge_id],
 [label('\u5bf9\u5e94\u4f9d\u636e','Correspondence evidence'),label('\u4e3b\u7ba1\u4e24\u81c2\u5df2\u72ec\u7acb\u5bf9\u5e94\uff0c\u7b2c\u4e09\u81c2\u53ca\u4e24\u4fa7\u539f\u751f\u7b26\u53f7\uff0f\u8def\u5f84\u590d\u8bc1','Two independently mapped main arms; native third arm and drawing boundaries replayed')],
 [label('\u65c1\u652f\u53c2\u6570\u8303\u56f4','Branch parameter scope'),label('\u4ec5\u5e73\u9762\u5df2\u7ed8\u8303\u56f4\uff1b\u7ad6\u5411\u4ecd\u53d611\u56fe\uff0c\u6574\u8fb9\u957f\u5ea6\u548c\u8fdc\u7aef\u8bbe\u5907\u8eab\u4efd\u672a\u77e5','Drawn plan scope only; all vertical portions use drawing 11; whole length and remote identity unknown')]];
}
export const anchoredTerminalBranchCsvFields=['anchored_branch_mapping_id','anchored_branch_plan_edge','anchored_branch_plan_DN_mm','anchored_branch_plan_pipe_XY_mm','anchored_branch_plan_source_sha256','anchored_branch_plan_graph_sha256','anchored_branch_scope','anchored_branch_evidence_json'];
export function anchoredTerminalBranchCsvValues(edge,context){const r=checkedAnchoredTerminalBranch(edge,context);if(!r)return{};return{anchored_branch_mapping_id:r.mapping_id,anchored_branch_plan_edge:r.plan_edge_id,anchored_branch_plan_DN_mm:r.plan_DN_record.nominal_mm??'',anchored_branch_plan_pipe_XY_mm:r.plan_horizontal_projection.value_mm,anchored_branch_plan_source_sha256:context.anchored_terminal_branches.source_bindings.plan_source,anchored_branch_plan_graph_sha256:context.anchored_terminal_branches.source_bindings.plan_graph,anchored_branch_scope:r.source_scope,anchored_branch_evidence_json:JSON.stringify(r)};}

export function anchoredTerminalConnectionProperties(edge,context,previous){
 const r=checkedAnchoredTerminalBranch(edge,context);if(!r)return [['Connection',previous]];
 return [['\u5f53\u524d\u53ef\u89c1\u652f\u8def','\u4e3b\u7ba1T\u548c\u53ef\u89c1\u6e90\u7ebf\u5df2\u56de\u8bc1\uff1b\u7b26\u53f7\u540e\u8fdc\u7aef\u8bbe\u5907\u672a\u77e5'],['\u5386\u53f2\u56fe\u7ea7\u8fde\u63a5\u72b6\u6001',previous]];
}
