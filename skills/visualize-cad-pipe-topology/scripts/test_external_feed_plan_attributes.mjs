import test from 'node:test';import assert from 'node:assert/strict';
import {checkedExternalFeed,externalFeedProperties,externalFeedCsvValues,checkedExternalBoundary,externalBoundaryLabel,externalBoundaryProperties} from '../assets/viewer/public/external-feed-plan-attributes.js';
import {createModel,canCross,traceNetwork} from '../assets/viewer/public/core.js';
import {edgeAttributeProperties,crossViewAttributeCsvValues,edgeAttributeCsvFields} from '../assets/viewer/public/edge-attributes.js';

function fixture(){
 const sources={plan:'d'.repeat(64),iso:'e'.repeat(64)},graphs={plan:'f'.repeat(64),iso:'1'.repeat(64)},destination='室外冷冻站';
 const node={node_id:'V',node_type:'virtual_equipment',subtype:'external_system_interface',floor:1,x:25,y:0,source_marker_handle:'M',ports:[]},edges=[],ports=[];
 for(let i=0;i<4;i++){
  const system=i%2?'return':'supply',identifier=(i%2?'CHWR':'CHWS')+(Math.floor(i/2)+1),pid='PORT'+i,x=10+i*10,eid='AXIS'+i,plan='PLAN'+i;
  const path=[[25,0],[x,0],[x,10],[x,20],[x,30]],r={axis_edge:eid,mapping_id:'MAP'+i,floor:1,system,identifier,destination,axis_boundary_node:'V',axis_port_id:pid,plan_boundary_node:'UT'+i,plan_edges:[plan],
   scope:'native_external_pipe_segments_only_excluding_marker_and_inline_gap',path_index:0,segment_indices:[1,3],scope_paths:structuredClone([path.slice(1,3),path.slice(3,5)]),display_only_segment_index:0,inline_gap_segment_indices:[2],
   nominal_mm:450,whole_axis_edge_DN_selected:false,physical_ports_verified:false,physical_external_connection_verified:false,external_ports_connected_to_each_other:false,human_accepted:false,related_HIL_confirmation_inherited:false,
   complete_horizontal_centerline_route_mm:null,installed_whole_edge_length_mm:null,pipe_net_cut_length_mm:null,mapping_sha256:'b'.repeat(64),source_scope_sha256:'c'.repeat(64),attribute_parent_graph_sha256:'a'.repeat(64),source_sha256:sources,local_graph_sha256:graphs};
  r.diameter_evidence={edge_id:plan,system,nominal_mm:450,scope:'source_checked_native_through_plan_pipe_paths_only',human_accepted:false,status:'direct_plan_DN',scope_paths:[[[0,0],[30,0]]],lineage:[{nominal_mm:450,evidence:[{evidence_id:'source:DN'+i,edge_path:[plan]}]}]};
  r.horizontal_projection={value_mm:30,installed_whole_edge_length_mm:null,unshown_connection_length_mm:null,inline_joint_interior_length_mm:null,joint_graphic_spans_added:false,pieces:[{plan_edge:plan,path_index:0,segment_index:0,source_line_handle:'LINE'+i,length_mm:30,points:[[0,0],[30,0]]}]};
  edges.push({edge_id:eid,system,floor_start:1,floor_end:1,start_node_id:'V',end_node_id:'T'+i,start_port_id:pid,attribute_paths:[path],external_feed_plan_attributes:r});
  node.ports.push({port_id:pid,node_id:'V',system,x,y:0,source_marker_handle:'M'});ports.push({port_id:pid,edge_id:eid,system,identifier,native_port_XYZ:[x,0,0]});
 }
 node.source_external_destination_context={status:'source_declared_destination_external_connectivity_unknown',destination,node_id:'V',floor:1,source_marker_handle:'M',native_node_position:[25,0],ports,
  source_sha256:sources,local_graph_sha256:graphs,mapping_sha256:'b'.repeat(64),attribute_scope_sha256:'c'.repeat(64),plan_destination_sha256:'2'.repeat(64),axis_destination_sha256:'3'.repeat(64),attribute_parent_graph_sha256:'a'.repeat(64),
  plan_caption_evidence:{text:'接至'+destination},axis_caption_evidence:{text:'接'+destination},direct_connection_between_ports:false,physical_equipment:false,physical_ports_verified:false,physical_external_connection_verified:false,human_accepted:false};
 return {node,edges};
}

test('source pipe450 and XY exclude marker and joint while whole length stays blank',()=>{
 const {node,edges}=fixture(),before=structuredClone(edges),e=edges[0];assert.ok(checkedExternalFeed(e));assert.deepEqual(edges,before);
 const csv=externalFeedCsvValues(e);assert.equal(csv.external_feed_pipe_nominal_mm,450);assert.equal(csv.external_feed_pipe_XY_mm,30);assert.equal(csv.external_feed_installed_whole_length_mm,'');assert.ok(!('diameter_nominal_mm' in csv));
 assert.match(JSON.stringify(externalFeedProperties(e)),/DN450/);assert.ok(checkedExternalBoundary(node,edges));assert.match(externalBoundaryLabel(node,edges),/室外冷冻站/);assert.match(externalBoundaryLabel(node,edges),/4路独立/);assert.ok(externalBoundaryProperties(node,edges).length>=5);
});
test('unknown plan DN is not filled from a known destination or other pipe',()=>{
 const {node,edges}=fixture(),r=edges[0].external_feed_plan_attributes;r.nominal_mm=null;Object.assign(r.diameter_evidence,{nominal_mm:null,status:'unresolved',lineage:[]});
 assert.ok(checkedExternalFeed(edges[0]));assert.equal(externalFeedCsvValues(edges[0]).external_feed_pipe_nominal_mm,'');assert.ok(checkedExternalBoundary(node,edges));assert.ok(!JSON.stringify(externalFeedProperties(edges[0])).includes('DN450'));
});
test('wrong geometry ownership hashes metric or physical claims cannot expose checked values',()=>{
 for(const change of [
  (e,r)=>r.segment_indices.push(0),(e,r)=>{e.attribute_paths[0][2][0]+=1},(e,r)=>{r.mapping_sha256='bad'},
  (e,r)=>{r.axis_port_id='other'},(e,r)=>{r.diameter_evidence.lineage[0].evidence[0].edge_path=['OTHER']},
  (e,r)=>{r.horizontal_projection.value_mm=31},(e,r)=>{r.horizontal_projection.joint_graphic_spans_added=true},
  (e,r)=>{r.installed_whole_edge_length_mm=0},(e,r)=>{r.external_ports_connected_to_each_other=true},(e,r)=>{r.human_accepted=true},(e,r)=>{e.cross_view_attributes={}},
 ]){const {node,edges}=fixture(),e=edges[0];change(e,e.external_feed_plan_attributes);assert.equal(checkedExternalFeed(e),null);assert.deepEqual(externalFeedCsvValues(e),{});assert.deepEqual(externalFeedProperties(e),[]);assert.equal(checkedExternalBoundary(node,edges),null);}
});
test('destination label requires every separate native port and source-backed feed',()=>{
 for(const change of [
  (n,e,c)=>{c.direct_connection_between_ports=true},(n,e,c)=>{c.physical_equipment=true},(n,e,c)=>{c.ports.pop()},
  (n,e,c)=>{n.ports[0].x+=1},(n,e,c)=>{c.axis_caption_evidence.text='elsewhere'},(n,e,c)=>{c.destination='elsewhere'},
  (n,e,c)=>{c.attribute_scope_sha256='0'.repeat(64)},(n,e,c)=>{e.push({...e[0],edge_id:'extra'})},
 ]){const {node,edges}=fixture();change(node,edges,node.source_external_destination_context);assert.equal(externalBoundaryLabel(node,edges),null);assert.deepEqual(externalBoundaryProperties(node,edges),[]);}
 assert.deepEqual(externalFeedProperties({}),[]);assert.deepEqual(externalFeedCsvValues({}),{});assert.equal(externalBoundaryLabel({},[]),null);
});

test('declared destination context never lets tracing cross the common virtual marker',()=>{
 const {node,edges}=fixture(),nodes=[node,...edges.map(e=>({node_id:e.end_node_id,node_type:'physical_junction',floor:1}))],model=createModel({nodes,edges,instances:[]});
 assert.ok(checkedExternalBoundary(node,edges));assert.equal(canCross(model,'V',edges[0],edges[2]),false);
 assert.equal(canCross(model,'V',edges[1],edges[3]),false);assert.equal(canCross(model,'V',edges[0],edges[1]),false);
 for(const e of edges)assert.deepEqual([...traceNetwork(model,e.edge_id)],[e.edge_id]);
});

test('actual edge property and CSV entries expose pipe scope without whole-edge physical values',()=>{
 const {edges}=fixture(),e=edges[0],before=structuredClone(e),properties=edgeAttributeProperties(e,{display:{edge_attribute_language:'zh-CN'}}),csv=crossViewAttributeCsvValues(e);
 assert.ok(properties[0][1].includes('DN450'));assert.ok(properties[0][1].includes('原管线范围'));assert.equal(properties[1][1],'1F');assert.deepEqual(e,before);
 assert.equal(csv.external_feed_pipe_nominal_mm,450);assert.equal(csv.external_feed_pipe_XY_mm,30);assert.equal(csv.external_feed_installed_whole_length_mm,'');assert.ok(edgeAttributeCsvFields.includes('external_feed_scope_json'));assert.ok(!Object.hasOwn(csv,'diameter_nominal_mm'));
 const old=structuredClone(e);delete old.external_feed_plan_attributes;assert.deepEqual(edgeAttributeProperties(old,{display:{edge_attribute_language:'zh-CN'}}),[]);assert.deepEqual(crossViewAttributeCsvValues(old),{});
});
