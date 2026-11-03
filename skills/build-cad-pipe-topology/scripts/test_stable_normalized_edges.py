import unittest
from stable_normalized_edges import reconcile

class StableNormalizedEdges(unittest.TestCase):
 def case(self):
  nodes=[dict(node_id='EQ',node_type='equipment'),dict(node_id='T',node_type='tee')]
  graph={'nodes':nodes,'edges':[dict(edge_id='NEW',start_node_id='EQ',end_node_id='T',source_handles=['A','B','C'])]}
  prior={'edges':[dict(edge_id='E1',start_node_id='EQ',end_node_id='DEAD',source_handles=['A'],path_length=5),dict(edge_id='E2',start_node_id='DEAD',end_node_id='T',source_handles=['B','C'],path_length=10)]}
  return graph,prior
 def test_equipment_branch_identity_preferred_and_retired_route_mapped(self):
  g,p=self.case();a=reconcile(g,p,['A']);self.assertEqual(g['edges'][0]['edge_id'],'E1');self.assertEqual(a['retired_edges'][0]['replacement_edge_id'],'E1')
 def test_unwitnessed_route_not_reidentified(self):
  g,p=self.case();a=reconcile(g,p,['UNRELATED']);self.assertEqual(g['edges'][0]['edge_id'],'NEW');self.assertEqual(a['edge_id_mapping'],{})
 def test_shared_boundary_without_source_subset_not_enough(self):
  g,p=self.case();p['edges'][0]['source_handles']=['MISSING'];p['edges'][1]['source_handles']=['MISSING'];reconcile(g,p,['A']);self.assertEqual(g['edges'][0]['edge_id'],'NEW')
 def test_no_double_claim_of_old_identity(self):
  g,p=self.case();g['edges'].append(dict(g['edges'][0],edge_id='NEW2'));reconcile(g,p,['A']);self.assertEqual(len({e['edge_id']for e in g['edges']}),2)

if __name__=='__main__':unittest.main()
