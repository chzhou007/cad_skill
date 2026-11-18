import test from 'node:test';
import assert from 'node:assert/strict';
import {equipmentIdentityCandidateProperties as props,equipmentIdentityResolutionProperties as resolved} from '../assets/viewer/public/equipment-identity-candidates.js';

test('unresolved paired candidates remain visibly unconfirmed',()=>{
 const rows=props({node_type:'equipment',identity_status:'unresolved',source_label_candidates:['CRAH-1','CRAH-2'],source_label_pair_evidence:{identity_confirmed:false}});
 assert.match(rows[0][1],/CRAH-1.*CRAH-2/);assert.match(rows[1][1],/未确认/);
});

test('resolved rotated source identity is visibly distinct from port acceptance',()=>{
 const node={node_type:'equipment',node_id:'CRAH-1',source_handle:'BODY',identity_status:'source_layout_identity_resolved_human_unreviewed',source_identity_evidence:{rule:'robust_rotated_caption_footprint',ports_inferred:false,human_accepted:false,record:{new_node_id:'CRAH-1',old_node_id:'EQ-SOURCE-BODY',source_handle:'BODY',label:'CRAH-1',source_text_handle:'TEXT',source_text_rotation:90}}};
 const rows=resolved(node);assert.match(rows[0][1],/已回证/);assert.match(rows[1][1],/90°/);assert.match(rows.at(-1)[1],/端口.*未确认/);assert.deepEqual(props(node),[]);
 const wrong=structuredClone(node);wrong.source_identity_evidence.record.new_node_id='OTHER';assert.deepEqual(resolved(wrong),[]);
 const accepted=structuredClone(node);accepted.source_identity_evidence.ports_inferred=true;assert.deepEqual(resolved(accepted),[]);
});
test('missing or confirmed provenance does not manufacture a candidate display',()=>{
 for(const n of [{node_type:'equipment',identity_status:'unresolved',source_label_candidates:['A','B']},{node_type:'equipment',identity_status:'confirmed',source_label_candidates:['A','B'],source_label_pair_evidence:{identity_confirmed:false}},{node_type:'equipment',identity_status:'unresolved',source_label_candidates:['A'],source_label_pair_evidence:{identity_confirmed:false}}])assert.deepEqual(props(n),[]);
});
