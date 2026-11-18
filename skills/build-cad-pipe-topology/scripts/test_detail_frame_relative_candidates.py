import copy,unittest
from detail_frame_relative_candidates import compare

class FrameRelative(unittest.TestCase):
 def setUp(self):
  self.h={'source_sha256':'S','graph_sha256':'G','glyphs_sha256':'H','frames_sha256':'F'};self.g={'edges':[{'edge_id':x,'system':'supply'} for x in ['U1','U2','D1','D2']]};self.rows=[{'system':'supply','rank':1,'upper_edge':'U1','detail_edge':'D1','upper':{'center':[20,33]},'detail':{'center':[0,0]}},{'system':'supply','rank':2,'upper_edge':'U2','detail_edge':'D2','upper':{'center':[32,33]},'detail':{'center':[10,0]}}];self.glyph={'source_sha256':'S','graph_sha256':'G','graph_mutated':False,'rows':self.rows};self.f={'status':'source_dashed_frame_context_not_mapping','source_sha256':'S','graph_sha256':'G','glyphs_sha256':'H','mapping_ready':False,'human_accepted':False,'frames':[{'frame_id':'L','source_line_offset':[20,30]}],'candidate_rows':[{k:r[k] for k in ('system','rank','upper_edge','detail_edge')}|{'status':'source_frame_context_not_individual_mapping','shared_frame_candidates':['L']} for r in self.rows]}
 def test_exception_and_nearest_are_evidence_only(self):
  x=compare(self.f,self.glyph,self.g,self.h);self.assertEqual(x['records'][0]['proposed_horizontal_residual_drawing_units'],0);self.assertEqual(x['records'][1]['proposed_horizontal_residual_drawing_units'],2);self.assertFalse(x['mapping_ready'])
 def test_stale_or_cross_system_fails(self):
  g=copy.deepcopy(self.g);g['edges'][0]['system']='return'
  with self.assertRaises(ValueError):compare(self.f,self.glyph,g,self.h)
  with self.assertRaises(ValueError):compare(self.f,self.glyph,self.g,{**self.h,'glyphs_sha256':'bad'})
if __name__=='__main__':unittest.main()
