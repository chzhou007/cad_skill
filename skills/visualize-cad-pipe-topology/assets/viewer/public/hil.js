import {nativePaths,geometryBounds,portableObject,clipPaths,sourceAnnotationMarkup} from './native-rendering.js';
import {buildingPairContext} from './architecture.js';
import {pendingSourceObjectMarkup} from './native-rendering.js';
const $=s=>document.querySelector(s);
const NS='http://www.w3.org/2000/svg';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone=x=>structuredClone(x);
const uid=()=>crypto.randomUUID();
const intersects=(a,b)=>a[0]<=b[0]+b[2]&&a[0]+a[2]>=b[0]&&a[1]<=b[1]+b[3]&&a[1]+a[3]>=b[1];
const path=pts=>'M'+pts.map(p=>p.join(',')).join(' L');
const structural=errors=>JSON.stringify(errors.map(e=>[e.id,[...e.nodes].sort(),[...e.edges].sort(),e.region,!!e.closed]).sort());

export async function initHil(api){
  const {data,model,state}=api;
  let doc,enabled=false,boxMode=false,selectedNodes=new Set(),selectedEdges=new Set(),region=null,
    currentId=null,editing=null,undo=[],dirty=0,saved=0,inflight=null,failed=false,saveMessage='',
    expanded=false,drag=null,sourceIndex=null,previewIds=[],previewBoxes=new Map(),previewAt=0;
  const css=document.createElement('link');css.rel='stylesheet';css.href='hil.css';document.head.append(css);
  $('#review-toggle').firstElementChild.textContent=data.metadata?.hil_ready===false?'Source comparison':'Topology hints';
  const toolbar=document.createElement('div');toolbar.className='hil-toolbar';toolbar.innerHTML=`
    <button id="hil-toggle">Review</button><span id="hil-actions" hidden>
    <button id="hil-box">Box select</button><button id="hil-mark">Mark Error</button>
    <button id="hil-reset">Clear selection</button><button id="hil-undo">Undo</button>
    <button id="hil-collapse">Wide canvas</button></span><span id="hil-save-status" role="status">Loading review...</span>`;
  $('.canvas-toolbar').after(toolbar);
  const panel=document.createElement('section');panel.id='hil-panel';panel.hidden=true;panel.innerHTML=`
    <h2>Human review</h2><label>Reviewer<input id="hil-author" placeholder="Your name"></label>
    <p id="hil-summary"></p><p id="hil-selection"></p><button id="hil-finish" class="primary">Finish Review</button>
    <p id="hil-confirmation"></p><div class="hil-panel-tools"><button id="hil-backup">Export backup</button>
    <button id="hil-import">Import JSON</button><button id="hil-retry">Retry save</button></div>
    <input id="hil-import-file" type="file" accept=".json,application/json" hidden>
    <label>Filter issues<input id="hil-filter" placeholder="Issue ID, object or note"></label>
    <select id="hil-status-filter" aria-label="Issue status"><option value="all">All issues</option><option value="open">Open</option><option value="explained">Explained</option><option value="closed">Closed</option></select>
    <div class="hil-panel-tools"><button id="hil-export-all">Export open pairs</button><button id="hil-notes">Show / hide notes</button></div>
    <div id="hil-list"></div><details><summary>Historical expert responses</summary><div id="hil-history"></div></details>`;
  $('.inspector').append(panel);
  const dialogs=document.createElement('div');dialogs.innerHTML=`
    <dialog id="hil-error-dialog"><form id="hil-error-form"><h2 id="hil-dialog-title">Mark Error</h2>
    <p id="hil-targets"></p><label>Error annotation<textarea id="hil-note" rows="5" maxlength="20000" placeholder="Describe what is wrong and the expected connection. Any language is supported."></textarea></label>
    <p><button type="button" id="hil-replace-targets">Use current selection / region</button></p>
    <details id="hil-resolution"><summary>Resolution (optional)</summary><label><input id="hil-closed" type="checkbox"> Close this issue after human review</label>
    <label>Conclusion when closing<textarea id="hil-closure" rows="2" maxlength="20000"></textarea></label></details>
    <p id="hil-dialog-message"></p><div class="hil-dialog-actions"><button type="button" id="hil-cancel">Cancel</button><button id="hil-error-save" type="submit" class="primary">Save</button></div></form></dialog>
    <dialog id="hil-finish-dialog"><form id="hil-finish-form"><h2>${data.metadata?.extraction_status==='partial'?'Finish loaded-graph review':'Finish entire-dataset review'}</h2><p id="hil-finish-count"></p>
    ${data.metadata?.extraction_status==='partial'?'<p><strong>Partial extraction: confirmation covers the loaded graph only. Unresolved source paths and equipment connections remain pending.</strong></p>':''}<p><strong>All items other than the marked errors have been reviewed and confirmed.</strong></p>
    <p>Applies to all floors and systems, including items hidden by current filters. Marked errors remain open.</p>
    <label>Reviewer<input id="hil-finish-author" required maxlength="200"></label><p id="hil-finish-error"></p>
    <div class="hil-dialog-actions"><button type="button" id="hil-finish-cancel">Cancel</button><button class="primary">Confirm review</button></div></form></dialog>
    <dialog id="hil-pair-dialog"><h2>Expert pair preview</h2><p id="hil-pair-caption"></p><p>Both panes use the same bounds. Export includes original and annotated PNG / SVG, local source vectors, context and an offline expert form.</p>
    <div class="hil-panel-tools"><button id="hil-pair-prev">Previous</button><button id="hil-pair-next">Next</button><button id="hil-pair-current">Use current viewport</button><button id="hil-pair-context">Fit issue + context</button></div>
    <div id="hil-pair-images"></div><p id="hil-pair-message"></p><div class="hil-dialog-actions"><button id="hil-pair-cancel">Cancel</button><button id="hil-pair-download" class="primary">Download pair ZIP</button></div></dialog>`;
  document.body.append(dialogs);
  if(data.metadata?.hil_ready===false){$('#hil-finish').disabled=true;$('#hil-finish').title=data.metadata.hil_block_reason||'Source comparison required';$('#hil-toggle').textContent='Comparison notes';}

  try{doc=await request('/api/review');saveMessage='Saved';}catch(e){saveMessage='Review unavailable: '+e.message;failed=true;doc={schemaVersion:1,datasetId:null,revision:0,errors:[],confirmation:null,historicalResponses:[]};}
  try{$('#hil-author').value=localStorage.getItem('hil-reviewer')||'';}catch{}
  $('#hil-author').oninput=()=>{try{localStorage.setItem('hil-reviewer',$('#hil-author').value)}catch{}};

  async function request(url,method='GET',body){
    const r=await fetch(url,{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
    if(!r.ok){let text;try{text=(await r.json()).error}catch{text=await r.text()}throw Error(text||`HTTP ${r.status}`)}
    return r.json();
  }
  function download(blob,name){const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1500);}
  async function persist(confirm=false,reviewer=''){
    if(inflight){await inflight;if(failed)return false;return persist(confirm,reviewer);}
    if(!doc.datasetId){saveMessage='Cannot save: review API is unavailable';failed=true;renderPanel();return false;}
    if(dirty===saved&&!confirm)return !failed;
    const generation=dirty,snapshot=clone(doc);saveMessage='Saving...';renderPanel();
    inflight=(async()=>{try{
      const result=await request('/api/review','PUT',{baseRevision:snapshot.revision,document:snapshot,confirm,reviewer,invalidateConfirmation:!!snapshot.invalidateConfirmation});
      if(generation===dirty)doc=result;else{doc.revision=result.revision;doc.updatedAt=result.updatedAt;}
      saved=generation;failed=false;saveMessage='Saved';return true;
    }catch(e){failed=true;saveMessage='Save failed: '+e.message;return false;}finally{inflight=null;renderPanel();renderOverlays();}})();
    const ok=await inflight;if(ok&&dirty>saved)return persist();return ok;
  }
  function commit(errors){
    undo.push(clone(doc.errors));if(undo.length>30)undo.shift();
    if(structural(errors)!==structural(doc.errors))doc.confirmation=null;
    doc.errors=errors;dirty++;renderPanel();renderOverlays();void persist();
  }
  function pointsForSelection(){return [...selectedNodes].map(id=>{const n=model.nodes.get(id);return[n.px,n.py]}).concat([...selectedEdges].flatMap(id=>model.edges.get(id).points));}
  function boundPoints(points,padding=.12){
    if(!points.length)return null;
    const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),w=Math.max(.2,Math.max(...xs)-Math.min(...xs)),h=Math.max(.2,Math.max(...ys)-Math.min(...ys)),pad=Math.max(w,h)*padding+.8;
    return[Math.min(...xs)-pad,Math.min(...ys)-pad,w+2*pad,h+2*pad];
  }
  function selectionBox(){return region||boundPoints(pointsForSelection());}
  function renderPanel(){
    $('#hil-save-status').textContent=saveMessage;$('#hil-save-status').className=failed?'hil-save-failed':'';
    const active=doc.errors.filter(e=>!e.closed),nodes=new Set(active.flatMap(e=>e.nodes)),edges=new Set(active.flatMap(e=>e.edges)),confirmed=!!doc.confirmation;
    $('#hil-summary').textContent=`${active.length} open issue groups · ${nodes.size} marked nodes · ${edges.size} marked edges. ${confirmed?(data.metadata?.extraction_status==='partial'?'Remaining loaded items confirmed; source coverage remains pending.':'Remaining items confirmed.'):'Remaining items unreviewed.'}`;
    $('#hil-selection').textContent=`Selected: ${selectedNodes.size} nodes + ${selectedEdges.size} edges${region?' + custom region':''}`;
    $('#hil-confirmation').textContent=confirmed?`Entire dataset confirmed by ${doc.confirmation.reviewer} · ${doc.confirmation.confirmedAt}`:'Entire-dataset review not confirmed.';
    const q=$('#hil-filter').value.toLowerCase(),filter=$('#hil-status-filter').value;
    const shown=doc.errors.filter(e=>(filter==='all'||(filter==='closed'?e.closed:filter==='explained'?!e.closed&&e.expertResponses?.length:!e.closed&&!e.expertResponses?.length))&&
      `${e.label} ${e.note} ${e.nodes.join(' ')} ${e.edges.join(' ')}`.toLowerCase().includes(q));
    $('#hil-list').innerHTML=shown.map(e=>`<article class="hil-card ${e.id===currentId?'active':''}"><button class="hil-issue-title" data-focus="${e.id}">${esc(e.label)} · ${e.closed?'Closed':e.expertResponses?.length?'Explained':'Open'}</button>
      <p class="hil-note-text">${esc(e.note||'No explanation provided')}</p><small>${e.nodes.length} nodes + ${e.edges.length} edges · r${e.issueRevision||1}</small>
      <div class="hil-panel-tools"><button data-edit="${e.id}">Edit</button><button data-pair="${e.id}">Pair</button><button data-remove="${e.id}">Remove</button></div>
      ${(e.expertResponses||[]).map(r=>`<details><summary>Expert: ${esc(r.expertName||'Unnamed')} · ${esc(r.verdict)}</summary><p class="hil-note-text">${esc(r.reason)}</p><p>Expected: ${esc(r.expectedConnection)}</p><p>Suggestion: ${esc(r.suggestion)}</p></details>`).join('')}</article>`).join('')||'<p>No matching issues.</p>';
    $('#hil-history').textContent=(doc.historicalResponses||[]).map(r=>`${r.issueId}: ${r.reason} (${r.historicalReason})`).join('\n')||'No historical responses.';
    $('#hil-undo').disabled=!undo.length;$('#hil-mark').disabled=!selectionBox();
    for(const b of $('#hil-list').querySelectorAll('[data-focus]'))b.onclick=()=>focusIssue(b.dataset.focus);
    for(const b of $('#hil-list').querySelectorAll('[data-edit]'))b.onclick=()=>openError(b.dataset.edit);
    for(const b of $('#hil-list').querySelectorAll('[data-pair]'))b.onclick=()=>openPairs([b.dataset.pair]);
    for(const b of $('#hil-list').querySelectorAll('[data-remove]'))b.onclick=()=>{commit(doc.errors.filter(e=>e.id!==b.dataset.remove));if(currentId===b.dataset.remove)currentId=null;};
  }
  function setEnabled(value){
    enabled=value;document.body.classList.toggle('hil-enabled',value);panel.hidden=!value;$('#hil-actions').hidden=!value;$('#hil-toggle').classList.toggle('active',value);
    if(value){api.setCompare(true);state.selection=null;state.focus=null;api.render();}
    else{document.body.classList.remove('hil-wide');api.render();}
    renderPanel();renderOverlays();
  }
  function renderOverlays(){
    for(const [id,svg] of [['hil-graph-overlay',$('#graph-svg')],['hil-cad-overlay',$('#cad-svg')]]){
      svg.querySelector('#'+id)?.remove();if(!enabled||!state.view)continue;
      const view=(id==='hil-cad-overlay'&&!state.sync?state.cadView:state.view)||state.view;
      const unit=view[2]/Math.max(svg.clientWidth,100),group=document.createElementNS(NS,'g');group.id=id;
      let markup='',labelSlots=[];
      for(const e of doc.errors.filter(e=>!e.closed)){
        if(!intersects(view,e.region))continue;
        const[x,y,w,h]=e.region,focus=currentId===e.id;
        markup+=`<rect data-issue="${e.id}" x="${x}" y="${y}" width="${w}" height="${h}" fill="${focus?'#dc262608':'none'}" stroke="#dc2626" stroke-width="${focus?2:1.1}" stroke-dasharray="4 3" vector-effect="non-scaling-stroke"/>`;
        let lx=Math.max(view[0]+8*unit,Math.min(x,view[0]+view[2]-190*unit)),ly=Math.max(view[1]+30*unit,y-5*unit);
        while(labelSlots.some(p=>Math.abs(p[0]-lx)<480*unit&&Math.abs(p[1]-ly)<23*unit))ly+=24*unit;
        labelSlots.push([lx,ly]);const text=e.label+(expanded&&e.note?' · '+[...e.note].slice(0,Math.max(6,Math.floor(svg.clientWidth/12)-18)).join(''):'');
        markup+=`<g data-issue="${e.id}" class="hil-svg-label"><title>${esc(e.note||'No explanation provided')}</title><rect x="${lx}" y="${ly-16*unit}" width="${Math.min(Math.max(100,svg.clientWidth-24),Math.max(98,text.length*12))*unit}" height="${22*unit}" rx="${3*unit}" fill="white" stroke="#dc2626" stroke-width="1" vector-effect="non-scaling-stroke"/><text x="${lx+5*unit}" y="${ly}" fill="#b91c1c" font-size="${12*unit}">${esc(text)}</text></g>`;
      }
      for(const id of selectedEdges){const e=model.edges.get(id);markup+=`<path d="${path(e.points)}" fill="none" stroke="#2462ed" stroke-width="5" stroke-opacity=".65" vector-effect="non-scaling-stroke" pointer-events="none"/>`;}
      for(const id of selectedNodes){const n=model.nodes.get(id);markup+=`<circle cx="${n.px}" cy="${n.py}" r="${9*unit}" fill="#2462ed20" stroke="#2462ed" stroke-width="2" vector-effect="non-scaling-stroke" pointer-events="none"/>`;}
      if(region){markup+=`<rect x="${region[0]}" y="${region[1]}" width="${region[2]}" height="${region[3]}" fill="#2462ed08" stroke="#2462ed" stroke-dasharray="3 3" vector-effect="non-scaling-stroke" pointer-events="none"/>`;}
      group.innerHTML=markup;svg.append(group);
    }
  }
  function focusIssue(id){
    const e=doc.errors.find(e=>e.id===id);if(!e)return;currentId=id;selectedNodes=new Set(e.nodes);selectedEdges=new Set(e.edges);region=[...e.region];
    state.floor='all';state.systems=new Set(['supply','return']);api.updateControls();api.setCompare(true);
    state.view=api.aspectFit(contextBox(e),$('#graph-svg'));state.cadView=[...state.view];api.render();renderPanel();renderOverlays();
  }
  function openError(id=null){
    const e=doc.errors.find(e=>e.id===id);editing=e?clone(e):{id:uid(),nodes:[...selectedNodes],edges:[...selectedEdges],region:selectionBox(),note:'',author:$('#hil-author').value,closed:false,closureNote:''};
    if(!editing.region){api.notify('Select nodes / edges, or box-select a region first.');return;}
    $('#hil-dialog-title').textContent=e?`Edit ${e.label}`:'Mark Error';$('#hil-note').value=editing.note;
    $('#hil-resolution').hidden=!e;$('#hil-resolution').open=false;$('#hil-replace-targets').hidden=!e;$('#hil-closed').checked=!!editing.closed;$('#hil-closure').value=editing.closureNote||'';$('#hil-dialog-message').textContent='';targetSummary();$('#hil-error-dialog').showModal();$('#hil-note').focus();
  }
  function targetSummary(){$('#hil-targets').textContent=`${editing.nodes.length} nodes + ${editing.edges.length} edges · ${editing.nodes.concat(editing.edges).join(', ')||'Region only (missing object)'}`;}
  function pad(box,f=.15){const p=Math.max(box[2],box[3])*f;return[box[0]-p,box[1]-p,box[2]+2*p,box[3]+2*p]}
  function point(svg,e){const p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const q=p.matrixTransform(svg.getScreenCTM().inverse());return[q.x,q.y]}
  function hit(e){const target=e.target.closest('[data-issue],[data-node],[data-edge]');if(target?.dataset.issue)return{issue:target.dataset.issue};if(target?.dataset.node)return{node:target.dataset.node};if(target?.dataset.edge)return{edge:target.dataset.edge};return null;}
  for(const svg of [$('#graph-svg'),$('#cad-svg')]){
    svg.addEventListener('pointerdown',e=>{if(!enabled||e.button!==0)return;e.stopImmediatePropagation();svg.setPointerCapture(e.pointerId);drag={svg,start:point(svg,e),screen:[e.clientX,e.clientY],view:[...(svg.id==='cad-svg'&&!state.sync?state.cadView:state.view)],box:boxMode,hit:hit(e),shift:e.shiftKey,moved:false};},true);
    svg.addEventListener('pointermove',e=>{if(!enabled)return;e.stopImmediatePropagation();if(!drag||drag.svg!==svg)return;const d=drag;
      d.moved ||= Math.hypot(e.clientX-d.screen[0],e.clientY-d.screen[1])>4;
      if(d.box){const p=point(svg,e);region=[Math.min(d.start[0],p[0]),Math.min(d.start[1],p[1]),Math.max(.01,Math.abs(p[0]-d.start[0])),Math.max(.01,Math.abs(p[1]-d.start[1]))];renderOverlays();}
      else if(d.moved){const r=svg.getBoundingClientRect(),view=[d.view[0]-(e.clientX-d.screen[0])*d.view[2]/r.width,d.view[1]-(e.clientY-d.screen[1])*d.view[3]/r.height,d.view[2],d.view[3]];
        if(svg.id==='cad-svg'&&!state.sync)state.cadView=view;else state.view=view;api.applyView();renderOverlays();}
    },true);
    svg.addEventListener('pointerup',e=>{if(!enabled)return;e.stopImmediatePropagation();const d=drag;drag=null;if(!d)return;
      if(d.box&&d.moved&&region){if(!d.shift){selectedNodes.clear();selectedEdges.clear();}for(const n of data.nodes)if(intersects(region,[n.px,n.py,0,0])&&(state.floor==='all'||String(n.floor)===state.floor)&&(!n.system||state.systems.has(n.system))&&state.layers[n.node_type==='equipment'?'equipment':n.node_type==='virtual_equipment'?'virtual':'tee'])selectedNodes.add(n.node_id);
        for(const edge of data.edges)if(api.visibleEdge(edge,state.floor,state.systems)&&polylineIntersects(edge.points,region))selectedEdges.add(edge.edge_id);boxMode=false;$('#hil-box').classList.remove('active');}
      else if(!d.moved){if(d.hit?.issue){focusIssue(d.hit.issue);openError(d.hit.issue);return;}
        if(!d.shift){selectedNodes.clear();selectedEdges.clear();region=null;}const set=d.hit?.node?selectedNodes:d.hit?.edge?selectedEdges:null,id=d.hit?.node||d.hit?.edge;
        if(set){if(d.shift&&set.has(id))set.delete(id);else set.add(id);}currentId=null;}
      api.render();renderPanel();renderOverlays();
    },true);
    svg.addEventListener('pointercancel',()=>{drag=null;},true);
  }
  $('#hil-toggle').onclick=()=>setEnabled(!enabled);
  $('#hil-box').onclick=()=>{boxMode=!boxMode;$('#hil-box').classList.toggle('active',boxMode)};
  $('#hil-mark').onclick=()=>openError();
  $('#hil-reset').onclick=()=>{selectedNodes.clear();selectedEdges.clear();region=null;currentId=null;renderPanel();renderOverlays()};
  $('#hil-undo').onclick=()=>{if(!undo.length)return;const last=undo.pop();if(structural(last)!==structural(doc.errors))doc.confirmation=null;doc.errors=last;dirty++;renderPanel();renderOverlays();void persist()};
  $('#hil-collapse').onclick=()=>{document.body.classList.toggle('hil-wide');requestAnimationFrame(()=>{api.applyView();renderOverlays()})};
  $('#hil-notes').onclick=()=>{expanded=!expanded;renderOverlays()};
  $('#hil-filter').oninput=renderPanel;$('#hil-status-filter').onchange=renderPanel;
  $('#hil-cancel').onclick=()=>$('#hil-error-dialog').close();
  $('#hil-replace-targets').onclick=()=>{const box=selectionBox();if(!box)return;editing.nodes=[...selectedNodes];editing.edges=[...selectedEdges];editing.region=[...box];targetSummary()};
  $('#hil-error-form').onsubmit=e=>{e.preventDefault();const closed=$('#hil-closed').checked,conclusion=$('#hil-closure').value;if(closed&&!conclusion.trim()){$('#hil-dialog-message').textContent='Enter a conclusion before closing.';return;}
    editing.note=$('#hil-note').value;editing.author=$('#hil-author').value;editing.closed=closed;editing.closureNote=conclusion;
    const next=doc.errors.filter(x=>x.id!==editing.id);next.push(editing);currentId=editing.id;commit(next);$('#hil-error-dialog').close();};
  $('#hil-finish').onclick=async()=>{if(!await persist())return;$('#hil-finish-count').textContent=`Entire dataset: ${data.nodes.length} nodes and ${data.edges.length} edges · ${doc.errors.filter(e=>!e.closed).length} marked error groups.`;$('#hil-finish-author').value=$('#hil-author').value;$('#hil-finish-error').textContent='';$('#hil-finish-dialog').showModal()};
  $('#hil-finish-cancel').onclick=()=>$('#hil-finish-dialog').close();
  $('#hil-finish-form').onsubmit=async e=>{e.preventDefault();if(await persist(true,$('#hil-finish-author').value)){$('#hil-finish-dialog').close()}else $('#hil-finish-error').textContent=saveMessage};
  $('#hil-retry').onclick=()=>{if(!doc.datasetId){location.reload();return;}saved=-1;void persist()};
  $('#hil-backup').onclick=()=>download(new Blob([JSON.stringify(doc,null,2)],{type:'application/json'}),`review-backup-${data.project.id}.json`);
  $('#hil-import').onclick=()=>$('#hil-import-file').click();
  $('#hil-import-file').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{
    const value=JSON.parse(await file.text());if(!await persist())throw Error('Save pending edits before importing.');
    if(Array.isArray(value.errors)){
      if(value.datasetId!==doc.datasetId)throw Error('Backup belongs to another dataset; no object labels were applied.');
      if(!confirm('Replace current error groups with this backup? Current revisions remain in local history.'))return;
      commit(clone(value.errors));if(!await persist())return;
      const responses=value.errors.flatMap(e=>e.expertResponses||[]).concat(value.historicalResponses||[]);
      if(responses.length){const r=await request('/api/expert','POST',{baseRevision:doc.revision,response:{responses}});doc=r.document;}
      api.notify('Error groups restored. Entire-dataset confirmation must be completed again.');doc.confirmation=null;doc.invalidateConfirmation=true;saved=-1;await persist();
    }else{const r=await request('/api/expert','POST',{baseRevision:doc.revision,response:value});doc=r.document;api.notify(`Expert import: ${r.imported} applied, ${r.historical} historical, ${r.duplicates} duplicates.`);}
    renderPanel();renderOverlays();
  }catch(error){api.notify('Import failed: '+error.message)}finally{e.target.value=''}};
  $('#hil-export-all').onclick=()=>openPairs(doc.errors.filter(e=>!e.closed).map(e=>e.id));
  $('#hil-pair-cancel').onclick=()=>$('#hil-pair-dialog').close();
  $('#hil-pair-prev').onclick=()=>{previewAt=Math.max(0,previewAt-1);void showPreview()};
  $('#hil-pair-next').onclick=()=>{previewAt=Math.min(previewIds.length-1,previewAt+1);void showPreview()};
  $('#hil-pair-current').onclick=()=>{previewBoxes.set(previewIds[previewAt],[...state.view]);void showPreview()};
  $('#hil-pair-context').onclick=()=>{const id=previewIds[previewAt];previewBoxes.set(id,contextBox(doc.errors.find(e=>e.id===id)));void showPreview()};
  document.addEventListener('keydown',e=>{if(!enabled||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||$('dialog[open]'))return;
    if(e.key.toLowerCase()==='e'){e.preventDefault();openError()}if(e.ctrlKey&&e.key.toLowerCase()==='z'){e.preventDefault();$('#hil-undo').click()}
  });
  let pendingFrame=false;document.addEventListener('cad-view-changed',()=>{if(pendingFrame)return;pendingFrame=true;requestAnimationFrame(()=>{pendingFrame=false;renderOverlays()})});
  function contextBox(issue){const ids=new Set(issue.nodes);for(const id of issue.edges){const e=model.edges.get(id);ids.add(e.start_node_id);ids.add(e.end_node_id)}
    const points=[];for(const id of ids)for(const e of model.adj.get(id)||[])points.push(...e.points);
    const box=boundPoints(points,.06);if(!box)return pad(issue.region);
    return boundPoints([[box[0],box[1]],[box[0]+box[2],box[1]+box[3]],[issue.region[0],issue.region[1]],[issue.region[0]+issue.region[2],issue.region[1]+issue.region[3]]],.03);
  }
  async function openPairs(ids){
    if(!ids.length){api.notify('No open issues to export.');return;}if(!await persist())return;
    previewIds=ids;previewAt=0;previewBoxes=new Map(ids.map(id=>[id,contextBox(doc.errors.find(e=>e.id===id))]));
    api.setCompare(true);await new Promise(requestAnimationFrame);$('#hil-pair-dialog').showModal();await showPreview();
  }
  function indexSource(){if(sourceIndex)return sourceIndex;sourceIndex=[...$('#cad-source-geometry').querySelectorAll('[data-source-handle]')].map((el,i)=>{
    try{const b=el.getBBox();return{el,bounds:[b.x,b.y,b.width,b.height],sourceHandle:el.dataset.sourceHandle||null,vectorId:el.dataset.vectorId||`vector-${i+1}`}}catch{return null}
  }).filter(Boolean);return sourceIndex;}
  function pairVectors(issue,box){
    const nodes=data.nodes.filter(n=>intersects(box,geometryBounds(n)));
    const components=data.instances.filter(d=>intersects(box,geometryBounds(d)));
    const edges=data.edges.filter(e=>polylineIntersects(e.points,box));
    const unit=box[2]/1600;
    const defs='<defs>'+Object.entries(data.symbols).map(([code,s])=>`<symbol id="pair-${code}" viewBox="0 0 64 64">${s.markup}</symbol>`).join('')+'</defs>';
    const pairPath=e=>clipPaths([{points:e.points,fill:false}],box).map(p=>path(p.points)).join(' ');
    const pipes=edges.map(e=>`<path d="${pairPath(e)}" fill="none" stroke="${data.systems[e.system].color}" stroke-width="1.6" stroke-dasharray="${data.systems[e.system].dash||'none'}" vector-effect="non-scaling-stroke"/>`).join('');
    const glyphs=nodes.map(n=>{const s=6*unit;return n.node_type==='equipment'?portableObject(n,unit,'pair-','equipment',box):n.node_type==='virtual_equipment'?`<path d="M${n.px},${n.py-s} l${s},${s} l${-s},${s} l${-s},${-s} Z" fill="white" stroke="#354b6b" stroke-width="1" vector-effect="non-scaling-stroke"/>`:`<circle cx="${n.px}" cy="${n.py}" r="${3*unit}" fill="white" stroke="#354b6b" vector-effect="non-scaling-stroke"/>`}).join('')+components.map(d=>portableObject(d,unit,'pair-','component',box)).join('');
    const sources=indexSource().filter(s=>intersects(box,s.bounds));
    const cad=`<g fill="none" stroke="#63778f" color="#63778f">${sources.map(s=>{
      const paths=[...s.el.querySelectorAll('path')].map(el=>{const nums=(el.getAttribute('d')||'').match(/[-+]?(?:\d*\.)?\d+(?:e[-+]?\d+)?/gi)||[];return{points:Array.from({length:Math.floor(nums.length/2)},(_,i)=>[Number(nums[2*i]),Number(nums[2*i+1])]),fill:el.getAttribute('fill')!=='none'};});
      return `<g data-source-handle="${esc(s.sourceHandle)}">${nativePaths(clipPaths(paths,box))}</g>`;
    }).join('')}</g>`;
    const selectionLabels=[...issue.nodes.map(id=>{const n=model.nodes.get(id);return{id,p:[n.px,n.py]}}),...issue.edges.map(id=>{const points=clipPaths([{points:model.edges.get(id).points,fill:false}],box).flatMap(p=>p.points);return{id,p:points[Math.floor(points.length/2)]}})].filter(x=>x.p).map(x=>`<text x="${x.p[0]+5*unit}" y="${x.p[1]-5*unit}" font-size="${14*unit}" font-family="Arial" fill="#b91c1c" stroke="white" stroke-width="${2*unit}" paint-order="stroke">${esc(x.id)}</text>`).join('');
    const height=Math.max(600,Math.min(1600,Math.round(1600*box[3]/box[2]))),note=[...issue.note].slice(0,100).join('')+(issue.note.length>100?'...':'');
    const wrapper=(body,annotated,title)=>`<svg xmlns="${NS}" width="1600" height="${height+100}" viewBox="0 0 1600 ${height+100}"><rect width="100%" height="100%" fill="white"/>${defs}<text x="20" y="28" font-family="Segoe UI,Arial" font-size="20" fill="#24344d">${esc(title)} | ${esc(issue.label)} | drawing units</text><svg x="0" y="45" width="1600" height="${height}" viewBox="${box.join(' ')}" preserveAspectRatio="xMidYMid meet">${body}${annotated?`${selectionLabels}<rect x="${issue.region[0]}" y="${issue.region[1]}" width="${issue.region[2]}" height="${issue.region[3]}" fill="none" stroke="#dc2626" stroke-width="3" stroke-dasharray="6 4" vector-effect="non-scaling-stroke"/>${issue.nodes.map(id=>model.nodes.get(id)).map(n=>`<circle cx="${n.px}" cy="${n.py}" r="${8*unit}" fill="#dc262620" stroke="#dc2626" vector-effect="non-scaling-stroke"/>`).join('')}${issue.edges.map(id=>model.edges.get(id)).map(e=>`<path d="${pairPath(e)}" fill="none" stroke="#dc2626" stroke-width="3" vector-effect="non-scaling-stroke"/>`).join('')}`:''}</svg><text x="20" y="${height+76}" font-family="Segoe UI,Arial" font-size="16" fill="${annotated?'#b91c1c':'#63778f'}">${annotated?esc(note||'No explanation provided'):'Local source geometry; English building aliases, originals in context.json.'}</text></svg>`;
    const building=api.buildingContext?.data;
    const annotationText=sourceAnnotationMarkup(data.sourceAnnotations,box);
    return{vectors:Object.fromEntries(['cad','topology'].flatMap(pane=>['original','annotated'].map(kind=>[`${pane}-${kind}.svg`,wrapper((pane==='cad'?cad+buildingPairContext(building,box,true):buildingPairContext(building,box)+pendingSourceObjectMarkup(data.pendingSourceObjects,box)+pipes+glyphs)+annotationText,kind==='annotated',pane==='cad'?'CAD':'Topology')]))),sources:sources.map(s=>({vectorId:s.vectorId,sourceHandle:s.sourceHandle,bounds:s.bounds}))};
  }
  async function showPreview(){
    const issue=doc.errors.find(e=>e.id===previewIds[previewAt]);if(!issue)return;
    $('#hil-pair-caption').textContent=`${previewAt+1} / ${previewIds.length} · ${issue.label} · ${issue.note||'No explanation provided'}`;
    $('#hil-pair-message').textContent='';const {vectors}=pairVectors(issue,previewBoxes.get(issue.id));
    $('#hil-pair-images').replaceChildren();
    for(const pane of ['topology','cad']){const img=new Image();img.alt=pane+' annotated preview';img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(vectors[pane+'-annotated.svg']);$('#hil-pair-images').append(img)}
  }
  async function png(svg){const img=new Image();const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));try{
    img.src=url;await img.decode();const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0);return canvas.toDataURL('image/png').split(',')[1];
  }finally{URL.revokeObjectURL(url)}}
  $('#hil-pair-download').onclick=async()=>{
    const button=$('#hil-pair-download');button.disabled=true;
    try{if(!await persist())throw Error('Save changes before export.');
      for(let offset=0;offset<previewIds.length;offset+=6){const pairs=[];
        for(const id of previewIds.slice(offset,offset+6)){const e=doc.errors.find(e=>e.id===id),box=previewBoxes.get(id),{vectors,sources}=pairVectors(e,box),assets={...vectors};
          $('#hil-pair-message').textContent=`Preparing ${e.label} (${offset+ pairs.length+1} / ${previewIds.length})...`;
          for(const[name,value]of Object.entries(vectors))assets[name.replace('.svg','.png')]=await png(value);
          pairs.push({issueId:id,issueRevision:e.issueRevision,viewBox:box,assets,sourceEntities:sources});}
        const response=await fetch('/api/pairs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({baseRevision:doc.revision,pairs})});
        if(!response.ok)throw Error((await response.json()).error);download(await response.blob(),`expert-pairs-${Math.floor(offset/6)+1}.zip`);
      }$('#hil-pair-message').textContent='Pair ZIP downloaded. Original annotations were preserved.';
    }catch(e){$('#hil-pair-message').textContent='Export failed: '+e.message}finally{button.disabled=false}
  };
  api.hil={get document(){return clone(doc)},get selection(){return{nodes:[...selectedNodes],edges:[...selectedEdges],region}},setEnabled,focusIssue,flush:persist,openPairs};
  window.addEventListener('beforeunload',e=>{if(dirty!==saved||failed){e.preventDefault();e.returnValue=''}});
  renderPanel();
}

export function polylineIntersects(points,box){
  for(let i=1;i<points.length;i++){
    const[a,b]=[points[i-1],points[i]];let lo=0,hi=1;
    for(let axis=0;axis<2;axis++){const delta=b[axis]-a[axis],min=box[axis],max=min+box[axis+2];
      if(Math.abs(delta)<1e-12){if(a[axis]<min||a[axis]>max){hi=-1;break}}
      else{let t0=(min-a[axis])/delta,t1=(max-a[axis])/delta;if(t0>t1)[t0,t1]=[t1,t0];lo=Math.max(lo,t0);hi=Math.min(hi,t1)}
    }if(lo<=hi)return true;
  }return false;
}
