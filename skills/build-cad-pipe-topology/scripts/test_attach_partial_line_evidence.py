import copy,unittest,ezdxf
from partial_native_line_coverage import audit
from attach_partial_line_evidence import attach

class AttachPartialLineTest(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();self.d.modelspace().add_line((0,0),(8,0),dxfattribs={'layer':'空调冷冻水供水'});self.g={'nodes':[{'node_id':'A'},{'node_id':'B'}],'edges':[{'edge_id':'E','system':'supply','attribute_paths':[[[0,0],[10,0]]],'path_length':5,'path_length_complete':False,'physical_length':'unknown'}]};self.c={'status':'partial_source_coverage_not_physical_length','source_sha256':'S','graph_mutated':False,'edges':[{'edge_id':'E','system':'supply','segments':[{'index':0,'start':[0,0],'end':[10,0],'status':'no_witness_in_scoped_search'}]}]};self.p={'source_sha256':'S','graph_sha256':'G','coverage_sha256':'C','selections':[{'edge_id':'E','segment_index':0}]};self.s=audit(self.d,self.g,self.c,self.p,'S','G','C')
 def run_attach(self):return attach(self.d,self.g,self.c,self.s,self.p,'S','G','C','H')
 def test_candidate_is_evidence_only(self):
  before=copy.deepcopy(self.g);g,r=self.run_attach();self.assertEqual(self.g,before);self.assertEqual(g['nodes'],before['nodes']);self.assertEqual(g['edges'][0]['path_length'],5);self.assertEqual(g['edges'][0]['source_partial_line_evidence']['records'][0]['unique_source_drawing_length'],8);self.assertFalse(r['review_inherited']);self.assertEqual(g['edges'][0]['physical_length'],'unknown')
 def test_tampered_or_known_physical_length_fails(self):
  self.s['records'][0]['unique_source_drawing_length']=9
  with self.assertRaisesRegex(ValueError,'screen mismatch'):self.run_attach()
  self.s=audit(self.d,self.g,self.c,self.p,'S','G','C');self.g['edges'][0]['physical_length']=0
  with self.assertRaisesRegex(ValueError,'unknown length'):self.run_attach()
if __name__=='__main__':unittest.main()
