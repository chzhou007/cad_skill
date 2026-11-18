// Original axis segment identities delimit plan-derived values.
export function checkedPlanSegments(edge){
 if(edge.plan_segment_attributes&&edge.network_named_lower_plan_attributes)return null;
 const rows=edge.plan_segment_attributes||(edge.network_named_lower_plan_attributes?[edge.network_named_lower_plan_attributes]:null),hash=/^[0-9a-f]{64}$/;
 if(!Array.isArray(rows)||rows.length!==1)return null;
 for(const r of rows){
  if(!r||typeof r!=='object')return null;
  const path=edge.attribute_paths?.[r.path_index],indices=r.segment_indices;
  const network=r.scope==='native_network_named_lower_floor_prefix_only';
  const lower=network||r.scope==='native_plan_matched_lower_floor_axis_segments_only';
  const kind=lower?'named_riser_lower_floor_segment_':'named_riser_floor_segment_';
  if(r.edge_id!==edge.edge_id||r.system!==edge.system||!['supply','return'].includes(r.system)||!Number.isInteger(r.floor)||!Number.isInteger(r.path_index)||r.path_index<0||!Array.isArray(indices)||!indices.length||indices.some((v,i)=>!Number.isInteger(v)||v<0||(i&&v!==indices[i-1]+1))||!path||indices.at(-1)>=path.length-1)return null;
  const points=path.slice(indices[0],indices.at(-1)+2);
  if(JSON.stringify(points)!==JSON.stringify(r.scope_points)||points.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>!Number.isFinite(v)))||!['native_plan_matched_upper_floor_axis_segments_only','native_plan_matched_lower_floor_axis_segments_only','native_network_named_lower_floor_prefix_only'].includes(r.scope)||r.human_accepted!==false||r.physical_port_verified!==false||r.pipe_net_cut_length_mm!==null||r.unshown_connection_length_mm!==null)return null;
  if(!['source_scope_sha256','mapping_sha256','attribute_parent_graph_sha256'].every(k=>hash.test(r[k]||''))||!['plan','iso'].every(k=>hash.test(r.source_sha256?.[k]||'')&&hash.test(r.local_graph_sha256?.[k]||'')))return null;
  const ids=network?['identifier','plan_riser_interface','plan_network_T','axis_network_T','mapping_id','independent_adjoining_main_mapping_id']:['identifier','equipment_anchor','plan_riser_interface','plan_network_T','axis_network_T','plan_equipment_T','axis_equipment_T','mapping_id'];
  if(!Number.isFinite(r.nominal_mm)||r.nominal_mm<=0||!ids.every(k=>typeof r[k]==='string'&&r[k].trim())||!new RegExp(r.system==='supply'?'^CHWS[1-9][0-9]*$':'^CHWR[1-9][0-9]*$').test(r.identifier)||r.plan_edges?.length!==1)return null;
  const d=r.diameter_evidence,m=r.horizontal_projection;
  if(d?.nominal_mm!==r.nominal_mm||d.system!==r.system||d.edge_id!==r.plan_edges[0]||d.scope!=='native_plan_drawn_pipe_paths_only'||d.human_accepted!==false||!d.lineage?.length||d.lineage.some(c=>c.nominal_mm!==r.nominal_mm||!c.evidence?.length||c.evidence.some(e=>typeof e.evidence_id!=='string'||!e.evidence_id.startsWith('source:')||!e.edge_path?.length||e.edge_path.at(-1)!==d.edge_id)))return null;
  if(!Array.isArray(d.scope_paths)||!d.scope_paths.length||d.scope_paths.some(path=>!Array.isArray(path)||path.length<2||path.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>!Number.isFinite(v)))))return null;
  if(!Number.isFinite(m?.value_mm)||m.value_mm<=0||m.installed_whole_edge_length_mm!==null||m.unshown_connection_length_mm!==null||!m.pieces?.length||m.pieces.length!==d.scope_paths.reduce((n,p)=>n+p.length-1,0)||new Set(m.pieces.map(p=>`${p.path_index}:${p.segment_index}`)).size!==m.pieces.length||m.pieces.some(p=>p.plan_edge!==d.edge_id||typeof p.source_line_handle!=='string'||!p.source_line_handle.trim()||!Number.isInteger(p.path_index)||!Number.isInteger(p.segment_index)||!Number.isFinite(p.length_mm)||p.length_mm<=0||!Array.isArray(p.points)||p.points.length!==2||JSON.stringify(d.scope_paths[p.path_index]?.slice(p.segment_index,p.segment_index+2))!==JSON.stringify(p.points)||Math.abs(Math.hypot(p.points[1][0]-p.points[0][0],p.points[1][1]-p.points[0][1])-p.length_mm)>.05)||Math.abs(m.pieces.reduce((sum,p)=>sum+p.length_mm,0)-m.value_mm)>.05)return null;
  if(r.whole_local_edge===true){
   if(r.mapping_kind!==kind+'network_link'||r.whole_edge_nominal_mm!==r.nominal_mm||r.whole_edge_centerline_route_mm!==m.value_mm||r.length_scope!=='complete_mapped_T_to_T_centerline_route_not_pipe_net_cut_length'||Number(edge.floor_start??edge.start_floor)!==r.floor||Number(edge.floor_end??edge.end_floor)!==r.floor||edge.attribute_paths.length!==1||JSON.stringify(path)!==JSON.stringify(points)||points.some((p,i)=>i&&Math.abs(p[0]-points[i-1][0])<=.05))return null;
  }else{
   if(r.whole_local_edge!==false||r.mapping_kind!==(network?'network_anchored_named_lower_floor_approach':kind+'approach')||r.whole_edge_nominal_mm!==null||r.whole_edge_centerline_route_mm!==null||r.length_scope!=='mapped_plan_drawn_approach_only'||!edge.axis_riser_attributes?.length||edge.axis_riser_attributes.some(v=>v.path_index===r.path_index&&indices.includes(v.segment_index)))return null;
   if(network){
    const v=edge.axis_riser_attributes[0],saved=r.retained_vertical_scope;
    if(r.whole_edge_physical_length_mm!==null||r.related_HIL_confirmation_inherited!==false||!saved||['edge_id','segment_index','scope_points','floor_pair','source_line_handle'].some(k=>JSON.stringify(v[k])!==JSON.stringify(saved[k])))return null;
   }
   if(lower){
    const v=edge.axis_riser_attributes[0];
    if(Number(edge.floor_start??edge.start_floor)!==r.floor||Number(edge.floor_end??edge.end_floor)!==r.floor+1||edge.attribute_paths.length!==1||r.path_index!==0||indices[0]!==0||indices.at(-1)!==path.length-3||edge.axis_riser_attributes.length!==1||v.path_index!==0||v.segment_index!==indices.at(-1)+1||JSON.stringify(v.scope_points)!==JSON.stringify(path.slice(v.segment_index,v.segment_index+2))||JSON.stringify(v.floor_pair)!==JSON.stringify([r.floor,r.floor+1]))return null;
   }else if(indices[0]!==1||Number(edge.floor_end??edge.end_floor)!==r.floor||Number(edge.floor_start??edge.start_floor)!==r.floor-1)return null;
  }
 }
 return rows;
}

export function planSegmentProperties(edge,zh=true){
 const rows=checkedPlanSegments(edge);if(!rows)return [];
 const r=rows[0],metric=r.horizontal_projection;
 return [[zh?'\u5e73\u9762\u5bf9\u5e94\u5206\u6bb5\u7ba1\u5f84':'Plan-matched segment DN',`${r.floor}F / ${r.path_index}:${r.segment_indices.join(',')} / DN${r.nominal_mm}`],
  [zh?'\u5bf9\u5e94\u5e73\u9762\u7ba1\u6bb5':'Mapped plan edges',r.plan_edges.join(', ')],
  [zh?'\u5e73\u9762\u6e90\u7ebf\u8def\u5f84\u957f\u5ea6':'Plan source path length',`${(metric.value_mm/1000).toFixed(4)} m (${metric.value_mm.toFixed(1)} mm)`],
  [zh?'\u7ba1\u5f84\u6765\u6e90\u4e0e\u7ee7\u627f':'DN source and inheritance',r.diameter_evidence.lineage.flatMap(c=>c.evidence.map(e=>`${e.evidence_id}: ${e.edge_path.join(' -> ')}`)).join('; ')],
  [zh?'\u957f\u5ea6\u6e90\u7ebf':'Length source lines',metric.pieces.map(p=>`${p.source_line_handle} [${p.path_index}:${p.segment_index}]`).join('; ')],
  [zh?'\u7acb\u7ba1\u4e0e\u8bbe\u5907\u5bf9\u5e94':'Riser and equipment correspondence',`${r.identifier} / ${r.plan_riser_interface} / ${r.equipment_anchor||r.independent_adjoining_main_mapping_id} / ${r.plan_network_T} -> ${r.axis_network_T}`],
  [zh?'\u5c5e\u6027\u8303\u56f4':'Attribute scope',r.whole_local_edge?(zh?'\u4e24\u7aef\u4e09\u901a\u95f4\u7684\u5b8c\u6574\u6c34\u5e73\u4e3b\u7ba1\uff1b\u957f\u5ea6\u4e3a\u4e2d\u5fc3\u7ebf\u8def\u5f84\uff0c\u51c0\u4e0b\u6599\u957f\u5ea6\u672a\u77e5':'Complete horizontal T-to-T main; centerline route, net cut length unknown'):(zh?'\u4ec5\u4e0a\u8ff0\u697c\u5c42\u6c34\u5e73\u63a5\u5165\u6bb5\uff1b\u8de8\u5c42\u7ad6\u6bb5\u4f7f\u752811\u53f7\u56fe\u4f9d\u636e\uff1b\u6574\u8fb9\u7ba1\u5f84\u548c\u957f\u5ea6\u672a\u8d4b\u503c':'Only the specified-floor horizontal approach; vertical evidence comes from drawing 11; mixed whole-edge values unassigned')],
  [zh?'\u9a8c\u6536\u72b6\u6001':'Review status',zh?'\u539f\u56fe\u6280\u672f\u56de\u8bc1\uff1b\u4eba\u5de5\u9a8c\u6536\u5f85\u5b8c\u6210':'Source checked; human acceptance pending']];
}

export function planSegmentCsvValues(edge){
 const rows=checkedPlanSegments(edge);if(!rows)return {};
 const r=rows[0];return {diameter_nominal_mm:r.whole_local_edge?r.nominal_mm:'',diameter_text:r.whole_local_edge?`DN${r.nominal_mm}`:'',
  diameter_status:r.whole_local_edge?'source_checked_plan_segment_complete_horizontal_main':'source_checked_plan_segment_mixed_whole_unknown',
  plan_segment_nominal_mm:r.nominal_mm,plan_segment_projection_mm:r.horizontal_projection.value_mm,
  plan_segment_attributes_json:JSON.stringify(rows),plan_segment_plan_edges:r.plan_edges.join(';'),plan_segment_plan_source_sha256:r.source_sha256.plan,
  plan_segment_whole_main_nominal_mm:r.whole_local_edge?r.nominal_mm:'',plan_segment_whole_main_centerline_mm:r.whole_local_edge?r.whole_edge_centerline_route_mm:'',
  plan_segment_net_cut_length_mm:''};
}
export const planSegmentCsvFields=['plan_segment_nominal_mm','plan_segment_projection_mm','plan_segment_attributes_json','plan_segment_plan_edges','plan_segment_plan_source_sha256','plan_segment_whole_main_nominal_mm','plan_segment_whole_main_centerline_mm','plan_segment_net_cut_length_mm'];
