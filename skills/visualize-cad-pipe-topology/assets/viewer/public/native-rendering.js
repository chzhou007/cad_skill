// Native paths are shared by the interactive canvas and portable expert pairs.
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const path=pts=>'M'+pts.map(p=>p.join(',')).join(' L');
export function pointBounds(points,pad=12,fallback=[0,0,1000,800]){
 if(!points.length)return fallback;
 let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
 for(const [x,y]of points){if(x<minX)minX=x;if(y<minY)minY=y;if(x>maxX)maxX=x;if(y>maxY)maxY=y;}
 return [minX-pad,minY-pad,Math.max(5,maxX-minX)+pad*2,Math.max(5,maxY-minY)+pad*2];
}
export function nativePaths(paths){return paths.map(p=>`<path d="${path(p.points)}" fill="${p.fill?'currentColor':'none'}" stroke="currentColor" stroke-width="1" vector-effect="non-scaling-stroke"/>`).join('');}
export function pendingSourceObjectMarkup(objects=[],box=null,floor='all'){
 return objects.filter(o=>floor==='all'||String(o.floor)===String(floor)).map(o=>{
  const paths=box?clipPaths(o.sourceGeometry||[],box):o.sourceGeometry||[];
  return paths.length?`<g data-pending-source-object="${esc(o.id)}" color="#92743c" pointer-events="none"><title>${esc(o.id)}: unresolved source component; edge ownership unconfirmed</title>${nativePaths(paths)}</g>`:'';
 }).join('');
}
export function sourceAnnotationMarkup(records=[],box=null){
 return records.filter(r=>!box||(r.px>=box[0]-r.fontHeight*30&&r.px<=box[0]+box[2]&&r.py>=box[1]-r.fontHeight&&r.py<=box[1]+box[3]+r.fontHeight)).map(r=>`<text data-source-annotation="${esc(r.id)}" x="${r.px}" y="${r.py}" font-size="${r.fontHeight}" transform="rotate(${-r.rotation} ${r.px} ${r.py})" font-family="Microsoft YaHei, Noto Sans CJK SC, SimSun, sans-serif" fill="${r.kind==='pipe_diameter'?'#b14667':'#596c86'}" stroke="none">${esc(r.text)}</text>`).join('');
}
export function sourceRegionGuide(floor,nodes,unit){
 const points=nodes.filter(n=>String(n.floor)===String(floor)).map(n=>[n.px,n.py]);
 if(!points.length)return null;
 const box=pointBounds(points,0);return {x:box[0],y:box[1]-8*unit};
}
export function clipPaths(paths,box){
 const [x,y,w,h]=box,out=[],inside=p=>p[0]>=x&&p[0]<=x+w&&p[1]>=y&&p[1]<=y+h;
 for(const p of paths){
  if(p.fill){
   let pts=p.points;
   for(const [axis,value,sign]of [[0,x,1],[0,x+w,-1],[1,y,1],[1,y+h,-1]]){
    const next=[];for(let i=0;i<pts.length;i++){const a=pts[i],b=pts[(i+1)%pts.length],ia=(a[axis]-value)*sign>=0,ib=(b[axis]-value)*sign>=0;if(ia)next.push(a);if(ia!==ib){const t=(value-a[axis])/(b[axis]-a[axis]);next.push([a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])]);}}pts=next;
   }if(pts.length>=3)out.push({points:pts,fill:true});continue;
  }
  for(let i=1;i<p.points.length;i++){
   const a=p.points[i-1],b=p.points[i];let lo=0,hi=1;
   for(let axis=0;axis<2;axis++){const delta=b[axis]-a[axis],min=box[axis],max=min+box[axis+2];if(Math.abs(delta)<1e-12){if(a[axis]<min||a[axis]>max){hi=-1;break}}else{let t0=(min-a[axis])/delta,t1=(max-a[axis])/delta;if(t0>t1)[t0,t1]=[t1,t0];lo=Math.max(lo,t0);hi=Math.min(hi,t1)}}
   if(lo<=hi)out.push({points:[lo,hi].map(t=>[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])]),fill:false});
  }
 }return out;
}
export function geometryBounds(obj){
 const pts=(obj.sourceGeometry||[]).flatMap(p=>p.points);
 if(!pts.length)return [obj.px,obj.py,0,0];
 const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);return [Math.min(...xs),Math.min(...ys),Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys)];
}
export function portableObject(obj,unit,prefix='pair-',kind='component',box=null){
 const name=obj.node_id||obj.source_device_name||obj.id,color=obj.source_head_status?.startsWith('pending_')?'#b77910':'#354b6b';
 if(obj.sourceGeometry?.length)return `<g data-source-object="${esc(name)}" color="${color}" data-native="true">${nativePaths(box?clipPaths(obj.sourceGeometry,box):obj.sourceGeometry)}</g>`;
 const size=(kind==='equipment'?15:18)*unit,key=obj.symbol_key||obj.type||'EQUIPMENT';
 return `<g data-source-object="${esc(name)}" data-native="unverified" color="${color}" fill="none" stroke="currentColor"><title>${esc(name)}: native placement unverified; source symbol reference</title><use href="#${prefix}${esc(key)}" x="${obj.px-size/2}" y="${obj.py-size/2}" width="${size}" height="${size}"/></g>`;
}
// Retain the independently owned native building DOM across pipe selections.
// Recreating it on every graph redraw is prohibitive on real building plans.
export function replaceGraphMarkup(svg,markup){
 const building=svg.querySelector('#topology-building-context');
 if(building)building.remove();
 svg.innerHTML=markup;
 if(building)svg.insertBefore(building,svg.firstChild);
}
