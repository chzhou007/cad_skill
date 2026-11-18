import copy,unittest,ezdxf
from final_plan_line_coverage import inventory
from micro_line_circle_evidence import compare
class MicroLineCircleTest(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();m=self.d.modelspace();self.l=m.add_line((0,0),(0.002,0),dxfattribs={'layer':'供'});self.c=m.add_circle((0,0),2,dxfattribs={'layer':'供'});self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'T','node_type':'tee','x':0,'y':0,'source_handles':[self.c.dxf.handle]}],'edges':[{'edge_id':'E','system':'supply','start_node_id':'T','end_node_id':'X','source_handles':[]}]};self.p={'source_sha256':'S','graph_sha256':'G','system_layers':{'供':'supply'},'normalization_tolerance':.05};self.i=inventory(self.d,self.g,self.p,'S','G')
 def test_circle_node_evidence_does_not_classify(self):
  before=copy.deepcopy(self.g);r=compare(self.d,self.g,self.i,'S','G');self.assertEqual(self.g,before);x=r['records'][0];self.assertEqual(x['same_layer_center_circles'][0]['graph_nodes'][0]['node_id'],'T');self.assertEqual(x['status'],'micro_line_source_context_not_classified');self.assertFalse(r['human_accepted'])
 def test_stale_geometry_fails(self):
  self.l.dxf.end=(1,0,0)
  with self.assertRaisesRegex(ValueError,'micro line mismatch'):compare(self.d,self.g,self.i,'S','G')
  with self.assertRaisesRegex(ValueError,'stale'):compare(self.d,self.g,self.i,'S','other')
 def test_circle_provenance_on_incident_edge_is_not_lost(self):
  self.g['nodes'][0]['source_handles']=[];self.g['edges'][0]['source_circle_connection']={'circle_handle':self.c.dxf.handle,'expert_issue':'ISSUE'}
  node=compare(self.d,self.g,self.i,'S','G')['records'][0]['same_layer_center_circles'][0]['graph_nodes'][0];self.assertFalse(node['circle_handle_in_node_source']);self.assertEqual(node['incident_edge_circle_evidence'],[{'edge_id':'E','field':'source_circle_connection','expert_issue':'ISSUE'}])
if __name__=='__main__':unittest.main()
