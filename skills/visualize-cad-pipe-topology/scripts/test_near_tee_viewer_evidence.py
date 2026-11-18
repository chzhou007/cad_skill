import copy,unittest
from near_tee_viewer_evidence import attach

class NearTeeViewerEvidenceTest(unittest.TestCase):
 def setUp(self):
  self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'T','node_type':'tee','system':'supply','source_handles':['M','B']}],'edges':[{'edge_id':str(i),'start_node_id':'T','system':'supply','source_handles':[h]} for i,h in enumerate(('M','M','B'))]}
  self.s={'graph_sha256':'G','source_sha256':'S','script_sha256':'X','status':'applied_near_tees_pending_review','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':[{'node_id':'T','system':'supply','main_handle':'M','branch_handle':'B','incident_edge_ids':['0','1','2'],'status':'source_normalized_tee_not_human_accepted'}]}
 def test_viewer_copy_has_pending_state(self):
  before=copy.deepcopy(self.g);v=attach(self.g,self.s,'G','H','X');self.assertEqual(self.g,before);self.assertEqual(v['nodes'][0]['resolution_state'],'source_contact_reconstructed_pending_comparison');self.assertTrue(v['nodes'][0]['review_required'])
 def test_stale_or_mixed_fails_closed(self):
  with self.assertRaisesRegex(ValueError,'stale'):attach(self.g,self.s,'other','H','X')
  self.g['edges'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'incidence'):attach(self.g,self.s,'G','H','X')
 def test_review_and_ids_not_transferred(self):
  self.s['human_accepted']=True
  with self.assertRaisesRegex(ValueError,'stale'):attach(self.g,self.s,'G','H','X')
  self.s['human_accepted']=False;self.s['records'][0]['incident_edge_ids']=['0','1','3']
  with self.assertRaisesRegex(ValueError,'incidence'):attach(self.g,self.s,'G','H','X')
if __name__=='__main__':unittest.main()
