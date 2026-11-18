import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from normalized_near_tee_state_gate import check,verified_confirmations

class NormalizedNearTeeStateGateTest(unittest.TestCase):
 def setUp(self):
  self.event={'status':'applied','source_handles':['B'],'main_source_handles':['M'],'semantic_endpoint':[0,5]}
  self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'T','node_type':'tee','system':'supply','x':0,'y':5,'resolution_state':'source_contact_reconstructed_pending_comparison','review_required':True,'source_near_tee_evidence':{'source_sha256':'S','branch_handle':'B','main_handle':'M','incident_edge_ids':['0','1','2'],'human_accepted':False}}],'edges':[{'edge_id':str(i),'start_node_id':'T','system':'supply','source_handles':[h]} for i,h in enumerate(('M','M','B'))]}
 def test_pending_state_passes_without_acceptance(self):
  before=copy.deepcopy(self.g);r=check(self.g,[self.event],'S');self.assertEqual(before,self.g);self.assertFalse(r['hil_ready']);self.assertEqual(r['records'][0]['status'],'pending_state_present')
 def test_missing_state_and_stale_incidence_fail(self):
  del self.g['nodes'][0]['resolution_state']
  with self.assertRaisesRegex(ValueError,'pending state'):check(self.g,[self.event],'S')
  self.setUp();self.g['edges'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'pending state'):check(self.g,[self.event],'S')
 def test_no_matching_final_tee_is_explicitly_unverified(self):
  self.g['nodes']=[];r=check(self.g,[self.event],'S');self.assertEqual(r['records'][0]['status'],'no_matching_final_tee_not_verified')
 def test_pending_normalization_not_misclassified(self):
  self.event['status']='pending';self.assertEqual(check(self.g,[self.event],'S')['records'],[])
 def test_confirmation_flag_requires_native_artifacts(self):
  self.g['nodes'][0].update(resolution_state='source_contact_reconstructed_user_confirmed',review_required=False)
  with self.assertRaisesRegex(ValueError,'native replay'):check(self.g,[self.event],'S')
 def test_only_native_replayed_confirmations_are_allowed(self):
  self.g['nodes'][0].update(resolution_state='source_contact_reconstructed_user_confirmed',review_required=False)
  with patch('normalized_near_tee_state_gate.verified_confirmations',return_value={'T'}) as replay:
   result=check(self.g,[self.event],'S',confirmed_directory='artifacts')
   replay.assert_called_once_with('artifacts',self.g,[self.event],'S')
   self.assertEqual(result['records'][0]['status'],'explicit_confirmation_native_replayed')
  with patch('normalized_near_tee_state_gate.verified_confirmations',return_value=set()):
   with self.assertRaisesRegex(ValueError,'pending state'):check(self.g,[self.event],'S',confirmed_directory='artifacts')
 def test_changed_incidence_or_missing_confirmed_event_still_fails(self):
  self.g['nodes'][0].update(resolution_state='source_contact_reconstructed_user_confirmed',review_required=False)
  with patch('normalized_near_tee_state_gate.verified_confirmations',return_value={'T'}):
   with self.assertRaisesRegex(ValueError,'missing current'):check(self.g,[],'S',confirmed_directory='artifacts')
   self.g['edges'][0]['system']='return'
   with self.assertRaisesRegex(ValueError,'pending state'):check(self.g,[self.event],'S',confirmed_directory='artifacts')
 def test_replayed_event_tuples_equal_serialized_lists_but_changed_values_fail(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);normalization=root/'normalization.json'
   normalization.write_text(json.dumps({'near_junction':[self.event]}),encoding='utf8')
   (root/'graph_with_confirmed_near_tees.json').write_text(json.dumps(self.g),encoding='utf8')
   (root/'near-tee-confirmation-audit.json').write_text(json.dumps({'source_sha256':'S','normalization':str(normalization)}),encoding='utf8')
   event=copy.deepcopy(self.event);event['semantic_endpoint']=tuple(event['semantic_endpoint'])
   with patch('confirm_normalized_near_tees.verify_output',return_value={'T'}):
    self.assertEqual(verified_confirmations(root,self.g,[event],'S'),{'T'})
    event['semantic_endpoint']=(0,6)
    with self.assertRaisesRegex(ValueError,'differs from replay'):verified_confirmations(root,self.g,[event],'S')
if __name__=='__main__':unittest.main()
