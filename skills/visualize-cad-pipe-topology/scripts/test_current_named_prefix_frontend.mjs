import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {checkedCurrentNamedPrefix,currentNamedPrefixProperties,currentNamedPrefixCsvFields,currentNamedPrefixCsvValues} from '../assets/viewer/public/current-named-prefix-evidence.js';
import {edgeAttributeProperties,crossViewAttributeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';
const root=path.dirname(fileURLToPath(import.meta.url));
const fixture=JSON.parse(fs.readFileSync(path.join(root,'../assets/regression/current-named-prefix-native.json'),'utf8'));

test('four actual native-bridge scopes display current provenance without changing old values',()=>{
 assert.equal(fixture.edges.length,4);
 for(const edge of fixture.edges){
  const before=structuredClone(edge),old=structuredClone(edge);delete old.current_named_prefix_source_evidence;
  assert.ok(checkedCurrentNamedPrefix(edge),edge.edge_id);
  const rows=edgeAttributeProperties(edge,{display:{edge_attribute_language:'zh-CN'}});
  assert.ok(rows.some(r=>r[0]==='当前平面源图复核'),edge.edge_id);
  assert.ok(rows.some(r=>r[1].includes('人工验收待完成')));
  const csv=crossViewAttributeCsvValues(edge),previous=crossViewAttributeCsvValues(old);
  for(const [key,value] of Object.entries(previous))assert.deepEqual(csv[key],value,edge.edge_id+'/'+key);
  assert.equal(csv.named_prefix_mapping_id,edge.plan_segment_attributes[0].mapping_id);
  assert.equal(csv.named_prefix_current_plan_graph_sha256,edge.current_named_prefix_source_evidence.current_plan_graph_sha256);
  assert.deepEqual(edge,before);
 }
 for(const key of currentNamedPrefixCsvFields)assert.ok(edgeAttributeCsvFields.includes(key));
});

test('JSON serialization retains evidence and mixed vertical unknowns',()=>{
 for(const original of fixture.edges){
  const edge=JSON.parse(JSON.stringify(original));
  assert.ok(checkedCurrentNamedPrefix(edge));
  assert.deepEqual(edge.axis_riser_attributes,original.axis_riser_attributes);
  if(!edge.plan_segment_attributes[0].whole_local_edge){
   assert.equal(crossViewAttributeCsvValues(edge).diameter_nominal_mm,'');
   assert.equal(edge.plan_segment_attributes[0].whole_edge_centerline_route_mm,null);
  }
 }
});

test('wrong source, service, mapping or accepted-state claims are rejected',()=>{
 const fields={source_sha256:'9'.repeat(64),historical_plan_graph_sha256:'9'.repeat(64),
  original_mapping_sha256:'9'.repeat(64),historical_attribute_scope_sha256:'9'.repeat(64),
  native_prefix_bridge_sha256:'not-a-hash',axis_edge:'other',system:'unknown',floor:99,
  mapping_id:'other',values_replaced:true,human_accepted:true,physical_ports_verified:true,
  related_HIL_confirmation_inherited:true,native_DN_XY_and_source_paths_preserved:false};
 for(const [field,value] of Object.entries(fields)){
  const edge=structuredClone(fixture.edges[0]);edge.current_named_prefix_source_evidence[field]=value;
  assert.equal(checkedCurrentNamedPrefix(edge),null,field);
  assert.deepEqual(currentNamedPrefixCsvValues(edge),{},field);
 }
});

test('missing new evidence preserves historical display while changed scope geometry is blocked',()=>{
 const edge=structuredClone(fixture.edges[0]);delete edge.current_named_prefix_source_evidence;
 assert.deepEqual(currentNamedPrefixProperties(edge),[]);
 assert.equal(crossViewAttributeCsvValues(edge).plan_segment_nominal_mm,300);
 const changed=structuredClone(fixture.edges[0]);
 const scope=changed.plan_segment_attributes[0];changed.attribute_paths[scope.path_index][scope.segment_indices[0]][0]+=100;
 assert.equal(checkedCurrentNamedPrefix(changed),null);
});

test('public template uses ASCII escapes and renders readable Chinese',()=>{
 const text=fs.readFileSync(path.join(root,'../assets/viewer/public/current-named-prefix-evidence.js'),'utf8');
 assert.ok([...text].every(c=>c.charCodeAt(0)<128));
 assert.ok(currentNamedPrefixProperties(fixture.edges[0]).some(r=>r[0]==='当前平面版本'));
});
