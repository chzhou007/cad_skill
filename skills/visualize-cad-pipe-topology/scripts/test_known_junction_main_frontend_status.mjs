import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.dirname(fileURLToPath(import.meta.url));
const fixture=JSON.parse(fs.readFileSync(path.join(root,'../assets/regression/sh16-known-junction-main-frontend.json'),'utf8'));
const patched=await import(pathToFileURL(path.join(root,'../assets/viewer/public/anchored-floor-main-attributes.js')).href);
const attributes=await import(pathToFileURL(path.join(root,'../assets/viewer/public/edge-attributes.js')).href);
const samples=[];let rejected=0;
for(const edge of fixture.edges){
 const a=patched.checkedAnchoredMain(edge);assert.ok(a,edge.edge_id);assert.equal(a.nominal_mm,200);
 const properties=attributes.edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}});
 const csv=attributes.crossViewAttributeCsvValues(edge);
 assert.equal(properties[0][1],'DN200');assert.equal(csv.diameter_nominal_mm,200);
 assert.equal(csv.anchored_main_plan_XY_mm,a.horizontal_projection.value_mm);
 assert.equal(csv.anchored_main_plan_edges,a.plan_edges[0]);
 if(a.inline_interiors_unknown){assert.equal(csv.anchored_main_complete_centerline_mm,'');assert.equal(a.complete_horizontal_centerline_route_mm,null);}
 for(const mutate of [e=>e.anchored_floor_main_attributes.status='unverified_unknown_status',e=>e.anchored_floor_main_attributes.human_accepted=true,
   e=>e.system=e.system==='supply'?'return':'supply',e=>e.floor_end=99,e=>e.anchored_floor_main_attributes.installed_whole_edge_length_mm=0,
   e=>e.anchored_floor_main_attributes.parent_graph_sha256='wrong',e=>e.attribute_paths=[]]){
  const invalid=structuredClone(edge);mutate(invalid);assert.equal(patched.checkedAnchoredMain(invalid),null);assert.deepEqual(patched.anchoredMainCsvValues(invalid),{});rejected++;
 }
 assert.ok(!JSON.stringify(properties).includes('\ufffd'));
 samples.push({edge_id:edge.edge_id,nominal_mm:a.nominal_mm,plan_XY_mm:a.horizontal_projection.value_mm,inline_interiors_unknown:a.inline_interiors_unknown,properties,csv});
}
assert.equal(samples.length,4);assert.equal(rejected,28);
console.log('Four native-derived main scopes and28 invalid claims passed');
