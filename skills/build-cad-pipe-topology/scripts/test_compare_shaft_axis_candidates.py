import copy,unittest
from compare_shaft_axis_candidates import compare


class ShaftAxisTests(unittest.TestCase):
 def setUp(self):
  self.a={'status':'translation_hypothesis_not_confirmed','graph_mutated':False,'hil_ready':False,'source_sha256':['s1','s2'],'input_sha256':{'graph-b':'g2'},'same_system_riser_pairs':[{'source_node':'P1','target_node':'P2','system':'supply','status':'spatial_candidate_not_a_connection'}]}
  self.b={'status':'translation_hypothesis_not_confirmed','graph_mutated':False,'hil_ready':False,'source_sha256':['s2','s3'],'input_sha256':{'graph-a':'g2'},'same_system_riser_pairs':[{'source_node':'P2','target_node':'P3','system':'supply','status':'spatial_candidate_not_a_connection'}]}
  self.g={'edges':[{'edge_id':'A','system':'supply','start_node_id':'X','end_node_id':'Y'},{'edge_id':'B','system':'supply','start_node_id':'Y','end_node_id':'Z'}]}
  self.d={'status':'candidate_diagnostics_not_physical_length','graph_mutated':False,'hil_ready':False,'edges':[{'edge_id':'A','system':'supply','floor_start':1,'floor_end':2,'segments':[{'drawing_direction':'vertical','source_handle':'L1'}]},{'edge_id':'B','system':'supply','floor_start':2,'floor_end':3,'segments':[{'drawing_direction':'vertical','source_handle':'L2'}]}]}
 def test_match_remains_unconfirmed(self):
  original=copy.deepcopy((self.a,self.b,self.g,self.d));r=compare(self.a,self.b,self.g,self.d);self.assertEqual((self.a,self.b,self.g,self.d),original);self.assertEqual(len(r['records'][0]['axis_chain_candidates']),1);self.assertFalse(r['mapping_ready']);self.assertEqual(r['records'][0]['physical_length'],'unknown')
 def test_middle_floor_or_promoted_registration_rejected(self):
  self.b['input_sha256']['graph-a']='other'
  with self.assertRaises(ValueError):compare(self.a,self.b,self.g,self.d)
  self.b['input_sha256']['graph-a']='g2';self.a['hil_ready']=True
  with self.assertRaises(ValueError):compare(self.a,self.b,self.g,self.d)
 def test_disconnected_or_unwitnessed_axis_not_selected(self):
  self.g['edges'][1]['start_node_id']='other';self.assertEqual(compare(self.a,self.b,self.g,self.d)['records'][0]['axis_chain_candidates'],[])
  self.g['edges'][1]['start_node_id']='Y';self.d['edges'][0]['segments']=[];self.assertEqual(compare(self.a,self.b,self.g,self.d)['records'][0]['axis_chain_candidates'],[])

if __name__=='__main__':unittest.main()
