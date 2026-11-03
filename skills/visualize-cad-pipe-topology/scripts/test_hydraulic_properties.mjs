import test from 'node:test';
import assert from 'node:assert/strict';
import {hydraulicProperties} from '../assets/viewer/public/core.js';
test('missing equipment parameters never imply zero resistance',()=>{const p=Object.fromEntries(hydraulicProperties({node_type:'equipment'}));assert.equal(p['Resistance parameters'],'Required');assert.equal(p['Zero resistance'],'Not assumed');});
test('included calculation equipment preserves required parameter state',()=>{const p=Object.fromEntries(hydraulicProperties({node_type:'equipment',hydraulic_model:{included:true,resistance_status:'parameter_required'}}));assert.equal(p['Calculation scope'],'Included');assert.equal(p['Resistance parameters'],'Required');});
test('virtual boundaries are not equipment resistance models',()=>assert.deepEqual(hydraulicProperties({node_type:'virtual_equipment'}),[]));
