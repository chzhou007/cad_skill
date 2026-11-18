import copy,unittest
from audit_component_rebinding import audit

class ComponentRebindingTest(unittest.TestCase):
 def setUp(self):
  self.h={'source_sha256':'s','old_graph_sha256':'a','new_graph_sha256':'b','identity_sha256':'i','old_components_sha256':'c','new_components_sha256':'d'};self.p={**self.h,'maximum_anchor_distance':5};edge={'system':'supply','source_handles':['L'],'path':[[0,0],[10,0]]};self.a={'metadata':{'source_sha256':'s'},'edges':[{'edge_id':'E1',**edge},{'edge_id':'E2',**edge}]};self.b={'metadata':{'source_sha256':'s'},'edges':[{'edge_id':'E1',**edge},{'edge_id':'E9',**edge}]};self.x=[{'device_name':'D','source_handle':'H','equipment_type':'阀','edge_id':'E1','x':'5','y':'1'}];self.y=[{'device_name':'D','source_handle':'H','equipment_type':'阀','edge_id':'E9','x':'5','y':'1'}];self.i={'source_sha256':'s','old_graph_sha256':'a','new_graph_sha256':'b','status':'identity_candidates_only_no_review_transfer','graph_mutated':False,'human_accepted':False,'edges':{'candidates':[{'old_id':'E1','new_id':'E9'}],'same_id_different_or_unknown_signature':['E1']}}
 def run_it(self):return audit(self.a,self.b,self.x,self.y,self.i,self.p,self.h)
 def test_candidate_is_never_ownership_approval(self):
  before=copy.deepcopy((self.a,self.b,self.x,self.y));r=self.run_it();self.assertEqual(r['records'][0]['status'],'unique_same_source_path_candidate');self.assertTrue(r['records'][0]['old_edge_id_reused_for_other_path']);self.assertTrue(r['records'][0]['same_system_source_geometry_candidate']);self.assertFalse(r['records'][0]['physical_ownership_verified']);self.assertEqual(before,(self.a,self.b,self.x,self.y))
 def test_same_id_different_path_remains_pending(self):
  self.y[0]['edge_id']='E1';r=self.run_it();self.assertEqual(r['records'][0]['status'],'split_or_unmatched_edge_requires_review');self.assertTrue(r['records'][0]['same_numeric_edge_id'])
 def test_missing_component_and_stale_audit_rejected(self):
  self.y=[]
  with self.assertRaisesRegex(ValueError,'identity set'):self.run_it()
  self.y=copy.deepcopy(self.x);self.i['new_graph_sha256']='old'
  with self.assertRaisesRegex(ValueError,'stale'):self.run_it()
 def test_far_anchor_is_not_ownership_candidate(self):
  self.x[0]['y']=self.y[0]['y']='10';self.assertFalse(self.run_it()['records'][0]['same_system_source_geometry_candidate'])
if __name__=='__main__':unittest.main()
