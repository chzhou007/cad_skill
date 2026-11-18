import copy,unittest
from source_named_service_evidence import attach
class NamedService(unittest.TestCase):
 def fixture(self):
  g={'edges':[{'edge_id':'E1','system':'unclassified_water','start_node_id':'A','end_node_id':'B'}]};group={'node_id':'A','kind':'makeup_water_interface','status':'candidate_trace_only','label':'冷却水箱补水管','label_handle':'H1','leader_handles':['L1'],'source_layer':'BS','edges':['E1']}
  trace={'source_sha256':'S','graph_sha256':'G','conflicting_edges':{},'groups':[group]};leader={'source_sha256':'S','graph_sha256':'G','status':'PASS','verified':1,'total':1,'checks':[{'node_id':'A','source_text':group['label'],'label_handle':'H1','leader_handles':['L1'],'meets_prior_calibration':True,'connected_leader_path':True}]};boundary={'source_sha256':'S','graph_sha256':'G','edges_touching_mixed_or_other_layer':0,'edges':[{'edge_id':'E1','kind':group['kind'],'source_layer':'BS','contacts':[{'mixed_source_contact':False,'system_review_required':False,'different_or_missing_native_layer':[]}]}]};return g,trace,leader,boundary
 def test_source_label_attached_without_changing_connectivity_or_system(self):
  g,t,l,b=self.fixture();original=copy.deepcopy(g);out,report=attach(g,t,l,b,'S','G');self.assertEqual(g,original);self.assertEqual(out['edges'][0]['system'],'unclassified_water');self.assertEqual(out['edges'][0]['source_named_service']['display_zh'],'补水');self.assertEqual(report['edges_with_source_named_service'],1)
 def test_stale_graph_and_incomplete_leader_fail_closed(self):
  g,t,l,b=self.fixture()
  with self.assertRaises(ValueError):attach(g,t,l,b,'S','different')
  l['checks'][0]['connected_leader_path']=False
  with self.assertRaises(ValueError):attach(g,t,l,b,'S','G')
 def test_mixed_boundary_and_conflicting_sources_rejected(self):
  g,t,l,b=self.fixture();b['edges_touching_mixed_or_other_layer']=1
  with self.assertRaises(ValueError):attach(g,t,l,b,'S','G')
  g,t,l,b=self.fixture();t['conflicting_edges']={'E1':['drain_interface','makeup_water_interface']}
  with self.assertRaises(ValueError):attach(g,t,l,b,'S','G')
 def test_missing_audited_edge_fails_closed(self):
  g,t,l,b=self.fixture();b['edges']=[]
  with self.assertRaises(ValueError):attach(g,t,l,b,'S','G')
