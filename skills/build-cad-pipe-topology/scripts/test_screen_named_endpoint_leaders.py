import copy,unittest,ezdxf
from screen_named_endpoint_leaders import screen
class NamedEndpointLeaderTest(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();m=self.d.modelspace();self.pipe=m.add_line((0,0),(0,10),dxfattribs={'layer':'supply'});self.leader=m.add_line((0,0),(10,0),dxfattribs={'layer':'leader'});self.text=m.add_text('CHWS1 DN450',dxfattribs={'insert':(10,0),'height':1,'layer':'text'});self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'N','boundary_type':'unresolved_source_terminal','system':'supply','x':0,'y':0,'source_handles':[self.pipe.dxf.handle]}],'edges':[]};self.p={'source_sha256':'S','graph_sha256':'G','endpoint_tolerance':.05,'max_text_height_gap':.6,'selections':[{'node_id':'N','leader_handle':self.leader.dxf.handle,'text_handle':self.text.dxf.handle,'pipe_handle':self.pipe.dxf.handle,'leader_layer':'leader','text_layer':'text','pipe_layer':'supply','expected_text':'CHWS1 DN450'}]}
 def test_candidate_does_not_mutate_or_confirm(self):
  old=copy.deepcopy(self.g);r=screen(self.d,self.g,self.p,'S','G');self.assertEqual(old,self.g);self.assertFalse(r['mapping_ready']);self.assertEqual(r['selections'][0]['label']['route_number'],'1')
 def test_wrong_system_or_geometry_rejected(self):
  self.g['nodes'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'system'):screen(self.d,self.g,self.p,'S','G')
  self.g['nodes'][0]['system']='supply';self.leader.dxf.start=(2,0)
  with self.assertRaisesRegex(ValueError,'leader endpoint'):screen(self.d,self.g,self.p,'S','G')
 def test_competing_text_and_stale_graph_rejected(self):
  self.d.modelspace().add_text('CHWR2 DN450',dxfattribs={'insert':(10,0),'height':1})
  with self.assertRaisesRegex(ValueError,'ambiguous'):screen(self.d,self.g,self.p,'S','G')
  with self.assertRaisesRegex(ValueError,'stale'):screen(self.d,self.g,self.p,'S','wrong')
if __name__=='__main__':unittest.main()
