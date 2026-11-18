import test from 'node:test';
import assert from 'node:assert/strict';
import {edgeAttributeProperties,ownershipLengthScopeProperties,ownershipLengthScopeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';
const mode='calibrated_ownership_preserve_source_scopes_v2';
function fixture(){
 const prior={path_length_scope:'drawing_paths_excluding_source_crossover_gaps_physical_length_unknown'},r={edge_id:'E',equipment_id:'EQ',system:'supply',human_accepted:false,physical_port_verified:false,length_scope_composition:mode,prior_edge_length_scope:prior};
 const edge={edge_id:'E',system:'supply',start_node_id:'T',end_node_id:'EQ',path_length_scope:prior.path_length_scope,path_length_complete:false,physical_length:'unknown',equipment_connector_length_mm:null,equipment_connector_length_status:'unshown_interface_to_equipment_unknown',length_scope_evidence:[{kind:'inherited_local_edge_length_scope'},{kind:'source_calibrated_logical_ownership_connector'}],source_layout_equipment_interface:r};
 return {edge,data:{display:{edge_attribute_language:'zh-CN'},sourceLayoutEquipmentOwnership:{scope_composition_mode:mode,prior_edge_scopes_preserved:true,records:[structuredClone(r)]}}};
}
test('prior crossover scope and unknown connector are visible without a physical length claim',()=>{
 const {edge,data}=fixture(),before=structuredClone({edge,data}),rows=edgeAttributeProperties(edge,data),csv=ownershipLengthScopeCsvValues(edge,data);
 assert.ok(rows.some(([k,v])=>k==='保留的原图长度范围'&&v.includes('跨管断口')));assert.ok(rows.some(([k,v])=>k==='设备接管长度'&&v.includes('未知')));
 assert.equal(csv.equipment_connector_length_mm,'');assert.equal(csv.prior_length_scope,edge.path_length_scope);assert.equal(JSON.parse(csv.length_scope_evidence_json).length,2);
 assert.ok(edgeAttributeCsvFields.includes('length_scope_evidence_json'));assert.deepEqual({edge,data},before);
});
test('an absent old scope stays unknown and is not promoted to whole length',()=>{
 const {edge,data}=fixture();delete edge.source_layout_equipment_interface.prior_edge_length_scope.path_length_scope;data.sourceLayoutEquipmentOwnership.records=[structuredClone(edge.source_layout_equipment_interface)];
 assert.ok(ownershipLengthScopeProperties(edge,data).some(([k,v])=>k==='保留的原图长度范围'&&v.includes('未单独给出')));assert.equal(ownershipLengthScopeCsvValues(edge,data).prior_length_scope,'');
});
test('stale duplicated or conflicting records cannot display source-checked scope',()=>{
 for(const mode of ['root','scope','owner','system','record','duplicate','measured','complete','accepted']){
  const {edge,data}=fixture();
  if(mode==='root')delete data.sourceLayoutEquipmentOwnership;
  else if(mode==='scope')edge.path_length_scope='changed';
  else if(mode==='owner')edge.end_node_id='OTHER';
  else if(mode==='system')edge.system='return';
  else if(mode==='record')data.sourceLayoutEquipmentOwnership.records[0].prior_edge_length_scope={};
  else if(mode==='duplicate')data.sourceLayoutEquipmentOwnership.records.push(structuredClone(edge.source_layout_equipment_interface));
  else if(mode==='measured')edge.equipment_connector_length_mm=0;
  else if(mode==='complete')edge.path_length_complete=true;
  else edge.source_layout_equipment_interface.human_accepted=true;
  assert.deepEqual(ownershipLengthScopeProperties(edge,data),[],mode);assert.deepEqual(ownershipLengthScopeCsvValues(edge,data),{},mode);
 }
});
