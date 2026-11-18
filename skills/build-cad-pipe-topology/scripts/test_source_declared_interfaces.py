import unittest,ezdxf
from source_declared_interfaces import attach
class InterfaceTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();note=m.add_text('接至3F-A1',dxfattribs={'insert':(0,0)});lt=m.add_text('3F-A1',dxfattribs={'insert':(0,100)});nodes=[{'node_id':'EQ','node_type':'equipment'}];edges=[];services={}
  for i,system in enumerate(('supply','return')):
   y=10+i*10;ny=110+i*10;target=m.add_line((0,y),(20,y));leader=m.add_line((0,0),(10,y));local=m.add_line((0,100),(10,ny));nid='U'+str(i);eid='E'+str(i);ref={'label':'3F-A1','system':system,'source_pipe_handle':target.dxf.handle,'leader_handle':leader.dxf.handle,'text_handle':note.dxf.handle,'point':[10,y],'target_edge_id':eid};ann={'text':'3F-A1','text_handle':lt.dxf.handle,'leader_handle':local.dxf.handle};nodes.append({'node_id':nid,'boundary_type':'unresolved_source_terminal','system':system,'x':10,'y':ny,'source_endpoint_annotation':ann,'source_annotation_reference':ref});edges.append({'edge_id':eid,'system':system,'source_handles':[target.dxf.handle],'attribute_paths':[[[0,y],[20,y]]]});services[system]={'endpoint_node_id':nid,'annotated_target_edge_id':eid,'equipment_port_id':'P'+str(i)}
  self.g={'metadata':{'source_sha256':'S'},'nodes':nodes,'edges':edges,'sourceLabeledEquipmentGroups':[{'label':'3F-A1','equipment_id':'EQ','hydraulic_connection_confirmed':False,'services':services}]}
 def test_named_interface_preserves_physical_graph(self):
  out,a=attach(self.g,self.doc,'S');self.assertEqual(a['classified_interfaces'],2);self.assertEqual(out['edges'],self.g['edges']);self.assertEqual(out['nodes'][1]['resolution_state'],'source_declared_connection_route_pending');self.assertFalse(out['sourceDeclaredConnections'][0]['physical_route_verified'])
 def test_wrong_service_rejected(self):
  self.g['nodes'][1]['system']='return'
  with self.assertRaises(ValueError):attach(self.g,self.doc,'S')
 def test_changed_note_rejected(self):
  self.doc.entitydb[self.g['nodes'][1]['source_annotation_reference']['text_handle']].dxf.text='接至3F-A2'
  with self.assertRaises(ValueError):attach(self.g,self.doc,'S')
 def test_changed_path_rejected(self):
  self.g['edges'][0]['attribute_paths']=[[[0,30],[20,30]]]
  with self.assertRaises(ValueError):attach(self.g,self.doc,'S')
if __name__=='__main__':unittest.main()
