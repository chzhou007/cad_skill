const positive=n=>typeof n==='number'&&Number.isFinite(n)&&n>0;
export function checkedAnchoredMain(edge){
 const a=edge.anchored_floor_main_attributes;if(!a)return null;
 const d=a.diameter_evidence,m=a.horizontal_projection;
 if(!['source_checked_anchored_floor_main_attributes_human_pending','source_checked_known_junction_main_attributes_human_pending'].includes(a.status)||a.scope!=='native_same_floor_T_to_T_main'||a.axis_edge!==edge.edge_id||a.iso_edges?.length!==1||a.iso_edges[0]!==edge.edge_id||a.plan_edges?.length!==1||a.system!==edge.system||a.floor!==(edge.floor_start??edge.start_floor)||a.floor!==(edge.floor_end??edge.end_floor)||JSON.stringify(a.scope_paths)!==JSON.stringify(edge.attribute_paths)||a.human_accepted!==false||a.physical_ports_verified!==false||a.related_HIL_confirmation_inherited!==false||a.installed_whole_edge_length_mm!==null||a.pipe_net_cut_length_mm!==null||![a.mapping_sha256,a.attribute_scope_sha256,a.parent_graph_sha256].every(s=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s))||!d||d.edge_id!==a.plan_edges[0]||d.system!==a.system||d.nominal_mm!==a.nominal_mm||!d.lineage?.length||!m||!positive(m.value_mm)||!m.pieces?.length||m.pieces.some(p=>!positive(p.length_mm))||Math.abs(m.pieces.reduce((n,p)=>n+p.length_mm,0)-m.value_mm)>.0001)return null;
 if(a.nominal_mm===null){if(!['conflict','unresolved'].includes(d.status))return null;}
 else if(!positive(a.nominal_mm)||!['direct_plan_DN','T_inherited_plan_DN'].includes(d.status))return null;
 if(a.inline_interiors_unknown===true){if(a.complete_horizontal_centerline_route_mm!==null||m.joint_graphic_spans_added!==false||m.inline_joint_interior_length_mm!==null)return null;}
 else if(a.inline_interiors_unknown!==false||a.complete_horizontal_centerline_route_mm!==m.value_mm)return null;
 return a;
}
export function anchoredMainProperties(edge,zh=true){
 const a=checkedAnchoredMain(edge);if(!a)return [];
 const dn=a.nominal_mm===null?(zh?'\u672a\u77e5\uff1b\u6807\u6ce8\u7ee7\u627f\u51b2\u7a81':'Unknown; conflicting annotation inheritance'):`DN${a.nominal_mm}`;
 return [[zh?'\u5e73\u9762\u4e3b\u7ba1\u7ba1\u5f84':'Floor-plan main DN',dn],
 [zh?'\u5e73\u9762\u7ba1\u7ebfXY\u957f\u5ea6':'Plan pipe XY length',`${a.horizontal_projection.value_mm.toFixed(2)} mm${a.inline_interiors_unknown?(zh?'\uff08\u4e0d\u542b\u8f6f\u63a5\u5185\u90e8\uff09':' (inline interiors excluded)'):''}`],
 [zh?'\u5b8c\u6574\u6c34\u5e73\u4e2d\u5fc3\u7ebf\u8def\u5f84':'Complete horizontal centerline route',a.complete_horizontal_centerline_route_mm===null?(zh?'\u672a\u77e5':'Unknown'):`${a.complete_horizontal_centerline_route_mm.toFixed(2)} mm`],
 [zh?'\u5e73\u9762\u6765\u6e90':'Plan source',`${a.floor}F / ${a.plan_edges.join(' / ')} / ${a.mapping_id}`],
 [zh?'\u7ba1\u5f84\u7ee7\u627f\u94fe':'DN inheritance lineage',a.diameter_evidence.lineage.map(l=>`DN${l.nominal_mm}: ${(l.evidence||[]).map(e=>`${e.evidence_id} ${(e.edge_path||[]).join(' -> ')}`).join('; ')}`).join(' | ')],
 [zh?'\u5b89\u88c5\u51c0\u7ba1\u957f':'Installed net pipe length',zh?'\u672a\u77e5\uff1b\u672a\u6309\u96f6\u8ba1\u5165':'Unknown; not counted as zero']];
}
export const anchoredMainCsvFields=['anchored_main_mapping_id','anchored_main_plan_edges','anchored_main_plan_XY_mm','anchored_main_complete_centerline_mm','anchored_main_DN_evidence_json','anchored_main_source_json','anchored_main_inline_interiors_unknown'];
export function anchoredMainCsvValues(edge){
 const a=checkedAnchoredMain(edge);if(!a)return {};
 return {diameter_nominal_mm:a.nominal_mm??'',diameter_text:a.nominal_mm===null?'':`DN${a.nominal_mm}`,diameter_status:a.diameter_evidence.status,
 anchored_main_mapping_id:a.mapping_id,anchored_main_plan_edges:a.plan_edges.join(';'),anchored_main_plan_XY_mm:a.horizontal_projection.value_mm,
 anchored_main_complete_centerline_mm:a.complete_horizontal_centerline_route_mm??'',anchored_main_DN_evidence_json:JSON.stringify(a.diameter_evidence),
 anchored_main_source_json:JSON.stringify(a.source_sha256),anchored_main_inline_interiors_unknown:a.inline_interiors_unknown};
}
