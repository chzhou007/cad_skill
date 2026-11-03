import unittest
from double_line_pipes import discover_straight_centerlines
C=dict(tolerance=.01,minimum_width=1,maximum_width=20,minimum_overlap=50,minimum_overlap_ratio=.8)
def wall(a,b,g='supply'):return dict(a=a,b=b,group=g,source_chain=[str(a),str(b)])
class DoubleWalls(unittest.TestCase):
 def test_straight_pair_center_is_source_supported(self):
  r=discover_straight_centerlines([wall((0,0),(100,0)),wall((100,10),(0,10))],C);self.assertEqual(r[0]['status'],'candidate');self.assertEqual(r[0]['a'],[0,5]);self.assertEqual(r[0]['b'],[100,5])
 def test_different_groups_not_paired(self):self.assertFalse(discover_straight_centerlines([wall((0,0),(100,0)),wall((0,10),(100,10),'return')],C))
 def test_third_parallel_wall_prevents_false_wide_pipe(self):
  r=discover_straight_centerlines([wall((0,0),(100,0)),wall((0,5),(100,5)),wall((0,10),(100,10))],C);self.assertFalse(any(c['status']=='candidate'for c in r))
 def test_nonoverlap_not_paired(self):self.assertFalse(discover_straight_centerlines([wall((0,0),(100,0)),wall((150,10),(250,10))],C))
 def test_short_graphics_not_pipe(self):self.assertFalse(discover_straight_centerlines([wall((0,0),(10,0)),wall((0,5),(10,5))],C))
 def test_parallel_projection_not_crossing_connection(self):self.assertFalse(discover_straight_centerlines([wall((0,0),(100,0)),wall((0,10),(100,20))],C))
 def test_config_required(self):
  with self.assertRaises(ValueError):discover_straight_centerlines([],None)
if __name__=='__main__':unittest.main()
