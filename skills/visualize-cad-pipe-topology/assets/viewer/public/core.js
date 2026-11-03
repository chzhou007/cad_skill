export function createModel(data) {
  const nodes = new Map(data.nodes.map(n => [n.node_id, n]));
  const edges = new Map(data.edges.map(e => [e.edge_id, e]));
  const adj = new Map(data.nodes.map(n => [n.node_id, []]));
  for (const e of data.edges) { adj.get(e.start_node_id).push(e); adj.get(e.end_node_id).push(e); }
  const instancesByEdge = new Map();
  for (const d of data.instances) for(const id of new Set([d.edge_id,...(d.related_edge_ids||[])])) { if (!instancesByEdge.has(id)) instancesByEdge.set(id, []); instancesByEdge.get(id).push(d); }
  return {data, nodes, edges, adj, instancesByEdge};
}
export function traceNetwork(model, seedId) {
  const seed = model.edges.get(seedId);
  if (!seed) return new Set();
  const found = new Set([seedId]), seen = new Set(), todo = [seed.start_node_id, seed.end_node_id];
  while (todo.length) {
    const id = todo.pop();
    if (seen.has(id)) continue;
    seen.add(id);
    // Explicit equipment and virtual interfaces are terminal boundaries, even multiport ones.
    if (model.nodes.get(id).node_type !== 'physical_junction') continue;
    for (const e of model.adj.get(id)) if (e.system === seed.system) {
      found.add(e.edge_id);
      todo.push(e.start_node_id === id ? e.end_node_id : e.start_node_id);
    }
  }
  return found;
}
export function connectedEquipment(model, ids) {
  const result = new Map();
  for (const id of ids) {
    const e = model.edges.get(id);
    if (!e) continue;
    for (const nodeId of [e.start_node_id,e.end_node_id]) {
      const n = model.nodes.get(nodeId);
      if (n.node_type !== 'physical_junction') result.set(nodeId,n);
    }
  }
  return [...result.values()].sort((a,b) => a.node_id.localeCompare(b.node_id, 'en', {numeric:true}));
}
export function inventory(model, ids) {
  const byType = new Map(),seen=new Set();
  for (const id of ids) for (const d of model.instancesByEdge.get(id) || []) {
    if(seen.has(d.id))continue;seen.add(d.id);
    if (!byType.has(d.type)) byType.set(d.type, {type:d.type,label:d.label,instances:[]});
    byType.get(d.type).instances.push(d);
  }
  return [...byType.values()].sort((a,b) => a.label.localeCompare(b.label));
}
export function shortestPath(model, from, to, system) {
  if (!model.nodes.has(from) || !model.nodes.has(to)) return {error:'Select valid start and end nodes.'};
  if (from === to) return {edges:[],length:0};
  const dist = new Map([[from,0]]), prev = new Map(), open = new Set([from]);
  while (open.size) {
    let u; for (const n of open) if (u===undefined || dist.get(n)<dist.get(u)) u=n;
    open.delete(u);
    if (u===to) break;
    if (u!==from && model.nodes.get(u).node_type!=='physical_junction') continue;
    for (const e of model.adj.get(u)) if (e.system===system) {
      const v=e.start_node_id===u?e.end_node_id:e.start_node_id;
      const d=dist.get(u)+e.path_length;
      if (!dist.has(v) || d<dist.get(v)) {dist.set(v,d);prev.set(v,[u,e.edge_id]);open.add(v);}
    }
  }
  if (!prev.has(to)) return {error:'No same-system path. Equipment and interfaces are traversal boundaries.'};
  const edges=[]; for(let n=to;n!==from;){const [p,e]=prev.get(n);edges.unshift(e);n=p;}
  return {edges,length:dist.get(to)};
}
export function visibleEdge(e, floor, systems) {
  return systems.has(e.system) && (floor==='all' || String(e.floor_start)===String(floor) || String(e.floor_end)===String(floor));
}
export function makeCsv(rows, columns) {
  const quote = v => '"'+String(v??'').replaceAll('"','""')+'"';
  return '\uFEFF'+[columns.map(quote).join(','),...rows.map(r=>columns.map(c=>quote(r[c])).join(','))].join('\r\n');
}

export function hydraulicProperties(node){
 if(node?.node_type!=='equipment')return [];
 const h=node.hydraulic_model||{};
 return [['Calculation scope',h.included===true?'Included':'Source topology'],['Resistance parameters',h.resistance_status==='verified'?'Verified':'Required'],['Zero resistance','Not assumed']];
}
// Unlocated read-only source context must not stretch a selected floor's fit
// across every plan occurrence. It remains visible in the all-floor context.
export function sourceContextPoints(paths,floor='all'){
 return paths.filter(p=>floor==='all'||String(p.floor)===String(floor)).flatMap(p=>p.points);
}
