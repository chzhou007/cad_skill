import copy,unittest,ezdxf
from partial_native_line_coverage import intervals,audit

class PartialCoverageTest(unittest.TestCase):
 def test_partial_reversed_crossing_and_overlapping(self):
  lines=[('A',(0,0),(7,0)),('B',(9,0),(5,0)),('cross',(4,-3),(4,3)),('parallel',(0,1),(10,1))]
  r=intervals((0,0),(10,0),lines)
  self.assertEqual([(x['start_distance'],x['end_distance'],x['status']) for x in r],[(0,5,'unique_source_line'),(5,7,'ambiguous_overlapping_lines'),(7,9,'unique_source_line'),(9,10,'unwitnessed')])
 def test_rotated_and_mirror(self):
  r=intervals((10,10),(0,0),[('L',(9,9),(1,1))]);self.assertAlmostEqual(r[1]['drawing_length'],8*2**.5);self.assertEqual(r[1]['source_handles'],['L'])
 def test_pinned_evidence_and_segment_change_fail_closed(self):
  d=ezdxf.new();d.modelspace().add_line((0,0),(8,0),dxfattribs={'layer':'空调冷冻水供水'});d.modelspace().add_line((8,0),(10,0),dxfattribs={'layer':'空调冷冻水回水'})
  g={'edges':[{'edge_id':'E','system':'supply','attribute_paths':[[[0,0],[10,0]]]}]};c={'status':'partial_source_coverage_not_physical_length','source_sha256':'S','graph_mutated':False,'edges':[{'edge_id':'E','system':'supply','segments':[{'index':0,'start':[0,0],'end':[10,0],'status':'no_witness_in_scoped_search'}]}]};p={'source_sha256':'S','graph_sha256':'G','coverage_sha256':'C','selections':[{'edge_id':'E','segment_index':0}]};before=copy.deepcopy(g)
  r=audit(d,g,c,p,'S','G','C');self.assertEqual(g,before);self.assertAlmostEqual(r['records'][0]['unique_source_drawing_length'],8);self.assertAlmostEqual(r['records'][0]['unwitnessed_drawing_length'],2);self.assertFalse(r['human_accepted'])
  with self.assertRaises(ValueError):audit(d,g,c,p,'S','different','C')
  c['edges'][0]['segments'][0]['end']=[9,0]
  with self.assertRaises(ValueError):audit(d,g,c,p,'S','G','C')
if __name__=='__main__':unittest.main()
