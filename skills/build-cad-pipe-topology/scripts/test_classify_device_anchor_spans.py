import copy,unittest
from classify_device_anchor_spans import classify

class AnchorSpanTest(unittest.TestCase):
 def setUp(self):
  self.h={'source_sha256':'s','graph_sha256':'g','coverage_sha256':'c','joints_sha256':'j'};self.policy={**self.h,'edge_ids':['E']};chain={'source_sha256':'s','joint_handle':'J','inner_line_handle':'I','outer_line_handle':'O','circle_handle':'C'}
  self.graph={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'D','node_type':'equipment','x':0,'y':0}],'edges':[{'edge_id':'E','system':'supply','start_node_id':'D','end_node_id':'T','attribute_paths':[[[0,0],[2,0],[5,0]]],'source_exploded_device_chain':chain}]}
  self.coverage={'source_sha256':'s','graph_sha256':'g','hil_ready':False,'status':'partial_source_coverage_not_physical_length','edges':[{'edge_id':'E','system':'supply','segments':[{'index':0,'start':[0,0],'end':[2,0],'drawing_length':2,'status':'no_witness_in_scoped_search'},{'index':1,'start':[2,0],'end':[5,0],'status':'single_source_line_covers'}]}]}
  self.joints={'source_sha256':'s','graph_sha256':'g','hil_ready':False,'status':'native_exploded_device_joint_geometry_unreviewed','records':[{'edge_id':'E','equipment_id':'D','system':'supply','joint_handle':'J','inner_line_handle':'I','outer_line_handle':'O','circle_handle':'C','joint_contacts':[[1,0],[2,0]],'inner_line_endpoints':[[0.5,0],[1,0]],'outer_line_endpoints':[[2,0],[5,0]],'circle_center':[0.5,0],'status':'native_chain_geometry_unreviewed','physical_port_verified':False,'physical_length':'unknown'}]}
 def run_it(self):return classify(self.graph,self.coverage,self.joints,self.policy,self.h)
 def test_classifies_but_does_not_accept(self):
  before=copy.deepcopy(self.graph);r=self.run_it();self.assertEqual(self.graph,before);self.assertFalse(r['human_accepted']);self.assertFalse(r['records'][0]['connectivity_accepted']);self.assertEqual(r['records'][0]['physical_length'],'unknown')
 def test_rejects_wrong_anchor_and_stale_evidence(self):
  self.graph['nodes'][0]['x']=0.5
  with self.assertRaisesRegex(ValueError,'anchor'):self.run_it()
  self.graph['nodes'][0]['x']=0;self.joints['graph_sha256']='stale'
  with self.assertRaisesRegex(ValueError,'stale'):self.run_it()
 def test_rejects_unrelated_component_and_additional_missing(self):
  self.joints['records'][0]['joint_handle']='other'
  with self.assertRaisesRegex(ValueError,'identity'):self.run_it()
  self.joints['records'][0]['joint_handle']='J';self.coverage['edges'][0]['segments'][1]['status']='no_witness_in_scoped_search'
  with self.assertRaisesRegex(ValueError,'ambiguous'):self.run_it()
if __name__=='__main__':unittest.main()
