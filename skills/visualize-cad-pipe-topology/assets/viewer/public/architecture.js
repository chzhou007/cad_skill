// Source-derived building context remains separate from the hydraulic graph.
import {clipPaths} from './native-rendering.js';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function buildingPointBounds(points,pad=10){
 if(!points.length)return null;
 let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
 for(const [x,y]of points){minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);}
 return [minX-pad,minY-pad,Math.max(20,maxX-minX+pad*2),Math.max(20,maxY-minY+pad*2)];
}
export function buildingPairContext(data,box,labelsOnly=false){
 if(!data)return '';
 return data.records.map(r=>{
  let body='';
  if(r.display_position){const[x,y]=r.display_position,b=r.display_text_bounds||[x,y,0,0];if(b[0]>box[0]+box[2]||b[0]+b[2]<box[0]||b[1]>box[1]+box[3]||b[1]+b[3]<box[1])return '';body=`<text x="${x}" y="${y}" transform="rotate(${-r.rotation} ${x} ${y})" font-size="${r.font_height}" font-family="Arial,sans-serif" fill="#586a80" stroke="none">${esc(r.label)}</text>`;}
  else if(!labelsOnly){const paths=clipPaths(r.paths.map(p=>({points:p.display_points,fill:p.fill})),box);if(!paths.length)return '';const d=paths.map(p=>'M'+p.points.map(q=>q.join(',')).join(' L')+(p.fill?' Z':'')).join(' ');body=`<path d="${d}" fill="${r.render_role==='occlusion_mask'?'white':paths.some(p=>p.fill)?'#b5bfca':'none'}" fill-rule="evenodd" stroke="${r.render_role==='occlusion_mask'?'none':'#8190a2'}" stroke-width=".6" vector-effect="non-scaling-stroke"/>`;}
  return body?`<g data-building-id="${esc(r.id)}">${body}</g>`:'';
 }).join('');
}
export async function initArchitecture(api){
 const manifest=await(await fetch('data/manifest.json')).json();if(manifest.displayTitle){document.querySelector('#brand-title').textContent=manifest.displayTitle;document.title=manifest.displayTitle;}if(!manifest.buildingContext)return;
 const response=await fetch('data/architecture.json');if(response.status===404)return;if(!response.ok)throw Error('Building context could not be loaded');
 const data=await response.json();if(!data.records?.length)return;
 const svg=await(await fetch('data/architecture.svg')).text();
 const parsed=new DOMParser().parseFromString(svg,'image/svg+xml');
 const content=parsed.documentElement.innerHTML,NS='http://www.w3.org/2000/svg';
 const section=document.createElement('section');section.id='building-context-controls';
 section.innerHTML='<h2>Building context</h2><label class="check"><input id="building-geometry" type="checkbox" checked><span>Walls, openings & grids</span></label><label class="check"><input id="building-labels" type="checkbox" checked><span>Room labels & dimensions</span></label><button id="fit-building" class="source-button">Fit building extent</button><input id="building-search" aria-label="Find building label" placeholder="Find room or grid label" style="width:100%;box-sizing:border-box;margin-top:8px"><select id="building-results" aria-label="Building labels" style="width:100%;margin-top:6px"><option value="">Locate a source label</option></select><small id="building-summary"></small>';
 document.querySelector('.sidebar section')?.before(section);
 const geometry=section.querySelector('#building-geometry'),labels=section.querySelector('#building-labels'),results=section.querySelector('#building-results');
 section.querySelector('#building-summary').textContent=`${data.summary.records} source records. ${data.issues.filter(i=>i.reason==='translation_pending').length} labels need translation. Layer candidates; room boundaries unverified.`;
 let cachedEntries=null,visibilityKey='',hiddenSource=null;
 function update(){
  let group=document.querySelector('#topology-building-context');
  if(!group){group=document.createElementNS(NS,'g');group.id='topology-building-context';group.setAttribute('pointer-events','none');group.innerHTML=content;const canvas=document.querySelector('#graph-svg');canvas.insertBefore(group,canvas.querySelector('defs')?.nextSibling||canvas.firstChild);}
  const nextVisibility=`${geometry.checked}:${labels.checked}`;
  if(nextVisibility!==visibilityKey){
   if(!cachedEntries)cachedEntries=[...group.querySelectorAll('[data-building-id]')].map(node=>({node,text:!!node.querySelector('text')}));
   for(const {node,text}of cachedEntries){node.style.display=(text?labels.checked:geometry.checked)?'':'none';node.style.opacity=text?'.95':'.5';}
   visibilityKey=nextVisibility;
  }
  const source=document.querySelector('#cad-source-geometry');
  if(source?.dataset.loaded&&hiddenSource!==source){for(const node of source.querySelectorAll('[data-building-id]'))if(node.querySelector('text'))node.style.display='none';hiddenSource=source;}
  if(api.state.compare){let overlay=document.querySelector('#cad-building-labels');if(!overlay){overlay=document.createElementNS(NS,'g');overlay.id='cad-building-labels';overlay.setAttribute('pointer-events','none');overlay.setAttribute('color','#586a80');for(const node of group.querySelectorAll('[data-building-id]'))if(node.querySelector('text')){const copy=node.cloneNode(true);copy.style.display='';overlay.append(copy);}document.querySelector('#cad-svg').append(overlay);}overlay.style.display=labels.checked?'':'none';}
 }
 const allPoints=data.records.flatMap(r=>r.paths.flatMap(p=>p.display_points).concat(r.display_position?[r.display_position]:[]));
 const locate=(points,pad=10)=>{const b=buildingPointBounds(points,pad);if(!b)return;api.state.view=api.aspectFit(b,document.querySelector('#graph-svg'));if(api.state.sync)api.state.cadView=[...api.state.view];api.renderGraph();};
 geometry.onchange=labels.onchange=update;section.querySelector('#fit-building').onclick=()=>locate(allPoints);
 const labelRecords=data.records.filter(r=>r.label);
 function search(){const q=section.querySelector('#building-search').value.trim().toLowerCase();results.replaceChildren(new Option('Locate a source label',''));for(const r of labelRecords.filter(r=>!q||r.label.toLowerCase().includes(q)).slice(0,100))results.add(new Option(`${r.label} [${r.id}]`,r.id));}
 section.querySelector('#building-search').oninput=search;results.onchange=()=>{const r=labelRecords.find(r=>r.id===results.value);if(r){const el=document.querySelector(`#topology-building-context [data-building-id="${r.id}"]`),b=el?.getBBox();if(b)locate([[b.x,b.y],[b.x+b.width,b.y+b.height]],Math.max(b.width*.8,b.height*5));else locate([r.display_position],50);}};search();
 document.addEventListener('cad-view-changed',update);update();
 api.buildingContext={data,update,fit:()=>locate(allPoints)};
}
