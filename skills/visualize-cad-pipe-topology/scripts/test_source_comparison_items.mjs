import test from 'node:test';
import assert from 'node:assert/strict';
import {sourceComparisonItems,sourceComparisonBadge} from '../assets/viewer/public/source-comparison-items.js';

test('unassigned gap joint is visible as a candidate linked only for navigation',()=>{
 const items=sourceComparisonItems({pendingGapJoints:[{source_handles:['H'],candidate_edge_id:'E',ownership:'unconfirmed'}]});
 assert.deepEqual(items,[{kind:'gap_joint',id:'H',edge:'E'}]);
});

test('nested families and explicit source conflicts remain visible',()=>{
 const previous={families:[{id:'old',status:'pending'},{id:'repeat',status:'pending'}]};
 const data={preHilComparison:{families:[{id:'repeat',status:'pending'}],previous_comparison:previous},edges:[{edge_id:'E1',source_handles:['A']},{edge_id:'E2',source_handles:[]}],sourceCircleCrossoverConflicts:[{source_handles:['A','B'],circle_conflicts:[{circle_handle:'C'}]}],sourceInlineSystemConflicts:[{joint_handle:'J',assigned_edge_id:'E2',device_name:'D'}]};
 const items=sourceComparisonItems(data);assert.equal(items.length,4);assert.deepEqual(items.map(x=>x.id),['repeat','old','C','J']);assert.equal(items[2].edge,'E1');assert.equal(items[3].edge,'E2');
});
test('cyclic history terminates and missing graph edges stay unlinked',()=>{
 const history={families:[{id:'X'}]};history.previous_comparison=history;
 const items=sourceComparisonItems({preHilComparison:history,edges:[],sourceInlineSystemConflicts:[{joint_handle:'J',assigned_edge_id:'missing'}]});assert.equal(items.length,2);assert.equal(items[1].edge,null);
});

test('archived circle family is resolved only while current separate tees match',()=>{
 const d={metadata:{source_sha256:'s'},preHilComparison:{families:[{id:'circle_crossover_conflict',status:'pending'},{id:'other',status:'pending'}]},sourceCircleCrossoverConflicts:[],nodes:[],edges:[]};
 const connections=[];
 for(const i of [1,2]){
  const ev={circle_handle:'C'+i,branch_handle:'B'+i,user_evidence_manifest_sha256:'ev'};
  d.nodes.push({node_id:'T'+i,node_type:'tee',system:'supply',user_confirmed_overlap_connection:ev});
  d.edges.push({edge_id:'B'+i,start_node_id:'T'+i,end_node_id:'V'+i,system:'supply',user_confirmed_overlap_connection:ev},{edge_id:'M'+i,start_node_id:'T'+i,end_node_id:'X'+i,system:'supply'});
  connections.push({node_id:'T'+i,branch_edge:'B'+i,branch_handle:'B'+i,circle_handle:'C'+i,main_edges:['M'+i,'MID']});
 }
 d.edges.push({edge_id:'MID',start_node_id:'T1',end_node_id:'T2',system:'supply'});
 d.sourceCircleCrossoverConflictHistory=[{source_sha256:'s',connectivity_changed:false,evidence_manifest_sha256:'ev',records:[{resolution:'separate_confirmed_tees_on_native_main_not_collinear_gap',connections,native_main_edge:'MID'}]}];
 assert.deepEqual(sourceComparisonItems(d).map(x=>x.status),['resolved','pending']);
 const rendered=structuredClone(d);rendered.nodes.forEach(n=>n.node_type='physical_junction');assert.equal(sourceComparisonItems(rendered)[0].status,'resolved');
 for(const mutate of [x=>{x.edges[0].end_node_id='T2'},x=>{x.edges[0].system='return'},x=>{x.metadata.source_sha256='wrong'},x=>{x.sourceCircleCrossoverConflicts=[{}]},x=>{delete x.sourceCircleCrossoverConflictHistory}]){
  const changed=structuredClone(d);mutate(changed);assert.equal(sourceComparisonItems(changed)[0].status,'pending');
 }
 assert.equal(d.preHilComparison.families[0].status,'pending');
});

test('empty comparison list stays pending and nonempty count is only loaded items',()=>{
 assert.equal(sourceComparisonBadge([]),'\u5f85\u5bf9\u7167');
 assert.equal(sourceComparisonBadge([{id:'A'},{id:'B'}]),'2');
});

test('named leader candidate is visible with node and source handles',()=>{
 const rows=sourceComparisonItems({sourceNamedEndpointLeaderCandidates:[{node_id:'U',pipe_handle:'P',leader_handle:'L',text_handle:'T',label:{original_text:'CHWS1 DN450'}}]});
 assert.deepEqual(rows[0],{kind:'named_leader',id:'U',node:'U',label:'CHWS1 DN450',pipe:'P',leader:'L',text:'T'});
});

test('repeated plan lines stay pending as one navigable group with all source handles',()=>{
 const data={pendingPlanLineGroups:[{id:'MICRO-001',status:'pending_source_comparison',members:[{source_handle:'A',node_id:'T1'},{source_handle:'B',node_id:'T2'}]}]};
 assert.deepEqual(sourceComparisonItems(data),[{kind:'plan_line_group',id:'MICRO-001',members:[{handle:'A',node:'T1'},{handle:'B',node:'T2'}],count:2}]);
});
