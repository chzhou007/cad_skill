import copy,unittest
from attach_final_source_segment_dimensions import apply
from test_attach_source_segment_dimensions import SegmentDimensions

class FinalSourceDimensionTests(unittest.TestCase):
 def setUp(self):self.f=SegmentDimensions();self.f.setUp()
 def test_partial_segment_added_without_changing_length_or_source(self):
  f=self.f;before=copy.deepcopy(f.g);out,rows=apply(f.d,f.g,f.p,'S','G');self.assertEqual(before,f.g);self.assertEqual(rows[0]['dimension_value_mm'],2400);self.assertFalse(rows[0]['edge_total_length_known']);self.assertEqual(out['edges'][0]['path_length'],2600);self.assertFalse(out['metadata']['hil_ready'])
 def test_previous_dimension_or_dn_evidence_requires_recheck(self):
  f=self.f
  for k in ('sourceSegmentDimensions','diameterInheritanceCandidates'):
   f.g[k]={'existing':True}
   with self.assertRaises(ValueError):apply(f.d,f.g,f.p,'S','G')
   del f.g[k]
  f.g['edges'][0]['pipe_diameter']={'status':'unknown'}
  with self.assertRaises(ValueError):apply(f.d,f.g,f.p,'S','G')
 def test_stale_source_and_wrong_dimension_rejected(self):
  f=self.f
  with self.assertRaises(ValueError):apply(f.d,f.g,f.p,'S','old')
  f.p['dimensions'][0]['expected_text']='bad'
  with self.assertRaises(ValueError):apply(f.d,f.g,f.p,'S','G')
if __name__=='__main__':unittest.main()
