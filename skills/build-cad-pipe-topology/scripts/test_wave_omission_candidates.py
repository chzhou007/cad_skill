import copy
import unittest
import ezdxf
from wave_omission_candidates import block_fingerprint, screen

class WaveCandidatesTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();block=self.doc.blocks.new('wave')
  block.add_lwpolyline([(-1,-10,-.5),(0,0,.5),(1,10,0)],format='xyb')
  self.fingerprint=block_fingerprint(block);m=self.doc.modelspace()
  m.add_blockref('wave',(0,0));m.add_blockref('wave',(100,0))
  self.graph={'nodes':[{'node_id':'a','subtype':'unresolved_source_terminal','system':'supply','floor':2,'x':0.,'y':0.},
                       {'node_id':'b','subtype':'unresolved_source_terminal','system':'supply','floor':2,'x':100.,'y':0.}],
              'edges':[{'edge_id':'1','system':'supply','start_node_id':'x','end_node_id':'a','path': [[-100,0],[0,0]]},
                       {'edge_id':'2','system':'supply','start_node_id':'b','end_node_id':'y','path': [[100,0],[200,0]]}]}
 def run_screen(self):return screen(self.doc,self.graph,block_name='wave',expected_fingerprint=self.fingerprint,max_gap=200)
 def test_facing_source_endpoints_are_candidates_only(self):
  before=copy.deepcopy(self.graph);r=self.run_screen();self.assertEqual(len(r['candidate_pairs']),1)
  self.assertTrue(r['candidate_pairs'][0]['unique_for_each_endpoint']);self.assertFalse(r['human_accepted']);self.assertEqual(before,self.graph)
 def test_no_cross_system_or_floor_join(self):
  self.graph['nodes'][1]['system']='return';self.graph['edges'][1]['system']='return';self.assertFalse(self.run_screen()['candidate_pairs'])
  self.graph['nodes'][1]['system']='supply';self.graph['edges'][1]['system']='supply';self.graph['nodes'][1]['floor']=3;self.assertFalse(self.run_screen()['candidate_pairs'])
 def test_non_facing_and_block_mismatch(self):
  self.graph['edges'][1]['path']=[[100,0],[0,0]];self.assertFalse(self.run_screen()['candidate_pairs'])
  with self.assertRaises(ValueError):screen(self.doc,self.graph,block_name='wave',expected_fingerprint='bad',max_gap=200)
 def test_ambiguous_wave_is_not_matched(self):
  self.doc.modelspace().add_blockref('wave',(0,0));self.assertFalse(self.run_screen()['candidate_pairs'])
if __name__=='__main__':unittest.main()
