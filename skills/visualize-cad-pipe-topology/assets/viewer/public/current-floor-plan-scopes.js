const hash=/^[0-9a-f]{64}$/;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const positive=v=>Number.isFinite(v)&&v>0;
export function checkedCurrentFloorPlanScope(edge){
 const s=edge.current_floor_plan_scope_evidence,c=edge.cross_view_attributes;
 if(!s||!c||s.edge_id!==edge.edge_id||s.system!==edge.system||s.floor!==c.floor||s.historical_mapping_id!==c.mapping_id||!same(s.plan_edges,c.plan_edges)||!same(s.iso_edges,c.iso_edges))return null;
 if(![s.plan_graph_sha256,s.iso_graph_sha256,s.prior_plan_graph_sha256,s.source_scope_sha256,s.historical_attribute_sha256,s.source_sha256?.plan,s.source_sha256?.iso].every(v=>hash.test(v||'')))return null;
 if(s.source_sha256.plan!==c.source_hashes?.plan||s.source_sha256.iso!==c.source_hashes?.isometric||s.iso_graph_sha256!==c.source_hashes?.local_iso_graph||s.prior_plan_graph_sha256!==c.source_hashes?.plan_graph)return null;
 if([s.whole_axis_DN_selected,s.physical_ports_verified,s.equal_plan_axis_segment_extents_proved,s.related_HIL_confirmation_inherited,s.human_accepted].some(v=>v!==false)||s.whole_axis_physical_length_mm!==null)return null;
 const d=s.diameter,m=s.horizontal_projection,old=c.diameter?.plan_drawn_nominal_mm??c.diameter?.plan_candidate?.nominal_mm;
 if(s.plan_edges.length!==1||s.iso_edges.length!==1||s.iso_edges[0]!==edge.edge_id||d?.edge_id!==s.plan_edges[0]||d.system!==s.system||!positive(d.nominal_mm)||d.nominal_mm!==old||!Array.isArray(d.lineage)||!d.lineage.length||d.human_accepted!==false)return null;
 if(!m||!Array.isArray(m.pieces)||!m.pieces.length||!same(m.pieces,c.horizontal_projection?.pieces)||m.value_mm!==c.horizontal_projection?.value_mm||m.installed_whole_edge_length_mm!==null||m.unshown_connection_length_mm!==null)return null;
 if(m.value_mm===null){const x=m.detail_context;if(m.status!=='source_confirmed_detail_topology_physical_length_unknown'||x?.physical_units_applied!==false||x.plan_graph_sha256!==s.plan_graph_sha256||x.plan_source_sha256!==s.source_sha256.plan||x.human_accepted!==false||!same(x.plan_edges,s.plan_edges))return null;}else if(!positive(m.value_mm))return null;
 const candidates=s.axis_local_DN_candidates;if(!Array.isArray(candidates)||new Set(candidates.map(r=>r.source_text?.handle)).size!==candidates.length)return null;
 for(const p of candidates){const points=edge.attribute_paths?.[p.path_index]?.slice(p.segment_index,p.segment_index+2);if(p.edge_id!==edge.edge_id||p.system!==edge.system||p.status!=='segment_dn_candidate_not_accepted'||p.source_text?.source_sha256!==s.source_sha256.iso||!positive(p.nominal_mm_candidate)||!p.source_line_handle||!Number.isInteger(p.path_index)||!Number.isInteger(p.segment_index)||!same(points,p.scope_points)||p.whole_axis_DN_selected!==false||p.inter_floor_riser_proved!==false||p.physical_length_mm!==null||p.human_accepted!==false)return null;}
 return s;
}
export function currentFloorPlanScopeProperties(edge,zh=true){
 const s=checkedCurrentFloorPlanScope(edge);if(!s)return [];
 const value=s.horizontal_projection.value_mm;
 const rows=[[zh?'\u5f53\u524d\u5e73\u9762\u56fe\u56de\u8bc1':'Current floor-plan verification',s.current_mapping_id],
  [zh?'\u5f53\u524d\u5e73\u9762\u5df2\u7ed8\u7247\u6bb5\u7ba1\u5f84':'Current drawn-plan DN',`DN${s.diameter.nominal_mm} [${s.floor}F]`],
  [zh?'\u5f53\u524d\u5e73\u9762XY\u6295\u5f71':'Current plan XY projection',value===null?(zh?'\u672a\u77e5\uff1b\u8be6\u56fe\u8de8\u5ea6\u4e0d\u8ba1\u7269\u7406\u957f\u5ea6':'Unknown; detail span is not physical length'):`${(value/1000).toFixed(3)} m`],
  [zh?'\u5c5e\u6027\u8303\u56f4':'Attribute extent',zh?'\u5e73\u9762\u5df2\u7ed8\u7247\u6bb5\uff1b\u8bbe\u5907\u63a5\u7ba1\u53ca\u6574\u8fb9\u5b89\u88c5\u957f\u5ea6\u4ecd\u672a\u77e5':'Drawn plan scope; equipment connectors and installed whole length remain unknown']];
 if(s.axis_local_DN_candidates.length)rows.push([zh?'11\u53f7\u56fe\u5c40\u90e8\u6807\u6ce8\u5019\u9009':'Local axis annotation candidates',s.axis_local_DN_candidates.map(p=>`DN${p.nominal_mm_candidate} [11:${p.source_text.handle}; ${p.path_index}/${p.segment_index}]`).join('; ')],[zh?'\u7ba1\u5f84\u8303\u56f4\u4e92\u8bc1':'DN extent comparison',zh?'\u5206\u522b\u4fdd\u7559\uff1b\u672a\u8bc1\u660e\u4e0e\u5e73\u9762\u7247\u6bb5\u8303\u56f4\u76f8\u540c':'Retained separately; equal plan/axis extents unproved']);
 return rows;
}
export const currentFloorPlanScopeCsvFields=['current_floor_scope_mapping_id','current_floor_scope_plan_graph_sha256','current_floor_scope_evidence_sha256','current_floor_scope_DN_mm','current_floor_scope_XY_mm','current_floor_scope_axis_local_DN_candidates_json'];
export function currentFloorPlanScopeCsvValues(edge){
 const s=checkedCurrentFloorPlanScope(edge);if(!s)return {};
 return {current_floor_scope_mapping_id:s.current_mapping_id,current_floor_scope_plan_graph_sha256:s.plan_graph_sha256,current_floor_scope_evidence_sha256:s.source_scope_sha256,current_floor_scope_DN_mm:s.diameter.nominal_mm,current_floor_scope_XY_mm:s.horizontal_projection.value_mm??'',current_floor_scope_axis_local_DN_candidates_json:JSON.stringify(s.axis_local_DN_candidates)};
}
