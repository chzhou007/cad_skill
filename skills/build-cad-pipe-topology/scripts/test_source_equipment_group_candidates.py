import copy,unittest
from source_equipment_group_candidates import attach

class SourceGroupsTest(unittest.TestCase):
 def setUp(self):
  self.g={'nodes':[{'node_id':'A','node_type':'equipment','display_source_chain':['1','A'],'ports':[{'port_id':'A1'}]},{'node_id':'B','node_type':'equipment','display_source_chain':['1','B'],'ports':[]}],'edges':[{'edge_id':'E','start_node_id':'A','end_node_id':'B'}]}
  self.e={'source_03_sha256':'s','graph_03_sha256':'g','source_02_sha256':'r','caption_03_fragments':['冷塔单模块','17T','，一组','2','台','17*2','余同'],'caption_03_handles':list('1234567'),'native_03_module_pairs':1,'native_02_tagged_two_cell_groups':1,'groups_02':[{'tag':'reference'}],
          'pairs_03':[{'pair_id':'PAIR','module_node_ids':['A','B'],'source_chains':[['1','A'],['1','B']],'native_gap':64}]}
 def apply(self):return attach(self.g,self.e,'s','g','r')
 def test_no_nodes_ports_or_edges_merged(self):
  old=copy.deepcopy(self.g);out,summary=self.apply();self.assertEqual(self.g,old);self.assertEqual(out['edges'],old['edges']);self.assertEqual(out['nodes'][0]['ports'],old['nodes'][0]['ports']);self.assertEqual(out['nodes'][0]['source_assembly_candidate']['peer_node_id'],'B');self.assertEqual(summary['nodes_merged'],0)
 def test_stale_or_incomplete_fails(self):
  with self.assertRaises(ValueError):attach(self.g,self.e,'s','stale','r')
  self.e['caption_03_fragments'][0]='changed'
  with self.assertRaises(ValueError):self.apply()
 def test_ambiguous_source_and_overlapping_groups_fail(self):
  self.e['pairs_03'][0]['source_chains'][0]=['wrong']
  with self.assertRaises(ValueError):self.apply()
  self.e['pairs_03'][0]['source_chains'][0]=['1','A'];self.e['pairs_03'].append(copy.deepcopy(self.e['pairs_03'][0]));self.e['native_03_module_pairs']=2
  with self.assertRaises(ValueError):self.apply()

if __name__=='__main__':unittest.main()
