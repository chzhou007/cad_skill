import test from 'node:test';
import assert from 'node:assert/strict';
import {edgeAttributeProperties,edgeAttributeCsvFields,waveOmissionDescription,upstreamJointSystemProperties,nodeFloorRepairProperties} from '../assets/viewer/public/edge-attributes.js';
import {sourceAnnotationMarkup} from '../assets/viewer/public/native-rendering.js';
test('reconciled node floor remains distinct from cross-view path acceptance',()=>{
 const node={node_id:'T',floor:2,source_floor_reconciliation:{status:'source_main_caption_floor_label_reconciled',node_id:'T',from_floor:3,to_floor:2,physical_floor_verified:false,main_edge_ids:['A','B']}};
 const rows=nodeFloorRepairProperties(node,{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([k,v])=>k==='楼层标签修复'&&v==='3 → 2'));
 assert.ok(rows.some(([k,v])=>k==='校核范围'&&v.includes('跨图路径仍待核')));
 assert.deepEqual(nodeFloorRepairProperties({...node,floor:3},{}),[]);
 assert.deepEqual(nodeFloorRepairProperties({...node,node_id:'OTHER'},{}),[]);
});
test('upstream correction reports owner history and keeps physical length unknown',()=>{
 const record={status:'source_colour_error_resolved_by_confirmed_upstream_rule',to_edge:'E',from_edge:'R',system:'supply',joint_handle:'J',upstream_tee:'T',source_line_handles:['L'],confirmation:{rule:'expert_confirmed_no_system_change_follow_upstream_main',status:'user_confirmed'},physical_port_verified:false,physical_length:'unknown',original_device_name:'OLD/hose',device_name:'NEW/hose'};
 const e={edge_id:'E',system:'supply',source_inline_system_resolutions:[record]};
 const r=edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(r.some(([k,v])=>k==='软接系统校准'&&v.includes('J: 供水; T')));
 assert.ok(r.some(([k,v])=>k==='元件归属变更'&&v==='OLD/hose [R] → NEW/hose [E]'));
 assert.ok(r.some(([k,v])=>k==='物理端口与安装长度'&&v.includes('安装长度未知')));
 assert.deepEqual(upstreamJointSystemProperties({...e,system:'return'}),[]);
 assert.deepEqual(upstreamJointSystemProperties({...e,edge_id:'OTHER'}),[]);
 assert.deepEqual(upstreamJointSystemProperties({...e,source_inline_system_resolutions:[{...record,physical_length:0}]}),[]);
 assert.deepEqual(upstreamJointSystemProperties({...e,source_inline_system_resolutions:[{...record,confirmation:{}}]}),[]);
});
test('partial line evidence remains a candidate in drawing units',()=>{
 const edge={source_partial_line_evidence:{records:[{unique_source_drawing_length:230.4477,pieces:[{status:'unique_source_line',source_handles:['1556B']}]}]}};
 const rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([k,v])=>k==='局部源线重合候选'&&v.includes('230.45 图纸单位 [1556B]')));
 assert.ok(rows.some(([k,v])=>k==='局部证据状态'&&v.includes('实体长度待核')));
});
test('source Chinese labels and explicit missing diameter',()=>{
 const rows=edgeAttributeProperties({pipe_diameter:{},pipe_floor_location:{display_zh:'\u673a\u623f\u5c42'}},{display:{edge_attribute_language:'zh-CN'}});
 assert.equal(rows[0][0],'\u7ba1\u5f84');assert.equal(rows[1][1],'\u673a\u623f\u5c42');assert.match(rows[0][1],/\u5f85\u6838\u5b9e/);assert.ok(edgeAttributeCsvFields.includes('diameter_nominal_mm'));
});
test('native annotation escapes markup and preserves rotation and Chinese',()=>{
 const s=sourceAnnotationMarkup([{id:'a',text:'\u673a\u623f\u5c42<D',px:5,py:6,fontHeight:2,rotation:90,width_factor:0.6}]);assert.match(s,/\u673a\u623f\u5c42&lt;D/);assert.match(s,/x="0" y="0"/);assert.match(s,/transform="translate\(5 6\) rotate\(-90\) scale\(0\.6 1\)"/);assert.match(s,/font-size="2"/);
});
test('source named service is explicitly candidate and retains native text',()=>{
 const rows=edgeAttributeProperties({source_named_service:{display_zh:'\u8865\u6c34',witnesses:[{original_text:'DN125,\u51b7\u5374\u6c34\u7bb1\u8865\u6c34\u7ba1',label_handle:'AB'}]}},{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([k,v])=>k==='\u539f\u56fe\u8bed\u4e49\u5019\u9009'&&v==='\u8865\u6c34\uff08\u5f85\u6838\u5b9e\uff09'));
 assert.ok(rows.some(([,v])=>v.includes('DN125,\u51b7\u5374\u6c34\u7bb1\u8865\u6c34\u7ba1 [AB]')));
});
test('midpath source circle is visible without asserting a vertical connection',()=>{
 const edge={source_midpath_symbol_candidates:[{source_circle_handle:'5755'}]};
 const zh=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(zh.some(([k,v])=>k==='原图管中圆形标记'&&v==='5755'));
 assert.ok(zh.some(([k,v])=>k==='标记含义'&&v==='待核实；未推断竖向连接'));
 const en=edgeAttributeProperties(edge,{display:{edge_attribute_language:'en'}});
 assert.ok(en.some(([k,v])=>k==='Symbol meaning'&&v.includes('no vertical connection inferred')));
});
test('partial inline axis coverage is visible and does not assert continuity',()=>{
 const rows=edgeAttributeProperties({source_inline_axis_candidates:[{source_device_name:'NPV-1',status:'axis_projection_partial'}]},{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([k,v])=>k==='元件轴向投影'&&v.includes('NPV-1 (部分覆盖)')));
 assert.ok(rows.some(([k,v])=>k==='连通状态'&&v.includes('物理连通待核')));
});
test('crossover evidence distinguishes independent crossing from unknown elevation',()=>{
 const rows=edgeAttributeProperties({source_straight_crossover_evidence:{source_gap_id:'GAP-014',source_handles:['14771','14772'],crossed_handle:'12E28'}},{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([k,v])=>k==='交叉处关系'&&v.includes('交叉处不连接')));
 assert.ok(rows.some(([k,v])=>k==='跨越段实际长度及高差'&&v==='未知'));
});
test('builder crossover evidence exposes the same independent-crossing semantics',()=>{
 const rows=edgeAttributeProperties({source_normalized_crossovers:[{source_handles:['14771','14772'],crossings:[{crossed_handle:'12E28'}]}]},{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([k,v])=>k==='跨越证据'&&v.includes('14771 / 14772')&&v.includes('12E28')));
 assert.ok(rows.some(([k,v])=>k==='交叉处关系'&&v.includes('交叉处不连接')));
});
test('expert circle link exposes unknown projected length',()=>{
 const rows=edgeAttributeProperties({source_expert_circle_link:{expert_issue:'ERR-BB565D',circle_handle:'12F6C'}},{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([k,v])=>k==='专家圆圈接管'&&v.includes('12F6C')));
 assert.ok(rows.some(([k,v])=>k==='连接段实际长度'&&v.includes('不是实测管长')));
 const inferred=edgeAttributeProperties({source_expert_circle_link:{expert_issue:'ERR-BB565D',circle_handle:'12F6D',similar_location_inferred:true}},{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(inferred.some(([k,v])=>k==='证据状态'&&v.includes('待专家逐点复核')));
 assert.ok(!rows.some(([k])=>k==='证据状态'));
});

test('local source DN displays scope without reporting edge-wide nominal value',()=>{
 const edge={diameter_nominal_mm:null,diameter_status:'local_source_observation_edgewide_unverified',pipe_diameter:{nominal_mm:null,display:'DN300（标注处；整边待核）',observations:[{nominal_mm:300,text:{text:'DN300(3.200)',source_id:'09',handle:'B747'}}]}};
 const rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}});assert.ok(rows.some(([,v])=>v==='DN300（标注处；整边待核）'));assert.ok(rows.some(([,v])=>v.includes('DN300(3.200) [09:B747]')));assert.equal(edge.diameter_nominal_mm,null);
});

test('diameter inheritance candidate shows provenance and remains unverified',()=>{
 const edge={diameter_nominal_mm:null,pipe_diameter:{display:'DN300（T继承候选；待核）',observations:[]},diameter_inference:{lineage:[{source_text:'DN300(3.200)',source_text_handle:'B747',edge_path:['E0123','E0124']}]}};
 const rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}});assert.ok(rows.some(([,v])=>v.includes('DN300(3.200) [B747]: E0123 → E0124')));assert.ok(rows.some(([,v])=>v.includes('整段管径和继承待核')));assert.equal(edge.diameter_nominal_mm,null);
});

test('candidate export fields are explicitly named and distinct from authoritative DN',()=>{for(const k of ['diameter_nominal_mm','diameter_candidate_mm','diameter_candidate_status','diameter_candidate_lineage'])assert.ok(edgeAttributeCsvFields.includes(k));});

test('dimensioned segment is visible without claiming a whole-edge length',()=>{
 const edge={source_dimensioned_segments:[{dimension_handle:'12F9B',dimension_value_mm:2400,segment_index:1,edge_total_length_known:false}],physical_edge_length_status:'unknown_other_segments_or_geometry'};const rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([,v])=>v==='2400 mm [12F9B]'));assert.ok(rows.some(([k,v])=>k==='整边物理长度'&&v.includes('未知')));assert.ok(edgeAttributeCsvFields.includes('source_dimensioned_segments_json'));assert.ok(edgeAttributeCsvFields.includes('physical_edge_length_status'));
});

// Paired wave evidence is not automatically a confirmed connection.
{
 const pending={source_wave_omission:{human_accepted:false},connection_mode:'source_calibrated_wave_omission_unreviewed'};
 assert.match(waveOmissionDescription(pending),/\u5f85\u6838/);
 assert.match(waveOmissionDescription({...pending,source_wave_omission:{scoped_expert_convention_confirmed:true}}),/\u7ba1\u8def\u8fde\u7eed/);
 assert.match(waveOmissionDescription({...pending,connection_mode:'expert_confirmed_wave_schematic_continuity'}),/\u7ba1\u8def\u8fde\u7eed/);
 assert.equal(waveOmissionDescription({}),null);
}
