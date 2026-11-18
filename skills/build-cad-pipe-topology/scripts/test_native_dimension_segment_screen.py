import copy,unittest
import ezdxf
from native_dimension_segment_screen import screen

class DimensionSegmentScreenTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();self.dim=self.doc.modelspace().add_linear_dim(base=(0,10),p1=(0,0),p2=(100,0),angle=0).dimension
  self.graph={'metadata':{'source_sha256':'s'},'edges':[{'edge_id':'E','system':'supply','attribute_paths':[[[0,0],[100,0]]]}]};self.policy={'source_sha256':'s','graph_sha256':'g'}
 def test_exact_geometry_stays_unaccepted(self):
  before=copy.deepcopy(self.graph);r=screen(self.doc,self.graph,self.policy,'s','g');self.assertEqual(r['records'][0]['status'],'unique_exact_segment_geometry_candidate');self.assertFalse(r['human_accepted']);self.assertEqual(before,self.graph)
 def test_projected_distance_between_different_points_is_not_pipe_length(self):
  self.dim.dxf.defpoint3=(100,50,0);r=screen(self.doc,self.graph,self.policy,'s','g');self.assertEqual(r['records'][0]['status'],'no_exact_segment_geometry');self.assertEqual(r['records'][0]['matches'],[])
 def test_duplicate_parallel_edges_are_ambiguous(self):
  self.graph['edges'].append(dict(self.graph['edges'][0],edge_id='E2',system='return'));self.assertEqual(screen(self.doc,self.graph,self.policy,'s','g')['records'][0]['status'],'ambiguous_exact_segment_geometry')
 def test_stale_and_unsupported_dimension(self):
  with self.assertRaises(ValueError):screen(self.doc,self.graph,self.policy,'s','old')
  self.dim.dxf.dimtype=1;self.assertEqual(screen(self.doc,self.graph,self.policy,'s','g')['records'][0]['status'],'unsupported_dimension_geometry')
if __name__=='__main__':unittest.main()
