const MODE='source_declared_capped_branch_roles_v1';
export function checkedCappedInterface(node,data){
 const root=data?.sourceDeclaredCappedBranchInterfaces,r=node?.source_declared_capped_branch;
 if(!root||root.mode!==MODE||root.nodes_retired!==0||root.connections_added!==0||root.physical_lengths_assigned!==0)return null;
 if(!root.source_sha256||root.source_sha256!==(data?.provenance?.sha256||data?.metadata?.source_sha256))return null;
 if(node.node_type!=='virtual_equipment'||node.boundary_type!=='source_declared_capped_branch_interface'||node.subtype!==node.boundary_type||node.resolution_state!=='native_reserved_capped_interface_role')return null;
 if(!r||r.node_id!==node.node_id||r.system!==node.system||r.role!=='reserved_capped_branch_annotation'||r.status!=='native_caption_leader_marker_frontier_witness_only'||r.physical_connection_assigned!==false||r.physical_length_mm!==null||r.quantity_expanded_into_ports!==false)return null;
 const rows=root.records?.filter(x=>x.node_id===node.node_id),p=r.source_geometry?.source_pipe_endpoints?.[0],h=r.source_geometry?.source_pipe_handle;
 if(rows?.length!==1||rows[0].source_role!=='reserved_capped_branch_interface'||rows[0].edge_id!==r.edge_id||rows[0].parent_node_snapshot?.node_id!==node.node_id)return null;
 const incident=data.edges?.filter(e=>e.start_node_id===node.node_id||e.end_node_id===node.node_id);
 if(incident?.length!==1||incident[0].edge_id!==r.edge_id||incident[0].system!==node.system||!incident[0].source_handles?.includes(h)||!node.source_handles?.includes(h))return null;
 if(!p||![p[0],p[1],node.x,node.y].every(Number.isFinite)||Math.abs(p[0]-node.x)>.05||Math.abs(p[1]-node.y)>.05)return null;
 if(!r.caption?.handle||!r.caption.text||r.qualifier?.text!=='\u76f2\u677f\u5c01\u5835'||r.marker_handles?.length!==2||!r.leader_chain?.length)return null;
 return r;
}
export function cappedInterfaceKind(node,data){return checkedCappedInterface(node,data)?'\u9884\u7559\u5c01\u5835\u63a5\u53e3':null;}
export function cappedInterfaceInterpretation(node,data){return checkedCappedInterface(node,data)?'\u539f\u56fe\u5df2\u660e\u786e\u9884\u7559\u5e76\u76f2\u677f\u5c01\u5835\uff1b\u672a\u65b0\u589e\u8bbe\u5907\u7aef\u53e3\u6216\u63a5\u7ba1':null;}
export function cappedInterfaceProperties(node,data){
 const r=checkedCappedInterface(node,data);if(!r)return [];
 return [['\u63a5\u53e3\u89d2\u8272',cappedInterfaceKind(node,data)],
  ['\u539f\u56fe\u6807\u6ce8',r.caption.text+' / '+r.qualifier.text],
  ['\u6807\u6ce8\u6765\u6e90',r.caption.handle+' / '+r.qualifier.handle],
  ['\u5f15\u7ebf\u4e0e\u6807\u8bb0',r.leader_chain.map(x=>x.handle).join(', ')+' / '+r.marker_handles.join(', ')],
  ['\u6e90\u7ba1\u7ebf',r.source_geometry.source_pipe_handle],
  ['\u8bc1\u636e\u8303\u56f4','\u53ea\u786e\u8ba4\u539f\u56fe\u63a5\u53e3\u89d2\u8272\uff1b\u539f\u8282\u70b9ID\u4e0e\u7ba1\u7ebf\u4fdd\u7559'],
  ['\u9a8c\u6536\u72b6\u6001','\u539f\u751f\u6807\u6ce8\u56de\u8bc1\uff1b\u6574\u56fe\u4eba\u5de5\u9a8c\u6536\u5f85\u5b8c\u6210']];
}
