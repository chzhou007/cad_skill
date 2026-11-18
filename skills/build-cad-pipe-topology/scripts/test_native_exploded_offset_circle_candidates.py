import copy,unittest
from native_exploded_offset_circle_candidates import collect
from test_native_exploded_device_joint_evidence import ExplodedDeviceJointTests
from native_line_path_evidence import LAYERS

class ExplodedOffsetTests(unittest.TestCase):
 def setUp(self):
  self.f=ExplodedDeviceJointTests();self.f.setUp();self.f.c.dxf.center=(-9.75,0);self.f.p['max_radius_ratio']=.2
 def test_offset_is_candidate_only(self):
  f=self.f;before=copy.deepcopy(f.g);r=collect(f.doc,f.g,f.inv,f.p,f.h);x=r['records'][0];self.assertEqual(x['status'],'unique_offset_candidate_not_connection');self.assertAlmostEqual(x['candidates'][0]['offset_radius_ratio'],.125);self.assertFalse(x['physical_port_verified']);self.assertFalse(r['hil_ready']);self.assertEqual(f.g,before)
 def test_competing_circle_and_wrong_z_are_not_unique(self):
  f=self.f;f.doc.modelspace().add_circle((-9.8,0),2);self.assertEqual(collect(f.doc,f.g,f.inv,f.p,f.h)['records'][0]['status'],'ambiguous_or_no_candidate')
  for c in f.doc.modelspace().query('CIRCLE'):c.dxf.center=(c.dxf.center.x,c.dxf.center.y,1)
  self.assertEqual(collect(f.doc,f.g,f.inv,f.p,f.h)['records'][0]['status'],'ambiguous_or_no_candidate')
 def test_system_and_stale_inputs_fail(self):
  f=self.f;f.b.dxf.layer=LAYERS['return']
  with self.assertRaises(ValueError):collect(f.doc,f.g,f.inv,f.p,f.h)
  f.b.dxf.layer=LAYERS['supply']
  with self.assertRaises(ValueError):collect(f.doc,f.g,f.inv,f.p,dict(f.h,graph_sha256='old'))
 def test_offset_limit_and_exact_circle_are_not_inferred(self):
  f=self.f;f.p['max_radius_ratio']=.1;self.assertEqual(collect(f.doc,f.g,f.inv,f.p,f.h)['records'][0]['status'],'ambiguous_or_no_candidate');f.c.dxf.center=(-10,0);f.p['max_radius_ratio']=.2;self.assertEqual(collect(f.doc,f.g,f.inv,f.p,f.h)['records'][0]['status'],'ambiguous_or_no_candidate')
if __name__=='__main__':unittest.main()
