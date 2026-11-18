import unittest,ezdxf
from source_endpoint_leader_labels import attach
class SourceEndpointLabelsTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.text=m.add_text('3F-A1',dxfattribs={'insert':(100,0),'layer':'ANNOT'});self.line=m.add_line((0,0),(100,0),dxfattribs={'layer':'ANNOT'});self.graph={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'U','boundary_type':'unresolved_source_terminal','x':0,'y':0}],'edges':[{'edge_id':'E'}]};self.row={'node_id':'U','text_handle':self.text.dxf.handle,'leader_handle':self.line.dxf.handle,'layer':'ANNOT','text':'3F-A1','endpoint_tolerance':.01,'text_anchor_tolerance':1}
 def test_attach_preserves_graph_and_edges(self):
  out,a=attach(self.graph,self.doc,'S',[self.row]);self.assertEqual(out['edges'],self.graph['edges']);self.assertNotIn('source_endpoint_annotation',self.graph['nodes'][0]);self.assertEqual(out['nodes'][0]['source_endpoint_annotation']['text'],'3F-A1');self.assertEqual(a['matched_nodes'],1)
 def test_reject_wrong_text_or_missed_node(self):
  for key,value in [('text','other'),('node_id','other'),('layer','other')]:
   r=dict(self.row);r[key]=value
   with self.assertRaises(ValueError):attach(self.graph,self.doc,'S',[r])
 def test_duplicate_rejected(self):
  with self.assertRaises(ValueError):attach(self.graph,self.doc,'S',[self.row,self.row])
 def test_forked_line_and_polyline_share_source_text(self):
  m=self.doc.modelspace();poly=m.add_lwpolyline([(0,10),(100,0),(130,0)],dxfattribs={'layer':'ANNOT'});self.graph['nodes'].append({'node_id':'V','boundary_type':'unresolved_source_terminal','x':0,'y':10});r=dict(self.row,node_id='V',leader_handle=poly.dxf.handle,shared_text_label=True)
  out,a=attach(self.graph,self.doc,'S',[self.row,r]);self.assertEqual(a['matched_nodes'],2);self.assertEqual(out['nodes'][1]['source_endpoint_annotation']['text'],'3F-A1')
 def test_reject_curved_polyline(self):
  m=self.doc.modelspace();poly=m.add_lwpolyline([(0,0,1),(100,0,0)],format='xyb',dxfattribs={'layer':'ANNOT'});r=dict(self.row,leader_handle=poly.dxf.handle)
  with self.assertRaises(ValueError):attach(self.graph,self.doc,'S',[r])
 def test_wrong_source_rejected(self):
  with self.assertRaises(ValueError):attach(self.graph,self.doc,'other',[self.row])
if __name__=='__main__':unittest.main()
