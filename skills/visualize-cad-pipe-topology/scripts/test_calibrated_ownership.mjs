import test from 'node:test';
import assert from 'node:assert/strict';
import {createModel,connectedEquipment,edgeContactEvidence} from '../assets/viewer/public/core.js';

function fixture(){
  const node={node_id:'EQ',node_type:'equipment',source_handle:'BODY',x:10,y:20};
  const edge={edge_id:'E',system:'supply',start_node_id:'T',end_node_id:'EQ',attribute_paths:[[[0,0],[5,0]]],path_length_complete:false};
  const record={equipment_id:'EQ',edge_id:'E',system:'supply',status:'source_calibrated_logical_ownership',source_sha256:'S',human_accepted:false,physical_port_verified:false,interface_to_equipment_length_known:false,
    endpoint_snapshot:{start_node_id:'T',end_node_id:'EQ',equipment_source_handle:'BODY',equipment_xy:[10,20],system:'supply',attribute_paths:structuredClone(edge.attribute_paths)}};
  edge.source_layout_equipment_interface=record;
  return createModel({nodes:[{node_id:'T',node_type:'physical_junction'},node],edges:[edge],instances:[],sourceLayoutEquipmentOwnership:{status:'native_calibrated_logical_ownership_source_checked',source_sha256:'S',physical_ports_verified:false,human_accepted:false,records:[structuredClone(record)]}});
}

test('logical owner is navigable while ports and installed length remain unknown',()=>{
  const m=fixture();assert.equal(connectedEquipment(m,new Set(['E'])).length,1);
  assert.match(edgeContactEvidence(m,m.edges.get('E')).end_contact_status,/\u7269\u7406\u7aef\u53e3/);
  assert.equal(m.edges.get('E').path_length_complete,false);
});

test('stale or forged ownership cannot enter legacy no-coverage shortcut',()=>{
  for(const change of [m=>m.edges.get('E').system='return',m=>m.nodes.get('EQ').x=11,m=>m.data.sourceLayoutEquipmentOwnership.records=[],m=>m.edges.get('E').attribute_paths[0][0]=[99,99],m=>m.edges.get('E').source_layout_equipment_interface.human_accepted=true]){
    const m=fixture();change(m);assert.equal(connectedEquipment(m,new Set(['E'])).length,0);
  }
});

test('native block source paths remain distinct from unknown physical connectors',()=>{
  const n={node_id:'EQ',node_type:'equipment'},paths=[[[0,0],[1,0]],[[5,0],[6,0]]];
  const e={edge_id:'E',system:'supply',start_node_id:'T',end_node_id:'EQ',attribute_paths:paths,path_length:2,path_length_complete:false,physical_length:'unknown'};
  e.source_native_block_branch={equipment_id:'EQ',system:'supply',source_sha256:'S',physical_port_verified:false,human_accepted:false,endpoint_snapshot:{start_node_id:'T',end_node_id:'EQ',system:'supply',attribute_paths:structuredClone(paths)}};
  const m=createModel({nodes:[{node_id:'T',node_type:'physical_junction'},n],edges:[e],instances:[],sourceNativeBlockBranchReconstruction:{status:'native_block_source_paths_reconstructed_hil_pending',source_sha256:'S',physical_ports_verified:false,human_accepted:false,records:[{edge_id:'E',equipment_id:'EQ',source_paths:structuredClone(paths)}]}});
  assert.equal(connectedEquipment(m,new Set(['E'])).length,1);
  assert.match(edgeContactEvidence(m,e).end_contact_status,/\u539f\u751f\u5757/);
  e.attribute_paths[1][1]=[9,9];assert.equal(connectedEquipment(m,new Set(['E'])).length,0);
});

test('source radius exclusion reuses immutable logical owner while current path stays exact',()=>{
  function normalizedFixture(){
    const m=fixture(),edge=m.edges.get('E'),before={start_node_id:edge.start_node_id,end_node_id:edge.end_node_id,system:edge.system,attribute_paths:structuredClone(edge.attribute_paths)};
    edge.attribute_paths=[[[2,0],[5,0]]];edge.physical_length='unknown';
    const row={edge_id:'E',source_sha256:'S',human_accepted:false,physical_connector_length:null,input_snapshot:before,
      output_snapshot:{...before,attribute_paths:structuredClone(edge.attribute_paths)}};
    edge.source_circle_path_normalization=row;
    m.data.sourceCirclePathNormalization={status:'native_circle_radius_excluded_local_topology_unchanged',source_sha256:'S',human_accepted:false,logical_connections_changed:false,records:[structuredClone(row)]};
    return m;
  }
  assert.equal(connectedEquipment(normalizedFixture(),new Set(['E'])).length,1);
  for(const change of [m=>m.data.sourceCirclePathNormalization.records=[],m=>m.edges.get('E').attribute_paths[0][0]=[99,99],
    m=>m.edges.get('E').source_circle_path_normalization.input_snapshot.system='return',m=>m.edges.get('E').physical_length=0,
    m=>m.data.sourceCirclePathNormalization.human_accepted=true]){
    const m=normalizedFixture();change(m);assert.equal(connectedEquipment(m,new Set(['E'])).length,0);
  }
});
