import unittest,math
import ezdxf
import pipe_geometry as pg
from exploded_templates import recover_exploded_templates

class ExplodedTemplatesTest(unittest.TestCase):
 def setUp(self):pg.set_tolerance(.0001)
 def tearDown(self):pg.set_tolerance(.5)
 def fixture(self,missing=False):
  d=ezdxf.new();bl=d.blocks.new('hose');pairs=[((0,0),(0,2)),((3,0),(3,2)),((0,1),(.75,2)),((.75,2),(2.25,0)),((2.25,0),(3,1))]
  for a,b in pairs:bl.add_line(a,b)
  for a,b in pairs[:-1]if missing else pairs:
   f=lambda p:(10-2*p[1],20-2*p[0])
   d.modelspace().add_line(f(a),f(b),dxfattribs={'layer':'different-drafting-layer'})
  return d
 def test_complete_rotated_mirrored_scaled_across_layer(self):
  r=recover_exploded_templates(self.fixture(),['hose'],[]);self.assertEqual(len(r),1);self.assertEqual(len(r[0]['source_handles']),5)
 def test_partial_rejected(self):self.assertEqual(recover_exploded_templates(self.fixture(True),['hose'],[]),[])
 def sensor(self,head):
  d=ezdxf.new();b=d.blocks.new('传感器');pts=[(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]
  for target in [b,d.modelspace()]:target.add_lwpolyline(pts,close=True);target.add_line((0,-.5),(0,-1.4131444826))
  if head:
   m=d.modelspace();m.add_circle((-1.5,0),.5,dxfattribs={'layer':'head-layer'});m.add_line((-.5,0),(-1,0),dxfattribs={'layer':'head-layer'});m.add_text('SFIT-X2',dxfattribs={'height':.1,'insert':(-1.7,0),'layer':'head-layer'})
  return d
 def test_square_with_lead_without_tagged_head_rejected(self):self.assertEqual(recover_exploded_templates(self.sensor(False),['传感器'],[]),[])
 def test_sensor_cross_layer_complete_tagged_head(self):
  r=recover_exploded_templates(self.sensor(True),['传感器'],[]);self.assertEqual(len(r),1);self.assertEqual(r[0]['head_evidence']['source_head_tag'],'SFIT-X2')

if __name__=='__main__':unittest.main()
