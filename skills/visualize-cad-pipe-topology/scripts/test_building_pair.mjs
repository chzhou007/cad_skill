import test from 'node:test';import assert from 'node:assert/strict';
import {buildingPairContext,buildingPointBounds} from '../assets/viewer/public/architecture.js';
const row={id:'W1',paths:[{display_points:[[-100,5],[100,5]],fill:false}]};
test('large actual-plan point sets fit without an argument-stack overflow',()=>{const points=Array.from({length:300000},(_,i)=>[i,-i]);assert.deepEqual(buildingPointBounds(points),[-10,-300009,300019,300019]);assert.equal(buildingPointBounds([]),null);});
test('building pair clips source geometry to crop',()=>{const s=buildingPairContext({records:[row]},[0,0,10,10]);const d=s.match(/d="(M[^"]+)"/)[1],numbers=d.match(/[-+]?[\d.]+/g).map(Number);assert.ok(Math.abs(numbers[0])<1e-8);assert.ok(Math.abs(numbers[2]-10)<1e-8);assert.ok(!s.includes('-100'));});
test('distant room labels are absent and text is escaped',()=>{const r={id:'R1',label:'Room <1>',display_position:[5,5],rotation:0,font_height:2,paths:[]};const s=buildingPairContext({records:[r,{...r,id:'R2',display_position:[100,100]}]},[0,0,10,10]);assert.ok(s.includes('Room &lt;1&gt;'));assert.ok(!s.includes('R2'));});
test('pair building context ignores hidden viewer controls',()=>assert.ok(buildingPairContext({records:[row]},[0,0,10,10]).includes('W1')));
test('legacy graph without building context is supported',()=>assert.equal(buildingPairContext(null,[0,0,10,10]),''));
test('partially visible label whose anchor is outside crop is retained',()=>{const r={id:'R1',label:'Corridor',display_position:[-5,5],display_text_bounds:[-5,3,20,3],rotation:0,font_height:2,paths:[]};assert.ok(buildingPairContext({records:[r]},[0,0,10,10]).includes('Corridor'));});
