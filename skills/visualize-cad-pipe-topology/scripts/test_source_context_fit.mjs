import test from 'node:test';
import assert from 'node:assert/strict';
import {sourceContextPoints} from '../assets/viewer/public/core.js';
import {replaceGraphMarkup,pendingSourceObjectMarkup} from '../assets/viewer/public/native-rendering.js';
test('unassigned source geometry is local, native and never an edge',()=>{
 const object={id:'DPI-1',floor:'Roof',sourceGeometry:[{points:[[-1,5],[20,5]],fill:false}]};
 const main=pendingSourceObjectMarkup([object]);assert.ok(main.includes('DPI-1'));assert.ok(main.includes('edge ownership unconfirmed'));assert.ok(!main.includes('data-edge='));
 const pair=pendingSourceObjectMarkup([object],[0,0,10,10]);assert.ok(pair.includes('M0,5 L10,5'));assert.equal(pendingSourceObjectMarkup([object],null,'F1'),'');assert.equal(pendingSourceObjectMarkup([object],[100,0,10,10]),'');
});
test('pipe redraw retains the exact native building node and its visibility state',()=>{
 let attached=true,writes=0;
 const building={style:{display:'none'},children:[{id:'wall-1'}],remove(){attached=false;}};
 const svg={querySelector:()=>attached?building:null,set innerHTML(value){this.markup=value;attached=false;writes++;},insertBefore(node){assert.equal(node,building);attached=true;},firstChild:{id:'pipes'}};
 replaceGraphMarkup(svg,'pipes-1');replaceGraphMarkup(svg,'pipes-2');assert.equal(writes,2);assert.equal(attached,true);assert.equal(building.style.display,'none');assert.equal(building.children[0].id,'wall-1');assert.equal(svg.markup,'pipes-2');
 const empty={querySelector:()=>null,innerHTML:''};replaceGraphMarkup(empty,'pipes-only');assert.equal(empty.innerHTML,'pipes-only');
});
test('selected floor fit excludes distant unlocated context without guessing its floor',()=>{
 const paths=[{points:[[0,10000]]},{floor:'F1',points:[[10,20],[30,40]]},{floor:'F2',points:[[1,5000]]}];
 assert.deepEqual(sourceContextPoints(paths,'F1'),[[10,20],[30,40]]);
 assert.equal(sourceContextPoints(paths,'all').length,4);
 assert.deepEqual(sourceContextPoints(paths,'Roof'),[]);
});
