import test from 'node:test';
import assert from 'node:assert/strict';
import {createModel,traceNetwork,shortestPath,inventory} from '../assets/viewer/public/core.js';
function fixture(){return createModel({nodes:[['A','equipment'],['T','physical_junction'],['B','equipment'],['U','physical_junction'],['C','equipment']].map(([node_id,node_type])=>({node_id,node_type})),edges:[['S','A','T','supply'],['P','T','U','unclassified_water'],['M','T','B','makeup_water'],['M2','B','C','makeup_water']].map(([edge_id,start_node_id,end_node_id,system])=>({edge_id,start_node_id,end_node_id,system,path_length:1})),instances:[]});}
test('supply trace cannot cross a mixed classification junction into pending or makeup',()=>assert.deepEqual([...traceNetwork(fixture(),'S')],['S']));
test('arbitrary configured system trace stops at equipment',()=>assert.deepEqual([...traceNetwork(fixture(),'M')],['M']));
test('same-system path cannot use pending segment to bridge supply',()=>assert.ok(shortestPath(fixture(),'A','U','supply').error));

test('one measurement component is reachable from both owners and counted once',()=>{const m=fixture();m.instancesByEdge.set('S',[{id:'D1',type:'DPA',label:'Pressure panel'}]);m.instancesByEdge.set('M',[{id:'D1',type:'DPA',label:'Pressure panel'}]);assert.equal(inventory(m,new Set(['M']))[0].instances.length,1);assert.equal(inventory(m,new Set(['S','M']))[0].instances.length,1);});
