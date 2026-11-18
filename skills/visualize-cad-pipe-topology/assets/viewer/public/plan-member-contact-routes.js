const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=/^[0-9a-f]{64}$/;
export function checkedPlanMemberContact(edge,context){
 const root=context?.plan_member_contact_routes,b=root?.source_bindings;
 if(root?.mode!=='qualified_plan_member_contact_viewer_v1'||root.physical_values_assigned!==0||root.axis_3D_reader_unchanged!==true||root.human_accepted!==false||!b||!Object.values(b).every(x=>hash.test(x||''))||!Array.isArray(root.records)||root.count!==root.records.length||new Set(root.records.map(r=>r.axis_edge_id)).size!==root.count)return null;
 const r=root.records.find(r=>r.axis_edge_id===edge.edge_id);if(!r)return null;
 if(r.native_T?.plan?.graph_sha256!==b.plan_graph||r.native_T?.axis?.graph_sha256!==b.native_axis_graph)return null;
 if(r.kind!=='member_to_ordinary_external_route'||r.system!==edge.system||edge.floor_start!==r.floor||edge.floor_end!==r.floor||!same(r.axis_nodes,[edge.start_node_id,edge.end_node_id])||!same(r.axis_attribute_paths,edge.attribute_paths)||!r.member_node_id?.startsWith('MEMBER:')||r.plan_remote?.startsWith('MEMBER:')||!r.axis_nodes.includes(r.member_axis_node)||!r.axis_nodes.includes(r.axis_remote)||r.member_axis_node===r.axis_remote||r.original_source_Z_preserved!==true||r.axis_component_reader_3D_unchanged!==true||r.plan_component_reading_mode!=='qualified_member_floor_plan_XY_contact_reading_v1'||r.whole_edge_DN_mm!==null||r.whole_edge_physical_length_mm!==null||r.physical_values_assigned!==0||r.attribute_adoption_allowed!==false||r.human_accepted!==false)return null;
 return r;
}
export function planMemberContactProperties(edge,prior,zh,context){
 const r=checkedPlanMemberContact(edge,context);if(!r)return prior;
 return [...prior,[zh?'\u5e73\u9762\u6210\u5458\u8def\u5f84\u5bf9\u5e94':'Plan member correspondence',`${r.floor===1?'08':r.floor===2?'09':'10'} / ${r.member_node_id} \u2194 ${r.plan_remote} / 11 ${r.member_axis_node} \u2194 ${r.axis_remote}`],
 [zh?'\u672c\u6b21\u8fde\u63a5\u4f9d\u636e':'Connection evidence',zh?'\u539f\u751f\u4e09\u901a\u3001\u5706\u5708\u7701\u7565\u4e0e\u6709\u5e8f\u5143\u4ef6\u5171\u540c\u56de\u8bc1\uff1b\u5e73\u9762\u63a5\u89e6\u6309XY\u8bfb\u53d6\uff0c\u539f\u59cbZ\u4fdd\u7559':'Native T, circle omission and ordered components; plan XY reading retains raw Z'],
 [zh?'\u957f\u5ea6\u4e0e\u7ad6\u6bb5\u8fb9\u754c':'Metric and vertical scope',zh?'\u4ec5\u8865\u9f50\u8def\u5f84\u5bf9\u5e94\uff1b\u5b9e\u9645\u63a5\u7ba1\u957f\u5ea6\u672a\u77e5\uff0c\u7ad6\u76f4\u90e8\u5206\u4ecd\u53d611\u56fe':'Correspondence only; installed connector length unknown, vertical portions remain on drawing11']];
}
export const planMemberContactCsvFields=['plan_member_contact_mapping_id','plan_member_contact_plan_path','plan_member_contact_evidence_json'];
export function planMemberContactCsvValues(edge,context){const r=checkedPlanMemberContact(edge,context);return r?{plan_member_contact_mapping_id:r.mapping_id,plan_member_contact_plan_path:r.plan_source_edge_id,plan_member_contact_evidence_json:JSON.stringify(r)}:{};}
