import copy,unittest
from named_leader_viewer_evidence import validate
class NamedLeaderViewerEvidenceTest(unittest.TestCase):
 def setUp(self):
  self.node={'node_id':'U','node_type':'virtual_equipment','boundary_type':'unresolved_source_terminal','system':'supply','x':1,'y':2,'source_handles':['P']};self.edge={'edge_id':'E','system':'supply','start_node_id':'U','end_node_id':'T','attribute_paths':[[[1,2],[3,4]]],'path_points':[[1,2],[3,4]]};self.g={'metadata':{'source_sha256':'S'},'nodes':[self.node],'edges':[self.edge]};self.s={'status':'scoped_leader_candidates_not_binding','source_sha256':'S','graph_sha256':'G','graph_mutated':False,'mapping_ready':False,'hil_ready':False,'selections':[{'node_id':'U','pipe_handle':'P','leader_handle':'L','text_handle':'T','system':'supply','status':'source_geometry_candidate_not_binding','label':{'system':'supply','binding_status':'unbound_source_text_candidate','original_text':'CHWS1 DN450'}}]}
 def test_matching_candidate_is_not_confirmation(self):
  self.assertEqual(validate(self.s,self.g,copy.deepcopy(self.g),'S','G')[0]['label']['original_text'],'CHWS1 DN450')
 def test_stale_graph_and_changed_viewer_fail(self):
  with self.assertRaises(ValueError):validate(self.s,self.g,self.g,'S','other')
  v=copy.deepcopy(self.g);v['edges'][0]['attribute_paths'][0][1]=[5,6]
  with self.assertRaises(ValueError):validate(self.s,self.g,v,'S','G')
  v=copy.deepcopy(self.g);v['nodes'][0]['x']=99
  with self.assertRaises(ValueError):validate(self.s,self.g,v,'S','G')
 def test_label_and_system_cannot_be_promoted(self):
  self.s['selections'][0]['label']['binding_status']='confirmed'
  with self.assertRaises(ValueError):validate(self.s,self.g,self.g,'S','G')
if __name__=='__main__':unittest.main()
