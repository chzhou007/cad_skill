import test from 'node:test';
import assert from 'node:assert/strict';
import {edgeAttributeProperties,crossViewAttributeProperties,crossViewAttributeCsvValues,checkedPlanDiameterScope,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';
const fixture=()=>({pipe_diameter:{display:'DN65'},cross_view_attributes:{status:'partial_plan_attributes_source_checked',mapping_id:'CV-1',plan_edges:['P'],source_hashes:{plan:'SOURCE'},
 horizontal_projection:{edge_value_mm:2175.5,allocation:'whole_mapped_axis_edge_projection',pieces:[{plan_edge:'P',source_line_handle:'LINE'}]},
 diameter:{status:'candidate_disagreement_unresolved',nominal_mm:null,plan_candidate:{nominal_mm:300,text:'DN300',handle:'PLAN'},axis_observation:{nominal_mm:65,text:'DN65',handle:'AXIS'}},axis_vertical_drawing_strokes:[{physical_length_mm:null}]}});
test('plan projection is displayed with source while axis DN is not selected',()=>{
 const edge=fixture(),before=structuredClone(edge),rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([key,value])=>key==='平面水平投影长度'&&value.includes('2.1755 m')));
 assert.ok(rows.some(([key,value])=>key==='长度证据'&&value==='P / LINE'));
 assert.ok(rows.some(([key,value])=>key==='整边物理长度'&&value.includes('未知')));
 assert.ok(rows.some(([key,value])=>key==='轴测竖线范围'&&value.includes('不按跨层管长取值')));
 assert.notEqual(rows[0][1],'DN65');assert.deepEqual(edge,before);
});
test('CSV keeps whole edge length and nominal DN blank rather than zero',()=>{
 const row=crossViewAttributeCsvValues(fixture());assert.equal(row.crossview_plan_horizontal_projection_mm,2175.5);
 assert.equal(row.diameter_nominal_mm,'');assert.equal(row.crossview_whole_edge_length_mm,'');
 assert.equal(row.crossview_plan_diameter_candidate_mm,300);assert.equal(row.crossview_axis_diameter_observation_mm,65);
});
test('one-to-many route totals are not repeated as individual edge lengths',()=>{
 const edge=fixture();edge.cross_view_attributes.horizontal_projection.edge_value_mm=null;
 edge.cross_view_attributes.horizontal_projection.allocation='route_total_only_not_allocated_to_each_axis_edge';
 assert.equal(crossViewAttributeCsvValues(edge).crossview_plan_horizontal_projection_mm,'');
 assert.ok(crossViewAttributeProperties(edge).some(([key,value])=>key==='平面水平投影长度'&&value.includes('未分配到本边')));
});
test('ordinary edges retain existing attribute behavior',()=>{
 assert.deepEqual(crossViewAttributeProperties({}),[]);assert.deepEqual(crossViewAttributeCsvValues({}),{});
 assert.equal(edgeAttributeProperties({pipe_diameter:{display:'DN80'}},{})[0][1],'DN80');
});

test('source checked DN observation remains local and technical basis is explicit',()=>{
 const edge=fixture();edge.cross_view_attributes.mapping_basis='native_source_and_main_branch_order';
 edge.cross_view_attributes.diameter.plan_candidate.scope='local_source_observation';
 const rows=crossViewAttributeProperties(edge);
 assert.ok(rows.some(([key,value])=>key==='平面管径候选'&&value.includes('局部标注')));
 assert.ok(rows.some(([key,value])=>key==='对应依据'&&value.includes('人工验收待完成')));
 assert.equal(crossViewAttributeCsvValues(edge).diameter_nominal_mm,'');
});

const scopedFixture=()=>{
 const edge=fixture(),c=edge.cross_view_attributes;
 Object.assign(c,{human_accepted:false,system:'supply',mapping_kind:'main_between_equipment_branches',iso_edges:['I'],plan_DN_scope_evidence_sha256:'a'.repeat(64),whole_axis_main_scope:'source_checked_plan_native_T_to_T_horizontal_main',whole_edge_physical_length_mm:2175.5,whole_edge_length_kind:'floor_plan_horizontal_main_centerline_route',whole_edge_length_scope:'complete_mapped_T_to_T_centerline_route_not_pipe_net_cut_length',pipe_net_cut_length_mm:null});
 c.source_hashes.plan='b'.repeat(64);c.horizontal_projection.route_scope_status='complete_mapped_horizontal_main_centerline';
 Object.assign(c.diameter,{plan_scope_evidence_sha256:'a'.repeat(64),plan_drawn_nominal_mm:200,nominal_mm:200,plan_drawn_status:'source_checked_plan_DN_scope_human_pending',status:'source_checked_whole_horizontal_main_DN',selected_physical_diameter:true,
 plan_drawn_values:[{edge_id:'P',system:'supply',nominal_mm:200,scope:'native_plan_drawn_pipe_paths_only',human_accepted:false,lineage:[{evidence:[{evidence_id:'source:TXT',edge_path:['P0','P']}]}]}]});
 return edge;
};

test('checked horizontal main exposes plan DN and centerline route with cut-length caveat',()=>{
 const edge=scopedFixture(),before=structuredClone(edge),rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}}),csv=crossViewAttributeCsvValues(edge);
 assert.equal(rows[0][1],'DN200');assert.ok(rows.some(([k,v])=>k==='水平主管中心线路径长度'&&v.includes('2.1755 m')));
 assert.ok(rows.some(([k,v])=>k==='长度范围'&&v.includes('净下料')));assert.ok(rows.some(([k,v])=>k==='平面管径继承依据'&&v==='source:TXT: P0 -> P'));
 assert.equal(csv.diameter_nominal_mm,200);assert.equal(csv.diameter_text,'DN200');assert.equal(csv.crossview_whole_edge_length_mm,2175.5);
 assert.equal(csv.crossview_whole_edge_length_kind,'floor_plan_horizontal_main_centerline_route');assert.equal(csv.crossview_plan_drawn_nominal_mm,200);assert.deepEqual(edge,before);
});

test('drawn branch scope has positive plan DN but never invents unseen connector diameter or length',()=>{
 const e=scopedFixture(),c=e.cross_view_attributes;Object.assign(c,{mapping_kind:'equipment_branch',whole_axis_main_scope:null,whole_edge_physical_length_mm:null});Object.assign(c.diameter,{nominal_mm:null,status:'source_checked_plan_DN_axis_extent_partial',selected_physical_diameter:false});
 const rows=edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'}}),csv=crossViewAttributeCsvValues(e);
 assert.ok(rows[0][1].includes('DN200'));assert.ok(rows[0][1].includes('整边范围待定'));assert.equal(csv.crossview_plan_drawn_nominal_mm,200);assert.equal(csv.diameter_nominal_mm,'');assert.equal(csv.crossview_whole_edge_length_mm,'');
});

test('stale source scopes cannot become a selected DN or length',()=>{
 for(const variant of ['hash','source','system','rowDN','rowScope','rowHuman','duplicate','owner','human','zero','nonfinite']){
  const e=scopedFixture(),c=e.cross_view_attributes,d=c.diameter;
  if(variant==='hash')d.plan_scope_evidence_sha256='changed';
  else if(variant==='source')c.source_hashes.plan='missing';
  else if(variant==='system')d.plan_drawn_values[0].system='return';
  else if(variant==='rowDN')d.plan_drawn_values[0].nominal_mm=65;
  else if(variant==='rowScope')d.plan_drawn_values[0].scope='whole_pipe';
  else if(variant==='rowHuman')d.plan_drawn_values[0].human_accepted=true;
  else if(variant==='duplicate')d.plan_drawn_values.push(structuredClone(d.plan_drawn_values[0]));
  else if(variant==='owner')d.plan_drawn_values[0].edge_id='other';
  else if(variant==='human')c.human_accepted=true;
  else if(variant==='zero')d.plan_drawn_nominal_mm=0;
  else d.plan_drawn_nominal_mm=NaN;
  assert.equal(checkedPlanDiameterScope(c),null,variant);const row=crossViewAttributeCsvValues(e);assert.equal(row.diameter_nominal_mm,'',variant);assert.equal(row.crossview_whole_edge_length_mm,'',variant);
 }
});

test('partial allocation or mismatched route length never upgrades the full edge',()=>{
 for(const variant of ['multiple','wrongDN','selected','length','netCut']){
  const e=scopedFixture(),c=e.cross_view_attributes;
  if(variant==='multiple')c.iso_edges.push('I2');
  else if(variant==='wrongDN')c.diameter.nominal_mm=65;
  else if(variant==='selected')c.diameter.selected_physical_diameter=false;
  else if(variant==='length')c.whole_edge_physical_length_mm=100;
  else c.pipe_net_cut_length_mm=0;
  const row=crossViewAttributeCsvValues(e);assert.equal(row.crossview_whole_edge_length_mm,'',variant);
  if(['multiple','wrongDN','selected'].includes(variant))assert.equal(row.diameter_nominal_mm,'',variant);
 }
 assert.ok(edgeAttributeCsvFields.includes('crossview_plan_drawn_nominal_mm'));assert.ok(edgeAttributeCsvFields.includes('crossview_whole_edge_length_kind'));
});
