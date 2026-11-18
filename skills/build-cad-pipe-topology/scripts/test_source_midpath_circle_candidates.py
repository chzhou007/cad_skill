import copy,unittest,ezdxf
from source_midpath_circle_candidates import attach

class MidpathCircleTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.circle=m.add_circle((0,.01),137.5,dxfattribs={'layer':'HVAC-D-CWR'});self.line=m.add_line((-1000,0),(1000,0),dxfattribs={'layer':'HVAC-D-CWR'})
  self.graph={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'CT','node_type':'equipment','source_internal_path_candidate':{'edge_id':'E'}}],'edges':[{'edge_id':'E','system':'cooling_return','source_handles':[self.line.dxf.handle],'start_node_id':'A','end_node_id':'B'}]}
  self.evidence={'source_sha256':'s','graph_sha256':'g','circles_examined':1,'records':[{'tower_id':'CT','edge_id':'E','circle_handle':self.circle.dxf.handle,'closest_line_handle':self.line.dxf.handle,'center':[0,.01],'radius':137.5,'fraction':.5,'center_distance':.01}]}
 def call(self):return attach(self.graph,self.evidence,'s','g',self.doc)
 def test_preserves_topology(self):
  original=copy.deepcopy(self.graph);out,v=self.call();self.assertEqual(self.graph,original);self.assertEqual(out['nodes'],original['nodes']);self.assertEqual(out['edges'][0]['start_node_id'],'A');self.assertEqual(out['edges'][0]['end_node_id'],'B');self.assertEqual(v['new_edges'],0);self.assertFalse(out['metadata']['hil_ready'])
 def test_stale_source_owner_and_geometry_fail(self):
  with self.assertRaises(ValueError):attach(self.graph,self.evidence,'s','other',self.doc)
  self.evidence['records'][0]['tower_id']='OTHER'
  with self.assertRaises(ValueError):self.call()
  self.evidence['records'][0]['tower_id']='CT';self.evidence['records'][0]['center_distance']=1
  with self.assertRaises(ValueError):self.call()
 def test_duplicate_and_line_mismatch_fail(self):
  self.evidence['records'][0]['closest_line_handle']='other'
  with self.assertRaises(ValueError):self.call()
  self.evidence['records'][0]['closest_line_handle']=self.line.dxf.handle;self.evidence['records'].append(copy.deepcopy(self.evidence['records'][0]));self.evidence['circles_examined']=2
  with self.assertRaises(ValueError):self.call()
 def test_rejects_changed_native_circle_and_layer(self):
  self.circle.dxf.radius=138
  with self.assertRaises(ValueError):self.call()
  self.circle.dxf.radius=137.5;self.line.dxf.layer='OTHER'
  with self.assertRaises(ValueError):self.call()
 def test_rejects_forged_projection_even_if_witness_looks_valid(self):
  self.evidence['records'][0]['fraction']=.6
  with self.assertRaises(ValueError):self.call()

if __name__=='__main__':unittest.main()
