import copy,unittest,ezdxf
from source_detail_frame_links import screen

class DetailFrameLinks(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();handles=[]
  for x,y in [(0,0),(10,0),(0,5),(10,5)]:
   line=m.add_line((x,y),(x+20,y+30),dxfattribs={'layer':'ANNO','linetype':'DASH'});handles.append(line.dxf.handle)
  self.hashes={'source_sha256':'S','graph_sha256':'G','glyphs_sha256':'H'};self.policy={**self.hashes,'annotation_layer':'ANNO','allowed_linetypes':['DASH'],'frames':[{'frame_id':'L','line_handles':handles}]};self.glyphs={'source_sha256':'S','graph_sha256':'G','graph_mutated':False,'rows':[{'system':'supply','rank':1,'upper_edge':'U','detail_edge':'D','upper':{'center':[25,32]},'detail':{'center':[5,2]}}]}
 def test_frame_is_context_not_mapping(self):
  out=screen(self.doc,self.glyphs,self.policy,self.hashes);self.assertEqual(out['candidate_rows'][0]['shared_frame_candidates'],['L']);self.assertFalse(out['mapping_ready']);self.assertFalse(out['human_accepted'])
 def test_wrong_layer_or_nonparallel_line_fails(self):
  line=self.doc.entitydb[self.policy['frames'][0]['line_handles'][0]];line.dxf.layer='PIPE'
  with self.assertRaises(ValueError):screen(self.doc,self.glyphs,self.policy,self.hashes)
  line.dxf.layer='ANNO';line.dxf.end=(99,99,0)
  with self.assertRaises(ValueError):screen(self.doc,self.glyphs,self.policy,self.hashes)
 def test_outside_candidate_never_forced_into_frame(self):
  g=copy.deepcopy(self.glyphs);g['rows'][0]['detail']['center']=[100,100]
  self.assertEqual(screen(self.doc,g,self.policy,self.hashes)['candidate_rows'][0]['shared_frame_candidates'],[])
if __name__=='__main__':unittest.main()
