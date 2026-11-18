import {componentInventoryGraphContext} from './component-inventory-attribute-bridge.js';
const hash=/^[0-9a-f]{64}$/;
const canonical=x=>JSON.stringify(stable(x));
function stable(x){if(Array.isArray(x))return x.map(stable);if(x&&typeof x==='object')return Object.fromEntries(Object.keys(x).sort().map(k=>[k,stable(x[k])]));return x;}
export function checkedFragmentOverlay(graph,parent,bridge){
 try{
  const a=graph.sourceNativeFragmentComponentIndex;
  if(bridge?.mode!=='native_fragment_component_index_v1'||a?.mode!==bridge.mode||canonical(a)!==canonical(bridge.audit)||a.pipe_graph_restoration_exact!==true||a.unknown_physical_parameters_assigned!==0||a.human_confirmation_inherited!==false||a.human_accepted!==false||!hash.test(a.native_proof_sha256||'')||!hash.test(a.parent_graph_sha256||'')||bridge.parent_graph_sha256!==a.parent_graph_sha256||!hash.test(bridge.current_graph_sha256||''))return false;
  const additions=a.added_instances,ids=new Set(additions.map(x=>x.id));
  if(!additions.length||ids.size!==additions.length||additions.length!==a.added_count||parent.instances.length!==a.prior_instances||graph.instances.length!==a.current_instances||graph.instances.length!==parent.instances.length+ids.size||new Set(graph.instances.map(x=>x.id)).size!==graph.instances.length||parent.instances.some(x=>ids.has(x.id)))return false;
  const restored=structuredClone(graph);delete restored.sourceNativeFragmentComponentIndex;
  const oldEdges=new Map(parent.edges.map(e=>[e.edge_id,e]));
  const changed=new Set(additions.map(x=>x.edge_id));
  if(canonical([...changed].sort())!==canonical(Object.keys(a.previous_edge_inventories).sort()))return false;
  for(const edge of restored.edges){
   if(!changed.has(edge.edge_id))continue;
   const old=oldEdges.get(edge.edge_id);if(!old||canonical(old.equipment_inventory)!==canonical(a.previous_edge_inventories[edge.edge_id]))return false;
   const expected=structuredClone(old.equipment_inventory);
   for(const add of additions.filter(x=>x.edge_id===edge.edge_id)){
    const instances=graph.instances.filter(x=>x.id===add.id);if(instances.length!==1)return false;
    const item=instances[0];if(item.source_top_handle!==add.source_handle||item.edge_id!==add.edge_id||item.type!==add.type||item.name!==add.name)return false;
    let row=expected.find(x=>x.type===add.type);
    if(row){row.count++;row.device_names.push(add.name);}else expected.push({type:add.type,label:item.label,count:1,device_names:[add.name]});
   }
   if(canonical(expected)!==canonical(edge.equipment_inventory))return false;
   edge.equipment_inventory=structuredClone(old.equipment_inventory);
  }
  restored.instances=restored.instances.filter(x=>!ids.has(x.id));
  return canonical(restored)===canonical(parent);
 }catch{return false;}
}
export async function fragmentOverlayGraphContext(manifest,actualHash,graph,fetcher=fetch){
 const b=manifest.componentFragmentOverlay;
 if(b?.parent_graph_path!=='data/fragment-component-parent-graph.json'||actualHash!==b.current_graph_sha256)return false;
 const response=await fetcher(b.parent_graph_path);if(!response.ok)return false;
 const raw=await response.text(),actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(raw)))].map(b=>b.toString(16).padStart(2,'0')).join('');
 if(actual!==b.parent_graph_sha256)return false;
 const parent=JSON.parse(raw);
 return componentInventoryGraphContext(manifest.attributeValueContext,actual,parent.edges)&&checkedFragmentOverlay(graph,parent,b);
}
