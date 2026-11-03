import unittest
import pipe_geometry as pg
from topology_normalization import snap_near_junction_endpoints
class NearJunctions(unittest.TestCase):
 def setUp(self):pg.set_tolerance(.05);self.cfg=dict(maximum_gap=10,maximum_ratio=.05,minimum_angle_degrees=20)
 def tearDown(self):pg.set_tolerance(.5)
 def case(self):return [dict(a=(0,-100),b=(0,-2.4),system='supply',handle='tail'),dict(a=(-100,0),b=(100,0),system='supply',handle='main')]
 def test_near_tail_makes_three_real_directions(self):
  rows,a=snap_near_junction_endpoints(self.case(),self.cfg);self.assertEqual(len(a),1);self.assertAlmostEqual(rows[0]['b'][1],0);v,p,ad=pg.build_network(rows);self.assertTrue(any(len(x)==3 for x in ad.values()))
 def test_conflicting_system_is_not_joined(self):
  s=self.case();s[1]['system']='return';self.assertFalse(snap_near_junction_endpoints(s,self.cfg)[1])
 def test_tiny_overshoot_is_trimmed_to_three_ray_contact(self):
  s=self.case();s[0]['b']=(0,.8);rows,a=snap_near_junction_endpoints(s,self.cfg);self.assertEqual(a[0]['action'],'trim');self.assertAlmostEqual(rows[0]['b'][1],0)
 def test_ordinary_large_gap_is_not_joined(self):
  s=self.case();s[0]['b']=(0,-20);self.assertFalse(snap_near_junction_endpoints(s,self.cfg)[1])
 def test_discovery_outside_verified_precision_is_explicit_pending(self):
  s=self.case();s[0]['b']=(0,-4);self.cfg.update(maximum_gap=3,discovery_maximum_gap=10);rows,a=snap_near_junction_endpoints(s,self.cfg);self.assertEqual(rows[0]['b'],s[0]['b']);self.assertEqual(a[0]['status'],'pending')
 def test_protected_device_gap_is_not_joined(self):
  self.cfg['protected_points']=[(0,-1)];self.assertFalse(snap_near_junction_endpoints(self.case(),self.cfg)[1])
if __name__=='__main__':unittest.main()
