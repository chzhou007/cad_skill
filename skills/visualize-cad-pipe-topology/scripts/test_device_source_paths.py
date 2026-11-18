import copy,unittest,ezdxf
from device_source_paths import device_source_paths

def fixture():
 d=ezdxf.new();d.blocks.new('J');b=d.blocks.new('EQ');circle=b.add_circle((0,0),1);line=b.add_line((0,0),(10,0),dxfattribs={'layer':'空调冷冻水供水'});outer=b.add_line((20,0),(30,0),dxfattribs={'layer':'空调冷冻水供水'});joint=b.add_blockref('J',(10,0));root=d.modelspace().add_blockref('EQ',(100,200),dxfattribs={'rotation':90,'xscale':-1})
 x={'status':'source_drawn_line_with_joint_evidence_unreviewed','source_sha256':'S','changes_topology':False,'physical_port_verified':False,'physical_length':'unknown','source_line_chain':[root.dxf.handle,line.dxf.handle],'source_circle_chain':[root.dxf.handle,circle.dxf.handle],'source_joint_chain':[root.dxf.handle,joint.dxf.handle],'source_outer_line_chain':[root.dxf.handle,outer.dxf.handle]}
 return d,{'source_device_extension':x,'source_insert_handle':root.dxf.handle,'system':'supply','physical_length':'unknown','path_length_complete':False}
class DevicePathTest(unittest.TestCase):
 def test_mirror_and_rotation(self):
  d,e=fixture();p=device_source_paths(d,e,'S')[0];self.assertAlmostEqual(p[0][0],100);self.assertAlmostEqual(p[0][1],200);self.assertAlmostEqual(p[1][0],100);self.assertAlmostEqual(p[1][1],190)
 def test_missing_or_wrong_source_fails_closed(self):
  d,e=fixture()
  with self.assertRaisesRegex(ValueError,'evidence'):device_source_paths(d,e,'wrong')
  x=copy.deepcopy(e);x['source_device_extension']['source_line_chain'][1]=x['source_device_extension']['source_circle_chain'][1]
  with self.assertRaisesRegex(ValueError,'child'):device_source_paths(d,x,'S')
  x=copy.deepcopy(e);x['system']='return'
  with self.assertRaisesRegex(ValueError,'system'):device_source_paths(d,x,'S')
 def test_empty(self):self.assertEqual(device_source_paths(None,{},'S'),[])
 def test_exploded_chain_uses_native_line_and_preserves_unknown_port(self):
  d=ezdxf.new();block=d.blocks.new('J');m=d.modelspace()
  for x in (0,10):block.add_line((x,-1),(x,1))
  for i in range(4):block.add_arc((i,5),1,0,90)
  j=m.add_blockref('J',(0,0));a=m.add_line((-10,0),(0,0),dxfattribs={'layer':'空调冷冻水供水'});b=m.add_line((10,0),(20,0),dxfattribs={'layer':'空调冷冻水供水'});c=m.add_circle((-10,0),2)
  r={'status':'native_chain_geometry_unreviewed','source_sha256':'S','physical_port_verified':False,'physical_length':'unknown','additional_line_length_not_added':True,'inner_line_handle':a.dxf.handle,'outer_line_handle':b.dxf.handle,'joint_handle':j.dxf.handle,'circle_handle':c.dxf.handle,'inner_line_endpoints':[list(a.dxf.start),list(a.dxf.end)]};e={'source_exploded_device_chain':r,'system':'supply','physical_length':'unknown','path_length_complete':False}
  self.assertEqual(device_source_paths(d,e,'S'),[[[-10.,0.],[0.,0.]]])
  with self.assertRaises(ValueError):device_source_paths(d,e,'wrong')
  bad=copy.deepcopy(e);bad['source_exploded_device_chain']['inner_line_endpoints'][0][0]=-11
  with self.assertRaises(ValueError):device_source_paths(d,bad,'S')
  bad=copy.deepcopy(e);bad['system']='return'
  with self.assertRaises(ValueError):device_source_paths(d,bad,'S')
  bad=copy.deepcopy(e);bad['source_exploded_device_chain']['physical_port_verified']=True
  with self.assertRaises(ValueError):device_source_paths(d,bad,'S')
if __name__=='__main__':unittest.main()
