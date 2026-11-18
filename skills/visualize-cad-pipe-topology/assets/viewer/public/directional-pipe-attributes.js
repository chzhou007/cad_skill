// A presentation contract over qualified existing readers, never a new CAD inference.
const positive=v=>typeof v==='number'&&Number.isFinite(v)&&v>0;
const parse=v=>{try{return typeof v==='string'?JSON.parse(v):v;}catch{return null;}};
const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const unique=xs=>[...new Set(xs)];
const sourceNumbers=v=>positive(v)?[v]:typeof v==='string'&&/^\d+(?:\.\d+)?(?:;\d+(?:\.\d+)?)*$/.test(v)?unique(v.split(';').map(Number).filter(positive)):[];
export const directionalCsvFields=['pipe_horizontal_attributes_json','pipe_vertical_attributes_json','pipe_unresolved_direction_json','pipe_whole_edge_manual_json'];
const planDNFields=[
 'crossview_plan_drawn_nominal_mm','plan_segment_nominal_mm','plan_segment_whole_main_nominal_mm',
 'anchored_main_DN_evidence_json','external_feed_pipe_nominal_mm','current_floor_scope_DN_mm',
 'batch_plan_DN_mm','batch_uniform_group_child_DN_mm','member_plan_run_DN_mm','ordered_branch_plan_DN_mm',
 'bounded_main_plan_DN_mm','compound_member_plan_DN_mm','noncompound_main_DN_mm','circle_member_DN_mm',
 'member_bridge_DN_mm','alias_member_horizontal_DN_mm','alias_bridge_DN_mm','riser_header_plan_DN_mm',
 'cohort_member_plan_DN_mm','contact_owner_plan_DN_mm','complementary_plan_DN_mm','anchored_branch_plan_DN_mm',
 'reviewed_partition_plan_nominal_mm','candidate_ring_partition_plan_nominal_mm'];
const completePlanLengths=['crossview_whole_edge_length_mm','batch_complete_horizontal_centerline_mm',
 'member_plan_run_centerline_mm','ordered_group_complete_run_mm','bounded_main_complete_centerline_mm',
 'noncompound_main_complete_centerline_mm','circle_member_complete_centerline_mm',
 'alias_member_horizontal_complete_centerline_mm','cycle_gate_complete_centerline_mm',
 'riser_header_complete_centerline_mm','cohort_member_complete_centerline_mm','contact_owner_complete_centerline_mm',
 'anchored_metric_complete_centerline_mm','complementary_plan_centerline_mm'];
const partialPlanLengths=['crossview_plan_horizontal_projection_mm','plan_segment_projection_mm',
 'anchored_main_plan_XY_mm','external_feed_pipe_XY_mm','current_floor_scope_XY_mm','batch_plan_pipe_XY_mm',
 'ordered_branch_plan_pipe_XY_mm','bounded_main_plan_pipe_XY_mm','compound_member_plan_run_centerline_mm',
 'member_bridge_plan_pipe_projection_mm','alias_bridge_plan_pipe_projection_mm','riser_header_drawn_projection_mm',
 'cohort_member_drawn_projection_mm','contact_owner_drawn_projection_mm','anchored_branch_plan_pipe_XY_mm',
 'plan_crossover_complete_XY_centerline_mm','plan_segment_whole_main_centerline_mm'];
const verticalFields=['axis_riser_segments_json','axis_vertical_DN_segments_json','unbranched_vertical_DN_segments_json',
 'axis_omission_vertical_DN_segments_json','axis_continuous_vertical_DN_segments_json',
 'axis_nested_pair_vertical_DN_segments_json','axis_nested_direct_vertical_DN_segments_json',
 'axis_rule_vertical_DN_segments_json','inherited_entry_vertical_DN_segments_json'];
const planDomainFields=['uniform_subroute_DN_domains_json','received_scope_uniform_DN_domains_json',
 'plan_branch_DN_domains_json','inherited_entry_DN_domains_json'];

function aggregate(observations){
 const xs=unique(observations.map(o=>o.value_mm).filter(positive));
 return {value_mm:xs.length===1?xs[0]:null,status:xs.length>1?'conflict':xs.length?'known':'unknown',observations};
}
function groups(segments,source){return {applicability:segments.length?'present':'not_present',source,segments,
 diameter:{value_mm:null,status:'unknown',observations:[]},
 length:{value_m:null,status:'unknown',kind:'centerline_not_net_cut_or_installed',observations:[]}};}

export function directionalPipeAttributes(edge,values={},routes=[]){
 const paths=edge.attribute_paths||[];
 const expected=paths.flatMap((p,pi)=>p.slice(1).map((b,si)=>({path_index:pi,segment_index:si,scope_points:[p[si],b]})));
 const own=routes.filter(r=>r.edge_id===edge.edge_id);
 if(own.length!==expected.length||expected.some(s=>own.filter(r=>r.path_index===s.path_index&&r.segment_index===s.segment_index&&r.system===edge.system&&eq(r.scope_points,s.scope_points)).length!==1))throw Error('Directional source path differs: '+edge.edge_id);
 const segments=own.map(r=>({path_index:r.path_index,segment_index:r.segment_index,scope_points:r.scope_points,
  direction:r.direction_class,diameter:{value_mm:null,status:'unknown',observations:[]},length:{value_m:null,status:'unknown'},
  source:r.direction_class==='horizontal'?'plan08_09_10':r.direction_class==='vertical'?'axis11':'direction_unresolved'}));
 const horizontal=groups(segments.filter(r=>r.direction==='horizontal'),'plan08_09_10');
 const vertical=groups(segments.filter(r=>r.direction==='vertical'),'axis11');
 const unresolved=segments.filter(r=>!['horizontal','vertical'].includes(r.direction));
 function assign(row,value,field,kind){
  if(!positive(value))return;
  const pi=row.path_index??row.axis_path_index,si=row.segment_index??row.axis_segment_index;
  const s=segments.find(s=>s.path_index===pi&&s.segment_index===si&&s.direction===kind);
  if(!s||!row.scope_points||!eq(s.scope_points,row.scope_points))return;
  s.diameter.observations.push({value_mm:value,source_field:field,scope:'exact_axis_segment',source:kind==='vertical'?'axis11':'plan08_09_10'});
 }
 for(const field of verticalFields){
  const rows=parse(values[field]);
  for(const row of Array.isArray(rows)?rows:[])assign(row,row.nominal_mm,field,'vertical');
 }
 for(const field of planDomainFields){
  const row=parse(values[field]);
  if(!row)continue;
  for(const s of row.horizontal_segment_domains||[])assign(s,row.nominal_mm,field,'horizontal');
 }
 const planSegments=parse(values.plan_segment_attributes_json);
 for(const row of Array.isArray(planSegments)?planSegments:[]){
  const indices=row.segment_indices||[],path=paths[row.path_index];
  if(!indices.length||!path||row.edge_id!==edge.edge_id||row.system!==edge.system||indices.some((v,i)=>v!==indices[0]+i)||!eq(path.slice(indices[0],indices.at(-1)+2),row.scope_points))continue;
  for(const si of indices)assign({path_index:row.path_index,segment_index:si,scope_points:path.slice(si,si+2)},row.nominal_mm,'plan_segment_attributes_json','horizontal');
 }
 for(const s of segments)s.diameter=aggregate(s.diameter.observations);
 const pureHorizontal=horizontal.segments.length===segments.length&&segments.length>0;
 const pureVertical=vertical.segments.length===segments.length&&segments.length>0;
 if(pureHorizontal&&positive(values.diameter_nominal_mm)){
  for(const s of horizontal.segments)s.diameter=aggregate([...s.diameter.observations,{value_mm:values.diameter_nominal_mm,source_field:'diameter_nominal_mm',scope:'qualified_whole_horizontal_edge',source:'plan08_09_10'}]);
 }
 // Whole-edge DN may not be borrowed for an unresolved direction or mixed route.
 for(const group of [horizontal,vertical]){
  const known=group.segments.filter(s=>s.diameter.status==='known'),nums=unique(known.map(s=>s.diameter.value_mm));
  group.diameter={value_mm:known.length===group.segments.length&&nums.length===1?nums[0]:null,
   status:group.segments.some(s=>s.diameter.status==='conflict')?'conflict':!group.segments.length?'not_applicable':known.length===group.segments.length?(nums.length===1?'known':'segmented'):known.length?'partial':'unknown',
   observations:group.segments.flatMap(s=>s.diameter.observations.map(o=>({...o,path_index:s.path_index,segment_index:s.segment_index})))};
 }
 for(const f of planDNFields)for(const value of sourceNumbers(values[f]))horizontal.diameter.observations.push({value_mm:value,source_field:f,scope:'original_provider_extent_not_reallocated',source:'plan08_09_10'});
 if(horizontal.segments.length&&horizontal.diameter.status==='unknown'&&horizontal.diameter.observations.length)horizontal.diameter.status='partial';
 for(const f of completePlanLengths)if(positive(values[f]))horizontal.length.observations.push({value_m:values[f]/1000,source_field:f,scope:pureHorizontal?'whole_horizontal_route':'original_provider_extent_not_reallocated',kind:'centerline_not_net_cut_or_installed'});
 for(const f of partialPlanLengths)if(positive(values[f]))horizontal.length.observations.push({value_m:values[f]/1000,source_field:f,scope:'partial_or_projection_not_whole_length',kind:'source_projection_or_partial_centerline'});
 // Only the existing effective whole-edge reader can promote a complete plan length.
 if(pureHorizontal&&positive(values.crossview_whole_edge_length_mm))horizontal.length={...horizontal.length,value_m:values.crossview_whole_edge_length_mm/1000,status:'known'};
 else if(horizontal.length.observations.length)horizontal.length.status='partial';
 if(pureVertical&&positive(values.axis_riser_physical_length_mm))vertical.length={...vertical.length,value_m:values.axis_riser_physical_length_mm/1000,status:'known',observations:[{value_m:values.axis_riser_physical_length_mm/1000,source_field:'axis_riser_physical_length_mm',source:'axis11',scope:'qualified_vertical_edge'}]};
 // No axis drawing distance, horizontal caption, floor difference or group allocation is a physical length.
 for(const g of [horizontal,vertical])if(!g.segments.length){g.diameter.status='not_applicable';g.length.status='not_applicable';}
 return {schema:'directional_pipe_attributes_v1',horizontal,vertical,unresolved_direction:{status:unresolved.length?'pending':'none',segments:unresolved},
  whole_edge_manual:{value_m:null,status:'not_set',allocation_to_directions:'not_assumed'}};
}

export function withManual(attributes,review={}){
 const a=structuredClone(attributes),v=review.manual_length_m;
 if(positive(v))a.whole_edge_manual={value_m:v,status:'manual_override',author:review.manual_length_author||'',updated_at:review.manual_length_updated_at||'',allocation_to_directions:'not_assumed'};
 const diameters=parse(review.manual_diameters_json)||{};
 for(const key of ['horizontal','vertical']){
  const scoped=diameters[key],whole=diameters.whole_edge,d=positive(scoped?.nominalMm)?scoped:whole;
  if(!positive(d?.nominalMm)||a[key].applicability!=='present')continue;
  const original=a[key].diameter;
  a[key].diameter={value_mm:d.nominalMm,status:'manual_override',source:'manual_user_override',scope:d===scoped?key:'whole_edge',author:d.author||'',updated_at:d.updatedAt||'',original,
   observations:[{value_mm:d.nominalMm,source:'manual_user_override',scope:d===scoped?key:'whole_edge'}]};
 }
 if(positive(diameters.whole_edge?.nominalMm))a.whole_edge_manual={...a.whole_edge_manual,status:positive(v)?'manual_override':'manual_diameter_override',diameter_nominal_mm:diameters.whole_edge.nominalMm,diameter_source:'manual_user_override'};
 if(Object.keys(diameters).length)a.manual_diameters=diameters;
 if(review.manual_note)a.note=review.manual_note;
 return a;
}
export function directionalCsvValues(attributes,review={}){
 const a=withManual(attributes,review);return Object.fromEntries(directionalCsvFields.map((f,i)=>[f,JSON.stringify([a.horizontal,a.vertical,a.unresolved_direction,a.whole_edge_manual][i])]));
}

const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=v=>Number(v).toLocaleString('zh-CN',{maximumFractionDigits:3});
function textLength(g){return positive(g.length.value_m)?number(g.length.value_m):g.length.status==='not_applicable'?'\u4e0d\u9002\u7528':g.length.observations.length?`\u5c40\u90e8/\u6295\u5f71 ${unique(g.length.observations.map(o=>number(o.value_m))).slice(0,3).join(' / ')}\uff1b\u6574\u6bb5\u672a\u77e5`:'\u672a\u77e5';}
function textDN(d){return positive(d.value_mm)?`DN${d.value_mm}`:d.status==='not_applicable'?'\u4e0d\u9002\u7528':d.status==='conflict'?'\u51b2\u7a81\uff0c\u8bf7\u6838\u9a8c':d.status==='segmented'?`\u5206\u6bb5 ${unique(d.observations.map(o=>`DN${o.value_mm}`)).join(' / ')}`:d.observations.length?`\u5c40\u90e8 ${unique(d.observations.map(o=>`DN${o.value_mm}`)).join(' / ')}\uff1b\u6574\u6bb5\u672a\u77e5`:'\u672a\u77e5';}
export async function initDirectionalAttributes(api){
 const manifest=await(await fetch('data/manifest.json')).json(),binding=manifest.directionalPipeAttributes;
 if(!binding)return;
 const response=await fetch(binding.path),bytes=await response.arrayBuffer();
 const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  if(hash!==binding.sha256)throw Error('Directional attributes changed');
 const doc=JSON.parse(new TextDecoder().decode(bytes)),by=new Map(doc.records.map(r=>[r.edge_id,r]));
 if(by.size!==api.data.edges.length||api.data.edges.some(e=>!by.has(e.edge_id)||by.get(e.edge_id).system!==e.system))throw Error('Directional edge inventory differs');
 api.data.directional_pipe_attributes=doc;
 const css=document.createElement('style');css.textContent='#directional-pipe-panel{margin:10px 0;border:1px solid #b8c9dc;border-radius:8px;background:#fff;padding:12px;font:13px Microsoft YaHei,sans-serif;line-height:1.7}#directional-pipe-panel h3{font-size:15px;margin:0 0 8px}#directional-pipe-panel table{width:100%;border-collapse:collapse}#directional-pipe-panel th,#directional-pipe-panel td{padding:6px;border-bottom:1px solid #e4ebf3;text-align:left}#directional-pipe-panel summary{cursor:pointer}#directional-pipe-panel button{margin:6px 4px 0 0;padding:6px}#directional-pipe-panel p{margin:6px 0;color:#586b80}';document.head.append(css);
 function current(e){return withManual(by.get(e.edge_id).pipe_attributes,api.reviewValues(e));}
 function download(name,doc){const u=URL.createObjectURL(new Blob([JSON.stringify(doc,null,2)],{type:'application/json;charset=utf-8'})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
 function render(){
  document.querySelector('#directional-pipe-panel')?.remove();
  const s=api.state.selection;if(s?.kind!=='edge')return;
  const e=api.model.edges.get(s.id),a=current(e),panel=document.createElement('section');panel.id='directional-pipe-panel';
  const cells=[[a.horizontal,'\u5e73\u9762\uff08\u6c34\u5e73\u6bb5\uff09','08\u201310'],[a.vertical,'\u5782\u76f4\u6bb5','11']];
  panel.innerHTML=`<h3>\u7ba1\u9053\u5c5e\u6027 \u00b7 ${esc(e.edge_id)}</h3><table><thead><tr><th>\u65b9\u5411</th><th>\u7ba1\u5f84</th><th>\u957f\u5ea6\uff08\u7c73\uff09</th></tr></thead><tbody>${cells.map(([g,label,sheet])=>`<tr><th>${label}</th><td>${esc(textDN(g.diameter))}</td><td>${esc(textLength(g))}</td></tr><tr><td colspan="3">\u6765\u6e90\uff1a${g.diameter.status==='manual_override'?'\u7ba1\u5f84\u4eba\u5de5\u4fee\u6b63\uff1b\u539f\u56fe\u6765\u6e90 ' : ''}${sheet}\u56fe${g.length.status==='partial'?'\uff1b\u4fdd\u7559\u5c40\u90e8\u957f\u5ea6\uff0f\u6295\u5f71\uff0c\u672a\u5145\u5f53\u6574\u6bb5\u957f\u5ea6':''}</td></tr>`).join('')}</tbody></table>
   ${a.unresolved_direction.segments.length?`<p>\u65b9\u5411\u5f85\u6838\u9a8c\uff1a${a.unresolved_direction.segments.length}\u4e2a\u6e90\u56fe\u6bb5\uff0c\u672a\u5f3a\u884c\u5f52\u5165\u5e73\u9762\u6216\u5782\u76f4\u3002</p>`:''}
   ${positive(a.whole_edge_manual.value_m)?`<p><b>\u4eba\u5de5\u6574\u8fb9\u957f\u5ea6\uff1a${number(a.whole_edge_manual.value_m)} m</b>\uff08\u672a\u81ea\u52a8\u5206\u914d\u5230\u4e24\u79cd\u65b9\u5411\uff09</p>`:''}
   <details><summary>\u5206\u6bb5\u7ba1\u5f84\u4e0e\u6765\u6e90\u503c</summary>${cells.map(([g,label])=>`<h4>${label}</h4><p>${g.segments.map(s=>`P${s.path_index+1}/S${s.segment_index+1}: ${textDN(s.diameter)}\uff0c\u957f\u5ea6\u672a\u77e5`).join('<br>')||'\u4e0d\u9002\u7528'}</p><p>${unique(g.diameter.observations.map(o=>`DN${o.value_mm} [${o.source_field}]`)).map(esc).join('<br>')}</p><p>${g.length.observations.map(o=>`${number(o.value_m)} m [${esc(o.source_field)}] \u00b7 ${esc(o.scope)}`).join('<br>')}</p>`).join('')}</details>
   <p>\u539f\u6709\u8bbe\u5907\u548c\u8fb9\u4e0a\u5143\u4ef6\u4fdd\u7559\uff1b\u672a\u77e5\u4e0d\u586b\u96f6\u3002\u8def\u7531\u4e2d\u5fc3\u7ebf\u957f\u5ea6\u4e0e\u51c0\u7ba1\u6750\u957f\u5ea6\u5206\u5f00\u3002</p><button id="download-directional-edge">\u5bfc\u51fa\u672c\u8fb9\u5c5e\u6027 JSON</button><button id="download-directional-graph">\u5bfc\u51fa\u5168\u56fe\u7edf\u4e00\u5c5e\u6027 JSON</button>`;
  document.querySelector('#detail-header .detail-title').after(panel);
  document.querySelector('#download-directional-edge').onclick=()=>download(e.edge_id+'-pipe-attributes.json',{edge_id:e.edge_id,pipe_attributes:current(e),equipment_inventory:e.equipment_inventory||[],component_instances:api.data.instances.filter(i=>i.edge_id===e.edge_id)});
  document.querySelector('#download-directional-graph').onclick=()=>download('SH16-11-directional-topology.json',{schema:doc.schema,source_bindings:doc.source_bindings,nodes:api.data.nodes,edges:api.data.edges.map(e=>({...e,pipe_attributes:current(e)})),component_instances:api.data.instances});
 }
 document.addEventListener('cad-details-changed',render);document.addEventListener('edge-review-saved',render);document.addEventListener('hil-document-updated',render);render();
}
