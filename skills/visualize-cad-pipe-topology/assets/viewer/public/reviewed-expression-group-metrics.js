const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b),hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
const finite=v=>typeof v==='number'&&Number.isFinite(v),point=p=>Array.isArray(p)&&p.length===2&&p.every(finite);
export function checkedExpressionGroupMetrics(edge,context=null){
 const root=context?.reviewed_expression_group_metrics,b=root?.source_bindings;
 if(root?.mode!=='qualified_reviewed_expression_group_metrics_v1'||root.human_accepted!==false||root.per_axis_edge_values_assigned!==0||!b||!Object.values(b).every(hash)||b.rendered_attribute_graph!==context.current_rendered_graph_sha256||!Array.isArray(root.records)||root.records.length!==root.count||new Set(root.records.map(r=>r.scope_id)).size!==root.count)return [];
 const rows=root.records.filter(r=>Array.isArray(r.axis_members)&&r.axis_members.some(m=>m.edge_id===edge.edge_id));
 if(rows.some(r=>{
  const member=r.axis_members.find(m=>m.edge_id===edge.edge_id);
  if(r.unit_calibration_evidence_unchanged!==true||r.graph_mutated!==false)return true;
  if(r.system!==edge.system||member.system!==edge.system||member.start_node_id!==edge.start_node_id||member.end_node_id!==edge.end_node_id||!equal(member.attribute_paths,edge.attribute_paths)||!equal(member.floors,[edge.floor_start,edge.floor_end]))return true;
  if(r.per_axis_edge_length_allocation!==null||r.per_axis_edge_DN_assignment!==null||r.complete_group_physical_length_mm!==null||r.internal_node_identities_assigned!==false||r.human_accepted!==false||r.measurement_kind!=='sum_of_native_floor_plan_LINE_fragments_not_installed_length'||!finite(r.known_plan_XY_fragment_sum_mm)||r.known_plan_XY_fragment_sum_mm<=0||!Array.isArray(r.plan_edges)||!r.plan_edges.length||new Set(r.plan_edges).size!==r.plan_edges.length||!Array.isArray(r.axis_edges)||new Set(r.axis_edges).size!==r.axis_edges.length||!equal(r.axis_edges,r.axis_members.map(m=>m.edge_id))||!Array.isArray(r.omitted_span_evidence)||r.omitted_span_evidence.some(g=>!r.plan_edges.includes(g.plan_edge)||g.physical_connector_length_mm!==null)||!Array.isArray(r.pieces)||!r.pieces.length)return true;
  const ids=new Set();let sum=0;
  for(const p of r.pieces){const id=`${p.plan_edge}:${p.path_index}:${p.segment_index}`;if(ids.has(id)||!r.plan_edges.includes(p.plan_edge)||!Number.isInteger(p.path_index)||p.path_index<0||!Number.isInteger(p.segment_index)||p.segment_index<0||typeof p.source_line_handle!=='string'||!p.source_line_handle||!Array.isArray(p.points)||p.points.length!==2||!p.points.every(point)||!finite(p.length_mm)||p.length_mm<=0||Math.abs(Math.hypot(p.points[1][0]-p.points[0][0],p.points[1][1]-p.points[0][1])-p.length_mm)>.0001)return true;ids.add(id);sum+=p.length_mm;}
  return Math.abs(sum-r.known_plan_XY_fragment_sum_mm)>.0001;
 }))return [];
 return rows;
}
export function expressionGroupMetricProperties(edge,zh=true,context=null){
 return checkedExpressionGroupMetrics(edge,context).flatMap(r=>[
  [zh?'\u5171\u4eab\u8303\u56f4\u91cf\u6d4b':'Shared range measurement',r.scope_id],
  [zh?'\u8303\u56f4\u5df2\u753b\u5e73\u9762\u6e90\u7ebf\u5408\u8ba1':'Shared drawn plan LINE sum',`${(r.known_plan_XY_fragment_sum_mm/1000).toFixed(3)} m`],
  [zh?'\u8ba1\u91cf\u8fb9\u754c':'Measurement scope',zh?`\u540c\u7ec4${r.axis_edges.length}\u6761\u8f74\u6d4b\u8fb9\u5171\u7528\uff1b\u6309\u8303\u56f4ID\u4ec5\u8ba1\u4e00\u6b21\uff1b\u5171\u4eab\u603b\u91cf\u672a\u5206\u644a\uff0c\u65e2\u6709\u72ec\u7acb\u91cf\u6d4b\u4fdd\u6301`:`Shared by ${r.axis_edges.length} axis edges; count once per scope ID; group sum unallocated, existing independent edge measurements retained`],
  [zh?'\u7701\u7565\u8fde\u63a5\u957f\u5ea6':'Omitted connection lengths',zh?`${r.omitted_span_evidence.length}\u5904\u672a\u77e5\uff1b\u5b8c\u6574\u5b89\u88c5\u957f\u5ea6\u672a\u77e5`:`${r.omitted_span_evidence.length} unknown; installed group length unknown`],
  [zh?'\u5e73\u9762\u6e90\u8bc1\u636e':'Floor plan source evidence',`${r.plan_edges.length} edges / ${r.pieces.length} native LINE fragments / ${context.reviewed_expression_group_metrics.source_bindings.plan_source}`]
 ]);
}
export const expressionGroupMetricCsvFields=['shared_plan_metric_scope_ids','shared_plan_metric_scopes_json','shared_plan_metric_source_sha256'];
export function expressionGroupMetricCsvValues(edge,context=null){const rows=checkedExpressionGroupMetrics(edge,context);if(!rows.length)return {};return {shared_plan_metric_scope_ids:rows.map(r=>r.scope_id).join(';'),shared_plan_metric_scopes_json:JSON.stringify(rows.map(r=>({...r,aggregation_key:r.scope_id,aggregation_policy:'count_once_per_scope_id_not_once_per_edge'}))),shared_plan_metric_source_sha256:context.reviewed_expression_group_metrics.source_bindings.plan_source};}
