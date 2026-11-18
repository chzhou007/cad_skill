import copy,unittest,ezdxf
from partial_line_evidence import validate

class PartialLineViewerEvidenceTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();line=self.doc.modelspace().add_line((0,0),(8,0),dxfattribs={'layer':'空调冷冻水供水'});h=line.dxf.handle
  self.e={'edge_id':'E','system':'supply','physical_length':'unknown','path_length_complete':False,'attribute_paths':[[[0,0],[10,0]]],'source_partial_line_evidence':{'source_sha256':'S','input_graph_sha256':'G','coverage_sha256':'C','screen_sha256':'H','status':'partial_source_overlap_candidate_not_physical_length','physical_length':'unknown','connection_confirmed':False,'human_accepted':False,'records':[{'edge_id':'E','system':'supply','segment_index':0,'start':[0,0],'end':[10,0],'drawing_length':10.,'unique_source_drawing_length':8.,'unwitnessed_drawing_length':2.,'ambiguous_drawing_length':0.,'physical_length':'unknown','pieces':[{'start_distance':0.,'end_distance':8.,'drawing_length':8.,'status':'unique_source_line','source_handles':[h]},{'start_distance':8.,'end_distance':10.,'drawing_length':2.,'status':'unwitnessed','source_handles':[]}]}]}}
 def test_source_is_verified_without_mutating_evidence(self):
  before=copy.deepcopy(self.e);validate(self.doc,self.e,'S');self.assertEqual(self.e,before)
 def test_changed_source_or_accepted_claim_fails(self):
  self.doc.modelspace().add_line((1,0),(7,0),dxfattribs={'layer':'空调冷冻水供水'})
  with self.assertRaises(ValueError):validate(self.doc,self.e,'S')
  self.e['source_partial_line_evidence']['human_accepted']=True
  with self.assertRaises(ValueError):validate(self.doc,self.e,'S')
if __name__=='__main__':unittest.main()
