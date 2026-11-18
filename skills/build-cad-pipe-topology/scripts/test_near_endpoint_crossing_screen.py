import copy,unittest,ezdxf
from near_endpoint_crossing_screen import screen
class NearEndpointScreen(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.main=m.add_line((0,-10),(0,10),dxfattribs={'layer':'S'});self.branch=m.add_line((-20,0),(.5,0),dxfattribs={'layer':'S'})
  self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'U','subtype':'unresolved_source_terminal','system':'supply','x':.5,'y':0},{'node_id':'A','system':'supply','x':-20,'y':0},{'node_id':'M1','system':'supply','x':0,'y':-10},{'node_id':'M2','system':'supply','x':0,'y':10}], 'edges':[{'edge_id':'B','system':'supply','start_node_id':'A','end_node_id':'U','source_handles':[self.branch.dxf.handle]},{'edge_id':'M','system':'supply','start_node_id':'M1','end_node_id':'M2','source_handles':[self.main.dxf.handle]}]};self.p={'source_sha256':'S','graph_sha256':'G','maximum_overshoot':1,'minimum_overshoot':.05,'node_tolerance':1,'z_tolerance':1,'minimum_sine_angle':.5,'source_layer_systems':{'S':'supply','R':'return'}}
 def run_case(self):return screen(self.doc,self.g,self.p,'S','G')
 def test_short_same_system_overshoot_is_only_candidate(self):
  before=copy.deepcopy(self.g);r=self.run_case();self.assertEqual(r['counts']['candidates'],1);self.assertEqual(r['candidates'][0]['endpoint_node_id'],'U');self.assertFalse(r['graph_mutated']);self.assertEqual(self.g,before)
 def test_system_or_z_conflicts_are_not_candidates(self):
  self.main.dxf.layer='R';self.assertEqual(self.run_case()['counts']['candidates'],0);self.main.dxf.layer='S';self.main.dxf.start=(0,-10,2);self.main.dxf.end=(0,10,2);self.assertEqual(self.run_case()['counts']['candidates'],0)
 def test_deep_crossing_or_stale_graph_rejected(self):
  self.branch.dxf.end=(3,0);self.g['nodes'][0]['x']=3;self.assertEqual(self.run_case()['counts']['candidates'],0);self.p['graph_sha256']='old'
  with self.assertRaises(ValueError):self.run_case()
if __name__=='__main__':unittest.main()
