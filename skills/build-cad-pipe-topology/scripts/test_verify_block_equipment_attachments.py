import copy,unittest,ezdxf
from verify_block_equipment_attachments import verify

class BlockAttachmentTest(unittest.TestCase):
 def fixture(self):
  d=ezdxf.new();blk=d.blocks.new('DEVICE');lines=[((0,0),(10,0)),((10,0),(10,10)),((10,10),(0,10)),((0,10),(0,0))]
  for _ in range(3):
   for a,b in lines:blk.add_line(a,b,dxfattribs={'layer':'空调平面'})
  circles=[blk.add_circle((3,3),1,dxfattribs={'layer':'空调平面'}),blk.add_circle((7,3),1,dxfattribs={'layer':'空调平面'})];root=d.modelspace().add_blockref('DEVICE',(0,0));d.modelspace().add_text('EQ',dxfattribs={'insert':(1,-2)});nodes=[{'node_id':'EQ','node_type':'equipment','x':5,'y':5},{'node_id':'T1','node_type':'tee','x':-2,'y':3},{'node_id':'T2','node_type':'tee','x':12,'y':3}];edges=[];j=[]
  for i,system in enumerate(('supply','return')):
   eid='E'+str(i);match={'inner_line_chain':[root.dxf.handle,'I'+str(i)],'circle_chain':[root.dxf.handle,circles[i].dxf.handle],'joint_chain':[root.dxf.handle,'J'+str(i)],'outer_line_chain':[root.dxf.handle,'O'+str(i)],'component_name':'EQ/joint'+str(i)};ext={'status':'source_drawn_line_with_joint_evidence_unreviewed','source_sha256':'S','physical_port_verified':False,'physical_length':'unknown','source_line_chain':match['inner_line_chain'],'source_circle_chain':match['circle_chain'],'source_joint_chain':match['joint_chain'],'source_outer_line_chain':match['outer_line_chain'],'joint_component_name':match['component_name']};edges.append({'edge_id':eid,'start_node_id':'EQ','end_node_id':'T'+str(i+1),'system':system,'source_insert_handle':root.dxf.handle,'device_label':'EQ','connection_mode':'direct_existing_cad_branch','attribute_paths':[[[0,0],[5,5]]],'source_device_extension':ext});j.append({'edge_id':eid,'system':system,'device_label':'EQ','status':'unique_source_symbol_evidence','matches':[match]})
  g={'nodes':nodes,'edges':edges};joint={'status':'native_joint_geometry_unreviewed','source_sha256':'S','graph_sha256':'OLD','graph_mutated':False,'hil_ready':False,'edges':j};return d,copy.deepcopy(g),g,joint
 def test_two_distinct_systems_support_one_logical_attachment(self):
  d,o,g,j=self.fixture();r=verify(d,o,g,j,'S','OLD','NEW');self.assertEqual(len(r['records']),1);self.assertEqual(len(r['records'][0]['edges']),2);self.assertFalse(r['records'][0]['physical_port_verified']);self.assertFalse(r['human_accepted'])
 def test_competing_body_and_stale_geometry_fail(self):
  d,o,g,j=self.fixture();g['nodes'].append({'node_id':'OTHER','node_type':'equipment','x':6,'y':6})
  with self.assertRaisesRegex(ValueError,'ambiguous'):verify(d,o,g,j,'S','OLD','NEW')
  g['nodes'].pop();g['edges'][0]['attribute_paths']=[[[1,1],[5,5]]]
  with self.assertRaisesRegex(ValueError,'changed edge'):verify(d,o,g,j,'S','OLD','NEW')
 def test_shared_circle_or_changed_system_cannot_pass(self):
  d,o,g,j=self.fixture();g['edges'][1]['source_device_extension']['source_circle_chain']=g['edges'][0]['source_device_extension']['source_circle_chain'];j['edges'][1]['matches'][0]['circle_chain']=g['edges'][0]['source_device_extension']['source_circle_chain']
  with self.assertRaisesRegex(ValueError,'circles'):verify(d,o,g,j,'S','OLD','NEW')
if __name__=='__main__':unittest.main()
