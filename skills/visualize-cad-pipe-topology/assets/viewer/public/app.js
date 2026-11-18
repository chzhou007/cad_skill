import {reviewCsvValues,reviewCsvFields,reviewAttributeCsvFields} from './edge-review.js';
import {fragmentOverlayGraphContext} from './fragment-component-overlay.js';
import {componentInventoryGraphContext} from './component-inventory-attribute-bridge.js';
import {createModel,traceNetwork,connectedEquipment,inventory,shortestPath,visibleEdge,makeCsv,hydraulicProperties,sourceContextPoints,edgeContactEvidence,shouldShowNodeLabel} from './core.js';
import {nativePaths,pointBounds,nativeObjectFocusBounds,sourceAnnotationMarkup,sourceRegionGuide,replaceGraphMarkup,pendingSourceObjectMarkup,sourceTerminalMarkup} from './native-rendering.js';
import {edgeAttributeProperties,edgeAttributeCsvFields,waveOmissionDescription,nodeFloorRepairProperties,crossViewAttributeCsvValues,ownershipLengthScopeCsvValues} from './edge-attributes.js';
import {crossbarCandidateProperties} from './source-crossbar.js';
import {sourceComparisonItems,sourceComparisonBadge} from './source-comparison-items.js';
import {equipmentIdentityCandidateProperties,equipmentIdentityResolutionProperties} from './equipment-identity-candidates.js';
import {cappedInterfaceKind,cappedInterfaceProperties,cappedInterfaceInterpretation} from './source-capped-interface.js';
import {externalBoundaryLabel,externalBoundaryProperties} from './external-feed-plan-attributes.js';

const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const NS='http://www.w3.org/2000/svg';
const COLOR={supply:'#cf26bd',return:'#aa7a10'};
const state={floor:'all',systems:new Set(['supply','return']),scope:'segment',selection:null,focus:null,tab:'connections',type:null,instance:null,filter:'',compare:false,sync:true,showSource:true,view:null,cadView:null,layers:{equipment:true,tee:true,virtual:true,components:false,labels:false},showPending:true};
let model, data, cadMarkup='', globalBounds, toastTimer, lastSearch=[], sourceReady=false, cadHitKey='';
const nodeSystem=n=>n.system||(n.subtype==='tee_supply'?'supply':n.subtype==='tee_return'?'return':null);
const nodeKind=n=>cappedInterfaceKind(n,data)||(n.resolution_state==='source_main_continuation_branch_pending'?'\u5f85\u6838\u67e5\u4e09\u5411\u63a5\u70b9':n.viewer_non_node_boundary?'\u975e\u7269\u7406\u8fb9\u754c\uff08\u67e5\u770b\u5668\u5360\u4f4d\uff09':n.node_type==='equipment'?'Equipment':n.node_type==='virtual_equipment'?(n.boundary_type==='unresolved_source_terminal'?'Unresolved Source Terminal':'Virtual Interface'):'T-junction');
const nativeEquipmentProperties=n=>{
 if(n.node_type!=='equipment')return [];
 const zh=data.display?.edge_attribute_language==='zh-CN',rows=[];
 rows.push(...equipmentIdentityCandidateProperties(n));
 rows.push(...equipmentIdentityResolutionProperties(n));
 if(n.source_enclosed_return_group){const q=n.source_enclosed_return_group;rows.push([zh?'\u6e90\u56fe\u8bbe\u5907\u8303\u56f4\u5185\u56de\u6c34\u7ec4':'Return graph inside source enclosure',`${q.node_ids.length} ${zh?'\u4e2a\u8282\u70b9':'nodes'} / ${q.edge_ids.length} ${zh?'\u6761\u8fb9':'edges'} / ${q.component_names.length} ${zh?'\u4e2a\u6784\u4ef6':'components'}`],[zh?'\u8bbe\u5907\u5f52\u5c5e\u72b6\u6001':'Equipment ownership',zh?'\u6e90\u56fe\u8303\u56f4\u5206\u7ec4\uff1b\u7269\u7406\u7aef\u53e3\u548c\u5f52\u5c5e\u5f85\u6838':'Source enclosure grouping; physical ports and ownership unverified']);}
 if(n.source_tower_design_requirement){const q=n.source_tower_design_requirement;rows.push([zh?'\u9879\u76ee\u8bbe\u8ba1\u8bf4\u660e':'Project design note',q.text+' ['+q.source_handle+']'],[zh?'\u8bf4\u660e\u9002\u7528\u72b6\u6001':'Note scope',zh?'\u4e00\u822c\u8981\u6c42\uff1b\u672a\u786e\u8ba4\u5177\u4f53\u7ba1\u53e3':'General requirement; individual port unconfirmed']);}
 if(n.source_caption)rows.push([zh?'\u8bbe\u5907\u539f\u6587':'Source caption',n.source_caption]);
 if(n.subtype)rows.push([zh?'\u8bbe\u5907\u7c7b\u578b':'Equipment type',zh?(n.subtype_zh||n.subtype):n.subtype]);
 if(n.source_class_reference)rows.push([zh?'\u9879\u76ee\u7c7b\u522b\u4f9d\u636e':'Project class reference',n.source_class_reference.text+' ['+n.source_class_reference.handle+']']);
 if(n.source_port_completeness==='unbound_source_contacts_require_comparison')rows.push([zh?'\u63a5\u7ba1\u72b6\u6001':'Port status',zh?'\u5c1a\u672a\u7ed1\u5b9a\uff0c\u9700\u5bf9\u7167\u539f\u56fe':'Not bound; compare source geometry']);
 if(n.source_port_candidates?.length)rows.push([zh?'\u5019\u9009\u7ba1\u53e3':'Candidate ports',n.source_port_candidates.length+(zh?' \u4e2a\uff08\u672a\u7ed1\u5b9a\uff09':' (not bound)')],[zh?'\u5019\u9009\u5185\u90e8\u7ba1\u6bb5':'Candidate internal path',n.source_internal_path_candidate?.edge_id||'']);
 if(n.source_assembly_candidate)rows.push([zh?'\u7ec4\u5408\u5019\u9009':'Assembly candidate',n.source_assembly_candidate.group_id],[zh?'\u76f8\u90bb\u6a21\u5757':'Paired source module',n.source_assembly_candidate.peer_node_id],[zh?'\u7cfb\u7edf\u56fe\u7f16\u53f7':'Schematic tag',zh?'\u5c1a\u672a\u5bf9\u5e94':'Not mapped']);
 if(n.source_internal_return_candidate)rows.push([zh?'\u56de\u6c34\u5165\u53e3\u5019\u9009':'Return entry candidate',n.source_internal_return_candidate.entry_edge_id+' / '+n.source_internal_return_candidate.junction_node_id],[zh?'\u5f52\u5c5e\u72b6\u6001':'Ownership status',zh?'\u672a\u7ed1\u5b9a\uff0c\u9700\u5bf9\u7167\u539f\u56fe':'Unbound; compare source']);
 return rows;
};
const systemName=s=>`${data.systems[s].code} \xb7 ${data.systems[s].name}`;
const englishMode=s=>String(s||'').replaceAll('_',' ').replaceAll('DIM SYMB','omission marker').replaceAll('T','T');
const edgePath=points=>points.length?'M'+points.map(p=>p.map(x=>x.toFixed(3)).join(',')).join(' L'):'';
const floorLabel=f=>f==='all'?'All floors':data.floors.find(x=>x.id===String(f))?.label||String(f);
function symbol(type,cls='symbol'){
  if(!data.symbols[type]) return `<span class="type-badge" title="Source symbol not isolated">${esc(type)}</span>`;
  return `<svg class="${cls}" viewBox="0 0 64 64" aria-hidden="true"><use href="#sym-${type}"/></svg>`;
}
function selectedIds(){
  const s=state.selection;
  if(!s)return new Set();
  if(s.kind==='edge')return state.scope==='network'?traceNetwork(model,s.id):new Set([s.id]);
  if(s.kind==='path')return new Set(s.ids);
  return new Set((model.adj.get(s.id)||[]).filter(e=>state.systems.has(e.system)).map(e=>e.edge_id));
}
function selectionNodes(ids=selectedIds()){
  const out=new Set();
  for(const id of ids){const e=model.edges.get(id);out.add(e.start_node_id);out.add(e.end_node_id);}
  if(state.selection?.kind==='node')out.add(state.selection.id);
  if(state.focus)out.add(state.focus);
  return out;
}
function visibleNodes(){return data.nodes.filter(n=>(state.floor==='all'||String(n.floor)===state.floor)&&(n.mixed_source_contact?(model.adj.get(n.node_id)||[]).some(e=>state.systems.has(e.system)):(!nodeSystem(n)||state.systems.has(nodeSystem(n)))));}
function bounds(points,pad=12){
  return pointBounds(points,pad,globalBounds||[0,0,1000,800]);
}
function aspectFit(b,svg){
  const r=svg.getBoundingClientRect(),ratio=r.width/Math.max(r.height,1),cx=b[0]+b[2]/2,cy=b[1]+b[3]/2;
  let w=b[2],h=b[3];if(w/h<ratio)w=h*ratio;else h=w/ratio;
  return [cx-w/2,cy-h/2,w,h];
}
function applyView(){
  if(!state.view)return;
  $('#graph-svg').setAttribute('viewBox',state.view.join(' '));
  $('#cad-svg').setAttribute('viewBox',(state.sync?state.view:state.cadView||state.view).join(' '));
  $('#zoom-value').textContent=`${Math.round(globalBounds[2]/state.view[2]*100)}%`;
  document.dispatchEvent(new Event('cad-view-changed'));
  const rect=$('#minimap-viewport');if(rect){['x','y','width','height'].forEach((k,i)=>rect.setAttribute(k,state.view[i]));}
}
function fitView(selection=false){
  let pts=[];
  if(selection){for(const id of selectedIds())pts.push(...model.edges.get(id).points);if(state.selection?.kind==='node'){const n=model.nodes.get(state.selection.id);pts.push([n.px,n.py]);}}
  else {for(const e of data.edges)if(visibleEdge(e,state.floor,state.systems))for(const p of e.points)pts.push(p);for(const n of visibleNodes()){pts.push([n.px,n.py]);for(const path of n.sourceGeometry||[])for(const p of path.points)pts.push(p);}if(state.showPending)for(const p of sourceContextPoints(data.pendingSourcePaths||[],state.floor))pts.push(p);}
  if(!pts.length)pts=visibleNodes().map(n=>[n.px,n.py]);
  const raw=bounds(pts,selection?8:20),r=$('#graph-svg').getBoundingClientRect();
  // Reserve the label bar and bottom controls rather than fitting under them.
  const scale=Math.min(Math.max(80,r.width-60)/raw[2],Math.max(80,r.height-100)/raw[3]);
  state.view=[raw[0]+raw[2]/2-r.width/scale/2,raw[1]+raw[3]/2-r.height/scale/2-8/scale,r.width/scale,r.height/scale];
  if(state.sync||!state.cadView)state.cadView=[...state.view];
  renderGraph();
}
function focusNode(id){
  const n=model.nodes.get(id);if(!n)return;
  state.focus=id;
  if(state.floor!=='all'&&state.floor!==String(n.floor)){state.floor=String(n.floor);updateControls();}
  const s=nodeSystem(n);if(s&&!state.systems.has(s)){state.systems.add(s);updateControls();}
  const adjacent=model.adj.get(id)||[];const points=adjacent.length?[[n.px,n.py],...adjacent.flatMap(e=>e.points)]:[[n.px-12,n.py-12],[n.px+12,n.py+12]];
  points.push(...(n.sourceGeometry||[]).flatMap(p=>p.points));
  state.view=aspectFit(bounds(points,5),$('#graph-svg'));
  if(state.sync)state.cadView=[...state.view];
  renderGraph();renderDetails();
}
function selectEdge(id,{focus=false}={}){
  const e=model.edges.get(id);if(!e)return;
  $('#toast').hidden=true;
  state.selection={kind:'edge',id};state.focus=null;state.type=null;state.instance=null;state.filter='';
  state.systems.add(e.system);
  if(state.floor!=='all'&&![e.floor_start,e.floor_end].map(String).includes(state.floor))state.floor=String(e.floor_start);
  updateControls();render();if(focus)fitView(true);
}
function selectNode(id,{focus=false}={}){
  if(!model.nodes.has(id))return;
  $('#toast').hidden=true;
  state.selection={kind:'node',id};state.focus=id;state.type=null;state.instance=null;state.filter='';
  render();if(focus)focusNode(id);
}
function notify(text){$('#toast').textContent=text;$('#toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').hidden=true,3800);}
function defsMarkup(){return `<defs>${Object.entries(data.symbols).map(([code,s])=>`<symbol id="sym-${code}" viewBox="0 0 64 64"><g stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round">${s.markup}</g></symbol>`).join('')}</defs>`;}
function renderGraph(){
  const svg=$('#graph-svg');if(!state.view)return;
  const ids=selectedIds(), sn=selectionNodes(ids), selected=!!state.selection;
  const rendered=data.edges.filter(e=>visibleEdge(e,state.floor,state.systems));
  const unit=state.view[2]/Math.max(svg.clientWidth,100), fs=11*unit;
  const pipe=(e,high=false)=>{
    const paths=(e.source_path_coverage||e.connection_mode==='source_calibrated_wave_omission_unreviewed'||e.path_length_scope==='drawing_paths_excluding_source_crossover_gaps_physical_length_unknown')?e.sourcePaths:[e.points];
    const witnessed=paths.map(p=>`<path data-edge="${e.edge_id}" d="${edgePath(p)}" fill="none" stroke="${COLOR[e.system]}" stroke-width="${high?3:1.4}" stroke-dasharray="${data.systems[e.system].dash||'none'}" vector-effect="non-scaling-stroke" opacity="${high?1:selected?.42:.85}"><title>${esc(e.edge_id)} \u00b7 ${esc(systemName(e.system))}</title></path>`).join('');
    const unknown=(e.unverifiedPaths||[]).map(p=>`<path data-edge="${e.edge_id}" d="${edgePath(p)}" fill="none" stroke="#8b6577" stroke-width="${high?2.6:1.2}" stroke-dasharray="2 5" vector-effect="non-scaling-stroke" opacity="${high?1:selected?.42:.8}"><title>\u56fe\u793a\u903b\u8f91\u8fde\u63a5\uff1a\u9650\u5b9a\u8303\u56f4\u5185\u672a\u627e\u5230\u6e90\u7ebf\u89c1\u8bc1\uff0c\u7269\u7406\u957f\u5ea6\u672a\u77e5</title></path>`).join('');
    const device=(e.deviceSourcePaths||[]).map(p=>`<path data-edge="${e.edge_id}" d="${edgePath(p)}" fill="none" stroke="${COLOR[e.system]}" stroke-width="${high?3:1.4}" stroke-dasharray="4 2" vector-effect="non-scaling-stroke" opacity="${high?1:selected?.42:.85}"><title>\u8bbe\u5907\u4fa7\u539f\u56fe\u7ebf\u6bb5\uff1b\u5b9e\u9645\u7aef\u53e3\u548c\u7269\u7406\u957f\u5ea6\u5f85\u6838</title></path>`).join('');
    return witnessed+unknown+device;
  };
  let paths=(state.showPending?(data.pendingSourcePaths||[]).map(p=>`<path d="${edgePath(p.points)}" fill="none" stroke="#8495aa" stroke-dasharray="2 5" stroke-width="1" opacity=".23" vector-effect="non-scaling-stroke" pointer-events="none"><title>Unresolved source context; not a recognized logical edge</title></path>`).join('')+pendingSourceObjectMarkup(data.pendingSourceObjects,null,state.floor):'')+rendered.map(e=>pipe(e)).join('');
  if(state.layers.virtual)paths+=sourceTerminalMarkup(data.sourceTerminalGlyphs,null,state.floor,state.systems);
  paths+=rendered.filter(e=>ids.has(e.edge_id)).map(e=>pipe(e,true)).join('');
  paths+=rendered.map(e=>`<path class="edge-hit" data-edge="${e.edge_id}" d="${edgePath(e.points)}" fill="none" stroke="transparent" stroke-width="12" vector-effect="non-scaling-stroke" tabindex="-1" aria-label="${e.edge_id} ${systemName(e.system)}"/>`).join('');
  const nodes=visibleNodes();let glyphs='';
  const reviewIds=new Set(data.review.map(r=>r.id));
  for(const n of nodes){
    const kind=n.node_type==='equipment'?'equipment':n.node_type==='virtual_equipment'?'virtual':'tee';
    if(!state.layers[kind])continue;
    const active=sn.has(n.node_id),focused=state.focus===n.node_id||state.selection?.id===n.node_id;
    const color=focused?'#2462ed':kind==='tee'?COLOR[nodeSystem(n)]:n.boundary_type==='unresolved_source_terminal'?'#b77910':'#354b6b';
    const size=kind==='equipment'?15*unit:kind==='virtual'?6*unit:2.5*unit;
    let shape=kind==='equipment'?`<use href="#sym-${n.symbol_key||'EQUIPMENT'}" x="${-size/2}" y="${-size/2}" width="${size}" height="${size}"/>`:kind==='virtual'?`<path d="M0,${-size} L${size},0 L0,${size} L${-size},0 Z" fill="white" stroke="${color}" stroke-width="1.2" vector-effect="non-scaling-stroke"/>`:`<circle r="${size}" fill="${active?color:'#fff'}" stroke="${color}" stroke-width="1.2" vector-effect="non-scaling-stroke"/>`;
    if(n.viewer_non_node_boundary)shape=`<path d="M${-size/2},${-size} L${size/2},${-size} M0,${-size} L0,${size}" fill="none" stroke="${color}" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`;
    if(kind==='equipment'&&n.sourceGeometry?.length)shape=nativePaths(n.sourceGeometry.map(p=>({...p,points:p.points.map(q=>[q[0]-n.px,q[1]-n.py])})));
    if(reviewIds.has(n.node_id))shape=`<circle r="${7*unit}" fill="#edae3320" stroke="#dca031" stroke-width="1" vector-effect="non-scaling-stroke"/>`+shape;
    if(focused)shape=`<circle r="${10*unit}" fill="#2462ed15" stroke="#2462ed" stroke-width="1.4" vector-effect="non-scaling-stroke"/>`+shape;
    const label=shouldShowNodeLabel(n,state.layers.labels,focused,active,ids.size);
    const labelY=n.sourceGeometry?.length?Math.max(...n.sourceGeometry.flatMap(p=>p.points.map(q=>q[1]-n.py)))+fs+3*unit:size+fs+3*unit;
    glyphs+=`<g class="node-hit" data-node="${n.node_id}" role="button" tabindex="0" aria-label="${n.node_id} ${nodeKind(n)}" transform="translate(${n.px},${n.py})" style="color:${color}" opacity="${selected&&!active?.22:1}"><circle r="${10*unit}" fill="transparent"/>${shape}${label?`<text x="0" y="${labelY}" text-anchor="middle" fill="${color}" font-size="${fs}" font-family="Segoe UI,Arial" stroke="white" stroke-width="${3*unit}" paint-order="stroke">${n.node_id}</text>`:''}</g>`;
  }
  let componentGlyphs='';
  if(state.layers.components){
    for(const d of data.instances){
      const linked=d.related_edge_ids||[d.edge_id];if(!linked.some(id=>visibleEdge(model.edges.get(id),state.floor,state.systems)))continue;
      if(selected&&!linked.some(id=>ids.has(id)))continue;
      if(d.sourceGeometry?.length){componentGlyphs+=`<g class="component-hit native-source-component" data-instance="${d.id}" aria-label="${esc(d.name)} ${esc(d.label)}" style="color:${d.source_head_status?.startsWith('pending_')?'#b77910':'#354b6b'}">${nativePaths(d.sourceGeometry)}</g>`;continue;}
      const size=18*unit;
      componentGlyphs+=`<g class="component-hit" data-instance="${d.id}" transform="translate(${d.px},${d.py})" style="color:#24344d"><rect x="${-size/2}" y="${-size/2}" width="${size}" height="${size}" fill="white" fill-opacity=".93"/>${data.symbols[d.type]?`<use href="#sym-${d.type}" x="${-size/2}" y="${-size/2}" width="${size}" height="${size}"/>`:`<text font-size="${9*unit}" text-anchor="middle">AV</text>`}</g>`;
    }
  }
  let edgeLabels='';
  if(ids.size>0&&ids.size<=8){for(const e of rendered.filter(e=>ids.has(e.edge_id))){const p=e.points[Math.floor(e.points.length/2)];edgeLabels+=`<text x="${p[0]}" y="${p[1]-6*unit}" text-anchor="middle" font-size="${fs}" fill="${COLOR[e.system]}" stroke="white" stroke-width="${3*unit}" paint-order="stroke" font-family="Segoe UI,Arial" pointer-events="none">${e.edge_id}</text>`;}}
  const floorGuides=state.floor==='all'?data.floors.map(floor=>{const f=floor.id,p=sourceRegionGuide(f,data.nodes,unit);return p?`<text x="${p.x}" y="${p.y}" font-size="${13*unit}" font-family="Segoe UI,Arial" fill="#7e8ca2" font-weight="600">${esc(floorLabel(f))}</text>`:'';}).join(''):'';
  replaceGraphMarkup(svg,`<g pointer-events="none">${floorGuides}</g><g id="edge-layer">${paths}</g><g id="node-layer">${glyphs}</g><g id="component-layer">${componentGlyphs}</g><g>${edgeLabels}</g><g id="source-text-annotations" pointer-events="none">${sourceAnnotationMarkup(data.sourceAnnotations)}</g>`);
  $('#empty-view').hidden=state.systems.size>0;
  $('#canvas-hint').textContent=!selected?'Select a pipe to inspect its connected equipment':`${ids.size} selected edge${ids.size===1?'':'s'} \xb7 ${rendered.filter(e=>ids.has(e.edge_id)).length} visible in current filters`;
  $('#view-title').textContent=state.compare?'Topology & CAD comparison':state.floor==='all'?'All-floor topology':`${floorLabel(state.floor)} \xb7 Pipe topology`;
  $('#view-filter-label').textContent=floorLabel(state.floor);
  $('#selection-status').textContent=selected?`${ids.size} selected edges \xb7 ${connectedEquipment(model,ids).length} equipment / interfaces \xb7 ${inventory(model,ids).reduce((s,x)=>s+x.instances.length,0)} components`:`${nodes.length} visible nodes \xb7 ${rendered.length} visible edges`;
  renderCad();renderMinimap();applyView();
}
function renderCad(){
  if(!state.compare)return;
  const ids=selectedIds();
  let high='';
  if(state.showSource)for(const id of ids){const e=model.edges.get(id);high+=[...e.sourcePaths,...(e.deviceSourcePaths||[])].map((path,i)=>`<path data-edge="${id}" data-source-edge="${id}" data-source-path="${i}" d="${edgePath(path)}" fill="none" stroke="${COLOR[e.system]}" stroke-width="2.5" stroke-dasharray="${data.systems[e.system].dash||'none'}" vector-effect="non-scaling-stroke"/>`).join('');}
  if(state.instance){const d=data.instances.find(d=>d.id===state.instance),u=(state.sync?state.view:state.cadView)[2]/Math.max($('#cad-svg').clientWidth,100);if(d)high+=`<circle cx="${d.sourceX}" cy="${d.sourceY}" r="${12*u}" fill="#2462ed18" stroke="#2462ed" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`;}
  const svg=$('#cad-svg');
  if(!$('#cad-source-geometry')){
    svg.innerHTML='<g id="cad-source-geometry" style="color:#63778f" opacity=".48"></g><g id="cad-edge-hits"></g><g id="cad-selected-paths"></g>';
    cadHitKey='';
  }
  const source=$('#cad-source-geometry');
  if(sourceReady&&!source.dataset.loaded){source.innerHTML=cadMarkup;source.dataset.loaded='true';}
  const key=[state.floor,...state.systems].join(':');
  if(key!==cadHitKey){$('#cad-edge-hits').innerHTML=data.edges.filter(e=>visibleEdge(e,state.floor,state.systems)).flatMap(e=>e.sourcePaths.map(path=>`<path class="cad-edge-hit" data-edge="${e.edge_id}" d="${edgePath(path)}" fill="none" stroke="transparent" stroke-width="10" vector-effect="non-scaling-stroke"/>`)).join('');cadHitKey=key;}
  $('#cad-selected-paths').innerHTML=high;
}
function renderMinimap(){
  const m=$('#minimap');m.setAttribute('viewBox',globalBounds.join(' '));
  if(m.childElementCount)return;
  const routes=data.edges.map(e=>`<path d="${edgePath(e.points)}" fill="none" stroke="${COLOR[e.system]}" opacity=".35" stroke-width=".6"/>`).join('');
  m.innerHTML=routes+`<rect id="minimap-viewport" x="${state.view[0]}" y="${state.view[1]}" width="${state.view[2]}" height="${state.view[3]}" fill="#2462ed12" stroke="#2462ed" stroke-width="3"/>`;
}
function headerProperties(rows){return `<dl class="properties">${rows.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>`;}
function renderDetails(){
  const ids=selectedIds(),equip=connectedEquipment(model,ids),groups=inventory(model,ids),count=groups.reduce((s,g)=>s+g.instances.length,0),s=state.selection;
  $('#equipment-count').textContent=equip.length;$('#component-count').textContent=count;
  const header=$('#detail-header');
  if(!s){header.innerHTML=`<div class="detail-eyebrow"><h2>Graph overview</h2><span class="tag">${esc(data.project.id)}</span></div><p class="detail-description">Explore the water network. Select a segment, trace a system, or locate equipment.</p><div class="overview-metrics"><div class="metric"><strong>${data.nodes.length.toLocaleString("en")}</strong><span>TOTAL NODES</span></div><div class="metric"><strong>${data.edges.length.toLocaleString("en")}</strong><span>LOGICAL EDGES</span></div><div class="metric"><strong>${data.nodes.filter(n=>n.node_type==="equipment").length.toLocaleString("en")}</strong><span>EQUIPMENT</span></div><div class="metric"><strong>${data.instances.length.toLocaleString("en")}</strong><span>PIPE COMPONENTS</span></div></div>`;}
  else if(s.kind==='edge'){
    const e=model.edges.get(s.id);
    const partialAxis=e.source_inline_axis_candidates?.some(x=>x.status==='axis_projection_partial'),zh=data.display?.edge_attribute_language==='zh-CN';
    const connection=e.source_wave_omission?.scoped_expert_convention_confirmed?'\u4e13\u5bb6\u786e\u8ba4\u957f\u7ba1\u7701\u7565\u8fde\u901a\uff1b\u6574\u56fe\u672a\u9a8c\u6536':e.source_path_coverage?(zh?'\u90e8\u5206\u56fe\u6bb5\u672a\u89c1\u8bc1\uff0c\u903b\u8f91\u8fde\u63a5\u5f85\u6838':'Logical connection; source evidence incomplete'):e.source_omission_length_status?(zh?'\u7701\u7565\u8868\u8fbe\u548c\u8bbe\u5907\u8fde\u63a5\u957f\u5ea6\u672a\u8bc1\u5b9e':'Omission and equipment connection length unverified'):partialAxis?(zh?'\u5c40\u90e8\u6295\u5f71\uff0c\u5143\u4ef6\u8fde\u901a\u5f85\u6838':'Partial axis projection; component continuity unverified'):englishMode(e.connection_mode);
    header.innerHTML=`<div class="detail-eyebrow"><h2>Pipe details</h2><span class="tag ${e.system}">${systemName(e.system)}</span></div><div class="detail-title">${e.edge_id}${state.scope==='network'?' \xb7 Network':''}</div>${headerProperties([['Start',e.start_node_id],['End',e.end_node_id],['Floor',e.floor_start===e.floor_end?`${floorLabel(e.floor_start)}`:`${floorLabel(e.floor_start)} \u2014 ${floorLabel(e.floor_end)}`],e.source_path_status==='user_confirmed_overlay_no_native_supply_path'?['\u539f\u56fe\u65e0\u72ec\u7acb\u4f9b\u6c34\u7ebf','\u7528\u6237\u786e\u8ba4\u53e0\u7ba1\uff1b\u957f\u5ea6\u672a\u77e5']:e.path_length_complete===false?[(e.source_omission_length_status||e.path_length_scope==='drawing_paths_excluding_source_crossover_gaps_physical_length_unknown')?'\u56fe\u793a\u7ebf\u6bb5\u957f\u5ea6\uff08\u7269\u7406\u957f\u5ea6\u672a\u77e5\uff09':'\u6e90\u56fe\u7ebf\u6bb5\u957f\u5ea6\uff08\u90e8\u5206\u957f\u5ea6\u672a\u77e5\uff09',(e.path_length===null?'\u672a\u77e5':e.path_length.toLocaleString('en',{maximumFractionDigits:1})+' \u56fe\u7eb8\u5355\u4f4d')]:['CAD path length',e.path_length.toLocaleString('en',{maximumFractionDigits:1})+' drawing units'],...edgeAttributeProperties(e,data),...((e.source_device_extension||e.source_exploded_device_chain)?[[zh?'\u8bbe\u5907\u4fa7\u7ebf\u6bb5':'Device-side line',zh?'\u672a\u8ba1\u5165\u4e0a\u8ff0\u56fe\u793a\u957f\u5ea6\uff1b\u7269\u7406\u957f\u5ea6\u672a\u77e5':'Excluded from the drawing length above; physical length unknown']]:[]),...(e.source_wave_terminal?[["\u7ed8\u56fe\u8bc1\u636e","\u5355\u4fa7\u6ce2\u6d6a\u65ad\u7ebf\uff1b\u8fdc\u7aef\u53bb\u5411\u5f85\u6838"],["\u539f\u56fe\u6ce2\u6d6a\u7b26",e.source_wave_terminal.source_wave_handle]]:[]),...(e.source_wave_omission?[["\u7ed8\u56fe\u8bc1\u636e",waveOmissionDescription(e)],["\u539f\u56fe\u6ce2\u6d6a\u7b26",(e.source_wave_omission.wave_handles||e.source_wave_omission.source_insert_handles||[]).join('\u3001')]]:[]),...(e.confirmed_equipment_interface?[["\u63a5\u53e3\u5f52\u5c5e","\u7528\u6237\u5df2\u786e\u8ba4\uff1b\u5b9e\u9645\u63a5\u7ba1\u4f4d\u7f6e\u672a\u8bc1\u5b9e"],["\u539f\u56fe\u63a5\u53e3",e.confirmed_equipment_interface.original_interface.node_id],["\u63a5\u7ba1\u957f\u5ea6","\u672a\u77e5"]]:[]),...(e.source_annotation_references||[]).flatMap(r=>[["\u539f\u56fe\u63a5\u81f3\u6807\u6ce8",r.source_note],["\u6807\u6ce8\u5173\u8054\u7aef\u70b9",r.endpoint_node_id],["\u5173\u8054\u72b6\u6001","\u539f\u56fe\u6807\u6ce8\u5173\u7cfb\uff1b\u8fde\u901a\u672a\u8bc1\u5b9e"]]),['Source paths',e.sourcePaths.length+(e.deviceSourcePaths||[]).length],['Connection',connection]])}${state.scope==='network'?'<p class="section-note">Same system only. Stops at equipment and virtual interface boundaries; current floor filters affect display, not tracing.</p>':''}`;
  }else if(s.kind==='node'){
    const n=model.nodes.get(s.id),rev=data.review.find(x=>x.id===s.id),adj=model.adj.get(s.id);
    header.innerHTML=`<div class="detail-eyebrow"><h2>${rev?'Pending review':nodeKind(n)+' details'}</h2><span class="tag ${rev?'review':''}">${floorLabel(n.floor)}</span></div><div class="detail-title">${n.node_id}</div>${headerProperties([['Type',nodeKind(n)],['Logical degree',adj.length],...nativeEquipmentProperties(n),...externalBoundaryProperties(n,data.edges,data.display?.edge_attribute_language==='zh-CN'),...cappedInterfaceProperties(n,data),...crossbarCandidateProperties(n),...nodeFloorRepairProperties(n,data),...(n.source_inline_endpoint_group?[["\u7ba1\u6bb5\u56fe\u5757\u5206\u7ec4",n.source_inline_endpoint_group.group_id],["\u6062\u590d\u56fe\u5757",n.source_inline_endpoint_group.source_insert_handle],...(n.source_inline_endpoint_group.source_provenance?[["\u53c2\u7167\u56fe\u5757\u53e5\u67c4",n.source_inline_endpoint_group.source_provenance.reference_insert_handle],["\u7ba1\u7ebf\u4e3b\u56fe\u53e5\u67c4",n.source_inline_endpoint_group.source_provenance.primary_line_handles.join(" / ")],["\u56fe\u5757\u6765\u6e90","T3 \u53c2\u7167\u6062\u590d\uff1b\u4e0e\u4e3b\u56fe\u4ee3\u7406\u5bf9\u8c61\u7684\u9010\u4e2a\u5bf9\u5e94\u5f85\u6838"]]:[]),["\u540c\u8fb9\u7aef\u70b9",n.source_inline_endpoint_group.endpoint_node_ids.join(' / ')],["\u8f74\u5411\u8986\u76d6",n.source_inline_endpoint_group.axis_projection_status==='axis_projection_partial'?"\u90e8\u5206\u6295\u5f71":"\u6295\u5f71\u8de8\u8d8a\u4e24\u70b9"],["\u5206\u7ec4\u542b\u4e49","\u56fe\u5757\u5df2\u6302\u63a5\u8be5\u8fb9\uff1b\u7aef\u70b9\u5f52\u5c5e\u548c\u8fde\u901a\u5f85\u6838"]]:[]),...((n.source_three_rim_family?[n.source_three_rim_family]:(n.source_three_rim_families||[])).flatMap(r=>[["\u56de\u6c34\u4e09\u7aef\u5706\u5019\u9009",r.group_id],["\u540c\u7ec4\u56de\u6c34\u7aef\u70b9",r.rim_node_ids.join(' / ')],["\u8bbe\u5907\u53ca\u76f8\u5207\u4f9b\u6c34\u5706",r.equipment_id+' / '+r.tangent_supply_circle_handle],["\u56fe\u5f62\u72b6\u6001","\u56fe\u5f62\u542b\u4e49\u5f85\u6838\uff1b\u672a\u63a8\u5b9a\u8fde\u901a"]])),...(n.source_declared_connection?.target_node_id?[["\u539f\u56fe\u58f0\u660e\u7f16\u53f7",n.source_declared_connection.label],["\u5bf9\u5e94\u7aef\u70b9",n.source_declared_connection.interface_role==='local'?n.source_declared_connection.target_node_id:n.source_declared_connection.endpoint_node_id],["\u539f\u56fe\u5706\u53e5\u67c4",n.source_declared_connection.target_circle_handle],["\u58f0\u660e\u72b6\u6001","\u539f\u56fe\u6807\u6ce8\u63a5\u81f3\uff1b\u5b9e\u9645\u8def\u5f84\u5f85\u6838"]]:[]),...(n.source_labeled_equipment_pair?[["\u539f\u56fe\u6210\u5bf9\u8bbe\u5907",n.source_labeled_equipment_pair.equipment_id],["\u8bbe\u5907\u652f\u8def\u6807\u6ce8",n.source_labeled_equipment_pair.label],["\u4f9b\u56de\u6c34\u7aef\u70b9",n.source_labeled_equipment_pair.services.supply.endpoint_node_id+" / "+n.source_labeled_equipment_pair.services.return.endpoint_node_id],["\u6807\u6ce8\u6240\u6307\u7ba1\u6bb5",n.source_labeled_equipment_pair.services.supply.annotated_target_edge_id+" / "+n.source_labeled_equipment_pair.services.return.annotated_target_edge_id],["\u6210\u5bf9\u72b6\u6001","\u4e00\u53f0\u8bbe\u5907\u7684\u4f9b\u56de\u6c34\u6807\u6ce8\uff1b\u8fde\u901a\u5f85\u6838"]]:[]),...(n.source_annotation_reference?[["\u539f\u56fe\u63a5\u81f3\u6807\u6ce8",n.source_annotation_reference.source_note],["\u6807\u6ce8\u6240\u6307\u7ba1\u6bb5",n.source_annotation_reference.target_edge_id],["\u5173\u8054\u72b6\u6001","\u539f\u56fe\u6807\u6ce8\u5173\u7cfb\uff1b\u8fde\u901a\u672a\u8bc1\u5b9e"]]:[]),...(n.source_endpoint_annotation?[["\u7aef\u70b9\u539f\u56fe\u6587\u5b57",n.source_endpoint_annotation.text],["\u539f\u6587\u548c\u5f15\u7ebf\u53e5\u67c4",n.source_endpoint_annotation.text_handle+" / "+n.source_endpoint_annotation.leader_handle],["\u6587\u5b57\u542b\u4e49","\u539f\u6587\u5df2\u5bf9\u5e94\uff0c\u8fdc\u7aef\u8fde\u63a5\u672a\u8bc1\u5b9e"]]:[]),...(n.source_ports?[['Native source ports',n.source_ports.length],['Ports with edges',n.source_ports.filter(p=>p.edge_id).length]]:[]),...(n.node_type==='virtual_equipment'?[['Semantic status',n.viewer_non_node_boundary?(n.boundary_evidence?.evidence_basis==='source_similar_inferred'?'\u4f9d\u636e\u4e13\u5bb6\u6837\u4f8b\u7684\u540c\u5f62\u63a8\u65ad\uff1b\u5f85\u9010\u70b9\u590d\u6838\uff0c\u8fdc\u7aef\u672a\u77e5':'\u4e13\u5bb6\u6807\u6ce8\u975e\u8282\u70b9\uff1b\u8fdc\u7aef\u8fde\u63a5\u672a\u77e5'):n.boundary_type==='source_declared_connection_interface'?'\u539f\u56fe\u5df2\u6807\u6ce8\u63a5\u81f3\uff1b\u5b9e\u9645\u8def\u5f84\u5f85\u6838':n.source_concentric_candidate?'\u539f\u56fe\u540c\u5fc3\u53cc\u5706\uff1b\u7269\u7406\u542b\u4e49\u548c\u5355\u4fa7\u6ce2\u6d6a\u65ad\u7ebf\uff1b\u8fdc\u7aef\u53bb\u5411\u5f85\u6838':n.interface_destination?('Known destination: '+n.interface_destination.text+'; remote port identity pending'):n.boundary_type==='source_native_downturn_terminal'?'\u539f\u56fe\u5411\u4e0b\u8f6c\u5f2f\uff1b\u5355\u4fa7\u6ce2\u6d6a\u65ad\u7ebf\uff1b\u8fdc\u7aef\u53bb\u5411\u5f85\u6838':n.boundary_type==='unresolved_source_terminal'?'Algorithm interpretation pending; inspect source comparison':(externalBoundaryLabel(n,data.edges,data.display?.edge_attribute_language==='zh-CN')||cappedInterfaceInterpretation(n,data)||'Unresolved external interface')],...(n.source_concentric_candidate?[['\u539f\u56fe\u5706\u53e5\u67c4',n.source_concentric_candidate.source_circle_handles.join(', ')]]:[]),...(n.source_floor_alignment_candidate?[['\u5e73\u9762\u540c\u4f4d\u5019\u9009',n.source_floor_alignment_candidate.group_id],['\u697c\u5c42\u548c\u8282\u70b9',n.source_floor_alignment_candidate.members.map(x=>x.floor+': '+x.node_id).join('; ')],...(n.source_floor_alignment_candidate.members.some(x=>x.diameter_status)?[['\u5404\u5c42\u76f4\u63a5\u6807\u6ce8\u7ba1\u5f84',n.source_floor_alignment_candidate.members.map(x=>x.floor+': '+(x.direct_diameter_mm!=null?'DN'+x.direct_diameter_mm:'\u672a\u7ed1\u5b9a\u6807\u6ce8')).join('; ')]]:[]),['\u8de8\u5c42\u8fde\u901a','\u672a\u8bc1\u5b9e']]:[]),...(n.source_downturn_evidence?[['\u56fe\u4f8b\u4f9d\u636e',n.source_downturn_evidence.legend_text+' ['+n.source_downturn_evidence.legend_text_handle+']'],['\u539f\u56fe\u5706\u53e5\u67c4',n.source_downturn_evidence.circle_handle]]:[]),[cappedInterfaceKind(n,data)?'\u903b\u8f91\u8fb9\u754c\u7aef\u53e3':'Ports',n.ports.length]]:[])])}${rev?`<div class="review-warning">${esc(rev.reason||'Expected junction degree 3; review source connectivity.')} This is an automatic hint, not a confirmed error.</div>`:''}${adj.map(e=>`<button class="link-row" data-select-edge="${e.edge_id}"><i class="line ${e.system}"></i><b>${e.edge_id}</b><span>${data.systems[e.system].name} \u2197</span></button>`).join('')}`;
  }else header.innerHTML=`<div class="detail-eyebrow"><h2>Path result</h2><span class="tag ${s.system}">${systemName(s.system)}</span></div><div class="detail-title">${s.from} \u2014 ${s.to}</div>${headerProperties([['Edges',ids.size],['CAD path length',s.length.toLocaleString('en',{maximumFractionDigits:1})+' drawing units'],['Direction','Undirected connectivity']])}<p class="section-note">Shortest path by source path length. Drawing units are not certified physical pipe lengths.</p>`;
  if(state.focus&&s&&s.kind!=='node'){
    const n=model.nodes.get(state.focus);
    if(n&&n.node_type!=='physical_junction')header.innerHTML+=`<div class="instance-details"><span class="eyebrow">LOCATED EQUIPMENT</span><p class="record-title">${n.node_id} \xb7 ${floorLabel(n.floor)}</p>${model.adj.get(n.node_id).map(e=>`<button class="link-row" data-select-edge="${e.edge_id}"><i class="line ${e.system}"></i>${e.edge_id}<span>${data.systems[e.system].name} \u2197</span></button>`).join('')}</div>`;
  }
  if(s?.kind==='node'&&model.nodes.get(s.id).source_equipment_overlap){const o=model.nodes.get(s.id).source_equipment_overlap;header.innerHTML+=headerProperties([['\u8bbe\u5907\u56fe\u5143\u5bf9\u7167','\u5b58\u5728\u90bb\u8fd1\u6216\u91cd\u5408\uff0c\u5f52\u5c5e\u5f85\u6838'],['\u5019\u9009\u8bbe\u5907',o.tower_node_id]]);}
  if(s?.kind==='node'&&model.nodes.get(s.id).source_equipment_owner_candidate){const o=model.nodes.get(s.id).source_equipment_owner_candidate;header.innerHTML+=headerProperties([['\u8bbe\u5907\u5f52\u5c5e\u5019\u9009',o.tower_node_id],['\u56de\u6c34\u5bf9\u7167','\u539f\u56fe\u56de\u6c34\u5165\u5854\uff1b\u7ba1\u53e3\u672a\u7ed1\u5b9a']]);}
  if(s?.kind==='node'&&model.nodes.get(s.id).source_tower_terminal_comparison){const q=model.nodes.get(s.id).source_tower_terminal_comparison;header.innerHTML+=headerProperties([['\u6e90\u56fe\u8bbe\u5907\u5019\u9009',q.tower_id],['\u539f\u56fe\u4e8c\u7ef4\u6700\u77ed\u56fe\u793a\u8ddd\u79bb',Number(q.nearest_primitive_distance_2d).toFixed(2)+' \u56fe\u7eb8\u5355\u4f4d'],['\u8ddd\u79bb\u542b\u4e49','\u975e\u5b9e\u6d4b\u7ba1\u957f\u6216\u9ad8\u5dee\uff1b\u7269\u7406\u7aef\u53e3\u5f85\u6838']]);}
  if(s?.kind==='node'&&model.nodes.get(s.id).source_tower_terminal_comparison?.source_centered_circles?.length){const cs=model.nodes.get(s.id).source_tower_terminal_comparison.source_centered_circles;header.innerHTML+=headerProperties([['\u539f\u56fe\u540c\u5fc3\u5706\u53e5\u67c4',cs.map(c=>c.handle).join(' / ')],['\u5706\u5f62\u8bc1\u636e','\u56de\u6c34\u7aef\u70b9\u5b58\u5728\u540c\u5fc3\u539f\u751f\u5706\u5f62\uff1b\u8bbe\u5907\u7aef\u53e3\u548c\u8fde\u63a5\u5173\u7cfb\u4ecd\u672a\u8bc1\u5b9e']]);}
  if(s?.kind==='node'&&model.nodes.get(s.id).source_tower_terminal_comparison?.source_overlapping_circle_line_witnesses?.length){const cs=model.nodes.get(s.id).source_tower_terminal_comparison.source_overlapping_circle_line_witnesses;header.innerHTML+=headerProperties([['\u53e6\u4e00\u539f\u56fe\u5706\u53e5\u67c4',cs.map(c=>c.handle).join(' / ')],['\u56fe\u5f62\u5173\u7cfb','\u5706\u5fc3\u5728\u540c\u5c42\u6e90\u7ebf\u4e0a\uff1b\u672a\u636e\u6b64\u589e\u52a0\u8fde\u63a5']]);}
  if(s?.kind==='node'&&model.nodes.get(s.id).source_enclosed_return_group){const q=model.nodes.get(s.id).source_enclosed_return_group;const ids=[q.entry_edge_id,...q.edge_ids].filter((id,i,a)=>a.indexOf(id)===i&&model.edges.has(id));header.innerHTML+='<div class="instance-details"><span class="eyebrow">\u6e90\u56fe\u8303\u56f4\u5185\u56de\u6c34\u8fb9</span><p>\u4ec5\u6309\u539f\u56fe\u8303\u56f4\u5206\u7ec4\uff1b\u8bbe\u5907\u5f52\u5c5e\u53ca\u7ba1\u53e3\u5f85\u6838\u3002</p>'+ids.map(id=>`<button class="link-row" data-select-edge="${esc(id)}">${esc(id)} \u2197</button>`).join('')+'</div>';}
  if(s?.kind==='node'){const candidates=model.sourcePortCandidateOwners.get(s.id)||[];if(candidates.length)header.innerHTML+='<div class="instance-details"><span class="eyebrow">\u539f\u56fe\u7ba1\u53e3\u5019\u9009\uff08\u5c1a\u672a\u7ed1\u5b9a\uff09</span><p>\u4ec5\u8868\u793a\u5f85\u5bf9\u7167\u7684\u6765\u6e90\u6807\u8bb0\uff0c\u4e0d\u4ee3\u8868\u8bbe\u5907\u7ba1\u53e3\u6216\u6c34\u529b\u8fde\u901a\u5df2\u786e\u8ba4\u3002</p>'+candidates.map(c=>`<button class="link-row" data-select-node="${esc(c.equipment_id)}">${esc(c.equipment_id)} \xb7 ${esc(c.edge_id||'')} \u2197</button>`).join('')+'</div>';}
  if(s?.kind==='node'){const n=model.nodes.get(s.id),candidates=(n.source_port_candidates||[]).filter(c=>c.status==='source_mark_candidate_not_bound'&&model.nodes.has(c.candidate_node_id));if(candidates.length)header.innerHTML+='<div class="instance-details"><span class="eyebrow">\u540c\u4e00\u8bbe\u5907\u7684\u539f\u56fe\u7aef\u70b9\u5019\u9009</span><p>\u5019\u9009\u6807\u8bb0\u5c1a\u672a\u7ed1\u5b9a\u4e3a\u8bbe\u5907\u7ba1\u53e3\uff0c\u4e0d\u8868\u793a\u5185\u90e8\u7ba1\u7ebf\u6216\u6c34\u529b\u8fde\u901a\u5df2\u786e\u8ba4\u3002</p>'+candidates.map(c=>`<button class="link-row" data-select-node="${esc(c.candidate_node_id)}">${esc(c.candidate_node_id)} \xb7 ${esc(c.edge_id||'')} \u2197</button>`).join('')+'</div>';}
  if(s?.kind==='edge'){const e=model.edges.get(s.id),status=edgeContactEvidence(model,e);if(status.start_contact_status||status.end_contact_status)header.innerHTML+=headerProperties([['\u8d77\u70b9\u63a5\u7ba1\u72b6\u6001',status.start_contact_status||'\u65e0\u672c\u8f6e\u6807\u8bb0'],['\u7ec8\u70b9\u63a5\u7ba1\u72b6\u6001',status.end_contact_status||'\u65e0\u672c\u8f6e\u6807\u8bb0']]);}
  if(s?.kind==='node'&&model.nodes.get(s.id).source_glyph_system_conflict){const q=model.nodes.get(s.id).source_glyph_system_conflict;header.innerHTML+=headerProperties([['\u539f\u56fe\u7b26\u53f7\u7cfb\u7edf\u51b2\u7a81','\u5706\u4e0e\u76f8\u63a5\u7ba1\u7ebf\u56fe\u5c42\u4e0d\u540c\uff0c\u5f85\u6838\u67e5'],['\u539f\u56fe\u5706',q.circle_handle+' \xb7 '+q.circle_source_layer],['\u539f\u56fe\u7ba1\u7ebf',q.pipe_handle+' \xb7 '+q.pipe_source_layer],['\u5904\u7406\u72b6\u6001','\u4fdd\u7559\u539f\u7ba1\u7ebf\u7cfb\u7edf\uff1b\u672a\u786e\u8ba4\u8bbe\u5907\u3001\u8fdc\u7aef\u6216\u8de8\u7cfb\u7edf\u8fde\u63a5']]);}
  if(s?.kind==='node'&&(model.adj.get(s.id)||[]).some(e=>e.source_expert_circle_link?.similar_location_inferred===true&&e.source_expert_circle_link.circle_handle===model.nodes.get(s.id)?.expert_circle_evidence?.circle_handle))header.innerHTML+='<p class="review-warning">\u76f8\u4f3c\u5706\u63a5\u70b9\u7684\u652f\u8def\u8fde\u63a5\u5f85\u6838\u67e5\uff1b\u7f51\u7edc\u8ffd\u8e2a\u4ec5\u5728\u539f\u751f\u4e3b\u7ba1\u8bc1\u636e\u53ef\u552f\u4e00\u8bc6\u522b\u65f6\u901a\u8fc7\u4e3b\u7ba1\uff0c\u4e0d\u8de8\u8d8a\u5f85\u6838\u652f\u8def\u3002</p>';
  if(s?.kind==='node'&&model.nodes.get(s.id).system_review_required)header.innerHTML+='<p class="review-warning">Source pipe geometry meets here. Hydraulic system classification is pending; same-system tracing does not cross into another class.</p>';
  if(s?.kind==='node'&&model.nodes.get(s.id).source_tangent_circle_candidate){const c=model.nodes.get(s.id).source_tangent_circle_candidate;header.innerHTML+=headerProperties([['\u539f\u56fe\u5706\u73af',c.source_circle_handle],['\u76f8\u5207\u5706\u73af',c.paired_circle_handle],['\u5bf9\u5e94\u7aef\u70b9',c.paired_node_id],['\u5173\u7cfb\u72b6\u6001','\u4ec5\u6e90\u56fe\u5f62\u5206\u7ec4\uff1b\u4e0d\u8868\u793a\u4f9b\u56de\u6c34\u8fde\u901a']]);}
  if(s?.kind==='node'&&['source_contact_reconstructed_pending_comparison','source_main_continuation_branch_pending'].includes(model.nodes.get(s.id).resolution_state))header.innerHTML+='<p class="review-warning">\u652f\u8def\u63a5\u70b9\u4ecd\u5f85\u539f\u56fe\u5bf9\u7167\uff1a\u7f51\u7edc\u8ffd\u8e2a\u4e0d\u4f1a\u8de8\u8d8a\u672a\u786e\u8ba4\u652f\u8def\uff1b\u539f\u4e3b\u7ba1\u8fde\u7eed\u6bb5\u4ec5\u5728\u6e90\u7ebf\u53ef\u552f\u4e00\u8bc6\u522b\u65f6\u7ee7\u7eed\u8ffd\u8e2a\u3002</p>';
  if(s?.kind==='node'){const n=model.nodes.get(s.id);if(n.node_type==='equipment'){const refs=n.profile_candidates||n.parameter_candidates||n.parameter_profile_candidates||[];header.innerHTML+=headerProperties(hydraulicProperties(n));header.innerHTML+=`<div class="instance-details"><span class="eyebrow">PARAMETER REFERENCES</span><p>${refs.length?refs.map(esc).join(', '):'No unique schedule match'}</p><p>Reference candidates only. Installed attributes and unproven ports remain unresolved.</p></div>`;}}
  $('#tab-connections').classList.toggle('active',state.tab==='connections');$('#tab-components').classList.toggle('active',state.tab==='components');$('#tab-instances').classList.toggle('active',state.tab==='instances');
  $$('.inspector-tabs button').forEach(b=>b.setAttribute('aria-selected',b.classList.contains('active')));
  const filter=state.filter.toLowerCase();let html='';
  if(!s)html='<div class="empty-detail"><span class="empty-icon">\u23af \u25cb \u23af \u25c7</span><strong>No pipe selected</strong><span>Click a pipe to display connected equipment and its source component inventory.</span></div>';
  else if(state.tab==='connections'){
    html=`<p class="section-note">${equip.filter(n=>n.node_type==='equipment').length} equipment \xb7 ${equip.filter(n=>n.node_type==='virtual_equipment').length} interfaces${state.floor!=='all'?' \xb7 Selection may extend outside this floor':''}</p>`;
    const rows=equip.filter(n=>`${n.node_id} ${nodeKind(n)}`.toLowerCase().includes(filter));
    html+=rows.map(n=>`<button class="record ${state.focus===n.node_id?'selected':''}" data-locate-node="${n.node_id}">${n.node_type==='equipment'?symbol(n.symbol_key||'EQUIPMENT'):'<span class="type-badge">\u25c7</span>'}<span><span class="record-title">${n.node_id}</span><span class="record-subtitle">${nodeKind(n)} \xb7 ${floorLabel(n.floor)}${n.node_type==='virtual_equipment'?' \xb7 Unresolved':''}</span></span><span class="record-end">\u2316</span></button>`).join('');
    if(s.kind==='node'&&model.nodes.get(s.id).node_type==='virtual_equipment'){
      html=(cappedInterfaceKind(model.nodes.get(s.id),data)?'<p class="section-note">\u9884\u7559\u5c01\u5835\u63a5\u53e3\uff1b\u672c\u56fe\u903b\u8f91\u8fb9\u754c\u7aef\u53e3\uff0c\u4e0d\u4ee3\u8868\u5df2\u8bc1\u5b9e\u7684\u8bbe\u5907\u5b9e\u4f53\u7aef\u53e3\u3002</p>':model.nodes.get(s.id).viewer_non_node_boundary?'<p class="section-note">\u67e5\u770b\u5668\u8fb9\u754c\u5360\u4f4d\uff1b\u8fde\u63a5\u7684\u662f\u672c\u56fe\u7ba1\u6bb5\uff0c\u975e\u5df2\u8bc1\u5b9e\u7684\u7269\u7406\u7aef\u53e3\u3002</p>':model.nodes.get(s.id).boundary_type==='unresolved_source_terminal'?'<p class="section-note">\u56fe\u7ed3\u6784\u8fb9\u754c\u5360\u4f4d\uff1b\u8bbe\u5907\u7aef\u53e3\u53ca\u8fdc\u7aef\u8fde\u63a5\u5c1a\u672a\u8bc1\u5b9e\u3002</p>':'<p class="section-note">Explicit source interface ports. Each port has one adjacent edge.</p>')+model.nodes.get(s.id).ports.map(p=>{const edge=(model.adj.get(s.id)||[]).find(e=>e.start_port_id===p.port_id||e.end_port_id===p.port_id);return `<div class="port-record"><strong>${p.port_id}</strong>${systemName(p.system)} \xb7 Marker ${p.source_marker_handle}<br>${edge?`<button class="link-row" data-port-edge="${edge.edge_id}">${edge.edge_id} \xb7 ${edge.start_node_id===s.id?edge.end_node_id:edge.start_node_id} \u2197</button>`:'Unresolved binding'}</div>`;}).join('')+html;
    }
    if(!rows.length)html+='<div class="empty-detail">'+(equip.length?'No matching equipment.':'No equipment endpoints on these edges. Expand to a same-system network or select an equipment branch.')+'</div>';
  }else if(state.tab==='components'){
    html=`<p class="section-note">${count} source instances \xb7 ${groups.length} types. Click a type to inspect individual assignments.</p>`;
    const rows=groups.filter(g=>g.label.toLowerCase().includes(filter));
    html+=rows.map(g=>`<button class="record" data-type="${g.type}">${symbol(g.type)}<span><span class="record-title">${g.label}</span><span class="record-subtitle">${g.type==='AAV'?'Source CAD table symbol':'Source CAD geometry'}</span></span><span class="record-end">\xd7 ${g.instances.length}</span></button>`).join('');
    if(!rows.length)html+='<div class="empty-detail">No components in this selection'+(filter?' match the filter.':'.')+'</div>';
  }else{
    let instances=groups.flatMap(g=>g.instances);
    if(state.type)instances=instances.filter(d=>d.type===state.type);
    instances=instances.filter(d=>`${d.name} ${d.id} ${d.label} ${d.edge_id} ${d.source_top_handle}`.toLowerCase().includes(filter));
    html=`<p class="section-note">${instances.length} instances. Distances are in source drawing units.${state.type?' <button class="reset-filter" id="reset-type">All types \xd7</button>':''}</p>`;
    if(state.instance){const d=data.instances.find(x=>x.id===state.instance);if(d)html+=`<div class="instance-details"><strong>${esc(d.name)}</strong>${headerProperties([['Instance ID',d.id],['Edge',d.edge_id],['Source kind',englishMode(d.source_kind)],['Source symbol',d.label],...(d.source_head_status?[['Recognition',d.source_head_status==='complete_tagged_head'?'Sensor and tagged head complete':'Sensor body assigned; head association pending']]:[]),...(d.source_instrument_tags?.length?[['Source tags',d.source_instrument_tags.join(', ')]]:[]),...(d.source_attributes?.length?[['Original attributes',d.source_attributes.map(a=>`${a.tag}=${a.text}`).join('\uff1b')],['Attribute scope','Original source values; no inferred model or engineering quantity']]:[]),['Source handle',d.source_top_handle||'Not recorded'],['Owner',d.owner_equipment||'Not bound'],['Assignment distance',d.edge_distance.toFixed(3)],['Status',d.assignment_status]])}</div>`;}
    html+=instances.map(d=>`<button class="record ${state.instance===d.id?'selected':''}" data-locate-instance="${d.id}">${symbol(d.type)}<span><span class="record-title">${esc(d.name)}</span><span class="record-subtitle">${d.id} \xb7 ${d.edge_id} \xb7 ${esc(englishMode(d.source_kind))}</span></span><span class="record-end">\u2316</span></button>`).join('');
    if(!instances.length)html+='<div class="empty-detail">No matching instances.</div>';
  }
  $('#detail-content').innerHTML=html;
  document.dispatchEvent(new Event('cad-details-changed'));
  $('#inspector-search').value=state.filter;
  if(s?.kind==='edge')$('#topology-caption').textContent=`${model.edges.get(s.id).edge_id} \xb7 ${systemName(model.edges.get(s.id).system).toUpperCase()}`;
  else $('#topology-caption').textContent='TOPOLOGY \xb7 ORIGINAL CAD POSITIONS';
}
function render(){renderGraph();renderDetails();}
function updateControls(){
  $$('#floor-buttons button').forEach(b=>b.classList.toggle('active',b.dataset.floor===state.floor));
  for(const s of Object.keys(data.systems))$('#system-'+s).checked=state.systems.has(s);
  $('#scope-segment').classList.toggle('active',state.scope==='segment');$('#scope-network').classList.toggle('active',state.scope==='network');
  $('#view-topology').classList.toggle('active',!state.compare);$('#view-cad').classList.toggle('active',state.compare);
  $('#compare-options').hidden=!state.compare;$('#cad-pane').hidden=!state.compare;$('#canvas-panes').classList.toggle('compare',state.compare);
}
function setCompare(value){state.compare=value;updateControls();requestAnimationFrame(()=>{state.view=aspectFit(state.view,$('#graph-svg'));if(state.sync)state.cadView=[...state.view];renderGraph();});}
function locateInstance(id){
  const d=data.instances.find(x=>x.id===id);if(!d)return;
  if(!(d.related_edge_ids||[d.edge_id]).some(id=>selectedIds().has(id)))selectEdge(d.edge_id);
  state.tab='instances';state.instance=id;state.type=d.type;state.compare=true;state.filter='';
  updateControls();
  requestAnimationFrame(()=>{
    // Fit both assignment and original symbol positions (display legs may be folded).
    state.view=aspectFit(nativeObjectFocusBounds(d)||bounds([[d.px,d.py],[d.sourceX,d.sourceY]],8),$('#graph-svg'));state.cadView=[...state.view];render();
  });
}
function zoom(factor,cx,cy,pane='graph'){
  const view=pane==='cad'&&!state.sync?(state.cadView||state.view):state.view;
  if(view[2]*factor<2||view[2]*factor>globalBounds[2]*10)return;
  cx??=view[0]+view[2]/2;cy??=view[1]+view[3]/2;
  const nv=[cx+(view[0]-cx)*factor,cy+(view[1]-cy)*factor,view[2]*factor,view[3]*factor];
  if(pane==='cad'&&!state.sync){state.cadView=nv;applyView();}else{state.view=nv;renderGraph();}
}
function toSvgPoint(svg,x,y){const p=svg.createSVGPoint();p.x=x;p.y=y;return p.matrixTransform(svg.getScreenCTM().inverse());}
function bindCanvas(svg,pane){
  let drag=null, moved=false;
  svg.addEventListener('pointerdown',e=>{if(e.button!==0)return;drag={x:e.clientX,y:e.clientY,view:[...(pane==='cad'&&!state.sync?state.cadView:state.view)]};moved=false;svg.setPointerCapture(e.pointerId);});
  svg.addEventListener('pointermove',e=>{
    if(drag){const r=svg.getBoundingClientRect(),dx=(e.clientX-drag.x)*drag.view[2]/r.width,dy=(e.clientY-drag.y)*drag.view[3]/r.height;if(Math.hypot(e.clientX-drag.x,e.clientY-drag.y)>3)moved=true;const nv=[drag.view[0]-dx,drag.view[1]-dy,drag.view[2],drag.view[3]];if(pane==='cad'&&!state.sync)state.cadView=nv;else state.view=nv;applyView();return;}
    if(pane!=='graph')return;
    const target=e.target.closest('[data-node],[data-edge],[data-instance]');
    if(!target){$('#graph-tooltip').hidden=true;return;}
    let text='';if(target.dataset.node){const n=model.nodes.get(target.dataset.node);text=`${n.node_id} \xb7 ${nodeKind(n)}\n${floorLabel(n.floor)} \xb7 ${model.adj.get(n.node_id).length} linked edges`;}
    else if(target.dataset.edge){const edge=model.edges.get(target.dataset.edge);text=`${edge.edge_id} \xb7 ${systemName(edge.system)}\n${edge.start_node_id} \u2014 ${edge.end_node_id}\n${(model.instancesByEdge.get(edge.edge_id)||[]).length} components`;}
    else{const d=data.instances.find(x=>x.id===target.dataset.instance);text=`${d.label} \xb7 ${d.edge_id}\n${d.name}`;}
    const tip=$('#graph-tooltip'),r=svg.getBoundingClientRect();tip.textContent=text;tip.hidden=false;tip.style.left=Math.min(e.clientX-r.left+14,r.width-240)+'px';tip.style.top=Math.max(40,Math.min(e.clientY-r.top+12,r.height-85))+'px';
  });
  svg.addEventListener('pointerup',e=>{if(!drag)return;drag=null;if(moved){renderGraph();$('#graph-tooltip').hidden=true;return;}const target=document.elementFromPoint(e.clientX,e.clientY)?.closest('[data-node],[data-edge],[data-instance]');if(target?.dataset.instance)locateInstance(target.dataset.instance);else if(target?.dataset.node)selectNode(target.dataset.node);else if(target?.dataset.edge)selectEdge(target.dataset.edge);});
  svg.addEventListener('pointercancel',()=>drag=null);
  svg.addEventListener('pointerleave',()=>$('#graph-tooltip').hidden=true);
  svg.addEventListener('wheel',e=>{e.preventDefault();const p=toSvgPoint(svg,e.clientX,e.clientY);zoom(Math.exp(Math.max(-.4,Math.min(.4,e.deltaY*.0015))),p.x,p.y,pane);},{passive:false});
  svg.addEventListener('dblclick',e=>{e.preventDefault();const p=toSvgPoint(svg,e.clientX,e.clientY);zoom(.65,p.x,p.y,pane);});
  svg.addEventListener('keydown',e=>{const n=e.target.closest('[data-node]');if(n&&['Enter',' '].includes(e.key)){e.preventDefault();selectNode(n.dataset.node);}if(e.key==='+'||e.key==='=')zoom(.8);if(e.key==='-')zoom(1.25);if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();const v=state.view;state.view=[v[0]+(e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0)*v[2]*.1,v[1]+(e.key==='ArrowDown'?1:e.key==='ArrowUp'?-1:0)*v[3]*.1,v[2],v[3]];renderGraph();}});
}
function search(query){
  const q=query.trim().toLowerCase(),box=$('#search-results');
  if(!q){box.hidden=true;lastSearch=[];return;}
  const results=[];
  for(const n of data.nodes)if(`${n.node_id} ${n.label} ${externalBoundaryLabel(n,data.edges,data.display?.edge_attribute_language==='zh-CN')||''}`.toLowerCase().includes(q))results.push({kind:'node',id:n.node_id,label:n.node_id,sub:`${nodeKind(n)} \xb7 ${floorLabel(n.floor)}`});
  for(const e of data.edges)if(`${e.edge_id} ${e.start_node_id} ${e.end_node_id}`.toLowerCase().includes(q))results.push({kind:'edge',id:e.edge_id,label:e.edge_id,sub:systemName(e.system)});
  for(const d of data.instances)if(`${d.name} ${d.id} ${d.label}`.toLowerCase().includes(q))results.push({kind:'instance',id:d.id,label:d.name,sub:`${d.id} \xb7 ${d.edge_id}`});
  lastSearch=results.slice(0,16);
  box.innerHTML=`<p class="section-note">${results.length} matches${results.length>16?' \xb7 first 16 shown':''}</p>`+lastSearch.map((r,i)=>`<button data-search-result="${i}"><span>${esc(r.label)}</span><small>${esc(r.sub)}</small></button>`).join('');box.hidden=false;
}
function chooseSearch(index){const r=lastSearch[index];if(!r)return;if(r.kind==='edge')selectEdge(r.id,{focus:true});else if(r.kind==='node')selectNode(r.id,{focus:true});else locateInstance(r.id);$('#search-results').hidden=true;$('#search').value='';}
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function exportSvg(){
  const t=$('#graph-svg'),view=state.view,ratio=t.clientHeight/t.clientWidth,w=1920,h=Math.round(w*ratio),selected=selectedIds();
  const attrs=`xmlns="${NS}" width="${w}" height="${h}" viewBox="${view.join(' ')}"`;
  // Inline definitions make exported geometry independent of the app document.
  let inner=t.innerHTML.replaceAll('stroke="transparent"','stroke="none"');
  const label=`${esc(data.project.id)} | ${state.compare?'Topology + actual CAD':'Topology'} | ${selected.size} selected edges`;
  if(state.compare){const cad=state.sync?state.view:state.cadView;return {w:w*2,h,svg:`<svg xmlns="${NS}" width="${w*2}" height="${h}" viewBox="0 0 ${w*2} ${h}"><rect width="100%" height="100%" fill="white"/>${defsMarkup()}<svg width="${w}" height="${h}" viewBox="${view.join(' ')}">${inner}</svg><svg x="${w}" width="${w}" height="${h}" viewBox="${cad.join(' ')}">${$('#cad-svg').innerHTML}</svg><text x="16" y="24" font-size="14" fill="#233955">${label}</text></svg>`};}
  return {w,h,svg:`<svg ${attrs}><rect x="${view[0]}" y="${view[1]}" width="${view[2]}" height="${view[3]}" fill="white"/>${defsMarkup()}${inner}</svg>`};
}
async function doExport(kind){
  $('#export-menu').open=false;const ids=selectedIds();
  if(['equipment','edges','instances'].includes(kind)&&!ids.size){notify('Select a pipe, node or path before exporting records.');return;}
  if(kind==='equipment'){const rows=connectedEquipment(model,ids).map(n=>({node_id:n.node_id,type:nodeKind(n),floor:n.floor,source_x:n.x,source_y:n.y}));download(new Blob([makeCsv(rows,['node_id','type','floor','source_x','source_y'])],{type:'text/csv;charset=utf-8'}),`${data.project.slug}-connected-equipment.csv`);}
  if(kind==='edges'){const rows=[...ids].map(id=>{const e=model.edges.get(id);return {...e,...edgeContactEvidence(model,e),...crossViewAttributeCsvValues(e,data.attribute_value_context),...ownershipLengthScopeCsvValues(e,data),...reviewCsvValues(e,crossViewAttributeCsvValues(e,data.attribute_value_context)),source_dimensioned_segments_json:JSON.stringify(e.source_dimensioned_segments||[])};});download(new Blob([makeCsv(rows,['edge_id','start_node_id','end_node_id','start_contact_status','end_contact_status','system','floor_start','floor_end','path_length','path_length_complete','path_length_scope','connection_mode',...edgeAttributeCsvFields,...reviewCsvFields,...reviewAttributeCsvFields])],{type:'text/csv;charset=utf-8'}),`${data.project.slug}-selected-edges.csv`);}
  if(kind==='instances'){const rows=inventory(model,ids).flatMap(g=>g.instances);download(new Blob([makeCsv(rows,['id','name','label','edge_id','source_kind','source_block_name','source_top_handle','owner_equipment','x','y','assignment_x','assignment_y','edge_distance','assignment_status','source_attributes'])],{type:'text/csv;charset=utf-8'}),`${data.project.slug}-component-instances.csv`);}
  if(kind==='svg'||kind==='png'){
    try{const {svg,w,h}=exportSvg();if(kind==='svg')download(new Blob([svg],{type:'image/svg+xml'}),`${data.project.slug}-current-view.svg`);
      else{const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'})),img=new Image();await new Promise((res,rej)=>{img.onload=res;img.onerror=rej;img.src=url;});const c=document.createElement('canvas');c.width=w;c.height=h;const ctx=c.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,w,h);ctx.drawImage(img,0,0);const blob=await new Promise(res=>c.toBlob(res,'image/png'));if(!blob)throw Error('Image encoding failed');download(blob,`${data.project.slug}-current-view.png`);URL.revokeObjectURL(url);}
    }catch(error){notify('Export failed. Try SVG export or reduce the viewport.');console.error(error);return;}
  }
  notify('Export ready. Saved using your browser download settings.');
}
function events(){
  $('#floor-buttons').addEventListener('click',e=>{const b=e.target.closest('[data-floor]');if(b){state.floor=b.dataset.floor;updateControls();fitView();renderDetails();}});
  for(const s of Object.keys(data.systems))$('#system-'+s).onchange=e=>{if(e.target.checked)state.systems.add(s);else state.systems.delete(s);render();};
  for(const key of ['equipment','tee','virtual','components','labels'])$('#layer-'+key).onchange=e=>{state.layers[key]=e.target.checked;renderGraph();};
  $('#view-topology').onclick=()=>setCompare(false);$('#view-cad').onclick=()=>setCompare(true);
  for(const scope of ['segment','network'])$('#scope-'+scope).onclick=()=>{state.scope=scope;if(state.selection?.kind==='node'){notify('Select a pipe to trace a same-system network.');}updateControls();render();};
  $('#fit').onclick=()=>fitView();$('#focus-selection').onclick=()=>fitView(!!state.selection);
  $('#clear').onclick=()=>{state.selection=null;state.focus=null;state.instance=null;state.type=null;state.filter='';render();};
  $('#zoom-in').onclick=()=>zoom(.75);$('#zoom-out').onclick=()=>zoom(1.3333);
  $('#review-toggle').onclick=()=>$('#review-list').hidden=!$('#review-list').hidden;
  $('#review-list').onclick=e=>{const b=e.target.closest('[data-review],[data-review-instance],[data-review-edge]');if(b?.dataset.reviewInstance){locateInstance(b.dataset.reviewInstance);}else if(b?.dataset.reviewEdge){selectEdge(b.dataset.reviewEdge);setCompare(true);requestAnimationFrame(()=>fitView(true));}else if(b){selectNode(b.dataset.review);setCompare(true);requestAnimationFrame(()=>fitView(true));}};
  $('#detail-header').onclick=e=>{const b=e.target.closest('[data-select-edge],[data-select-node]');if(b?.dataset.selectEdge)selectEdge(b.dataset.selectEdge,{focus:true});else if(b?.dataset.selectNode)selectNode(b.dataset.selectNode,{focus:true});};
  $('#detail-content').onclick=e=>{const b=e.target.closest('[data-locate-node],[data-type],[data-locate-instance],[data-port-edge],#reset-type');if(!b)return;if(b.dataset.portEdge)selectEdge(b.dataset.portEdge,{focus:true});else if(b.dataset.locateNode)focusNode(b.dataset.locateNode);else if(b.dataset.type){state.type=b.dataset.type;state.tab='instances';renderDetails();}else if(b.dataset.locateInstance)locateInstance(b.dataset.locateInstance);else{state.type=null;renderDetails();}};
  for(const tab of ['connections','components','instances'])$('#tab-'+tab).onclick=()=>{state.tab=tab;state.filter='';renderDetails();};
  $('#inspector-search').oninput=e=>{state.filter=e.target.value;renderDetails();};
  $('#locate-cad').onclick=()=>{if(!state.selection){notify('Select a pipe or equipment first.');return;}setCompare(true);requestAnimationFrame(()=>{const ids=selectedIds(),pts=[...ids].flatMap(id=>{const e=model.edges.get(id);return [...e.sourcePaths,...(e.deviceSourcePaths||[])].flat()});if(!pts.length)return;state.view=aspectFit(bounds(pts,8),$('#graph-svg'));state.cadView=[...state.view];renderGraph();});};
  $('#show-instances').onclick=()=>{state.tab='instances';state.type=null;state.filter='';renderDetails();};
  $('#path-toggle').onclick=()=>$('#path-panel').hidden=!$('#path-panel').hidden;
  $('#find-path').onclick=()=>{const from=$('#path-from').value.trim(),to=$('#path-to').value.trim(),system=$('#path-system').value,result=shortestPath(model,from,to,system);if(result.error){$('#path-result').textContent=result.error;notify(result.error);return;}state.selection={kind:'path',ids:result.edges,from,to,system,length:result.length};state.focus=from;state.type=null;state.filter='';state.instance=null;state.systems.add(system);state.floor='all';updateControls();$('#path-result').textContent=`${result.edges.length} edges \xb7 ${result.length.toFixed(1)} drawing units (schematic only; not physical length) \xb7 Undirected`;render();if(result.edges.length)fitView(true);else focusNode(from);};
  $('#sync-views').onchange=e=>{state.sync=e.target.checked;if(state.sync)state.cadView=[...state.view];applyView();};
  $('#source-paths').onchange=e=>{state.showSource=e.target.checked;renderCad();applyView();};
  $('#search').oninput=e=>search(e.target.value);$('#search').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();chooseSearch(0);}if(e.key==='Escape')$('#search-results').hidden=true;};
  $('#search-results').onclick=e=>{const b=e.target.closest('[data-search-result]');if(b)chooseSearch(Number(b.dataset.searchResult));};
  document.addEventListener('click',e=>{if(!e.target.closest('.search-wrap'))$('#search-results').hidden=true;});
  document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName)){e.preventDefault();$('#search').focus();}if(e.key==='Escape'&&e.target!==$('#search')){$('#search-results').hidden=true;if(!$('#info-dialog').open)$('#clear').click();}});
  $$('[data-export]').forEach(b=>b.onclick=()=>doExport(b.dataset.export));
  $('#source-info').onclick=()=>$('#info-dialog').showModal();$('#close-info').onclick=()=>$('#info-dialog').close();
  bindCanvas($('#graph-svg'),'graph');bindCanvas($('#cad-svg'),'cad');
  $('#minimap').onclick=e=>{const p=toSvgPoint($('#minimap'),e.clientX,e.clientY);state.view=[p.x-state.view[2]/2,p.y-state.view[3]/2,state.view[2],state.view[3]];renderGraph();};
  let resize;new ResizeObserver(()=>{clearTimeout(resize);resize=setTimeout(()=>{if(state.view){state.view=aspectFit(state.view,$('#graph-svg'));renderGraph();}},120);}).observe($('#graph-svg'));
}
async function init(){
  try{
    const response=await fetch('data/graph.json');if(!response.ok)throw Error('Graph dataset could not be loaded');const rawGraph=await response.text();data=JSON.parse(rawGraph);
    const attributeManifest=await(await fetch('data/manifest.json')).json();
    if(attributeManifest.attributeValueContext){
      const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(rawGraph)))].map(b=>b.toString(16).padStart(2,'0')).join('');
      if(!componentInventoryGraphContext(attributeManifest.attributeValueContext,actual,data.edges)&&!await fragmentOverlayGraphContext(attributeManifest,actual,data))throw Error('Attribute source context belongs to another rendered graph');
      data.attribute_value_context=attributeManifest.attributeValueContext;
    }
    model=createModel(data);
    document.title=`${data.project.id} \xb7 ${data.project.title}`;
    $('#brand-title').textContent=data.project.title;
    $('#brand-subtitle').textContent=`${data.project.id} / ${data.project.description}`;
    $('#project-eyebrow').textContent=`${data.project.id} \xb7 ${data.project.description}`;
    $('#footer-project').textContent=data.project.id+' dataset';
    $('#floor-buttons').innerHTML=`<button data-floor="all" class="active"><span>\u25a6 &nbsp; All Floors</span><span>${data.nodes.filter(n=>n.node_type==='equipment').length}</span></button>`+data.floors.map(f=>`<button data-floor="${esc(f.id)}"><span>${esc(f.label)}</span><span>${f.equipmentCount}</span></button>`).join('');
    $('#review-toggle b').textContent=data.review.length+(data.componentReview||[]).length;
    state.systems=new Set(Object.keys(data.systems));
    $('#system-controls').innerHTML=Object.entries(data.systems).map(([key,c])=>`<label class="check"><input id="system-${key}" type="checkbox" checked><i class="line ${key}" style="border-color:${c.color};border-top-style:${c.dash?'dashed':'solid'}"></i><span id="system-${key}-label">${esc(c.code)} \xb7 ${esc(c.name)}</span></label>`).join('');
    $('#system-legend').innerHTML=Object.entries(data.systems).map(([key,c])=>`<span><i class="line ${key}" style="border-color:${c.color};border-top-style:${c.dash?'dashed':'solid'}"></i> <span id="legend-${key}-label">${esc(c.code)}</span></span>`).join('')+'<span class="muted">\u25cb T &nbsp; \u25c7 Interface</span>';
    $('#path-system').innerHTML=Object.entries(data.systems).map(([key,c])=>`<option value="${key}">${esc(c.code)} \xb7 ${esc(c.name)}</option>`).join('');
    for(const [key,c]of Object.entries(data.systems)){COLOR[key]=c.color;document.documentElement.style.setProperty('--'+key,c.color);document.documentElement.style.setProperty('--'+key+'-border-style',c.dash?'dashed':'solid');}


    $('#symbol-defs').innerHTML=defsMarkup().replace(/^<defs>|<\/defs>$/g,'');
    $('#legend-symbols').innerHTML=data.types.map(t=>`<div class="symbol-entry">${symbol(t.code)}<span>${esc(t.label)}</span></div>`).join('')+(data.equipmentTypes?.length?data.equipmentTypes.map(t=>`<div class="symbol-entry">${symbol(t.code)}<span>${esc(t.label)}</span></div>`).join(''):`<div class="symbol-entry">${symbol('EQUIPMENT')}<span>${esc(data.project.equipmentLabel)}</span></div>`);
    $('#review-list').innerHTML=data.review.map(r=>`<button class="review-node" data-review="${r.id}">${r.id}<span>${floorLabel(r.floor)} \xb7 ${esc(r.reason||('degree '+r.degree))}</span></button>`).join('');
    $('#review-list').innerHTML+=(data.componentReview||[]).map(r=>`<button class="review-node" data-review-instance="${r.id}">${esc(r.name)}<span>${esc(r.reason)}</span></button>`).join('');
    $('#node-options').innerHTML=data.nodes.map(n=>`<option value="${n.node_id}">${nodeKind(n)} \xb7 ${floorLabel(n.floor)}</option>`).join('');
    if(data.metadata?.hil_ready===false){
      const items=sourceComparisonItems(data);
      $('#review-toggle b').textContent=sourceComparisonBadge(items);
      $('#review-toggle').firstElementChild.textContent='Source comparison';
      const priorHints=$('#review-list').innerHTML;
      const warning='<div class="review-node"><b>\u6e90\u56fe\u5bf9\u7167\u5c1a\u672a\u5b8c\u6210</b><span>\u5df2\u52a0\u8f7d\u9879\u6570\u4e0d\u4ee3\u8868\u5168\u90e8\u95ee\u9898\u6570\uff1b'+esc(data.metadata?.hil_block_reason||'\u9700\u8981\u8865\u5145\u5bf9\u7167\u8bc1\u636e')+'</span></div>';
      $('#review-list').innerHTML=warning+items.map(f=>f.kind==='family'?`<a class="review-node" style="display:block;padding:9px 4px;overflow-wrap:anywhere;text-decoration:none;border-bottom:1px solid #ddd" href="data/source-comparison.json" target="_blank" rel="noopener"><b>${esc(f.id)}</b><span style="display:block;line-height:1.5;font-size:11px;color:#63718a">${esc(f.status)} \xb7 ${esc(f.description)}</span></a>`:f.kind==='plan_line_group'?`<details class="review-node"><summary>${esc(f.id)} <span>\u540c\u7c7b\u6e90\u7ebf ${f.count} \u5904 \u00b7 \u5f85\u5bf9\u7167</span></summary>${f.members.map(m=>m.node?`<button class="review-node" data-review="${esc(m.node)}">${esc(m.handle)} <span>${esc(m.node)}</span></button>`:`<div>${esc(m.handle)} \u00b7 \u5f85\u5bf9\u7167</div>`).join('')}</details>`:f.kind==='named_leader'?`<button class="review-node" data-review="${esc(f.node)}">${esc(f.node)} <span>${esc(f.label)} \u00b7 \u5f15\u7ebf ${esc(f.leader)} \u00b7 \u539f\u6587 ${esc(f.text)} \u00b7 \u5f85\u5bf9\u7167</span></button>`:f.edge?`<button class="review-node" data-review-edge="${esc(f.edge)}">${f.kind==='gap_joint'?'\u91d1\u5c5e\u8f6f\u63a5\u5019\u9009':f.kind==='inline_conflict'?'\u8f6f\u63a5\u4f9b\u56de\u6c34\u51b2\u7a81':'\u5706\u73af\u8de8\u7ebf\u51b2\u7a81'} ${esc(f.id)}<span>${esc(f.edge)} \xb7 ${esc(f.device||'\u5f85\u539f\u56fe\u5bf9\u7167')}</span></button>`:`<div class="review-node">${esc(f.id)} <span>\u5f85\u539f\u56fe\u5bf9\u7167</span></div>`).join('')+priorHints;
    }
    $('#info-content').innerHTML=`<div class="info-section"><h3>Source dataset</h3><p>${data.nodes.filter(n=>!n.viewer_non_node_boundary).length} nodes \xb7 ${data.nodes.filter(n=>n.viewer_non_node_boundary).length} viewer boundary proxies \xb7 ${data.edges.length} edges \xb7 ${data.instances.length} component instances.<br>${data.nodes.filter(n=>n.node_type==="equipment").length} equipment, ${data.nodes.filter(n=>n.node_type==="physical_junction").length} T-junctions, ${data.nodes.filter(n=>n.node_type==="virtual_equipment"&&!n.viewer_non_node_boundary).length} interfaces; port records include viewer boundary proxies.</p></div><div class="info-section"><h3>Provenance</h3><p>${esc(data.provenance.dxf)}<br>SHA-256: <code>${data.provenance.sha256}</code></p></div><div class="info-section"><h3>Display & symbols</h3><p>CAD symbols are exported directly from the source DXF blocks, including filled shapes and curved outlines. Colors are adjusted for legibility. Original CAD positions and source paths are retained. ${data.display?.building_label_language==='source'?'Original building labels are displayed; other source annotations follow their own extraction scope.':'Building labels use English aliases; originals are retained in audit data.'} Graph dots and virtual diamonds are overlays. Symbol geometry is configured per project from the supplied main drawing or legend; no source-specific block name is assumed.</p></div><div class="info-section"><h3>Interpretation</h3><p>Same-system tracing and path search stop at equipment and virtual interfaces. Path length uses native drawing units; it is not a certified installed pipe length. The ${data.review.length} automatic topology hints are pending review, not confirmed faults. This is a local connectivity viewer with no runtime telemetry, hydraulic simulation, or inferred flow directions.</p></div>`;
    if(data.metadata?.extraction_status==='partial'){
      const banner=document.createElement('div');banner.id='extraction-warning';banner.style.cssText='position:fixed;bottom:0;left:0;right:0;z-index:10000;background:#fff0cd;color:#754900;padding:9px 18px;font:13px Arial;border-top:2px solid #d69214';
      const terminalCount=data.nodes.filter(n=>n.boundary_type==='unresolved_source_terminal').length;
      banner.textContent=data.metadata?.hil_ready===false?'SOURCE COMPARISON \xb7 Repeated algorithm families require resolution before expert HIL.':terminalCount?`PENDING REVIEW \xb7 ${terminalCount} source terminals remain unconfirmed. Hydraulic system classifications require review. Automatic hints are not confirmed errors.`:'PARTIAL EXTRACTION \xb7 Only source-supported connections are shown. Unresolved source geometry remains pending. Review confirms this loaded graph only.';
      const link=document.createElement('a');link.href='data/extraction-report.json';link.target='_blank';link.textContent=' Coverage report';banner.append(link);document.body.append(banner);const toggle=document.createElement('button');toggle.id='pending-source-toggle';toggle.textContent='Hide pending source paths';toggle.onclick=()=>{state.showPending=!state.showPending;toggle.textContent=state.showPending?'Hide pending source paths':'Show pending source paths';render()};if((data.pendingSourcePaths||[]).length)$('.canvas-toolbar').append(toggle);
    }
    globalBounds=bounds(data.edges.flatMap(e=>e.points).concat(data.nodes.map(n=>[n.px,n.py])).concat((data.pendingSourcePaths||[]).flatMap(p=>p.points)).concat(data.instances.flatMap(d=>(d.sourceGeometry||[]).flatMap(p=>p.points))),20);
    if(data.display?.components===true){state.layers.components=true;$('#layer-components').checked=true;}
    events();updateControls();$('#loading').hidden=true;fitView();renderDetails();
    const query=new URLSearchParams(location.search);if(query.get('edge')&&model.edges.has(query.get('edge')))selectEdge(query.get('edge'),{focus:true});if(query.get('node')&&model.nodes.has(query.get('node')))selectNode(query.get('node'),{focus:true});
    // Actual CAD loads independently so the topology is immediately usable.
    const cadResponse=await fetch('data/cad.svg');if(!cadResponse.ok)throw Error('Source CAD vectors could not be loaded');const xml=await cadResponse.text();const parsed=new DOMParser().parseFromString(xml,'image/svg+xml');cadMarkup=parsed.documentElement.innerHTML;sourceReady=true;if(state.compare){renderCad();applyView();}
    window.cadViewer={model,data,state,render,renderGraph,applyView,aspectFit,updateControls,setCompare,notify,visibleEdge,selectedIds,selectEdge,selectNode,traceNetwork:id=>traceNetwork(model,id),shortestPath:(a,b,s)=>shortestPath(model,a,b,s),exportSvg,isReady:()=>sourceReady};
    await (await import('./architecture.js')).initArchitecture(window.cadViewer);
    await (await import('./hil.js')).initHil(window.cadViewer);
    await (await import('./edge-review.js')).initEdgeReview(window.cadViewer);
  }catch(error){console.error(error);$('#loading').hidden=false;$('#loading').innerHTML=`<strong>Unable to load topology</strong><span>${esc(error.message)}</span><span>Start the local server with python serve.py, then reload.</span>`;}
}
init();
