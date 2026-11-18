// A checked segment never upgrades the mixed edge's scalar DN or length.
export function checkedAxisRiserSegments(edge){
 const rows=edge.axis_riser_attributes,hash=/^[0-9a-f]{64}$/;
 if(!Array.isArray(rows)||!rows.length)return null;
 const seen=new Set();
 for(const r of rows){
  const key=`${r.path_index}:${r.segment_index}`,path=edge.attribute_paths?.[r.path_index],points=path?.slice(r.segment_index,r.segment_index+2);
  if(seen.has(key)||r.edge_id!==edge.edge_id||r.system!==edge.system||!['supply','return'].includes(r.system)||!Number.isInteger(r.path_index)||r.path_index<0||!Number.isInteger(r.segment_index)||r.segment_index<0||points?.length!==2||JSON.stringify(points)!==JSON.stringify(r.scope_points))return null;
  if(points.some(p=>!Array.isArray(p)||p.length!==2||p.some(x=>!Number.isFinite(x)))||Math.abs(points[0][0]-points[1][0])>.05||Math.abs(points[0][1]-points[1][1])<=.05)return null;
  if(!Number.isFinite(r.nominal_mm)||r.nominal_mm<=0||r.scope!=='native_axis_vertical_segment_DN_only'||r.horizontal_values_source!=='floor_plan_correspondence'||!['direct_axis_segment_DN','T_inherited_axis_segment_DN'].includes(r.status)||r.human_accepted!==false||r.whole_edge_nominal_mm!==null||r.physical_length_mm!==null||r.whole_edge_physical_length_mm!==null)return null;
  if(!['source_scope_sha256','source_sha256','local_graph_sha256','attribute_parent_graph_sha256'].every(k=>hash.test(r[k]||''))||typeof r.source_line_handle!=='string'||!r.source_line_handle.trim())return null;
  if(!Array.isArray(r.floor_pair)||r.floor_pair.length!==2||r.floor_pair.some(x=>!Number.isInteger(x))||r.floor_pair[1]-r.floor_pair[0]!==1||JSON.stringify(r.floor_pair)!==JSON.stringify([Number(edge.floor_start),Number(edge.floor_end)].sort((a,b)=>a-b)))return null;
  if(!r.lineage?.length||r.lineage.some(c=>c.nominal_mm!==r.nominal_mm||!c.evidence?.length||c.evidence.some(e=>typeof e.evidence_id!=='string'||!e.evidence_id.startsWith('source:')||!e.edge_path?.length||e.edge_path.at(-1)!==`DN-SEG:${edge.edge_id}:${r.segment_index}`)))return null;
  seen.add(key);
 }
 return rows;
}

export function axisRiserAttributeProperties(edge,zh=true){
 const rows=checkedAxisRiserSegments(edge);if(!rows)return [];
 const scope=rows.map(r=>`${r.floor_pair[0]}F \u2192 ${r.floor_pair[1]}F / ${r.path_index}:${r.segment_index} / DN${r.nominal_mm}`).join('; ');
 return [[zh?'\u7ad6\u5411\u5206\u6bb5\u7ba1\u5f84':'Vertical segment DN',scope],
  [zh?'\u7ad6\u7ba1\u7ba1\u5f84\u6765\u6e90':'Vertical DN source',rows.map(r=>`SH16 11 / LINE ${r.source_line_handle} / ${r.lineage.flatMap(c=>c.evidence.map(e=>e.evidence_id)).join(', ')}`).join('; ')],
  [zh?'\u7ad6\u7ba1\u5b9e\u9645\u957f\u5ea6':'Vertical physical length',zh?'\u672a\u77e5\uff1b\u7ee7\u7eed\u6838\u5bf911\u53f7\u56fe\u5c3a\u5bf8\u4e0e\u6807\u9ad8\u4f9d\u636e':'Unknown; explicit axis dimensions/elevations require checking'],
  [zh?'\u6df7\u5408\u8fb9\u5c5e\u6027\u8303\u56f4':'Mixed edge attribute scope',zh?'\u7ad6\u5411\u7ba1\u5f84\u4ec5\u9650\u4e0a\u8ff0\u56fe\u6bb5\uff1b\u6c34\u5e73\u90e8\u5206\u53d6\u5bf9\u5e94\u5e73\u9762\u56fe\uff1b\u6574\u8fb9\u7ba1\u5f84\u4e0e\u957f\u5ea6\u672a\u8d4b\u503c':'Vertical DN applies only to these segments; horizontal values require floor-plan correspondence; whole-edge DN/length unassigned']];
}

export function axisRiserAttributeCsvValues(edge){
 const rows=checkedAxisRiserSegments(edge);if(!rows)return {};
 return {axis_riser_segment_nominal_mm:rows.map(r=>r.nominal_mm).join(';'),axis_riser_segments_json:JSON.stringify(rows),
  axis_riser_source_scope_sha256:[...new Set(rows.map(r=>r.source_scope_sha256))].join(';'),axis_riser_physical_length_mm:''};
}

export const axisRiserAttributeCsvFields=['axis_riser_segment_nominal_mm','axis_riser_segments_json','axis_riser_source_scope_sha256','axis_riser_physical_length_mm'];
