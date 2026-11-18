// Display existing source-comparison evidence only; do not change graph links.
function circleHistoryStillMatches(data){
 const history=data.sourceCircleCrossoverConflictHistory;
 if(!Array.isArray(data.sourceCircleCrossoverConflicts)||data.sourceCircleCrossoverConflicts.length||!Array.isArray(history)||!history.length)return false;
 const nodes=new Map((data.nodes||[]).map(n=>[n.node_id,n])),edges=new Map((data.edges||[]).map(e=>[e.edge_id,e]));
 for(const audit of history){
  if(audit.source_sha256!==data.metadata?.source_sha256||audit.connectivity_changed!==false||!Array.isArray(audit.records)||!audit.records.length)return false;
  for(const record of audit.records){
   const links=record.connections;
   if(record.resolution!=='separate_confirmed_tees_on_native_main_not_collinear_gap'||!Array.isArray(links)||links.length!==2||new Set(links.map(c=>c.node_id)).size!==2)return false;
   for(const c of links){
    const n=nodes.get(c.node_id),b=edges.get(c.branch_edge);
    if(!n||!b||!['tee','physical_junction'].includes(n.node_type))return false;
    const incident=[...edges.values()].filter(e=>[e.start_node_id,e.end_node_id].includes(c.node_id));
    if(incident.length!==3||!incident.includes(b)||incident.some(e=>e.system!==n.system))return false;
    const mains=incident.filter(e=>e!==b).map(e=>e.edge_id).sort();
    if(JSON.stringify(mains)!==JSON.stringify([...(c.main_edges||[])].sort()))return false;
    for(const obj of [n,b]){
     const ev=obj.user_confirmed_overlap_connection;
     if(!ev||ev.circle_handle!==c.circle_handle||ev.branch_handle!==c.branch_handle||ev.user_evidence_manifest_sha256!==audit.evidence_manifest_sha256)return false;
    }
   }
   const main=edges.get(record.native_main_edge);
   if(!main||JSON.stringify([main.start_node_id,main.end_node_id].sort())!==JSON.stringify(links.map(c=>c.node_id).sort()))return false;
  }
 }
 return true;
}

export function sourceComparisonItems(data){
 const items=[],seen=new Set(),seenFamilies=new Set();let comparison=data.preHilComparison;
 const archivedCircleResolution=circleHistoryStillMatches(data);
 while(comparison&&typeof comparison==='object'&&!seen.has(comparison)){
  seen.add(comparison);
  for(const family of Array.isArray(comparison.families)?comparison.families:[]){
   if(!family||seenFamilies.has(family.id))continue;seenFamilies.add(family.id);
   const archived=family.id==='circle_crossover_conflict'&&archivedCircleResolution;
   items.push({kind:'family',id:family.id||'unknown',status:archived?'resolved':family.status||'pending',description:archived?'Archived after source-bound separate-tee reconstruction; original conflict retained in graph history. Other checks remain pending.':family.disposition||''});
  }
  comparison=comparison.previous_comparison;
 }
 for(const row of data.sourceNamedEndpointLeaderCandidates||[])items.push({kind:'named_leader',id:row.node_id,node:row.node_id,label:row.label?.original_text||'',pipe:row.pipe_handle||'',leader:row.leader_handle||'',text:row.text_handle||''});
 for(const row of data.pendingGapJoints||[])items.push({kind:'gap_joint',id:row.source_handles?.[0]||'',edge:row.candidate_edge_id||null});
 for(const group of data.pendingPlanLineGroups||[]){
  if(group?.status!=='pending_source_comparison'||!Array.isArray(group.members)||!group.members.length)continue;
  items.push({kind:'plan_line_group',id:group.id,members:group.members.map(m=>({handle:m.source_handle,node:m.node_id||null})),count:group.members.length});
 }
 for(const conflict of data.sourceCircleCrossoverConflicts||[]){
  const handles=conflict.source_handles||[];const edge=(data.edges||[]).find(e=>handles.some(h=>(e.source_handles||[]).includes(h)));
  const circles=(conflict.circle_conflicts||[]).map(c=>c.circle_handle).filter(Boolean);
  items.push({kind:'circle_conflict',id:circles.join(', ')||'circle',edge:edge?.edge_id||null});
 }
 for(const conflict of data.sourceInlineSystemConflicts||[]){
  const edge=(data.edges||[]).find(e=>e.edge_id===conflict.assigned_edge_id);
  items.push({kind:'inline_conflict',id:conflict.joint_handle||'joint',edge:edge?.edge_id||null,device:conflict.device_name||''});
 }
 return items;
}

// A zero-length list is not evidence that source comparison was completed.
export function sourceComparisonBadge(items){
 return items.length ? String(items.length) : '\u5f85\u5bf9\u7167';
}
