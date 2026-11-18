import copy,unittest,ezdxf
from verify_split_component_positions import verify

class SplitComponentPositionsTest(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();self.d.blocks.new('valve');m=self.d.modelspace();self.l=m.add_line((0,0),(10,0),dxfattribs={'layer':'空调冷冻水供水'});self.e=m.add_blockref('valve',(4,0))
  self.g={'metadata':{'source_sha256':'S'},'edges':[{'edge_id':'E','system':'supply','source_handles':[self.l.dxf.handle],'attribute_paths':[[[0,0],[10,0]]]}]}
  self.r={'source_sha256':'S','new_graph_sha256':'G','status':'component_rebinding_candidates_not_ownership_acceptance','graph_mutated':False,'human_accepted':False,'records':[{'device_name':'V','source_handle':self.e.dxf.handle,'new_edge_id':'E','status':'split_or_unmatched_edge_requires_review'}]}
  self.h={'source_sha256':'S','graph_sha256':'G','rebinding_sha256':'R'};self.p={**self.h,'selections':[{'device_name':'V','source_handle':self.e.dxf.handle,'source_line_handle':self.l.dxf.handle,'source_block':'valve','new_edge_id':'E'}]}
 def test_unique_candidate_no_mutation(self):
  old=copy.deepcopy(self.g);r=verify(self.d,self.g,self.r,self.p,self.h);self.assertEqual(old,self.g);self.assertFalse(r['records'][0]['physical_ownership_verified']);self.assertFalse(r['hil_ready'])
 def test_competing_line_and_wrong_path_fail(self):
  self.d.modelspace().add_line((0,0),(10,0),dxfattribs={'layer':'空调冷冻水供水'})
  with self.assertRaisesRegex(ValueError,'ambiguous'):verify(self.d,self.g,self.r,self.p,self.h)
  self.setUp();self.g['edges'][0]['attribute_paths']=[[[5,0],[10,0]]]
  with self.assertRaisesRegex(ValueError,'graph path'):verify(self.d,self.g,self.r,self.p,self.h)
 def test_stale_and_wrong_block_fail(self):
  self.p['graph_sha256']='old'
  with self.assertRaisesRegex(ValueError,'stale'):verify(self.d,self.g,self.r,self.p,self.h)
  self.p['graph_sha256']='G';self.p['selections'][0]['source_block']='other'
  with self.assertRaisesRegex(ValueError,'native source'):verify(self.d,self.g,self.r,self.p,self.h)
if __name__=='__main__':unittest.main()
