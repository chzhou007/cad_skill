const hash=/^[0-9a-f]{64}$/;
export function componentInventoryAttributeScope(edge,context){
 const b=context?.component_inventory_bridge;if(!b)return true;
 if(b.mode!=='native_recovered_component_attribute_scope_bridge_v1'||b.native_source_replayed!==true||b.complete_parent_replayed!==true||b.pipe_graph_restoration_exact!==true||b.unknown_physical_parameters_assigned!==0||b.human_accepted!==false||!hash.test(b.native_proof_sha256||'')||!hash.test(b.current_rendered_graph_sha256||'')||b.current_rendered_graph_sha256!==context.current_rendered_graph_sha256||b.attribute_parent_rendered_graph_sha256!==context.rendered_graph_sha256)return false;
 const basis=['edge_id','start_node_id','end_node_id','system','floor_start','floor_end','attribute_paths'].map(k=>edge[k]??null);
 return JSON.stringify(b.edge_bases?.[edge.edge_id])===JSON.stringify(basis);
}
export function componentInventoryGraphContext(context,actualHash,edges){
 const b=context?.component_inventory_bridge;
 if(!b)return actualHash===context?.rendered_graph_sha256;
 if(!Array.isArray(edges)||actualHash!==context.current_rendered_graph_sha256||actualHash!==b.current_rendered_graph_sha256||Object.keys(b.edge_bases||{}).length!==edges.length||new Set(edges.map(e=>e.edge_id)).size!==edges.length)return false;
 return edges.every(e=>componentInventoryAttributeScope(e,context));
}
