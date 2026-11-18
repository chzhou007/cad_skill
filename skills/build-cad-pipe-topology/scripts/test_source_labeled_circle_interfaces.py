import unittest,ezdxf
from source_labeled_circle_interfaces import attach
class CircleInterfaceTest(unittest.TestCase):
 def setUp(self):
  d=ezdxf.new();m=d.modelspace();t=m.add_text('2F-A3',dxfattribs={'insert':(0,10)});note=m.add_text('接至2F-A3',dxfattribs={'insert':(100,10)});l=m.add_line((0,10),(0,0));tl=m.add_line((100,10),(100,0));c=m.add_circle((100,0),5,dxfattribs={'layer':'PIPE'});p=m.add_line((0,0),(10,0),dxfattribs={'layer':'PIPE'});q=m.add_line((105,0),(115,0),dxfattribs={'layer':'PIPE'});self.doc=d
  self.graph={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'A','boundary_type':'unresolved_source_terminal','system':'supply','floor':'F2','x':0,'y':0},{'node_id':'B','boundary_type':'unresolved_source_terminal','system':'supply','floor':'F2','x':105,'y':0}],'edges':[{'edge_id':'E1','start_node_id':'A','end_node_id':'X','system':'supply','source_handles':[p.dxf.handle]},{'edge_id':'E2','start_node_id':'B','end_node_id':'Y','system':'supply','source_handles':[q.dxf.handle]}]};self.row={'label':'2F-A3','system':'supply','local_node_id':'A','target_node_id':'B','local_text_handle':t.dxf.handle,'target_note_handle':note.dxf.handle,'local_leader_handle':l.dxf.handle,'target_leader_handle':tl.dxf.handle,'circle_handle':c.dxf.handle}
 def test_classifies_two_without_adding_edges(self):
  o,a=attach(self.graph,self.doc,'S',[self.row]);self.assertEqual(a['classified_interfaces'],2);self.assertEqual(o['edges'],self.graph['edges']);self.assertFalse(o['sourceDeclaredConnections'][0]['physical_route_verified'])
 def test_competing_circle_rim_node_rejected(self):
  self.graph['nodes'].append({'node_id':'C','x':95,'y':0})
  with self.assertRaises(ValueError):attach(self.graph,self.doc,'S',[self.row])
 def test_nonzero_offsets_require_bounded_calibration(self):
  self.doc.entitydb[self.row['local_text_handle']].dxf.insert=(0,45)
  self.doc.entitydb[self.row['target_leader_handle']].dxf.end=(100,15)
  r=dict(self.row,local_text_anchor_tolerance=50,target_center_tolerance=20)
  with self.assertRaises(ValueError):attach(self.graph,self.doc,'S',[r])
  r['local_calibration_evidence']='two repeated local drawings'
  out,a=attach(self.graph,self.doc,'S',[r]);self.assertEqual(a['new_source_declared_links'],1)
  r['target_center_tolerance']=21
  with self.assertRaises(ValueError):attach(self.graph,self.doc,'S',[r])
 def test_wrong_circle_layer_or_rim_rejected(self):
  self.doc.entitydb[self.row['circle_handle']].dxf.radius=6
  with self.assertRaises(ValueError):attach(self.graph,self.doc,'S',[self.row])
 def test_wrong_note_or_service_rejected(self):
  self.doc.entitydb[self.row['target_note_handle']].dxf.text='接至2F-A5'
  with self.assertRaises(ValueError):attach(self.graph,self.doc,'S',[self.row])
if __name__=='__main__':unittest.main()
