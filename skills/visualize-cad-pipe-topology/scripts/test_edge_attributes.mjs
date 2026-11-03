import test from 'node:test';
import assert from 'node:assert/strict';
import {edgeAttributeProperties,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';
import {sourceAnnotationMarkup} from '../assets/viewer/public/native-rendering.js';
test('source Chinese labels and explicit missing diameter',()=>{
 const rows=edgeAttributeProperties({pipe_diameter:{},pipe_floor_location:{display_zh:'\u673a\u623f\u5c42'}},{display:{edge_attribute_language:'zh-CN'}});
 assert.equal(rows[0][0],'\u7ba1\u5f84');assert.equal(rows[1][1],'\u673a\u623f\u5c42');assert.match(rows[0][1],/\u5f85\u6838\u5b9e/);assert.ok(edgeAttributeCsvFields.includes('diameter_nominal_mm'));
});
test('native annotation escapes markup and preserves rotation and Chinese',()=>{
 const s=sourceAnnotationMarkup([{id:'a',text:'\u673a\u623f\u5c42<D',px:5,py:6,fontHeight:2,rotation:90}]);assert.match(s,/\u673a\u623f\u5c42&lt;D/);assert.match(s,/rotate\(-90 5 6\)/);assert.match(s,/font-size="2"/);
});
