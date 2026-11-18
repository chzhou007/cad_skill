import test from 'node:test';
import assert from 'node:assert/strict';
import {crossViewAttributeProperties,crossViewAttributeCsvValues} from '../assets/viewer/public/edge-attributes.js';
const fixture=()=>({cross_view_attributes:{status:'partial_plan_attributes_source_checked',mapping_basis:'native_paired_service_corridors',mapping_id:'PS-1',plan_edges:['P'],source_hashes:{plan:'SOURCE'},
 horizontal_projection:{edge_value_mm:2500,allocation:'whole_mapped_axis_edge_projection',pieces:[{plan_edge:'P',source_line_handle:'LINE'}]},
 diameter:{status:'source_checked_plan_DN_axis_extent_partial',nominal_mm:null,plan_drawn_nominal_mm:200,plan_observations:[]},whole_edge_physical_length_mm:null,axis_vertical_drawing_strokes:[]}});
test('paired proof is stated separately and does not claim three-anchor order or acceptance',()=>{
 const edge=fixture(),before=structuredClone(edge),rows=crossViewAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}});
 assert.ok(rows.some(([k,v])=>k==='对应依据'&&v.includes('成对设备')&&v.includes('待完成')));
 assert.ok(!rows.some(([,v])=>v.includes('分支顺序已校验')));assert.deepEqual(edge,before);
});
test('paired evidence does not manufacture whole DN or connector length',()=>{
 const row=crossViewAttributeCsvValues(fixture());assert.equal(row.diameter_nominal_mm,'');assert.equal(row.crossview_whole_edge_length_mm,'');
 assert.equal(row.crossview_plan_horizontal_projection_mm,2500);
});
test('multi-edge paired route totals remain unallocated at each axis edge',()=>{
 const edge=fixture();edge.cross_view_attributes.horizontal_projection.edge_value_mm=null;
 edge.cross_view_attributes.horizontal_projection.allocation='route_total_only_not_allocated_to_each_axis_edge';
 const row=crossViewAttributeCsvValues(edge);assert.equal(row.crossview_plan_horizontal_projection_mm,'');assert.equal(row.crossview_whole_edge_length_mm,'');
});
