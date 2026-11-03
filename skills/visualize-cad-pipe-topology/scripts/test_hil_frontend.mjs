import test from 'node:test';
import assert from 'node:assert/strict';
import {polylineIntersects} from '../assets/viewer/public/hil.js';

const box=[0,0,10,10];
test('crossing segment with both endpoints outside is included',()=>assert.equal(polylineIntersects([[-5,5],[15,5]],box),true));
test('diagonal with overlapping bbox but no actual intersection is excluded',()=>assert.equal(polylineIntersects([[-5,8],[8,15]],box),false));
test('vertical pipe and reversed endpoints are supported',()=>assert.equal(polylineIntersects([[5,20],[5,-20]],box),true));
test('exact boundary touch is included',()=>assert.equal(polylineIntersects([[-5,0],[0,0]],box),true));
test('parallel outside pipe is excluded',()=>assert.equal(polylineIntersects([[-5,12],[15,12]],box),false));
test('polyline with a later intersecting span is included',()=>assert.equal(polylineIntersects([[-20,-20],[-10,3],[5,3]],box),true));
test('empty geometry does not claim coverage',()=>assert.equal(polylineIntersects([],box),false));
test('negative coordinates and tiny drawing units are supported',()=>assert.equal(polylineIntersects([[-.003,-.002],[.001,.002]],[-.001,-.001,.002,.002]),true));
