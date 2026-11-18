import unittest,ezdxf
from convert_user_confirmed_terminal_boundaries import convert

class TerminalBoundariesTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.c=m.add_circle((0,0),80,dxfattribs={'layer':'空调冷冻水供水'});self.pipe=m.add_line((0,0),(0,200),dxfattribs={'layer':'空调冷冻水供水'});self.mark=[m.add_line((i,0),(i,1),dxfattribs={'layer':'空调立管、水平支管'}) for i in range(4)]
  self.g={'nodes':[{'node_id':'T1','node_type':'tee','system':'supply','x':0,'y':200},{'node_id':'V1','node_type':'virtual_equipment','subtype':'out_of_plane_interface','system':'supply','x':0,'y':0,'ports':[{'port_id':'P1','system':'supply'}]}],'edges':[{'edge_id':'E1','start_node_id':'T1','end_node_id':'V1','end_port_id':'P1','edge_type':'tee_to_virtual_equipment','system':'supply','source_handles':[self.pipe.dxf.handle]}],'boundary_anchors':[]}
  self.row={'circle_handle':self.c.dxf.handle,'graph_id':'V1','edge_id':'E1','source_layer':'空调冷冻水供水'};self.man={'source_sha256':'s','graph_sha256':'g','rows':[self.row]}
  self.sig={'source_sha256':'s','graph_sha256':'g','review_manifest_sha256':'m','rows':[{'circle_handle':self.c.dxf.handle,'graph_id':'V1','edge_id':'E1','system':'supply','radius':80,'symbol_lines':[{'handle':e.dxf.handle,'relative_xyz':[[float(i),0.,0.],[float(i),1.,0.]]} for i,e in enumerate(self.mark)],'connected_native_pipe':{'handle':self.pipe.dxf.handle,'xy_offset':0.,'relative_z':0.}}]}
  self.confirm={'answer':'都是非节点边界，类似于管道变径，连接着末端空调'};self.pol={'source_sha256':'s','graph_sha256':'g','manifest_sha256':'m','confirmation_sha256':'c','circle_handles':[self.c.dxf.handle]}
 def run_convert(self):return convert(self.doc,self.g,self.man,self.sig,self.confirm,self.pol)
 def test_node_becomes_boundary_and_preserves_port_history(self):
  out,changes,_=self.run_convert();self.assertEqual(len(changes),1);self.assertEqual(out['edges'][0]['end_boundary_id'],'A-V1');self.assertNotIn('end_port_id',out['edges'][0]);a=out['boundary_anchors'][0];self.assertEqual(a['legacy_edge_port_id'],'P1');self.assertEqual(a['destination_instance'],'unknown');self.assertEqual(out['edges'][0]['edge_type'],'source_boundary_edge');self.assertEqual(self.g['edges'][0]['end_node_id'],'V1')
 def test_wrong_system_or_geometry_fails(self):
  self.g['edges'][0]['system']='return'
  with self.assertRaises(ValueError):self.run_convert()
  self.g['edges'][0]['system']='supply';self.mark[0].dxf.end=(0,2,0)
  with self.assertRaises(ValueError):self.run_convert()
 def test_unbound_port_or_unconfirmed_scope_fails(self):
  self.g['edges'][0]['end_port_id']='wrong'
  with self.assertRaises(ValueError):self.run_convert()
  self.g['edges'][0]['end_port_id']='P1';self.pol['circle_handles']=[]
  with self.assertRaises(ValueError):self.run_convert()
if __name__=='__main__':unittest.main()
