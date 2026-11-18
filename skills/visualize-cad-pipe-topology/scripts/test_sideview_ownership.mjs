import test from 'node:test';
import assert from 'node:assert/strict';
import {createModel,connectedEquipment,edgeContactEvidence} from '../assets/viewer/public/core.js';

function fixture(boundary=false){
  const node={node_id:'EQ',node_type:'equipment',source_handle:'BODY',floor:2,x:10,y:20};
  const edge={edge_id:'E',system:'supply',start_node_id:'T',end_node_id:'EQ',attribute_paths:[[[0,0],[5,0]]],physical_length:'unknown',path_length_complete:false,equipment_connector_length_mm:null};
  const original=boundary?{boundary_id:'V',legacy_node:{node_id:'OLD',floor:2}}:{node_id:'V',floor:2};
  const role={kind:'confirmed_detail_view',source_sha256:'S',input_graph_sha256:'P',confirmed_alias_root_sha256:'A',physical_length_from_drawing_span:false,metric_verified_by_this_stage:false};
  const record={equipment_id:'EQ',edge_id:'E',system:'supply',source_sha256:'S',input_graph_sha256:'P',sideview_root_sha256:'A',interface_side:'end',question_id:'Q',pair_sha256:'PAIR',human_accepted:false,physical_port_verified:false,interface_to_equipment_length_known:false,
    original_canonical_interface_id:'V',original_canonical_interface_kind:boundary?'non_node_boundary':'node',original_canonical_endpoint:original,endpoint_floor_evidence:{floor:2},body_evidence:{equipment_handle:'BODY'},
    source_alias:{canonical_edge:'E',canonical_interface:'V',canonical_interface_kind:boundary?'non_node_boundary':'node'},
    endpoint_snapshot:{start_node_id:'T',end_node_id:'EQ',equipment_source_handle:'BODY',equipment_xy:[10,20],system:'supply',attribute_paths:structuredClone(edge.attribute_paths)}};
  edge.source_sideview_equipment_interface=record;edge.source_view_context=role;
  const root={mode:'source_calibrated_confirmed_sideview_equipment_ownership_v1',source_sha256:'S',input_graph_sha256:'P',human_accepted:false,physical_ports_verified:false,records:[structuredClone(record)],
    retired_interface_nodes:boundary?[]:[structuredClone(original)],retired_boundary_anchors:boundary?[structuredClone(original)]:[],node_aliases:boundary?{}:{V:'EQ'},boundary_aliases:boundary?{V:'EQ'}:{},detail_edge_ids:['E']};
  return createModel({nodes:[{node_id:'T',node_type:'physical_junction'},node],edges:[edge],instances:[],metadata:{source_sha256:'S'},sourceSideviewEquipmentOwnership:root,
    confirmedSideviewCanonicalization:{records:[{canonical_edge:'E',canonical_interface:'V',canonical_interface_kind:record.original_canonical_interface_kind,question_id:'Q',pair_sha256:'PAIR',answer:{decision:'\u5bf9\u5e94\u540c\u4e00\u7ec4\u7ba1\u8def'}}]}});
}

test('both retired source endpoint roles retain logical equipment navigation and unknown metrics',()=>{
  for(const boundary of [false,true]){
    const m=fixture(boundary),edge=m.edges.get('E');
    assert.equal(connectedEquipment(m,new Set(['E'])).length,1);
    assert.match(edgeContactEvidence(m,edge).end_contact_status,/\u4e3b\u8be6\u56fe/);
    assert.equal(edge.equipment_connector_length_mm,null);assert.equal(edge.physical_length,'unknown');
  }
});

test('stale source owner alias and detail metric claims cannot use legacy no-coverage shortcut',()=>{
  const changes=[m=>m.data.sourceSideviewEquipmentOwnership.records=[],m=>m.data.sourceSideviewEquipmentOwnership.node_aliases={},
    m=>m.data.sourceSideviewEquipmentOwnership.input_graph_sha256='OTHER',m=>m.data.metadata.source_sha256='OTHER',
    m=>m.data.confirmedSideviewCanonicalization.records[0].pair_sha256='OTHER',m=>m.nodes.get('EQ').x=11,m=>m.nodes.get('EQ').floor=3,
    m=>m.edges.get('E').system='return',m=>m.edges.get('E').attribute_paths[0][0]=[9,9],
    m=>m.edges.get('E').source_view_context.metric_verified_by_this_stage=true,m=>m.edges.get('E').physical_length=0,
    m=>m.edges.get('E').equipment_connector_length_mm=0,m=>m.edges.get('E').source_sideview_equipment_interface=null,
    m=>m.data.sourceSideviewEquipmentOwnership.human_accepted=true,m=>m.data.sourceSideviewEquipmentOwnership.retired_interface_nodes=[]];
  for(const change of changes){const m=fixture();change(m);assert.equal(connectedEquipment(m,new Set(['E'])).length,0);}
});

test('non-node boundary needs preserved floor and alias evidence',()=>{
  for(const change of [m=>m.data.sourceSideviewEquipmentOwnership.boundary_aliases={},m=>m.data.sourceSideviewEquipmentOwnership.retired_boundary_anchors[0].legacy_node.floor=3,
    m=>m.data.boundary_anchors=[{boundary_id:'V'}]]){
    const m=fixture(true);change(m);assert.equal(connectedEquipment(m,new Set(['E'])).length,0);
  }
});
