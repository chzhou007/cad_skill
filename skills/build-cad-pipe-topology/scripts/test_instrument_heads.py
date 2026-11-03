import unittest,ezdxf
from instrumentation import instrument_head_match,source_gauges,bounds
class HeadAssemblyContracts(unittest.TestCase):
 def fixture(self,native=False,combined=False,rotate=0,mirror=False,extra=False,wire=True):
  d=ezdxf.new();m=d.modelspace();b=d.blocks.new('SENSOR');b.add_lwpolyline([(0,-5),(10,-5),(10,5),(0,5)],close=True);b.add_line((0,0),(-20,0)if native else(25,0));ins=m.add_blockref('SENSOR',(0,0));circle=m.add_circle((-30,0),10);text=m.add_text('PIT-A',dxfattribs={'insert':(-34,-1),'height':2})
  if wire and not native:m.add_line((-40,.05)if combined else(-20,0),(1,0))
  if extra:m.add_circle((-10,0),10);m.add_text('FIT-A',dxfattribs={'insert':(-14,-1),'height':2})
  if rotate or mirror:
   from ezdxf.math import Matrix44
   mat=Matrix44.chain(Matrix44.scale(-1 if mirror else 1,1,1),Matrix44.z_rotate(rotate))
   for e in list(m):e.transform(mat)
  s=dict(handle=ins.dxf.handle,entity=ins,block='传感器',bounds=bounds(ins));return d,s,circle.dxf.handle
 def test_modelspace_leader(self):
  d,s,h=self.fixture();self.assertEqual(instrument_head_match(s,d,source_gauges(d))['source_head_handle'],h)
 def test_native_insert_leader(self):
  d,s,h=self.fixture(native=True);r=instrument_head_match(s,d,source_gauges(d));self.assertEqual(r['source_head_handle'],h);self.assertTrue(r['native_block_lead'])
 def test_combined_diameter_and_leader(self):
  d,s,h=self.fixture(combined=True);self.assertEqual(instrument_head_match(s,d,source_gauges(d))['source_head_handle'],h)
 def test_rotated_and_mirrored_native_leader(self):
  import math
  d,s,h=self.fixture(native=True,rotate=math.pi/2,mirror=True);self.assertEqual(instrument_head_match(s,d,source_gauges(d))['source_head_handle'],h)
 def test_multiple_strokes_to_same_head_not_false_ambiguity(self):
  d,s,h=self.fixture(native=True);d.modelspace().add_line((-40,0),(0,0));r=instrument_head_match(s,d,source_gauges(d));self.assertEqual(r['status'],'complete_tagged_head');self.assertEqual(r['candidate_head_handles'],[h])
 def test_two_different_heads_stay_ambiguous(self):
  d,s,h=self.fixture(native=True,extra=True);r=instrument_head_match(s,d,source_gauges(d));self.assertEqual(r['status'],'pending_ambiguous_heads');self.assertNotIn('source_head_handle',r)
 def test_nearby_head_without_connected_leader_rejected(self):
  d,s,h=self.fixture(wire=False);self.assertEqual(instrument_head_match(s,d,source_gauges(d))['status'],'pending_no_proven_head')
if __name__=='__main__':unittest.main(verbosity=2)
