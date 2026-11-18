import test from 'node:test';import assert from 'node:assert/strict';
import {nativePaths,geometryBounds,portableObject,clipPaths,pointBounds,nativeObjectFocusBounds} from '../assets/viewer/public/native-rendering.js';
import {sourceTerminalMarkup,sourceAnnotationMarkup} from '../assets/viewer/public/native-rendering.js';
import {buildingDisplayLabel,buildingPairContext} from '../assets/viewer/public/architecture.js';
test('rotated source equipment text keeps width and remains visible when anchor lies outside crop',()=>{
 const r={id:'equipment-text-B385',text:'设备-1',px:5,py:50,fontHeight:5,rotation:90,width_factor:.6};
 const markup=sourceAnnotationMarkup([r],[0,30,10,10]);
 assert.ok(markup.includes('设备-1'));assert.ok(markup.includes('translate(5 50) rotate(-90) scale(0.6 1)'));
 assert.equal(sourceAnnotationMarkup([r],[500,500,10,10]),'');
});
test('building original Chinese labels stay readable and escaped in pair output',()=>{
 const row={id:'B1',label:'Source label B1',source_text:'不上人屋面 <东>',display_position:[5,5],display_text_bounds:[5,4,10,2],rotation:0,font_height:1,paths:[]};
 assert.equal(buildingDisplayLabel(row,true),'不上人屋面 <东>');assert.equal(buildingDisplayLabel(row,false),'Source label B1');
 const text=buildingPairContext({records:[row]},[0,0,20,20],true,true);assert.ok(text.includes('不上人屋面 &lt;东&gt;'));assert.ok(!text.includes('Source label B1'));
 const english=buildingPairContext({records:[row]},[0,0,20,20],true,false);assert.ok(english.includes('Source label B1'));
});
test('native terminal marks retain Chinese role and original geometry with floor/system filters',()=>{
 const glyph={id:'WAVE-1',node_id:'UT1',floor:'3',system:'return',sourceGeometry:[{points:[[-10,2],[10,2]],fill:false}]};
 const markup=sourceTerminalMarkup([glyph],[0,0,5,5],'3',new Set(['return']));
 assert.ok(markup.includes('Native wavy end mark'));assert.ok(markup.includes('M0,2 L5,2'));assert.ok(markup.includes('data-boundary-node="UT1"'));
 assert.equal(sourceTerminalMarkup([glyph],null,'2'),'');assert.equal(sourceTerminalMarkup([glyph],null,'all',new Set(['supply'])),'');assert.equal(sourceTerminalMarkup([glyph],[100,100,5,5]),'');
});
test('concentric candidate glyph retains source paths and does not claim remote connection',()=>{
 const glyph={id:'C1',node_id:'UT1',floor:'F1',system:'return',kind:'native_concentric_circle_candidate',sourceGeometry:[{points:[[0,0],[1,1]],fill:false}]};
 const markup=sourceTerminalMarkup([glyph],[0,0,5,5],'F1',new Set(['return']));assert.ok(markup.includes('Native concentric circles'));assert.ok(markup.includes('remote connection unconfirmed'));assert.ok(markup.includes('data-boundary-node="UT1"'));
});
test('minimum-sized bounds retain the actual source center',()=>{const b=pointBounds([[44,331],[45.5,331.7]],8);assert.ok(Math.abs(b[0]+b[2]/2-44.75)<1e-9);assert.ok(Math.abs(b[1]+b[3]/2-331.35)<1e-9);});
test('native instance focus uses full source geometry at its own scale',()=>{const obj={px:45,py:331,sourceX:45,sourceY:331,sourceGeometry:[{points:[[44,330.7],[45.5,331.4]]}]};const b=nativeObjectFocusBounds(obj);assert.ok(b[2]<2.5&&b[3]<2.5);assert.ok(b[0]<44&&b[0]+b[2]>45.5);assert.ok(Math.abs(b[0]+b[2]/2-44.75)<1e-9);});
test('native focus includes folded assignment and retains unverified fallback',()=>{const b=nativeObjectFocusBounds({px:10,py:20,sourceX:0,sourceY:0,sourceGeometry:[{points:[[0,0],[1,1]]}]});assert.ok(b[0]<=0&&b[0]+b[2]>=10&&b[1]+b[3]>=20);assert.equal(nativeObjectFocusBounds({px:0,py:0}),null);});
test('local pair omits distant CAD and clips long crossing segments',()=>{const paths=clipPaths([{points:[[-100,5],[100,5]],fill:false},{points:[[200,200],[300,300]],fill:false}],[0,0,10,10]);assert.equal(paths.length,1);assert.ok(Math.abs(paths[0].points[0][0])<1e-9);assert.ok(Math.abs(paths[0].points[1][0]-10)<1e-9);assert.ok(paths[0].points.every(p=>p[1]===5));});
test('filled source polygons are geometrically bounded, not hidden with a viewport',()=>{const p=clipPaths([{points:[[-100,-100],[100,-100],[100,100],[-100,100]],fill:true}],[0,0,10,10]);assert.equal(p.length,1);assert.ok(p[0].points.every(([x,y])=>x>=0&&x<=10&&y>=0&&y<=10));});
test('native geometry preserves coordinates and filled strokes',()=>{const p=[{points:[[100,200],[120,240]],fill:true}];const s=portableObject({id:'C1',sourceGeometry:p},.1);assert.ok(s.includes('M100,200 L120,240'));assert.ok(s.includes('fill="currentColor"'));assert.ok(s.includes('data-native="true"'));});
test('geometry extent includes object whose anchor is outside crop',()=>assert.deepEqual(geometryBounds({px:900,py:800,sourceGeometry:[{points:[[0,0],[20,30]]}]}),[0,0,20,30]));
test('missing native placement is explicit and source names escaped',()=>{const s=portableObject({id:'<script>',px:10,py:20,type:'V'},1);assert.ok(s.includes('native placement unverified'));assert.ok(!s.includes('<script>'));assert.ok(s.includes('stroke="currentColor"'));});
test('pair and main canvas use identical native path markup',()=>{const p=[{points:[[1,2],[3,4]],fill:false}];assert.ok(portableObject({id:'C',sourceGeometry:p},1).includes(nativePaths(p)));});

test('confirmed equipment interface keeps original glyph and discloses unknown physical port',()=>{
 const glyph={id:'CONFIRMED-V1',node_id:'D1',floor:'2',system:'supply',kind:'confirmed_equipment_interface',sourceGeometry:[{points:[[1,1],[3,1]],fill:false}]};
 const markup=sourceTerminalMarkup([glyph],[0,0,4,4],'2',new Set(['supply']));assert.ok(markup.includes('User-confirmed equipment interface'));assert.ok(markup.includes('physical port and connecting length unknown'));assert.ok(markup.includes('M1,1 L3,1'));assert.equal(sourceTerminalMarkup([glyph],null,'all',new Set(['return'])),'');
});

test('system conflict glyph retains original geometry without asserting resolution',()=>{
 const glyph={id:'CONFLICT-U',node_id:'U',floor:'3',system:'return',kind:'native_system_conflict',sourceGeometry:[{points:[[1,1],[3,1]],fill:false}]};const markup=sourceTerminalMarkup([glyph],[0,0,4,4],'3',new Set(['return']));assert.ok(markup.includes('systems conflict'));assert.ok(markup.includes('remote connection unconfirmed'));assert.ok(markup.includes('M1,1 L3,1'));assert.equal(sourceTerminalMarkup([glyph],null,'all',new Set(['supply'])),'');
});
