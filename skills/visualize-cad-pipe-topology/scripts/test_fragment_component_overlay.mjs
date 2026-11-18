import assert from 'node:assert/strict';
import {checkedFragmentOverlay,fragmentOverlayGraphContext} from '../assets/viewer/public/fragment-component-overlay.js';
const clone=x=>structuredClone(x),digest=async s=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)))].map(x=>x.toString(16).padStart(2,'0')).join('');
const parent={nodes:[{node_id:'T'}],edges:[{edge_id:'E',system:'supply',attribute_paths:[[[0,0],[1,0]]],equipment_inventory:[]}],instances:[{id:'OLD',name:'retained'}],symbols:{BALL:{native:'unchanged'}},types:[{code:'BALL'}]};
const raw=JSON.stringify(parent),parentHash=await digest(raw);
const added={id:'NEW',source_top_handle:'HANDLE',edge_id:'E',type:'BALL',name:'Ball',label:'Ball Valve'};
const audit={mode:'native_fragment_component_index_v1',parent_graph_sha256:parentHash,native_proof_sha256:'b'.repeat(64),added_instances:[{id:'NEW',source_handle:'HANDLE',edge_id:'E',type:'BALL',name:'Ball'}],previous_edge_inventories:{E:[]},prior_instances:1,added_count:1,current_instances:2,pipe_graph_restoration_exact:true,unknown_physical_parameters_assigned:0,human_confirmation_inherited:false,human_accepted:false};
const graph=clone(parent);graph.instances.push(added);graph.edges[0].equipment_inventory.push({type:'BALL',label:'Ball Valve',count:1,device_names:['Ball']});graph.sourceNativeFragmentComponentIndex=audit;
const bridge={mode:audit.mode,audit,parent_graph_sha256:parentHash,current_graph_sha256:await digest(JSON.stringify(graph)),parent_graph_path:'data/fragment-component-parent-graph.json'};
assert.equal(checkedFragmentOverlay(graph,parent,bridge),true);
for(const change of [g=>g.nodes[0].node_id='OTHER',g=>g.edges[0].system='return',g=>g.edges[0].attribute_paths[0][1][0]=2,g=>g.instances[0].name='mutated',g=>g.edges[0].equipment_inventory[0].count=2,g=>g.instances[1].source_top_handle='OTHER',g=>g.instances.push(clone(added))]){
 const broken=clone(graph);change(broken);assert.equal(checkedFragmentOverlay(broken,parent,bridge),false);
}
const manifest={componentFragmentOverlay:bridge,attributeValueContext:{rendered_graph_sha256:parentHash}};
assert.equal(await fragmentOverlayGraphContext(manifest,bridge.current_graph_sha256,graph,async()=>({ok:true,text:async()=>raw})),true);
assert.equal(await fragmentOverlayGraphContext(manifest,bridge.current_graph_sha256,graph,async()=>({ok:true,text:async()=>raw+' '})),false);
assert.equal(await fragmentOverlayGraphContext(manifest,'c'.repeat(64),graph),false);
assert.equal(await fragmentOverlayGraphContext({},bridge.current_graph_sha256,graph),false);
console.log('component overlay retains exact old graph/context; geometry, ownership, counts, parent bytes and hash guards passed');
