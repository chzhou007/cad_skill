const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=/^[0-9a-f]{64}$/;
export function checkedTwoArmExternalRoute(edge,context){
 const root=context?.native_two_arm_external_routes,b=root?.source_bindings;
 if(root?.mode!=='qualified_native_two_arm_external_routes_v1'||root.original_two_arm_rule_reused!==true||root.physical_Ts_added!==0||root.new_pipe_attribute_values!==0||root.human_accepted!==false||!b||!Object.values(b).every(v=>hash.test(v||''))||b.raw_axis_graph!==context.source_graph_sha256||b.rendered_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.count)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r)return null;
 if(r.kind!=='member_to_ordinary_external_route'||r.system!==edge.system||r.floor!==(edge.floor_start??edge.start_floor)||r.floor!==(edge.floor_end??edge.end_floor)||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||r.mixed_attribute_source_split_required!==true||r.whole_edge_DN_mm!==null||r.whole_edge_physical_length_mm!==null||r.physical_values_assigned!==0||r.attribute_adoption_allowed!==false||r.human_accepted!==false||!r.axis_nodes.includes(r.member_axis_node)||!r.axis_nodes.includes(r.axis_remote)||r.member_axis_node===r.axis_remote)return null;
 const binding=r.source_reading_graph_binding;
 if(!hash.test(binding?.source?.sha256||'')||!hash.test(binding?.reading_graph_sha256||'')||binding.separate_reading_graph!==true||!Object.values(binding.edge_aliases||{}).includes(r.plan_source_edge_id)||r.native_T?.plan?.graph_sha256!==binding.reading_graph_sha256||r.native_T?.axis?.graph_sha256!==b.native_axis_graph)return null;
 if(!r.source_omissions?.length||r.source_omissions.some(o=>o.kind!=='replayed_native_two_arm_circle_unknown_connector_length'||o.physical_connector_length_mm!==null||o.evidence?.physical_T_proven!==false||o.evidence?.physical_connector_length_mm!==null||o.evidence.system!==r.system||o.evidence.blockers?.length!==0))return null;
 return r;
}
export function twoArmExternalProperties(edge,prior,zh,context){
 const r=checkedTwoArmExternalRoute(edge,context);if(!r)return prior;const label=(a,b)=>zh?a:b;
 return [...prior,[label('\u5e73\u9762\u8fde\u7eed\u5173\u7cfb','Plan continuity'),`10 / ${r.plan_source_edge_id} / ${r.plan_remote} ↔ 11 / ${r.axis_remote}`],
 [label('\u8fde\u63a5\u4f9d\u636e','Connection evidence'),label('\u539f\u751f\u4e24\u81c2\u5706\u5708\u8fde\u7eed\uff1b\u5df2\u91cd\u5efa\u8fb9\u4e0e\u6210\u5458\u8def\u5f84\uff0c\u672a\u65b0\u589e\u4e09\u901a','Native two-arm circle; edge and member path rebuilt without adding a T')],
 [label('\u672c\u6b21\u5c5e\u6027\u72b6\u6001','Current attribute status'),label('\u4ec5\u8865\u9f50\u8fde\u63a5\u5bf9\u5e94\uff1b\u5706\u5708\u5185\u5b9e\u9645\u63a5\u7ba1\u957f\u5ea6\u672a\u77e5\uff0c\u7ad6\u5411\u90e8\u5206\u4ecd\u53d6\u0031\u0031\u53f7\u56fe','Correspondence only; circle connector length unknown, vertical portions still use drawing 11')]];
}
export const twoArmExternalCsvFields=['two_arm_external_mapping_id','two_arm_external_plan_path','two_arm_external_source_scope','two_arm_external_evidence_json'];
export function twoArmExternalCsvValues(edge,context){const r=checkedTwoArmExternalRoute(edge,context);return r?{two_arm_external_mapping_id:r.mapping_id,two_arm_external_plan_path:r.plan_source_edge_id,two_arm_external_source_scope:r.source_reading_graph_binding.reading_graph_sha256,two_arm_external_evidence_json:JSON.stringify(r)}:{};}
