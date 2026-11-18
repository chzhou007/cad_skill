import copy, unittest
import ezdxf
from correct_plan_crossover_lengths import apply, LAYERS

class CrossoverLengthTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new(); m=self.doc.modelspace()
  a=m.add_line((-10,0),(-1,0),dxfattribs={'layer':LAYERS['return']})
  b=m.add_line((1,0),(10,0),dxfattribs={'layer':LAYERS['return']})
  c=m.add_line((0,-10),(0,10),dxfattribs={'layer':LAYERS['supply']})
  h=[a.dxf.handle,b.dxf.handle]; cross={'crossing':[0,0],'crossed_handle':c.dxf.handle,'crossed_source_system':'supply'}
  self.gap={'id':'G1','a':[-1,0],'b':[1,0],'source_handles':h,'status':'applied','crossing_connectivity':'independent_pipes_no_junction'}
  self.frag={'normalization':'source_straight_crossover_gap','source_handles':h,'a':[-1,0],'b':[1,0],'system':'return','crossings':[cross],'crossing_connectivity':'independent_pipes_no_junction'}
  self.graph={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'n','x':-10,'y':0}],'edges':[{'edge_id':'E','system':'return','source_handles':h,'path':[[-10,0],[10,0]],'attribute_paths':[[[-10,0],[-1,0],[1,0],[10,0]]],'path_length':20}]}
  self.policy={'source_sha256':'s','graph_sha256':'g','gaps_sha256':'a','fragments_sha256':'f','gap_ids':['G1']}
 def run_apply(self):return apply(self.doc,self.graph,[self.gap],[self.frag],self.policy,'s','g','a','f')
 def test_splits_drawing_paths_without_topology_change(self):
  original=copy.deepcopy(self.graph);g,r=self.run_apply();e=g['edges'][0]
  self.assertEqual(self.graph,original);self.assertEqual(g['nodes'],original['nodes']);self.assertEqual(e['path'],original['edges'][0]['path']);self.assertEqual(e['path_length'],18);self.assertEqual(len(e['attribute_paths']),2);self.assertFalse(e['path_length_complete']);self.assertEqual(e['physical_length'],'unknown');self.assertFalse(r['human_accepted'])
 def test_previously_excluded_and_coverage_indices_become_historical(self):
  e=self.graph['edges'][0];e.update(path_length=18,path_length_complete=False,source_path_coverage={'unverified_segment_indices':[1]})
  g,_=self.run_apply();e=g['edges'][0];self.assertEqual(e['path_length'],18);self.assertNotIn('source_path_coverage',e);self.assertEqual(e['previous_source_path_coverage']['evidence']['unverified_segment_indices'],[1])
 def test_reject_stale_or_wrong_system(self):
  self.policy['source_sha256']='stale'
  with self.assertRaises(ValueError):self.run_apply()
  self.policy['source_sha256']='s';self.frag['crossings'][0]['crossed_source_system']='return'
  with self.assertRaises(ValueError):self.run_apply()
 def test_reject_dependent_attribute_and_unwitnessed_crossing(self):
  self.graph['edges'][0]['pipe_diameter']='DN50'
  with self.assertRaises(ValueError):self.run_apply()
  del self.graph['edges'][0]['pipe_diameter'];self.frag['crossings'][0]['crossing']=[5,0]
  with self.assertRaises(ValueError):self.run_apply()
 def test_already_split_requires_exact_evidence(self):
  e=self.graph['edges'][0];e.update(attribute_paths=[[[-10,0],[-1,0]],[[1,0],[10,0]]],path_length=18,path_length_complete=False,source_straight_crossover_evidence={'source_gap_id':'wrong','source_handles':self.gap['source_handles'],'crossing_connectivity':'independent_pipes_no_junction'})
  with self.assertRaises(ValueError):self.run_apply()
  e['source_straight_crossover_evidence']['source_gap_id']='G1';g,r=self.run_apply();self.assertEqual(r['records'][0]['status'],'already_excluded')
 def test_gap_only_path_is_removed_when_other_paths_witness_both_sides(self):
  e=self.graph['edges'][0];e['attribute_paths']=[[[-10,0],[-1,0]],[[-1,0],[1,0]],[[1,0],[10,0]]]
  g,_=self.run_apply();self.assertEqual(g['edges'][0]['attribute_paths'],[[[-10,0],[-1,0]],[[1,0],[10,0]]])
 def test_reject_noncollinear_tail_and_shared_system_node(self):
  line=self.doc.entitydb[self.gap['source_handles'][0]];line.dxf.start=(-10,2,0)
  with self.assertRaisesRegex(ValueError,'opposed and collinear'):self.run_apply()
  line.dxf.start=(-10,0,0);self.graph['nodes'].append({'node_id':'cross','x':0,'y':0})
  self.graph['edges'][0]['start_node_id']='cross';self.graph['edges'].append({'edge_id':'opposite','start_node_id':'cross','system':'supply'})
  with self.assertRaisesRegex(ValueError,'share crossing node'):self.run_apply()

if __name__=='__main__':unittest.main()
