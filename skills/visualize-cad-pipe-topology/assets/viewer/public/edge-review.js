// A separate human authority. Source values and component/graph identities stay intact.
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let documentState=null, queue=new Map();
export const reviewCsvFields=['review_required','review_reasons','review_status','manual_length_m','review_effective_length_m','review_effective_length_source','manual_length_author','manual_length_updated_at'];
export const reviewAttributeCsvFields=['manual_diameters_json','review_effective_diameter_mm','review_effective_diameter_source','manual_note','manual_note_author','manual_note_updated_at'];
export function savedEdgeNote(edit={},history=[],id=''){
 if(Object.hasOwn(edit,'note'))return edit.note;
 return edit.length?.note||edit.reviewed?.note||[...history].reverse().find(h=>h.edgeId===id&&h.note)?.note||'';
}
export function reviewAttributeCsvValues(edge,source={},doc=documentState){
 const edit=doc?.edgeEdits?.[edge.edge_id]||{},diameter=edit.diameters?.whole_edge;
 const old=typeof source.diameter_nominal_mm==='number'&&source.diameter_nominal_mm>0?source.diameter_nominal_mm:'';
 return {manual_diameters_json:edit.diameters&&Object.keys(edit.diameters).length?JSON.stringify(edit.diameters):'',review_effective_diameter_mm:diameter?.nominalMm??old,review_effective_diameter_source:diameter?'manual_user_override':old!==''?'source_checked_whole_edge':'unknown',manual_note:savedEdgeNote(edit,doc?.edgeEditHistory,edge.edge_id),manual_note_author:edit.noteAuthor||'',manual_note_updated_at:edit.noteUpdatedAt||''};
}
export function reviewCsvValues(edge,source={},doc=documentState,items=queue){
 const edit=doc?.edgeEdits?.[edge.edge_id],length=edit?.length;
 const sourceMM=source.crossview_whole_edge_length_mm;
 const sourceM=typeof sourceMM==='number'&&Number.isFinite(sourceMM)&&sourceMM>0?sourceMM/1000:'';
 return {review_required:items.has(edge.edge_id)&&!edit?.reviewed,review_reasons:(items.get(edge.edge_id)?.reasons||[]).join('\uff1b'),review_status:edit?.reviewed?'manually_checked':items.has(edge.edge_id)?'pending':'not_queued',manual_length_m:length?.valueM??'',review_effective_length_m:length?.valueM??sourceM,review_effective_length_source:length?'manual_user_override':sourceM!==''?'source_checked_whole_edge':'unknown',manual_length_author:length?.author??'',manual_length_updated_at:length?.updatedAt??'',...reviewAttributeCsvValues(edge,source,doc)};
}
export function midpoint(points){
 const segments=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
 let remain=segments.reduce((a,b)=>a+b,0)/2;
 for(let i=0;i<segments.length;i++){if(remain<=segments[i]&&segments[i]>0){const t=remain/segments[i];return points[i].map((v,j)=>v+(points[i+1][j]-v)*t)}remain-=segments[i];}
 return points[0]||[0,0];
}
export async function initEdgeReview(api){
 const {data,state,model}=api,$=s=>document.querySelector(s),NS='http://www.w3.org/2000/svg';
 async function request(method='GET',body){const r=await fetch('/api/edge-review',{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||`HTTP ${r.status}`);return d;}
 let loadingError='',busy=false,labels=true;const drafts=new Map();
 try{documentState=await request();}catch(e){loadingError=e.message;}
 try{const r=await fetch('data/edge-review-queue.json');if(r.ok){const q=await r.json();if(q.datasetId!==documentState?.datasetId)throw Error('\u5f85\u6838\u6e05\u5355\u4e0e\u5f53\u524d\u56fe\u7248\u672c\u4e0d\u5339\u914d');queue=new Map(q.items.filter(x=>model.edges.has(x.edgeId)).map(x=>[x.edgeId,x]));}}
 catch(e){loadingError=loadingError||e.message;}
 const css=document.createElement('style');css.textContent=`
 #edge-review-tools{display:flex;gap:8px;align-items:center;font:12px "Segoe UI","Microsoft YaHei",sans-serif;flex-wrap:wrap}
 #edge-review-panel{position:absolute;left:16px;top:110px;z-index:35;background:#fff;border:1px solid #d6a13b;border-radius:8px;padding:12px;width:330px;max-width:calc(100% - 32px);max-height:60vh;overflow:auto;box-shadow:0 5px 22px #27375130;color:#24344d}
 #edge-review-panel[hidden]{display:none}#edge-review-panel button[data-edge-review-select]{display:block;width:100%;text-align:left;margin:5px 0;padding:8px;background:#fff9e9;border:1px solid #ead099;border-radius:4px;color:#6b4800}
 #edge-review-panel button.active{outline:2px solid #2462ed}#edge-review-panel p{font-size:12px;line-height:1.5}
 .inspector #detail-header{max-height:68%}#edge-length-editor{margin-top:8px;padding:12px;border:1px solid #b7cae5;background:#f4f8ff;border-radius:6px;font-size:12px;line-height:1.65}
 #edge-length-editor h3{margin:0 0 5px;font-size:14px}#edge-length-editor input,#edge-length-editor select,#edge-length-editor textarea{width:100%;box-sizing:border-box;padding:7px;margin:3px 0;border:1px solid #afbed3;border-radius:4px}#edge-length-editor button{padding:6px 9px;margin:5px 4px 0 0}#edge-length-status{color:#9b4a00}#edge-length-editor details{max-height:180px;overflow:auto}.edge-review-badge{cursor:pointer}.edge-review-badge:focus{outline:none}.edge-review-badge:focus rect{stroke:#2462ed;stroke-width:3}
 `;document.head.append(css);
 const tools=document.createElement('div');tools.id='edge-review-tools';tools.innerHTML='<button id="edge-review-toggle">\u5f85\u4eba\u5de5\u6838\u9a8c</button><label><input id="edge-review-labels" type="checkbox" checked> \u663e\u793a\u5f85\u6838\u6807\u7b7e</label><span id="edge-review-count"></span>';
 $('.canvas-toolbar').after(tools);
 const panel=document.createElement('section');panel.id='edge-review-panel';panel.hidden=true;panel.setAttribute('aria-label','\u5f85\u4eba\u5de5\u6838\u9a8c\u7684\u8fb9');$('#graph-svg').parentElement.append(panel);
 $('#edge-review-toggle').onclick=()=>{panel.hidden=!panel.hidden;renderList()};$('#edge-review-labels').onchange=e=>{labels=e.target.checked;renderBadges()};
 const pending=id=>queue.has(id)&&!documentState?.edgeEdits?.[id]?.reviewed;
 const visible=e=>api.visibleEdge(e,state.floor,state.systems);
 function choose(id){state.scope='segment';api.selectEdge(id,{focus:true});renderList();renderEditor();renderBadges();}
 panel.onclick=e=>{const b=e.target.closest('[data-edge-review-select]');if(b)choose(b.dataset.edgeReviewSelect);if(e.target.id==='edge-review-close')panel.hidden=true};
 function renderList(){
  const rows=[...queue.values()].filter(q=>pending(q.edgeId)),shown=rows.filter(q=>visible(model.edges.get(q.edgeId)));
  $('#edge-review-count').textContent=`\u5f85\u6838 ${rows.length} \u6761 \u00b7 \u5f53\u524d\u7b5b\u9009 ${shown.length} \u6761`;
  panel.innerHTML=`<strong>\u5f85\u4eba\u5de5\u6838\u9a8c\u7684\u8fb9</strong><button id="edge-review-close" style="float:right">\u5173\u95ed</button><p>\u70b9\u51fb\u7f16\u53f7\u5b9a\u4f4d\u5e76\u9ad8\u4eae\u3002\u7f3a\u4fe1\u606f\u4e0d\u7b49\u4e8e\u8fde\u63a5\u9519\u8bef\uff1b\u5df2\u7b54\u590d\u7684\u753b\u6cd5\u7ed3\u8bba\u4e0d\u9700\u8981\u91cd\u7b54\u3002\u957f\u5ea6\u53ef\u5728\u53f3\u4fa7\u76f4\u63a5\u5f55\u5165\u3002</p>${shown.map(q=>`<button data-edge-review-select="${esc(q.edgeId)}" class="${state.selection?.id===q.edgeId?'active':''}"><b>${esc(q.edgeId)}</b> \u00b7 ${esc(q.label)}<br>${esc(q.reasons.join('\uff1b'))}</button>`).join('')||'<p>\u5f53\u524d\u7b5b\u9009\u4e0b\u6ca1\u6709\u5f85\u6838\u8fb9\u3002</p>'}`;
 }
 function renderBadges(){
  const svg=$('#graph-svg');svg.querySelector('#edge-review-badges')?.remove();if(!labels||!state.view)return;
  const u=state.view[2]/Math.max(svg.clientWidth,100),group=document.createElementNS(NS,'g');group.id='edge-review-badges';const occupied=[];
  for(const q of queue.values()){
   const e=model.edges.get(q.edgeId);if(!pending(e.edge_id)||!visible(e))continue;
   const p=midpoint(e.points),v=state.view;if(p[0]<v[0]||p[0]>v[0]+v[2]||p[1]<v[1]||p[1]>v[1]+v[3])continue;
   let x=p[0]+8*u,y=p[1]-8*u;const w=118*u,h=20*u;
   for(let n=0;n<24&&occupied.some(b=>x<b[0]+w&&x+w>b[0]&&y<b[1]+h&&y+h>b[1]);n++)y+=22*u;
   x=Math.max(v[0]+2*u,Math.min(x,v[0]+v[2]-w-2*u));y=Math.max(v[1]+2*u,Math.min(y,v[1]+v[3]-h-2*u));occupied.push([x,y]);
   const g=document.createElementNS(NS,'g');g.setAttribute('class','edge-review-badge');g.setAttribute('role','button');g.setAttribute('tabindex','0');g.setAttribute('aria-label',`${e.edge_id} \u5f85\u6838\u9a8c ${q.label}`);g.dataset.reviewBadge=e.edge_id;
   const leader=document.createElementNS(NS,'path');leader.setAttribute('d',`M${p} L${x},${y+h/2}`);leader.setAttribute('stroke','#ba7a10');leader.setAttribute('fill','none');leader.setAttribute('vector-effect','non-scaling-stroke');leader.setAttribute('pointer-events','none');group.append(leader);
   g.innerHTML=`<title>${esc(q.reasons.join('\uff1b'))}</title><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${3*u}" fill="${state.selection?.id===e.edge_id?'#2462ed':'#fff4d4'}" stroke="#bd8015" vector-effect="non-scaling-stroke"/><text x="${x+5*u}" y="${y+14*u}" font-size="${11*u}" fill="${state.selection?.id===e.edge_id?'white':'#704400'}">${esc(e.edge_id)} \u5f85\u6838\u00b7${esc(q.label)}</text>`;
   g.addEventListener('pointerdown',ev=>ev.stopPropagation());g.addEventListener('pointerup',ev=>ev.stopPropagation());g.addEventListener('click',ev=>{ev.stopPropagation();choose(e.edge_id)});g.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();choose(e.edge_id)}});group.append(g);
  }svg.append(group);
 }
 function renderEditor(){
  $('#edge-length-editor')?.remove();const s=state.selection;if(s?.kind!=='edge')return;
  const id=s.id,edit=documentState?.edgeEdits?.[id]||{},q=queue.get(id),draft=drafts.get(id)||{},scope=draft.diameterScope||'whole_edge',diameter=edit.diameters?.[scope],node=document.createElement('section');node.id='edge-length-editor';
  const history=(documentState?.edgeEditHistory||[]).filter(h=>h.edgeId===id).slice(-10).reverse();
  const note=draft.noteDirty?draft.note:savedEdgeNote(edit,documentState?.edgeEditHistory,id),length=draft.lengthDirty?draft.length:edit.length?.valueM??'',diameterValue=draft.diameterValues?.[scope]??diameter?.nominalMm??'';
  node.innerHTML=`<h3>\u5c5e\u6027\u4fee\u6539 \u00b7 ${esc(id)}</h3><div>\u5f53\u524d\u4eba\u5de5\u957f\u5ea6\uff1a<strong>${edit.length?esc(edit.length.valueM)+' m':'\u672a\u8bbe\u7f6e\uff08\u6cbf\u7528\u539f\u56fe\u5df2\u77e5\u503c\uff09'}</strong></div>${q?`<p>\u5f85\u6838\u539f\u56e0\uff1a${esc(q.reasons.join('\uff1b'))}</p>`:''}
  <label>\u6574\u6761\u8fb9\u7684\u5b9e\u9645\u957f\u5ea6\uff08\u7c73\uff09<input id="edge-length-value" type="number" step="any" min="0" placeholder="\u4f8b\u5982 12.35" value="${esc(length)}"></label><button id="edge-length-save">\u4fdd\u5b58\u957f\u5ea6</button><button id="edge-length-reset" ${!edit.length?'disabled':''}>\u6062\u590d\u539f\u56fe\u503c</button>
  <h4>\u7ba1\u5f84\u4fee\u6539</h4><label>\u7ba1\u5f84\u9002\u7528\u8303\u56f4<select id="edge-diameter-scope">${[['whole_edge','\u6574\u6761\u8fb9\uff08\u5355\u4e00\u7ba1\u5f84\uff09'],['horizontal','\u5e73\u9762\uff0f\u6c34\u5e73\u6bb5'],['vertical','\u5782\u76f4\u6bb5']].map(([key,label])=>`<option value="${key}" ${scope===key?'selected':''}>${label}</option>`).join('')}</select></label><p>\u5f53\u524d\u9009\u5b9a\u8303\u56f4\u7684\u4eba\u5de5\u7ba1\u5f84\uff1a<strong>${diameter?'DN'+esc(diameter.nominalMm):'\u672a\u8bbe\u7f6e'}</strong></p><label>\u7ba1\u5f84 DN\uff08\u6beb\u7c73\uff09<input id="edge-diameter-value" type="number" step="any" min="0" placeholder="\u4f8b\u5982 200" value="${esc(diameterValue)}"></label><button id="edge-diameter-save">\u4fdd\u5b58\u7ba1\u5f84</button><button id="edge-diameter-reset" ${!diameter?'disabled':''}>\u6062\u590d\u8be5\u8303\u56f4\u539f\u7ba1\u5f84</button><p>\u5206\u65b9\u5411\u4fee\u6539\u53ea\u5f71\u54cd\u6240\u9009\u8303\u56f4\uff1b\u6574\u8fb9\u7ba1\u5f84\u8868\u793a\u4eba\u5de5\u6307\u5b9a\u7684\u5355\u4e00\u503c\uff0c\u539f\u56fe\u5206\u6bb5\u4fdd\u7559\u3002</p>
  <label>\u5907\u6ce8\uff08\u53ef\u9009\uff09<textarea id="edge-length-note" rows="3" maxlength="2000" placeholder="\u6d4b\u91cf\u4f9d\u636e\u6216\u4fee\u6b63\u8bf4\u660e">${esc(note)}</textarea></label><button id="edge-note-save">\u4fdd\u5b58\u5907\u6ce8</button>${q?`<button id="edge-review-done">${edit.reviewed?'\u6062\u590d\u5f85\u6838':'\u6807\u8bb0\u672c\u8fb9\u5df2\u6838\u9a8c'}</button>`:''}<p id="edge-length-status" role="status">${esc(loadingError||'\u4eba\u5de5\u503c\u4e0e\u539f\u56fe\u503c\u5206\u522b\u4fdd\u7559\u3002\u5907\u6ce8\u53ef\u5355\u72ec\u4fdd\u5b58\uff0c\u5237\u65b0\u540e\u4ecd\u4fdd\u7559\u3002')}</p><details><summary>\u672c\u8fb9\u4fee\u6539\u8bb0\u5f55\uff08${history.length} \u6761\uff0c\u663e\u793a\u6700\u8fd110\u6761\uff09</summary>${history.map(h=>`<p>${esc(h.at)} \u00b7 ${esc(h.action)}<br>${esc(h.note)}</p>`).join('')}</details>`;
  $('#detail-header .detail-title').after(node);
  const change=()=>{const d=drafts.get(id)||{};drafts.set(id,d);return d;};
  $('#edge-length-note').oninput=()=>{const d=change();d.note=$('#edge-length-note').value;d.noteDirty=true;};
  $('#edge-length-value').oninput=()=>{const d=change();d.length=$('#edge-length-value').value;d.lengthDirty=true;};
  $('#edge-diameter-value').oninput=()=>{const d=change();(d.diameterValues??={})[scope]=$('#edge-diameter-value').value;};
  $('#edge-diameter-scope').onchange=()=>{change().diameterScope=$('#edge-diameter-scope').value;renderEditor();};
  $('#edge-length-save').onclick=()=>{const raw=$('#edge-length-value').value,v=Number(raw);if(!raw||!Number.isFinite(v)||v<=0){$('#edge-length-status').textContent='\u8bf7\u8f93\u5165\u5927\u4e8e 0 \u7684\u957f\u5ea6\uff0c\u5355\u4f4d\u4e3a\u7c73\u3002';return}void save('setLength',id,v);};
  $('#edge-length-reset').onclick=()=>void save('resetLength',id);
  $('#edge-diameter-save').onclick=()=>{const raw=$('#edge-diameter-value').value,v=Number(raw);if(!raw||!Number.isFinite(v)||v<=0){$('#edge-length-status').textContent='\u8bf7\u8f93\u5165\u5927\u4e8e 0 \u7684\u7ba1\u5f84\uff0c\u5355\u4f4d\u6beb\u7c73\u3002';return}void save('setDiameter',id,v,scope);};
  $('#edge-diameter-reset').onclick=()=>void save('resetDiameter',id,undefined,scope);
  $('#edge-note-save').onclick=()=>void save('saveNote',id);
  if($('#edge-review-done'))$('#edge-review-done').onclick=()=>void save(edit.reviewed?'unreview':'review',id);
  node.querySelectorAll('button').forEach(b=>{if(busy||loadingError)b.disabled=true});
 }
 async function save(action,id,value,diameterScope){
  if(busy)return;const note=$('#edge-length-note')?.value||'',author=$('#hil-author')?.value||'';busy=true;$('#edge-length-status').textContent='\u6b63\u5728\u4fdd\u5b58\u2026';
  try{
   documentState=await request('PUT',{datasetId:documentState.datasetId,baseRevision:documentState.revision,edgeId:id,action,...(action==='setLength'?{lengthM:value}:{}),...(diameterScope?{diameterScope,diameterMm:value}:{}),note,author});
   const d=drafts.get(id);if(d){if(d.note===note)delete d.noteDirty;if(action==='setLength'&&Number(d.length)===value||action==='resetLength')delete d.lengthDirty;if(diameterScope&&d.diameterValues&&(action==='resetDiameter'||Number(d.diameterValues[diameterScope])===value))delete d.diameterValues[diameterScope];}
   document.dispatchEvent(new CustomEvent('edge-review-saved',{detail:documentState}));api.notify('\u5df2\u4fdd\u5b58\uff1b\u7ba1\u5f84\u3001\u957f\u5ea6\u548c\u5907\u6ce8\u4e0e\u539f\u56fe\u4fe1\u606f\u5206\u522b\u4fdd\u7559\u3002');
  }catch(e){if($('#edge-length-status'))$('#edge-length-status').textContent='\u4fdd\u5b58\u5931\u8d25\uff1a'+e.message;busy=false;return;}
  busy=false;api.render();renderEditor();renderList();renderBadges();
 }
 document.addEventListener('cad-view-changed',()=>{renderBadges();renderList()});
 document.addEventListener('cad-details-changed',renderEditor);
 document.addEventListener('hil-document-updated',e=>{documentState=e.detail;api.render();renderList();renderBadges();renderEditor()});
 renderList();renderBadges();renderEditor();
}
