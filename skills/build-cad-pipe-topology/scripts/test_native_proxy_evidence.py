import unittest
from native_proxy_evidence import native_inline_candidates,inside_segment_bounds
class NativeProxyTests(unittest.TestCase):
 def test_native_bounds_and_axis_preserve_owner_without_healing(self):
  edges=[{'edge_id':'E1','path_points':[[.1,-3],[.1,3]]},{'edge_id':'E2','path_points':[[3,-3],[3,3]]}]
  self.assertEqual(native_inline_candidates(edges,[-1,-1,1,1],[0,2]),['E1'])
 def test_crossing_perpendicular_pipe_is_not_valve_owner(self):
  self.assertEqual(native_inline_candidates([{'edge_id':'E','path_points':[[-3,0],[3,0]]}],[-1,-1,1,1],[0,2]),[])
 def test_two_compatible_pipes_stay_ambiguous(self):
  edges=[{'edge_id':str(x),'path_points':[[x,-3],[x,3]]}for x in [0,.5]]
  self.assertEqual(len(native_inline_candidates(edges,[-1,-1,1,1],[0,2])),2)
 def test_rotation_and_mirror(self):
  edges=[{'edge_id':'E','path_points':[[3,.1],[-3,.1]]}]
  self.assertEqual(native_inline_candidates(edges,[-1,-1,1,1],[-2,0]),['E'])
 def test_bbox_overlap_without_segment_contact_rejected(self):
  self.assertFalse(inside_segment_bounds([-2,.5],[.5,2],[-1,-1,1,1]))
if __name__=='__main__':unittest.main()
