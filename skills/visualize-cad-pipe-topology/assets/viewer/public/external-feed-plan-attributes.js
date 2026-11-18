// Source pipe values and separate external boundary context; no new connections.
const hash=/^[0-9a-f]{64}$/;
const point=p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite);
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const positive=n=>Number.isFinite(n)&&n>0;

export function checkedExternalFeed(edge){
 const r=edge.external_feed_plan_attributes;
 if(!r||r.axis_edge!==edge.edge_id||r.system!==edge.system||!['supply','return'].includes(r.system)||!Number.isInteger(r.floor)||Number(edge.floor_start??edge.start_floor)!==r.floor||Number(edge.floor_end??edge.end_floor)!==r.floor)return null;
 if(['cross_view_attributes','axis_riser_attributes','plan_segment_attributes','anchored_floor_main_attributes','network_named_lower_plan_attributes'].some(k=>k in edge))return null;
 if(r.scope!=='native_external_pipe_segments_only_excluding_marker_and_inline_gap'||r.path_index!==0||edge.attribute_paths?.length!==1||r.plan_edges?.length!==1)return null;
 const path=edge.attribute_paths[0],indices=r.segment_indices,gaps=r.inline_gap_segment_indices,display=r.display_only_segment_index;
 if(!Array.isArray(path)||path.length<4||!path.every(point)||!Array.isArray(indices)||!indices.length||!Array.isArray(gaps)||!gaps.length||!Number.isInteger(display))return null;
 const all=[...indices,...gaps,display];
 if(all.some(i=>!Number.isInteger(i)||i<0||i>=path.length-1)||new Set(all).size!==all.length||all.length!==path.length-1||!same(r.scope_paths,indices.map(i=>path.slice(i,i+2))))return null;
 if(!['mapping_sha256','source_scope_sha256','attribute_parent_graph_sha256'].every(k=>hash.test(r[k]||''))||!['plan','iso'].every(v=>hash.test(r.source_sha256?.[v]||'')&&hash.test(r.local_graph_sha256?.[v]||'')))return null;
 if(!['identifier','destination','axis_boundary_node','axis_port_id','plan_boundary_node','mapping_id'].every(k=>typeof r[k]==='string'&&r[k].trim())||!new RegExp(r.system==='supply'?'^CHWS[1-9][0-9]*$':'^CHWR[1-9][0-9]*$').test(r.identifier))return null;
 const atStart=edge.start_node_id===r.axis_boundary_node,atEnd=edge.end_node_id===r.axis_boundary_node;
 if(atStart===atEnd||(atStart?edge.start_port_id:edge.end_port_id)!==r.axis_port_id||display!==(atStart?0:path.length-2))return null;
 if(!['whole_axis_edge_DN_selected','physical_ports_verified','physical_external_connection_verified','external_ports_connected_to_each_other','human_accepted','related_HIL_confirmation_inherited'].every(k=>r[k]===false)||r.complete_horizontal_centerline_route_mm!==null||r.installed_whole_edge_length_mm!==null||r.pipe_net_cut_length_mm!==null)return null;
 const d=r.diameter_evidence,m=r.horizontal_projection;
 if(d?.edge_id!==r.plan_edges[0]||d.system!==r.system||d.nominal_mm!==r.nominal_mm||d.scope!=='source_checked_native_through_plan_pipe_paths_only'||d.human_accepted!==false||!Array.isArray(d.lineage)||!Array.isArray(d.scope_paths)||!d.scope_paths.length||d.scope_paths.some(p=>!Array.isArray(p)||p.length<2||!p.every(point)))return null;
 if(r.nominal_mm===null){if(!['unresolved','conflict'].includes(d.status))return null;}
 else if(!positive(r.nominal_mm)||!['direct_plan_DN','T_inherited_plan_DN'].includes(d.status)||!d.lineage?.length||d.lineage.some(c=>c.nominal_mm!==r.nominal_mm||!c.evidence?.length||c.evidence.some(e=>typeof e.evidence_id!=='string'||!e.evidence_id.startsWith('source:')||e.edge_path?.at(-1)!==d.edge_id)))return null;
 if(!positive(m?.value_mm)||m.installed_whole_edge_length_mm!==null||m.unshown_connection_length_mm!==null||m.inline_joint_interior_length_mm!==null||m.joint_graphic_spans_added!==false||!m.pieces?.length)return null;
 const locations=new Set();
 for(const p of m.pieces){
  const key=p.path_index+':'+p.segment_index;
  if(locations.has(key)||p.plan_edge!==d.edge_id||typeof p.source_line_handle!=='string'||!p.source_line_handle.trim()||!Number.isInteger(p.path_index)||!Number.isInteger(p.segment_index)||!positive(p.length_mm)||!Array.isArray(p.points)||p.points.length!==2||!p.points.every(point)||!same(d.scope_paths[p.path_index]?.slice(p.segment_index,p.segment_index+2),p.points)||Math.abs(Math.hypot(p.points[1][0]-p.points[0][0],p.points[1][1]-p.points[0][1])-p.length_mm)>.05)return null;
  locations.add(key);
 }
 if(locations.size!==d.scope_paths.reduce((n,p)=>n+p.length-1,0)||Math.abs(m.pieces.reduce((n,p)=>n+p.length_mm,0)-m.value_mm)>.05)return null;
 return r;
}

export function externalFeedProperties(edge,zh=true){
 const r=checkedExternalFeed(edge);if(!r)return [];
 return [[zh?'\u7ba1\u9053\u53e3\u5f84\uff08\u539f\u7ba1\u7ebf\u8303\u56f4\uff09':'Source pipe DN',r.nominal_mm===null?(zh?'\u672a\u786e\u5b9a':'Unknown'):'DN'+r.nominal_mm],
  [zh?'\u5916\u90e8\u53bb\u5411':'External destination',r.destination+' / '+r.identifier+' / '+r.axis_port_id],
  [zh?'\u539f\u7ba1\u7ebfXY\uff08\u4e0d\u542b\u8f6f\u63a5\uff09':'Source pipe XY (joint excluded)',(r.horizontal_projection.value_mm/1000).toFixed(4)+' m ('+r.horizontal_projection.value_mm.toFixed(1)+' mm)'],
  [zh?'\u5bf9\u5e94\u5e73\u9762\u7ba1\u6bb5':'Mapped plan edges',r.plan_edges.join(', ')],
  [zh?'\u7ba1\u5f84\u6765\u6e90\u4e0e\u7ee7\u627f':'DN source and inheritance',r.diameter_evidence.lineage.flatMap(c=>c.evidence.map(e=>e.evidence_id+': '+e.edge_path.join(' -> '))).join('; ')||'Unknown'],
  [zh?'\u5c5e\u6027\u8303\u56f4':'Attribute scope',zh?'\u4ec5\u539f\u7ba1\u7ebf\uff1b\u7701\u7565\u6807\u8bb0\u3001\u4e2d\u5fc3\u663e\u793a\u7ebf\u548c\u8f6f\u63a5\u7f3a\u53e3\u4e0d\u8ba1\u5165':'Native pipe only; omission marker, centre display and joint gap excluded'],
  [zh?'\u6574\u8fb9\u5b89\u88c5\u957f\u5ea6':'Installed whole-edge length',zh?'\u672a\u77e5\uff1b\u8f6f\u63a5\u5185\u90e8\u672a\u8ba1':'Unknown; joint interior unmeasured'],
  [zh?'\u7aef\u53e3\u4e0e\u9a8c\u6536':'Ports and review',zh?'\u5404\u8def\u72ec\u7acb\uff1b\u5916\u90e8\u6c34\u529b\u8fde\u63a5\u4e0e\u4eba\u5de5\u9a8c\u6536\u672a\u786e\u8ba4':'Separate ports; external hydraulic connectivity and human acceptance unknown']];
}

export function externalFeedCsvValues(edge){
 const r=checkedExternalFeed(edge);if(!r)return {};
 return {external_feed_pipe_nominal_mm:r.nominal_mm??'',external_feed_pipe_XY_mm:r.horizontal_projection.value_mm,
  external_feed_installed_whole_length_mm:'',external_feed_destination:r.destination,external_feed_port_id:r.axis_port_id,
  external_feed_plan_edges:r.plan_edges.join(';'),external_feed_plan_source_sha256:r.source_sha256.plan,external_feed_scope_json:JSON.stringify(r)};
}
export const externalFeedCsvFields=['external_feed_pipe_nominal_mm','external_feed_pipe_XY_mm','external_feed_installed_whole_length_mm','external_feed_destination','external_feed_port_id','external_feed_plan_edges','external_feed_plan_source_sha256','external_feed_scope_json'];

export function checkedExternalBoundary(node,edges){
 const c=node.source_external_destination_context;
 if(!c||node.node_type!=='virtual_equipment'||node.subtype!=='external_system_interface'||c.node_id!==node.node_id||c.floor!==node.floor||c.source_marker_handle!==node.source_marker_handle||!same(c.native_node_position,[node.x,node.y])||c.status!=='source_declared_destination_external_connectivity_unknown')return null;
 if(!['direct_connection_between_ports','physical_equipment','physical_ports_verified','physical_external_connection_verified','human_accepted'].every(k=>c[k]===false)||!['mapping_sha256','attribute_scope_sha256','plan_destination_sha256','axis_destination_sha256','attribute_parent_graph_sha256'].every(k=>hash.test(c[k]||''))||!['plan','iso'].every(v=>hash.test(c.source_sha256?.[v]||'')&&hash.test(c.local_graph_sha256?.[v]||'')))return null;
 if(typeof c.destination!=='string'||!c.destination.trim()||![c.plan_caption_evidence?.text,c.axis_caption_evidence?.text].every(t=>t==='\u63a5\u81f3'+c.destination||t==='\u63a5'+c.destination)||!Array.isArray(c.ports)||!Array.isArray(node.ports)||c.ports.length<2||c.ports.length!==node.ports.length)return null;
 const all=edges instanceof Map?[...edges.values()]:edges;
 if(!Array.isArray(all)||all.filter(e=>[e.start_node_id,e.end_node_id].includes(node.node_id)).length!==c.ports.length)return null;
 const ids=new Set();
 for(const p of c.ports){
  const native=node.ports.find(q=>q.port_id===p.port_id),edge=all.find(e=>e.edge_id===p.edge_id),r=edge&&checkedExternalFeed(edge);
  if(ids.has(p.port_id)||!native||native.system!==p.system||native.source_marker_handle!==node.source_marker_handle||!Array.isArray(p.native_port_XYZ)||p.native_port_XYZ.length!==3||!p.native_port_XYZ.every(Number.isFinite)||Math.hypot(native.x-p.native_port_XYZ[0],native.y-p.native_port_XYZ[1])>.05||!r||r.axis_boundary_node!==node.node_id||r.axis_port_id!==p.port_id||r.system!==p.system||r.identifier!==p.identifier||r.destination!==c.destination||r.mapping_sha256!==c.mapping_sha256||r.source_scope_sha256!==c.attribute_scope_sha256||r.attribute_parent_graph_sha256!==c.attribute_parent_graph_sha256||!same(r.source_sha256,c.source_sha256)||!same(r.local_graph_sha256,c.local_graph_sha256))return null;
  ids.add(p.port_id);
 }
 if(node.ports.some(p=>!ids.has(p.port_id)))return null;
 return c;
}

export function externalBoundaryLabel(node,edges,zh=true){
 const c=checkedExternalBoundary(node,edges);return c?(zh?'\u63a5\u81f3'+c.destination+'\uff08'+c.ports.length+'\u8def\u72ec\u7acb\u8fb9\u754c\uff09':c.destination+' ('+c.ports.length+' separate boundary ports)'):null;
}
export function externalBoundaryProperties(node,edges,zh=true){
 const c=checkedExternalBoundary(node,edges);if(!c)return [];
 return [[zh?'\u539f\u56fe\u660e\u786e\u53bb\u5411':'Source-declared destination',c.destination],
  [zh?'\u72ec\u7acb\u7aef\u53e3':'Separate ports',c.ports.map(p=>p.identifier+' / '+p.port_id+' / '+p.edge_id).join('; ')],
  [zh?'\u8282\u70b9\u8bed\u4e49':'Node semantics',zh?'\u7ed8\u56fe\u8fb9\u754c\uff1b\u516c\u5171\u7701\u7565\u6807\u8bb0\u4e0d\u8868\u793a\u5404\u7aef\u53e3\u4e92\u901a':'Drawing boundary; common omission marker does not join ports'],
  [zh?'\u573a\u5916\u6c34\u529b\u8fde\u63a5':'External hydraulic connectivity',zh?'\u672a\u786e\u8ba4':'Unconfirmed'],
  [zh?'\u4eba\u5de5\u9a8c\u6536':'Human acceptance',zh?'\u672a\u5b8c\u6210':'Pending']];
}
