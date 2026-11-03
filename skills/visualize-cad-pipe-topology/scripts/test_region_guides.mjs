import test from 'node:test';import assert from 'node:assert/strict';
import {sourceRegionGuide}from '../assets/viewer/public/native-rendering.js';
test('side-by-side source panels retain different guide x positions',()=>{const n=[{floor:'L',px:10,py:20},{floor:'R',px:300,py:20}];assert.deepEqual(sourceRegionGuide('L',n,1),{x:10,y:12});assert.deepEqual(sourceRegionGuide('R',n,1),{x:300,y:12});});
test('unknown empty region has no guide',()=>assert.equal(sourceRegionGuide('Q',[],1),null));
test('stacked floor uses its own native range and scale',()=>assert.deepEqual(sourceRegionGuide('2',[{floor:'1',px:-80,py:500},{floor:2,px:20,py:0}],.5),{x:20,y:-4}));
