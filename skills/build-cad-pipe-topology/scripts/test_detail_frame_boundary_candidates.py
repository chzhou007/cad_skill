import copy,unittest
from detail_frame_boundary_candidates import compare

class FrameBoundaryCandidates(unittest.TestCase):
 def setUp(self):
  self.h={'source_sha256':'S','graph_sha256':'G','frames_sha256':'F','scope_sha256':'C','boundaries_sha256':'B'};common={'source_sha256':'S','graph_sha256':'G','mapping_ready':False,'graph_mutated':False,'human_accepted':False};self.frame={**common,'status':'source_dashed_frame_context_not_mapping','frames':[{'frame_id':'R','upper_bounds':[10,10,20,20],'lower_bounds':[0,0,10,10],'source_line_offset':[10,10]}]};self.scope={**common,'status':'scoped_coverage_not_mapping','upper':[{'node_id':'U','system':'supply','center':[15,15]}]};self.bound={**common,'status':'ordered_candidates_not_mapping','scope_sha256':'C','anchors':[{'boundary_id':'A','system':'supply','center':[5,5],'edge_id':'E','kind':'user_confirmed_non_node_source_boundary','circle_handle':'C1','pipe_handle':'L'}],'rows':[{'system':'supply','upper_glyph':'U','detail_boundary':'A','detail_edge':'E','source_circle_handle':'C1','source_pipe_handle':'L','status':'ordered_candidate_not_connection'}]};self.graph={'edges':[{'edge_id':'E','system':'supply'}]}
 def test_preserves_boundary_and_does_not_connect(self):
  r=compare(self.frame,self.scope,self.bound,self.graph,self.h);self.assertEqual(r['records'][0]['boundary_kind'],'user_confirmed_non_node_source_boundary');self.assertEqual(r['records'][0]['horizontal_residual_drawing_units'],0);self.assertFalse(r['mapping_ready']);self.assertFalse(r['graph_mutated'])
 def test_invalid_scope_or_other_system_fails(self):
  b=copy.deepcopy(self.bound);b['anchors'][0]['system']='return'
  with self.assertRaises(ValueError):compare(self.frame,self.scope,b,self.graph,self.h)
  with self.assertRaises(ValueError):compare(self.frame,self.scope,self.bound,self.graph,{**self.h,'scope_sha256':'stale'})
if __name__=='__main__':unittest.main()
