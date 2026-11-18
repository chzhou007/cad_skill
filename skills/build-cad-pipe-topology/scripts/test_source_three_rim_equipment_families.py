import unittest,ezdxf
from source_three_rim_equipment_families import attach
class ThreeRimTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();r=m.add_circle((0,0),85,dxfattribs={'layer':'暖通-冷冻水回水管'});s=m.add_circle((0,-170),85,dxfattribs={'layer':'暖通-冷冻水供水管'});nodes=[{'node_id':'EQ','node_type':'equipment'},{'node_id':'X','node_type':'tee'},{'node_id':'Y','node_type':'tee'}];edges=[];rim=[]
  for i,(x,y,other) in enumerate([(0,85,'X'),(85,0,'EQ'),(0,-85,'Y')]):
   l=m.add_line((x,y),(x+(20 if x else 0),y+(20 if y>0 else -20 if y<0 else 0)),dxfattribs={'layer':'暖通-冷冻水回水管'});nid='U'+str(i);nodes.append({'node_id':nid,'node_type':'virtual_equipment','boundary_type':'unresolved_source_terminal','system':'return','x':x,'y':y});edges.append({'edge_id':'E'+str(i),'start_node_id':nid,'end_node_id':other,'system':'return','source_handles':[l.dxf.handle]});rim.append({'node_id':nid})
  for n in nodes:
   n.setdefault('x',1000);n.setdefault('y',1000)
  self.g={'metadata':{'source_sha256':'S'},'nodes':nodes,'edges':edges};self.ev={'source_sha256':'S','graph_sha256':'G','records':[{'circle_handle':r.dxf.handle,'supply_tangent_circles':[{'handle':s.dxf.handle}],'rim_nodes':rim}]}
 def test_groups_without_hydraulic_edges(self):
  o,a=attach(self.g,self.doc,self.ev,'S','G');self.assertEqual(a['return_rim_endpoints'],3);self.assertEqual(o['edges'],self.g['edges']);self.assertFalse(o['sourceThreeRimEquipmentFamilies'][0]['cross_system_connection_confirmed'])
 def test_rejects_competing_system(self):
  self.g['nodes'][3]['system']='supply'
  with self.assertRaises(ValueError):attach(self.g,self.doc,self.ev,'S','G')
 def test_rejects_changed_tangency(self):
  self.doc.entitydb[self.ev['records'][0]['supply_tangent_circles'][0]['handle']].dxf.center=(0,-180)
  with self.assertRaises(ValueError):attach(self.g,self.doc,self.ev,'S','G')
if __name__=='__main__':unittest.main()
