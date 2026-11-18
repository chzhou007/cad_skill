export function createModel(data) {
  const nodes = new Map(data.nodes.map(n => [n.node_id, n]));
  const edges = new Map(data.edges.map(e => [e.edge_id, e]));
  const adj = new Map(data.nodes.map(n => [n.node_id, []]));
  for (const e of data.edges) { adj.get(e.start_node_id).push(e); adj.get(e.end_node_id).push(e); }
  const instancesByEdge = new Map();
  for (const d of data.instances) for(const id of new Set([d.edge_id,...(d.related_edge_ids||[])])) { if (!instancesByEdge.has(id)) instancesByEdge.set(id, []); instancesByEdge.get(id).push(d); }
  const sourcePortCandidateOwners=new Map();
  for(const n of data.nodes) for(const c of n.source_port_candidates||[]) {
    if(c.status!=='source_mark_candidate_not_bound'||!nodes.has(c.candidate_node_id)) continue;
    if(!sourcePortCandidateOwners.has(c.candidate_node_id))sourcePortCandidateOwners.set(c.candidate_node_id,[]);
    sourcePortCandidateOwners.get(c.candidate_node_id).push({equipment_id:n.node_id,edge_id:c.edge_id,source_handle:c.equipment_circle_handle});
  }
  return {data, nodes, edges, adj, instancesByEdge,sourcePortCandidateOwners};
}
// A reconstructed source contact remains provisional. Preserve only the two
// main-line continuations whose common source handle is uniquely identified.
function pendingMainHandle(model,id) {
  const n=model.nodes.get(id), edges=model.adj.get(id)||[];
  if(!n || edges.length!==3) return null;
  const mains=(n.source_handles||[]).filter(h=>edges.filter(e=>(e.source_handles||[]).includes(h)).length===2);
  return mains.length===1?mains[0]:null;
}
function sourceVerifiedPendingMain(model,id) {
  const n=model.nodes.get(id), q=n?.source_main_continuation, main=pendingMainHandle(model,id), edges=model.adj.get(id)||[];
  if(!q || !main || q.main_source_handle!==main || !Array.isArray(q.main_edge_ids) || q.main_edge_ids.length!==2) return null;
  const actual=edges.filter(e=>(e.source_handles||[]).includes(main));
  if(actual.length!==2 || actual.some(e=>e.system!==n.system) || actual.map(e=>e.edge_id).sort().join('\0')!==[...q.main_edge_ids].sort().join('\0'))return null;
  return main;
}
// Expert-scoped similar-circle branches are still unreviewed. A native
// main may continue only through the two unique edges bearing its source line.
// undefined means no such pending branch; null means evidence is inconsistent.
function inferredCircleMain(model,id) {
  const node=model.nodes.get(id), edges=model.adj.get(id)||[];
  const pending=edges.filter(e=>{
    const q=e.source_expert_circle_link;
    if(q?.similar_location_inferred!==true)return false;
    const other=e.start_node_id===id?e.end_node_id:e.start_node_id;
    const otherCircle=model.nodes.get(other)?.expert_circle_evidence?.circle_handle;
    return !q.circle_handle || q.circle_handle===node?.expert_circle_evidence?.circle_handle || q.circle_handle!==otherCircle;
  });
  if(!pending.length)return undefined;
  const ev=node?.expert_circle_evidence, link=pending[0].source_expert_circle_link;
  if(pending.length!==1 || edges.length!==3 || !ev?.circle_handle || !ev?.main_handle ||
     link.circle_handle!==ev.circle_handle || link.main_source_handle!==ev.main_handle ||
     link.branch_source_handle!==ev.branch_handle || !(node.source_handles||[]).includes(ev.circle_handle) ||
     edges.some(e=>e.system!==node.system))return null;
  const main=edges.filter(e=>(e.source_handles||[]).includes(ev.main_handle));
  if(main.length!==2 || main.includes(pending[0]) || !(pending[0].source_handles||[]).includes(ev.branch_handle))return null;
  return new Set(main.map(e=>e.edge_id));
}
export function canCross(model, id, incoming, outgoing) {
  const n=model.nodes.get(id);
  if(!n)return false;
  const circleMain=inferredCircleMain(model,id);
  if(circleMain!==undefined)return circleMain!==null && circleMain.has(incoming.edge_id) && circleMain.has(outgoing.edge_id);
  if(n.node_type==='virtual_equipment' && n.resolution_state==='source_main_continuation_branch_pending'){
    const main=sourceVerifiedPendingMain(model,id);
    return main!==null && (incoming.source_handles||[]).includes(main) && (outgoing.source_handles||[]).includes(main);
  }
  if (n.node_type!=='physical_junction') return false;
  if (n.resolution_state!=='source_contact_reconstructed_pending_comparison') return true;
  const main=pendingMainHandle(model,id);
  return main!==null && (incoming.source_handles||[]).includes(main) && (outgoing.source_handles||[]).includes(main);
}
// Source block evidence establishes only logical ownership, not a physical port.
function sourceSupportedEquipment(model,edge,id) {
  const a=edge.source_block_equipment_attachment, b=model.data.sourceBlockEquipmentAttachment;
  const c=edge.source_path_coverage, x=edge.source_device_extension;
  const side=edge.start_node_id===id?'start':edge.end_node_id===id?'end':null;
  if(model.nodes.get(id)?.node_type!=='equipment'||!side||!a||!b||!c||!x)return false;
  const n=model.nodes.get(id), snap=a.source_edge_snapshot;
  if(!snap||snap.start_node_id!==edge.start_node_id||snap.end_node_id!==edge.end_node_id||snap.system!==edge.system||
     JSON.stringify(snap.attribute_paths)!==JSON.stringify(edge.attribute_paths)||
     JSON.stringify(snap.equipment_xy)!==JSON.stringify([n.x,n.y]))return false;
  const matches=Array.isArray(b.mappings)?b.mappings.filter(m=>m.edge_id===edge.edge_id&&m.equipment_id===id&&m.system===edge.system&&m.source_insert_handle===a.source_insert_handle&&m.source_circle_handle===a.source_circle_handle):[];
  return a.status==='source_supported_logical_attachment_not_human_accepted' && b.status==='source_supported_logical_attachments_not_human_accepted' &&
    !!a.source_sha256 && a.source_sha256===b.source_sha256 && a.source_sha256===c.source_sha256 && a.source_sha256===x.source_sha256 &&
    !!a.input_graph_sha256 && a.input_graph_sha256===b.input_graph_sha256 && !!a.evidence_sha256 && a.evidence_sha256===b.evidence_sha256 &&
    a.equipment_id===id && a.interface_side===side && edge.source_insert_handle===a.source_insert_handle &&
    JSON.stringify(x.source_circle_chain)===JSON.stringify([a.source_insert_handle,a.source_circle_handle]) &&
    Array.isArray(a.source_joint_chain) && JSON.stringify(x.source_joint_chain)===JSON.stringify(a.source_joint_chain) &&
    x.status==='source_drawn_line_with_joint_evidence_unreviewed' && x.physical_port_verified===false && x.physical_length==='unknown' &&
    a.physical_port_verified===false && a.physical_length==='unknown' && a.human_accepted===false &&
    b.physical_ports_verified===false && b.physical_lengths_known===false && b.human_accepted===false &&
    edge.physical_length==='unknown' && edge.path_length_complete===false && matches.length===1;
}
// A drawn connector reaching an equipment node is not proof of its port.
function equipmentEndpointUnverified(model, edge, id) {
  const n=model.nodes.get(id), c=edge.source_path_coverage;
  if(n?.node_type==='equipment' && Object.hasOwn(edge,'source_sideview_equipment_interface')){
    const ev=edge.source_sideview_equipment_interface,root=model.data.sourceSideviewEquipmentOwnership;
    if(!ev || !root)return true;
    const snapshot=ev.endpoint_snapshot,role=edge.source_view_context,kind=ev.original_canonical_interface_kind;
    const nid=ev.original_canonical_interface_id,side=ev.interface_side;
    const rows=root.records?.filter(r=>r.edge_id===edge.edge_id && r.equipment_id===id)||[];
    const retired=(kind==='node'?root.retired_interface_nodes:kind==='non_node_boundary'?root.retired_boundary_anchors:[])||[];
    const originals=retired.filter(r=>(kind==='node'?r.node_id:r.boundary_id)===nid);
    const aliases=kind==='node'?root.node_aliases:root.boundary_aliases;
    const native=originals[0],floor=native?.floor??native?.legacy_node?.floor;
    const confirmed=model.data.confirmedSideviewCanonicalization?.records?.filter(r=>r.canonical_edge===edge.edge_id && r.canonical_interface===nid)||[];
    return !(root.mode==='source_calibrated_confirmed_sideview_equipment_ownership_v1' && root.human_accepted===false &&
      root.physical_ports_verified===false && ev.human_accepted===false && ev.physical_port_verified===false && ev.interface_to_equipment_length_known===false &&
      ev.equipment_id===id && ev.edge_id===edge.edge_id && ev.system===edge.system && ev.source_sha256===root.source_sha256 &&
      ev.source_sha256===model.data.metadata?.source_sha256 && ev.input_graph_sha256===root.input_graph_sha256 &&
      ['start','end'].includes(side) && edge[side+'_node_id']===id && snapshot?.equipment_source_handle===n.source_handle &&
      ev.body_evidence?.equipment_handle===n.source_handle && JSON.stringify(snapshot?.equipment_xy)===JSON.stringify([n.x,n.y]) &&
      ['start_node_id','end_node_id','start_boundary_id','end_boundary_id','system'].every(k=>(snapshot?.[k]??null)===(edge[k]??null)) &&
      JSON.stringify(snapshot?.attribute_paths)===JSON.stringify(edge.attribute_paths) && rows.length===1 && JSON.stringify(rows[0])===JSON.stringify(ev) &&
      originals.length===1 && JSON.stringify(native)===JSON.stringify(ev.original_canonical_endpoint) && aliases?.[nid]===id && !model.nodes.has(nid) &&
      !(model.data.boundary_anchors||[]).some(a=>a.boundary_id===nid) && Number.isInteger(floor) && floor===n.floor &&
      (native.floor==null || native.legacy_node?.floor==null || native.floor===native.legacy_node.floor) && ev.endpoint_floor_evidence?.floor===floor &&
      confirmed.length===1 && confirmed[0].question_id===ev.question_id && confirmed[0].pair_sha256===ev.pair_sha256 &&
      confirmed[0].canonical_interface_kind===kind && confirmed[0].answer?.decision==='\u5bf9\u5e94\u540c\u4e00\u7ec4\u7ba1\u8def' &&
      ev.source_alias?.canonical_edge===edge.edge_id && ev.source_alias?.canonical_interface===nid && ev.source_alias?.canonical_interface_kind===kind &&
      role?.kind==='confirmed_detail_view' && role.source_sha256===root.source_sha256 && role.input_graph_sha256===root.input_graph_sha256 &&
      role.confirmed_alias_root_sha256===ev.sideview_root_sha256 && role.physical_length_from_drawing_span===false && role.metric_verified_by_this_stage===false &&
      root.detail_edge_ids?.includes(edge.edge_id) && edge.physical_length==='unknown' && edge.path_length_complete===false && edge.equipment_connector_length_mm===null);
  }
  if(n?.node_type==='equipment' && edge.source_native_block_branch){
    const ev=edge.source_native_block_branch,proof=model.data.sourceNativeBlockBranchReconstruction,snapshot=ev.endpoint_snapshot;
    const rows=proof?.records?.filter(r=>r.edge_id===edge.edge_id && r.equipment_id===id) || [];
    return !(proof?.status==='native_block_source_paths_reconstructed_hil_pending' && proof.human_accepted===false &&
      proof.physical_ports_verified===false && ev.equipment_id===id && ev.system===edge.system && ev.source_sha256===proof.source_sha256 &&
      ev.physical_port_verified===false && ev.human_accepted===false && snapshot?.start_node_id===edge.start_node_id &&
      snapshot?.end_node_id===edge.end_node_id && snapshot?.system===edge.system &&
      JSON.stringify(snapshot?.attribute_paths)===JSON.stringify(edge.attribute_paths) && rows.length===1 &&
      JSON.stringify(rows[0].source_paths)===JSON.stringify(edge.attribute_paths) && edge.physical_length==='unknown' && edge.path_length_complete===false);
  }
  if(n?.node_type==='equipment' && edge.source_layout_equipment_interface){
    const ev=edge.source_layout_equipment_interface,proof=model.data.sourceLayoutEquipmentOwnership,snapshot=ev.endpoint_snapshot;
    let ownershipPaths=edge.attribute_paths;
    if(edge.source_circle_path_normalization){
      const normalized=edge.source_circle_path_normalization,stage=model.data.sourceCirclePathNormalization;
      const rows=stage?.records?.filter(r=>r.edge_id===edge.edge_id)||[];
      const before=normalized.input_snapshot,after=normalized.output_snapshot;
      if(!(stage?.status==='native_circle_radius_excluded_local_topology_unchanged' && stage.source_sha256===ev.source_sha256 &&
        stage.human_accepted===false && stage.logical_connections_changed===false && normalized.source_sha256===ev.source_sha256 &&
        normalized.human_accepted===false && normalized.physical_connector_length===null && edge.physical_length==='unknown' && edge.path_length_complete===false &&
        rows.length===1 && JSON.stringify(rows[0])===JSON.stringify(normalized) &&
        ['start_node_id','end_node_id','system'].every(k=>before?.[k]===edge[k] && after?.[k]===edge[k]) &&
        JSON.stringify(after?.attribute_paths)===JSON.stringify(edge.attribute_paths)))return true;
      ownershipPaths=before.attribute_paths;
    }
    const matches=proof?.records?.filter(r=>r.edge_id===edge.edge_id && r.equipment_id===id) || [];
    return !(proof?.status==='native_calibrated_logical_ownership_source_checked' && proof.human_accepted===false &&
      proof.physical_ports_verified===false && ev.status==='source_calibrated_logical_ownership' && ev.human_accepted===false &&
      ev.equipment_id===id && ev.system===edge.system && ev.source_sha256===proof.source_sha256 &&
      ev.physical_port_verified===false && ev.interface_to_equipment_length_known===false &&
      snapshot?.start_node_id===edge.start_node_id && snapshot?.end_node_id===edge.end_node_id &&
      snapshot?.equipment_source_handle===n.source_handle && snapshot?.system===edge.system &&
      JSON.stringify(snapshot?.equipment_xy)===JSON.stringify([n.x,n.y]) &&
      JSON.stringify(snapshot?.attribute_paths)===JSON.stringify(ownershipPaths) &&
      matches.length===1 && JSON.stringify(matches[0])===JSON.stringify(ev));
  }
  if(n?.node_type!=='equipment' || c==null)return false;
  const paths=edge.attribute_paths, ix=c.unverified_segment_indices;
  if(!Array.isArray(paths)||paths.length!==1||!Array.isArray(paths[0])||paths[0].length<2||
     !Array.isArray(ix)||!ix.length||ix.some(i=>!Number.isInteger(i)||i<0||i>=paths[0].length-1)||
     new Set(ix).size!==ix.length||![n.x,n.y].every(Number.isFinite))return true;
  const p=paths[0],distance=q=>Array.isArray(q)&&q.length===2&&q.every(Number.isFinite)?Math.hypot(q[0]-n.x,q[1]-n.y):Infinity;
  const touches=(ix.includes(0)&&distance(p[0])<=.05)||(ix.includes(p.length-2)&&distance(p[p.length-1])<=.05);
  const reaches=distance(p[0])<=.05||distance(p[p.length-1])<=.05;
  if(!touches&&reaches)return false;
  if(sourceSupportedEquipment(model,edge,id))return false;
  const ev=edge.confirmed_equipment_interface, answer=ev?.confirmation,side=edge.start_node_id===id?'start':'end';
  let repair=model.data.confirmedEquipmentInterfaceRepair,bound=false;
  while(repair && typeof repair==='object'){
    const rc=repair.confirmation;
    if(repair.source_sha256===c.source_sha256&&rc?.confirmed_by===answer?.confirmed_by&&rc?.question===answer?.question&&rc?.answer===answer?.answer&&Array.isArray(repair.mappings)&&repair.mappings.some(m=>m.edge_id===edge.edge_id&&m.equipment_id===id&&m.system===edge.system&&m.retired_node_id===ev?.original_interface?.node_id))bound=true;
    repair=repair.previous_repair;
  }
  return !(bound&&ev?.source_sha256===c.source_sha256&&ev.interface_side===side&&ev.physical_port_verified===false&&ev.interface_to_equipment_length_known===false&&answer?.confirmed_by==='user'&&answer.question&&answer.answer);
}
export function edgeContactEvidence(model,edge) {
  const describe=id=>{
    const node=model.nodes.get(id);
    if(equipmentEndpointUnverified(model,edge,id))return '\u8bbe\u5907\u63a5\u53e3\u8fde\u63a5\u5f85\u5bf9\u7167';
    if(edge.source_sideview_equipment_interface?.equipment_id===id)return '\u4e3b\u8be6\u56fe\u5df2\u786e\u8ba4\u5bf9\u5e94\u7684\u8bbe\u5907\u903b\u8f91\u5f52\u5c5e\uff1b\u7269\u7406\u7aef\u53e3\u548c\u63a5\u7ba1\u957f\u5ea6\u672a\u77e5';
    if(edge.source_native_block_branch?.equipment_id===id)return '\u539f\u751f\u5757\u5185\u63a5\u7ba1\u5df2\u56de\u8bc1\uff1b\u7701\u7565\u6bb5\u548c\u8f6f\u63a5\u957f\u5ea6\u672a\u77e5';
    if(edge.source_layout_equipment_interface?.equipment_id===id)return '\u6e90\u56fe\u6821\u51c6\u7684\u8bbe\u5907\u903b\u8f91\u5f52\u5c5e\uff1b\u7269\u7406\u7aef\u53e3\u548c\u63a5\u7ba1\u957f\u5ea6\u672a\u77e5';
    if(sourceSupportedEquipment(model,edge,id))return '\u539f\u56fe\u652f\u6301\u8bbe\u5907\u903b\u8f91\u5f52\u5c5e\uff1b\u7269\u7406\u63a5\u53e3\u4e0e\u63a5\u7ba1\u957f\u5ea6\u5f85\u6838';
    const circleMain=inferredCircleMain(model,id);
    if(circleMain!==undefined)return circleMain===null?'\u63a5\u70b9\u6765\u6e90\u4e0d\u552f\u4e00\uff0c\u5f85\u5bf9\u7167':circleMain.has(edge.edge_id)?'\u4e3b\u7ba1\u8fde\u7eed\uff0c\u652f\u8def\u5f85\u5bf9\u7167':'\u652f\u8def\u8fde\u63a5\u5f85\u5bf9\u7167';
    if(!['source_contact_reconstructed_pending_comparison','source_main_continuation_branch_pending'].includes(node?.resolution_state)) return '';
    const main=node.resolution_state==='source_main_continuation_branch_pending'?sourceVerifiedPendingMain(model,id):pendingMainHandle(model,id);
    return main===null?'\u63a5\u70b9\u6765\u6e90\u4e0d\u552f\u4e00\uff0c\u5f85\u5bf9\u7167':(edge.source_handles||[]).includes(main)?'\u4e3b\u7ba1\u8fde\u7eed\uff0c\u652f\u8def\u5f85\u5bf9\u7167':'\u652f\u8def\u8fde\u63a5\u5f85\u5bf9\u7167';
  };
  return {start_contact_status:describe(edge.start_node_id),end_contact_status:describe(edge.end_node_id)};
}
export function traceNetwork(model, seedId) {
  const seed = model.edges.get(seedId);
  if (!seed) return new Set();
  const found = new Set([seedId]), seen = new Set(), todo = [[seed.start_node_id,seed], [seed.end_node_id,seed]];
  while (todo.length) {
    const [id,incoming] = todo.pop(), key=JSON.stringify([id,incoming.edge_id]);
    if (seen.has(key)) continue;
    seen.add(key);
    for (const e of model.adj.get(id)) if (e.system === seed.system && canCross(model,id,incoming,e)) {
      found.add(e.edge_id);
      todo.push([e.start_node_id === id ? e.end_node_id : e.start_node_id,e]);
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
      if (n.node_type !== 'physical_junction' && !equipmentEndpointUnverified(model,e,nodeId)) result.set(nodeId,n);
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
  // A missing completeness flag is unknown, not evidence of a complete path.
  // The resulting value is in drawing units and is not a physical length.
  if ([...model.edges.values()].some(e=>e.system===system && (e.path_length_complete!==true || typeof e.path_length!=='number' || !Number.isFinite(e.path_length) || e.path_length<0)))
    return {error:'\u8be5\u7cfb\u7edf\u5b58\u5728\u957f\u5ea6\u4e0d\u5b8c\u6574\u7684\u7ba1\u6bb5\uff0c\u6682\u4e0d\u80fd\u8ba1\u7b97\u6700\u77ed\u8def\u5f84\u957f\u5ea6\u3002'};
  const start=JSON.stringify([from,null]), dist = new Map([[start,0]]), prev = new Map(), open = new Set([start]);
  let finish;
  while (open.size) {
    let u; for (const n of open) if (u===undefined || dist.get(n)<dist.get(u)) u=n;
    open.delete(u);
    const [nodeId,incomingId]=JSON.parse(u);
    if (nodeId===to) {finish=u;break;}
    const incoming=incomingId===null?null:model.edges.get(incomingId);
    for (const e of model.adj.get(nodeId)) if (e.system===system && !equipmentEndpointUnverified(model,e,nodeId) && (!incoming || canCross(model,nodeId,incoming,e))) {
      const v=e.start_node_id===nodeId?e.end_node_id:e.start_node_id, key=JSON.stringify([v,e.edge_id]);
      if(equipmentEndpointUnverified(model,e,v))continue;
      const d=dist.get(u)+e.path_length;
      if (!dist.has(key) || d<dist.get(key)) {dist.set(key,d);prev.set(key,[u,e.edge_id]);open.add(key);}
    }
  }
  if (!finish) return {error:'No confirmed same-system path. Equipment, interfaces and pending branch contacts can stop traversal.'};
  const edges=[]; for(let n=finish;n!==start;){const [p,e]=prev.get(n);edges.unshift(e);n=p;}
  return {edges,length:dist.get(finish)};
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
// Expert-scoped display policy does not remove a graph boundary or its evidence.
export function shouldShowNodeLabel(node, labelsEnabled, focused, active, selectedEdgeCount) {
  return node.node_label_visible !== false && (labelsEnabled || focused || (active && selectedEdgeCount <= 4));
}
