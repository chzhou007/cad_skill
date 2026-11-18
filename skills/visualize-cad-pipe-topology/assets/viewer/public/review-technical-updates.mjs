// Progress may be text-only; optional media must never prevent review rendering.
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function mediaPath(value){return value&&typeof value.path==='string'&&value.path.trim()?value.path:null;}
export function renderTechnicalUpdates(updates){
 if(!Array.isArray(updates))return '';
 return updates.filter(u=>u&&typeof u==='object').map(u=>{
  const svg=mediaPath(u.svg),overview=mediaPath(u.overview),pair=mediaPath(u.pair);
  const wide=svg||overview?`<div class="figure">${svg?`<a href="${escape(svg)}" target="_blank" rel="noopener">\u6253\u5f00\u539f CAD \u77e2\u91cf\u5b9a\u4f4d\u56fe</a>`:''}${overview?`<img loading="lazy" src="${escape(overview)}" alt="\u539f CAD \u5927\u8303\u56f4\u95ee\u9898\u5b9a\u4f4d">`:''}</div>`:'';
  const local=pair?`<div class="figure"><a href="${escape(pair)}" target="_blank" rel="noopener">\u6253\u5f00\u539f CAD\uff0f\u7ed3\u679c\u5bf9\u7167</a><img loading="lazy" src="${escape(pair)}" alt="${escape(u.title)} \u5bf9\u7167\u6750\u6599"></div>`:'';
  return `<details class="notice"><summary>${escape(u.title)}</summary><p>${escape(u.summary)}</p>${u.scope?`<p class="detail">${escape(u.scope)}</p>`:''}${u.viewer_url?`<p><a href="${escape(u.viewer_url)}" target="_blank" rel="noopener">\u6253\u5f00\u5f53\u524d\u9636\u6bb5\u67e5\u770b\u5668</a></p>`:''}${wide}${local}</details>`;
 }).join('');
}
