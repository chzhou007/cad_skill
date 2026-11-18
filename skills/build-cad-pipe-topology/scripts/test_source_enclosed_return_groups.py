import copy,unittest,ezdxf
from source_enclosed_return_groups import attach
class EnclosedReturnGroups(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();self.d.layers.new('HVAC-D-CWR');b=self.d.blocks.new('LT');b.add_lwpolyline([(0,0),(10,0),(10,5),(0,5)],close=True);m=self.d.modelspace();c1=m.add_blockref('LT',(0,0));c2=m.add_blockref('LT',(0,5));tag=m.add_text('CT1',dxfattribs={'insert':(1,1)});tower={'node_id':'CT1','node_type':'equipment','source_tag_handle':tag.dxf.handle,'source_bounds':[0,0,10,10]};nodes=[tower];pts=[(2,2),(3,2),(4,2),(5,2),(6,2),(6,4),(5,4),(4,4),(3,4)]
  for i,(x,y) in enumerate(pts):nodes.append({'node_id':f'N{i}','node_type':'tee' if i<5 else 'virtual_equipment','system':'cooling_return','x':x,'y':y})
  nodes.append({'node_id':'OUT','node_type':'tee','system':'cooling_return','x':-1,'y':2});edges=[]
  for i in range(9):
   line=m.add_line(pts[i],pts[(i+1)%9],dxfattribs={'layer':'HVAC-D-CWR'});edges.append({'edge_id':f'E{i}','start_node_id':f'N{i}','end_node_id':f'N{(i+1)%9}','system':'cooling_return','source_handles':[line.dxf.handle],'path_points':[list(pts[i]),list(pts[(i+1)%9])]})
  edges.append({'edge_id':'ENTRY','start_node_id':'OUT','end_node_id':'N0','system':'cooling_return','source_handles':[],'path_points':[[-1,2],[2,2]]});self.g={'nodes':nodes,'edges':edges,'metadata':{'original_dxf_sha256':'source'}};self.r=[{'tower_id':'CT1','original_02_cell_handles':[c1.dxf.handle,c2.dxf.handle],'original_02_tag_handle':tag.dxf.handle,'internal_junction_id':'N0','current_edge_id':'ENTRY'}];self.devices=[{'device_name':f'D{i}','edge_id':f'E{i}','equipment_type':'Butterfly Valve' if i<4 else 'Metal Flexible Joint'} for i in range(8)]
 def test_group_is_read_only_except_tower_annotation(self):
  before=copy.deepcopy(self.g);g,groups=attach(self.g,self.d,self.devices,self.r,'source','graph');self.assertEqual(self.g,before);self.assertEqual(g['edges'],before['edges']);self.assertEqual(len(groups[0]['node_ids']),9);self.assertEqual(len(groups[0]['component_names']),8);self.assertIn('ownership',groups[0]['semantics']);self.assertFalse(g['metadata']['hil_ready'])
 def test_refuses_wrong_layer_and_missing_component(self):
  doc=copy.deepcopy(self.d);doc.entitydb[self.g['edges'][0]['source_handles'][0]].dxf.layer='0'
  with self.assertRaises(ValueError):attach(self.g,doc,self.devices,self.r,'source','graph')
  with self.assertRaisesRegex(ValueError,'component group mismatch'):attach(self.g,self.d,self.devices[:-1],self.r,'source','graph')
 def test_refuses_false_enclosure_and_group_collision(self):
  g=copy.deepcopy(self.g);g['nodes'][0]['source_bounds']=[0,0,11,10]
  with self.assertRaisesRegex(ValueError,'enclosure mismatch'):attach(g,self.d,self.devices,self.r,'source','graph')
  with self.assertRaisesRegex(ValueError,'overlapping candidate groups'):attach(self.g,self.d,self.devices,self.r*2,'source','graph')
 def test_refuses_wrong_source_identity(self):
  with self.assertRaisesRegex(ValueError,'source identity mismatch'):attach(self.g,self.d,self.devices,self.r,'other','graph')
if __name__=='__main__':unittest.main()
