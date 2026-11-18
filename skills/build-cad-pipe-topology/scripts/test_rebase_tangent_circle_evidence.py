import copy
import unittest
from test_source_tangent_circle_candidates import fixture
from rebase_tangent_circle_evidence import apply

class TangentRebaseTests(unittest.TestCase):
 def setUp(self):
  self.doc,self.ref,self.evidence=fixture();self.graph=copy.deepcopy(self.ref)
  self.inventory={'source_sha256':'src','graph_sha256':'target','records':[{'node_id':'S','edge_id':'ES'},{'node_id':'R','edge_id':'ER'}]}
  self.policy={'source_sha256':'src','target_graph_sha256':'target','reference_graph_sha256':'graph','evidence_sha256':'evidence','inventory_sha256':'inventory'}
 def run_apply(self):return apply(self.graph,self.inventory,self.ref,self.evidence,self.doc,self.policy,source_sha256='src',graph_sha256='target',inventory_sha256='inventory',reference_sha256='graph',evidence_sha256='evidence')
 def test_adds_source_glyphs_without_connecting_or_deleting_records(self):
  before=copy.deepcopy(self.graph);out,inv,a=self.run_apply();self.assertEqual(self.graph,before)
  self.assertEqual(out['edges'],before['edges']);self.assertEqual(len(inv['records']),2);self.assertEqual(a['physical_connections_added'],0)
  self.assertTrue(all(r['source_tangent_circle_candidate']['status']=='source_shape_only_no_hydraulic_connection' for r in inv['records']))
  self.assertFalse(out['metadata']['hil_ready'])
 def test_stale_evidence_and_changed_terminal_rejected(self):
  self.policy['evidence_sha256']='old'
  with self.assertRaises(ValueError):self.run_apply()
  self.policy['evidence_sha256']='evidence';self.graph['nodes'][0]['x']=1
  with self.assertRaises(ValueError):self.run_apply()
 def test_changed_edge_source_or_inventory_rejected(self):
  self.graph['edges'][0]['source_handles']=['different']
  with self.assertRaises(ValueError):self.run_apply()
  self.graph=copy.deepcopy(self.ref);self.inventory['records'][0]['edge_id']='wrong'
  with self.assertRaises(ValueError):self.run_apply()
 def test_other_length_attribute_change_is_not_connectivity_change(self):
  self.graph['edges'][0]['path_length']=4
  out,_,_=self.run_apply();self.assertEqual(out['edges'][0]['path_length'],4)

if __name__=='__main__':unittest.main()
