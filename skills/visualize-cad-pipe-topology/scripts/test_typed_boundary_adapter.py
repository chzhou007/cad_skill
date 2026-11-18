import copy,hashlib,tempfile,unittest
from pathlib import Path
import ezdxf
from typed_boundary_adapter import adapt_typed_boundaries
class TypedBoundaryAdapter(unittest.TestCase):
 def test_empty_anchor_list_is_valid_only_when_all_endpoints_are_real_nodes(self):
  g=copy.deepcopy(self.g);g['boundary_anchors']=[];g['edges'][0].pop('end_boundary_id');g['edges'][0]['end_node_id']='T2';g['nodes'].append({'node_id':'T2'})
  before=copy.deepcopy(g);result=adapt_typed_boundaries(g,self.p,self.doc)
  self.assertEqual(g,before);self.assertEqual(result['nodes'],g['nodes']);self.assertEqual(result['edges'],g['edges'])
  self.assertEqual(result['boundary_anchors'],[]);self.assertFalse(result['metadata']['hil_ready'])
 def test_missing_or_empty_anchor_cannot_hide_a_boundary_reference(self):
  for value in (None,[]):
   g=copy.deepcopy(self.g);g['boundary_anchors']=value
   with self.assertRaises(ValueError):adapt_typed_boundaries(g,self.p,self.doc)
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name)/'s.dxf';self.doc=ezdxf.new();m=self.doc.modelspace();self.line=m.add_line((0,0),(10,0));self.circle=m.add_circle((0,0),1);self.doc.saveas(self.p);sha=hashlib.sha256(self.p.read_bytes()).hexdigest();self.old={'node_id':'old','node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'supply','x':0,'y':0,'floor':2};self.g={'metadata':{'graph_format':'experimental-typed-boundaries-v1','source_sha256':sha,'hil_ready':False},'nodes':[{'node_id':'T'}],'edges':[{'edge_id':'E','start_node_id':'T','end_node_id':None,'end_boundary_id':'A','system':'supply','source_handles':[self.line.dxf.handle]}],'boundary_anchors':[{'boundary_id':'A','kind':'expert_non_node_source_boundary','system':'supply','x':0,'y':0,'source_pipe_handle':self.line.dxf.handle,'source_circle_handle':self.circle.dxf.handle,'expert_issue':'ERR','connectivity_beyond_boundary':'unknown','legacy_node':self.old}]}
 def tearDown(self):self.t.cleanup()
 def test_leaf_adapter_preserves_input_and_marks_proxy(self):
  original=copy.deepcopy(self.g);r=adapt_typed_boundaries(self.g,self.p,self.doc);self.assertEqual(self.g,original);self.assertEqual(r['edges'][0]['end_node_id'],'A');p=r['nodes'][-1];self.assertTrue(p['viewer_non_node_boundary']);self.assertFalse(p['ports'][0]['physical_port_verified']);self.assertEqual(p['ports'][0]['port_id'],r['edges'][0]['end_port_id'])
 def test_wrong_service_and_unbound_source_rejected(self):
  for field,value in [('system','return'),('source_pipe_handle','bad'),('source_circle_handle','bad')]:
   g=copy.deepcopy(self.g);g['boundary_anchors'][0][field]=value
   with self.assertRaises(ValueError):adapt_typed_boundaries(g,self.p,self.doc)
 def test_multiple_incident_edges_and_dual_endpoint_rejected(self):
  g=copy.deepcopy(self.g);g['edges'].append(copy.deepcopy(g['edges'][0]));g['edges'][-1]['edge_id']='E2'
  with self.assertRaises(ValueError):adapt_typed_boundaries(g,self.p,self.doc)
  g=copy.deepcopy(self.g);g['edges'][0]['end_node_id']='T'
  with self.assertRaises(ValueError):adapt_typed_boundaries(g,self.p,self.doc)
 def test_source_mismatch_rejected(self):
  g=copy.deepcopy(self.g);g['metadata']['source_sha256']='wrong'
  with self.assertRaises(ValueError):adapt_typed_boundaries(g,self.p,self.doc)
 def test_circle_pipe_layer_mismatch_rejected(self):
  self.circle.dxf.layer='other'
  with self.assertRaises(ValueError):adapt_typed_boundaries(self.g,self.p,self.doc)
 def test_hil_ready_is_rejected(self):
  self.g['metadata']['hil_ready']=True
  with self.assertRaises(ValueError):adapt_typed_boundaries(self.g,self.p,self.doc)
 def test_two_bar_marker_and_negative_control(self):
  m=self.doc.modelspace();x=m.add_line((-1,0),(1,0),dxfattribs={'layer':'MARK'});y=m.add_line((-.5,.5),(.5,.5),dxfattribs={'layer':'MARK'});a=self.g['boundary_anchors'][0];a.pop('source_circle_handle');a.update(source_marker_kind='two_bar',source_marker_handles=[x.dxf.handle,y.dxf.handle],source_marker_layer='MARK',source_marker_lengths=[2,1],source_marker_spacing=.5);self.doc.saveas(self.p);self.g['metadata']['source_sha256']=hashlib.sha256(self.p.read_bytes()).hexdigest()
  self.assertTrue(adapt_typed_boundaries(self.g,self.p,self.doc)['nodes'][-1]['viewer_non_node_boundary'])
  a['source_marker_handles'][1]='missing'
  with self.assertRaisesRegex(ValueError,'two-bar marker missing'):adapt_typed_boundaries(self.g,self.p,self.doc)
 def test_user_confirmed_interface_proxy_and_missing_glyph(self):
  m=self.doc.modelspace();lines=[m.add_line((i,0),(i,1),dxfattribs={'layer':'空调立管、水平支管'}) for i in range(4)];self.doc.saveas(self.p);self.g['metadata']['source_sha256']=hashlib.sha256(self.p.read_bytes()).hexdigest();a=self.g['boundary_anchors'][0];a.update(kind='user_confirmed_non_node_source_boundary',user_confirmation_sha256='a'*64,destination_kind='terminal_air_conditioning_equipment',destination_instance='unknown',destination_port='unknown',source_glyph_handles=[x.dxf.handle for x in lines]);a['legacy_node']['subtype']='out_of_plane_interface'
  self.assertTrue(adapt_typed_boundaries(self.g,self.p,self.doc)['nodes'][-1]['viewer_non_node_boundary']);a['source_glyph_handles'][0]='bad'
  with self.assertRaises(ValueError):adapt_typed_boundaries(self.g,self.p,self.doc)

if __name__=='__main__':unittest.main()
