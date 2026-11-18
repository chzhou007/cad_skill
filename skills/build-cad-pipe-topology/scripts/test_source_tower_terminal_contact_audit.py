import copy,types,unittest,ezdxf
from source_tower_terminal_contact_audit import analyze,attach,_line_distance
class Note:
 def dxftype(self):return 'MTEXT'
 def plain_text(self):return '冷却塔与管道间采用软连接方式。'
class TerminalAudit(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();self.d.layers.new('HVAC-D-CWR');b=self.d.blocks.new('LT');b.add_circle((0,0),1);m=self.d.modelspace();c1=m.add_blockref('LT',(0,0));c2=m.add_blockref('LT',(0,10));self.nodes=[];edges=[]
  for i,y in enumerate([0,1,9,10]):
   line=m.add_line((2,y),(5,y),dxfattribs={'layer':'HVAC-D-CWR'});self.nodes.append({'node_id':f'N{i}','node_type':'virtual_equipment','x':2,'y':y});edges.append({'edge_id':f'E{i}','start_node_id':f'N{i}','end_node_id':f'T{i}','system':'cooling_return','source_handles':[line.dxf.handle]})
  self.group={'source_sha256':'sha','status':'source_enclosure_group_candidate_not_bound','source_cell_handles':[c1.dxf.handle,c2.dxf.handle],'node_ids':[f'N{i}' for i in range(4)],'edge_ids':[f'E{i}' for i in range(4)]};self.g={'metadata':{'original_dxf_sha256':'sha'},'nodes':[{'node_id':'CT','node_type':'equipment','source_enclosed_return_group':self.group}]+self.nodes,'edges':edges};self.design=types.SimpleNamespace(entitydb={'143':Note()})
 def test_audit_does_not_bind_ports_or_modify_edges(self):
  old=copy.deepcopy(self.g);r=analyze(self.g,self.d,self.design,'sha','design','graph');self.assertEqual(len(r),4);self.assertEqual(self.g,old);self.assertEqual(r[0]['nearest_primitive_distance_2d'],1);self.assertEqual(r[0]['remote_connection'],'unconfirmed');updated=attach(self.g,r);self.assertEqual(updated['edges'],old['edges']);self.assertEqual(updated['nodes'][0]['source_tower_design_requirement']['status'],'project_design_statement_not_port_binding');self.assertFalse(updated['metadata']['hil_ready'])
 def test_bad_source_or_double_incident_rejected(self):
  with self.assertRaisesRegex(ValueError,'source identity mismatch'):analyze(self.g,self.d,self.design,'wrong','design','graph')
  self.g['edges'].append(dict(self.g['edges'][0],edge_id='OTHER'))
  with self.assertRaisesRegex(ValueError,'incidence changed'):analyze(self.g,self.d,self.design,'sha','design','graph')
 def test_line_distance_clips_to_segment(self):
  a=types.SimpleNamespace(x=0,y=0);b=types.SimpleNamespace(x=10,y=0);self.assertEqual(_line_distance(5,3,a,b),3);self.assertEqual(_line_distance(13,4,a,b),5)
 def test_source_circle_is_recorded_without_binding_a_port(self):
  circle=self.d.modelspace().add_circle((2,0),.5,dxfattribs={'layer':'HVAC-D-CWR'})
  self.d.modelspace().add_circle((2.2,0),.5,dxfattribs={'layer':'HVAC-D-CWR'})
  r=analyze(self.g,self.d,self.design,'sha','design','graph')
  self.assertEqual([x['handle'] for x in r[0]['source_centered_circles']],[circle.dxf.handle])
  self.assertEqual(r[1]['source_centered_circles'],[])
  self.assertEqual(r[0]['remote_connection'],'unconfirmed')
 def test_offset_circle_requires_line_center_contact_and_same_layer(self):
  c=self.d.modelspace().add_circle((3,0),2,dxfattribs={'layer':'HVAC-D-CWR'})
  self.d.modelspace().add_circle((3,1),2,dxfattribs={'layer':'HVAC-D-CWR'})
  self.d.modelspace().add_circle((3,0),2,dxfattribs={'layer':'0'})
  r=analyze(self.g,self.d,self.design,'sha','design','graph')
  self.assertEqual([x['handle'] for x in r[0]['source_overlapping_circle_line_witnesses']],[c.dxf.handle])
  self.assertEqual(r[0]['source_overlapping_circle_line_witnesses'][0]['meaning'],'source_geometry_only_unresolved')
  self.assertEqual(r[0]['remote_connection'],'unconfirmed')
if __name__=='__main__':unittest.main()
