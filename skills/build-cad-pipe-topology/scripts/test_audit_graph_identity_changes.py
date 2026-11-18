import copy,unittest
from audit_graph_identity_changes import audit

class IdentityAuditTest(unittest.TestCase):
 def setUp(self):
  self.h={'source_sha256':'s','old_graph_sha256':'a','new_graph_sha256':'b'};self.p=dict(self.h);self.a={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'T1','node_type':'tee','floor':1,'system':'supply','x':0,'y':0},{'node_id':'T2','node_type':'tee','floor':1,'system':'supply','x':10,'y':0}],'edges':[{'edge_id':'E1','system':'supply','source_handles':['H'],'path':[[0,0],[10,0]]}]};self.b=copy.deepcopy(self.a);self.b['nodes'][0]['node_id']='T9';self.b['edges'][0]['edge_id']='E9'
 def run_it(self):return audit(self.a,self.b,self.p,self.h)
 def test_unique_candidates_do_not_transfer_review(self):
  before=copy.deepcopy((self.a,self.b));r=self.run_it();self.assertEqual(r['edges']['candidates'][0]['new_id'],'E9');self.assertEqual(r['nodes']['candidates'][0]['new_id'],'T9');self.assertFalse(r['human_accepted']);self.assertEqual((self.a,self.b),before)
 def test_reused_id_with_different_geometry_is_explicit(self):
  self.b['edges'][0]['edge_id']='E1';self.b['edges'][0]['path']=[[0,0],[5,0]];r=self.run_it();self.assertEqual(r['edges']['same_id_different_or_unknown_signature'],['E1']);self.assertEqual(r['edges']['old_unmatched_ids'],['E1'])
 def test_parallel_identical_paths_are_not_assigned(self):
  e=copy.deepcopy(self.b['edges'][0]);e['edge_id']='E10';self.b['edges'].append(e);r=self.run_it();self.assertEqual(r['edges']['candidates'],[]);self.assertEqual(r['edges']['ambiguous_signature_count'],1)
 def test_stale_source_and_missing_source_handles(self):
  self.p['source_sha256']='other'
  with self.assertRaises(ValueError):self.run_it()
  self.p['source_sha256']='s';self.b['edges'][0]['source_handles']=[];self.assertEqual(self.run_it()['edges']['candidates'],[])
if __name__=='__main__':unittest.main()
