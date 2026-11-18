import copy,unittest
from coverage_display_paths import partition

class CoverageDisplayTests(unittest.TestCase):
 def test_partial_path_and_unknown_gap_are_separate(self):
  e={'attribute_paths':[[[0,0],[10,0],[20,0],[30,0]]],'path_length_complete':False,'source_path_coverage':{'source_sha256':'s','coverage_sha256':'c','input_graph_sha256':'g','unverified_segment_indices':[1],'unverified_drawing_length':10}}
  before=copy.deepcopy(e);known,unknown=partition(e);self.assertEqual(known,[[[0,0],[10,0]],[[20,0],[30,0]]]);self.assertEqual(unknown,[[[10,0],[20,0]]]);self.assertEqual(e,before)
  for invalid in ([3],[1,1],[-1],[True]):
   x=copy.deepcopy(e);x['source_path_coverage']['unverified_segment_indices']=invalid
   with self.assertRaises(ValueError):partition(x)
 def test_complete_edges_keep_existing_source_paths(self):
  e={'attribute_paths':[[[0,0],[5,0]]]};self.assertEqual(partition(e),(e['attribute_paths'],[]))
 def test_wave_omission_keeps_source_and_logical_gap_separate(self):
  e={'attribute_paths':[[[0,0],[5,0]],[[10,0],[20,0]]],'connection_mode':'source_calibrated_wave_omission_unreviewed','path_length_complete':False,'source_wave_omission':{'source_endpoints':[[5,0],[10,0]],'wave_handles':['A','B'],'physical_length':'unknown'}}
  self.assertEqual(partition(e),(e['attribute_paths'],[[[5,0],[10,0]]]))
  for key,value in [('source_endpoints',[[4,0],[10,0]]),('wave_handles',['A','A']),('physical_length',0)]:
   bad=copy.deepcopy(e);bad['source_wave_omission'][key]=value
   with self.assertRaises(ValueError):partition(bad)
 def test_crossover_keeps_gap_unverified_and_drawing_length_separate(self):
  e={'attribute_paths':[[[0,0],[5,0]],[[10,0],[20,0]]],'path_length_scope':'drawing_paths_excluding_source_crossover_gaps_physical_length_unknown','path_length':15,'path_length_complete':False,'physical_length':'unknown','source_normalized_crossovers':[{'a':[5,0],'b':[10,0],'crossing_connectivity':'independent_pipes_no_junction','physical_length':'unknown'}]}
  self.assertEqual(partition(e),(e['attribute_paths'],[[[5,0],[10,0]]]))
  for key,value in [('path_length',20),('physical_length',0),('path_length_complete',True)]:
   bad=copy.deepcopy(e);bad[key]=value
   with self.assertRaises(ValueError):partition(bad)
  bad=copy.deepcopy(e);bad['source_normalized_crossovers'][0]['b']=[11,0]
  with self.assertRaises(ValueError):partition(bad)

if __name__=='__main__':unittest.main()
