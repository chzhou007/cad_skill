import assert from 'node:assert/strict';
import {checkedCappedInterface,cappedInterfaceKind,cappedInterfaceInterpretation,cappedInterfaceProperties} from '../assets/viewer/public/source-capped-interface.js';
function fixture(){
 const r={node_id:'UT0192',edge_id:'E0183',system:'supply',role:'reserved_capped_branch_annotation',status:'native_caption_leader_marker_frontier_witness_only',physical_connection_assigned:false,physical_length_mm:null,quantity_expanded_into_ports:false,
  source_geometry:{source_pipe_handle:'B4B7',source_pipe_endpoints:[[100,200,21],[100,0,0]]},caption:{handle:'12A4F',text:'\u9884\u7559\u652f\u7ba1\u63a5\u53e3/\u51712\u5904'},qualifier:{handle:'12A50',text:'\u76f2\u677f\u5c01\u5835'},marker_handles:['12A4A','12A4B'],leader_chain:[{handle:'12A52'}]};
 const n={node_id:'UT0192',node_type:'virtual_equipment',boundary_type:'source_declared_capped_branch_interface',subtype:'source_declared_capped_branch_interface',resolution_state:'native_reserved_capped_interface_role',system:'supply',x:100,y:200,source_handles:['B4B7'],source_declared_capped_branch:r};
 const d={provenance:{sha256:'S'},sourceDeclaredCappedBranchInterfaces:{mode:'source_declared_capped_branch_roles_v1',source_sha256:'S',nodes_retired:0,connections_added:0,physical_lengths_assigned:0,records:[{node_id:'UT0192',edge_id:'E0183',source_role:'reserved_capped_branch_interface',parent_node_snapshot:{node_id:'UT0192'}}]},edges:[{edge_id:'E0183',start_node_id:'T',end_node_id:'UT0192',system:'supply',source_handles:['B4B7']}]};return [n,d];
}
{
 const [n,d]=fixture(),before=JSON.stringify([n,d]);assert.ok(checkedCappedInterface(n,d));assert.equal(cappedInterfaceKind(n,d),'\u9884\u7559\u5c01\u5835\u63a5\u53e3');
 const rows=cappedInterfaceProperties(n,d);assert.ok(rows.some(([k,v])=>v.includes('12A4F')));assert.ok(rows.some(([k,v])=>v.includes('B4B7')));assert.ok(cappedInterfaceInterpretation(n,d).includes('\u672a\u65b0\u589e'));
 assert.equal(JSON.stringify([n,d]),before);
}
for(const mode of ['missingRoot','node','system','source','pipe','coordinate','physical','quantity','duplicatedEdge']){
 const [n,d]=fixture();
 if(mode==='missingRoot')delete d.sourceDeclaredCappedBranchInterfaces;
 else if(mode==='node')n.node_id='OTHER';
 else if(mode==='system')n.system='return';
 else if(mode==='source')d.provenance.sha256='OTHER';
 else if(mode==='pipe')d.edges[0].source_handles=['OTHER'];
 else if(mode==='coordinate')n.y=220;
 else if(mode==='physical')n.source_declared_capped_branch.physical_length_mm=0;
 else if(mode==='quantity')n.source_declared_capped_branch.quantity_expanded_into_ports=true;
 else d.edges.push({...d.edges[0],edge_id:'OTHER'});
 assert.equal(cappedInterfaceKind(n,d),null,mode);assert.deepEqual(cappedInterfaceProperties(n,d),[],mode);
}
console.log('source capped-interface properties: source/root/edge/coordinate guards passed');
