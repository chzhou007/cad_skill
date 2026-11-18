import unittest
from compare_shaft_axis_segment_dn import compare

class ShaftAxisDNTest(unittest.TestCase):
 def setUp(self):
  self.c={'status':'shaft_axis_candidate_inventory_not_mapping','input_sha256':{'axis_graph':'G'},'mapping_ready':False,'human_accepted':False,'hil_ready':False,'records':[{'system':'supply','plan_floor_nodes':['P1','P2','P3'],'mapping_ready':False,'axis_chain_candidates':[{'axis_1_to_2_edge':'A','axis_2_to_3_edge':'B'}]}]};self.d={'status':'segment_candidates_not_accepted','graph_sha256':'G','source_sha256':'S','observations':[{'edge_id':'B','segment_index':0,'source_line_handle':'L','source_text':{'handle':'D'},'nominal_mm_candidate':300}]};self.b={'graph_sha256':'G','source_sha256':'S','records':[{'text_handle':'D','status':'unique_source_line_and_graph_segment_candidate','system':'supply','edge_candidates':[{'edge_id':'B'}]},{'text_handle':'U','text':'DN450','status':'ambiguous_source_lines'}]}
 def test_candidates_remain_unaccepted(self):
  r=compare(self.c,self.d,self.b,'G',['U']);self.assertEqual(r['records'][0]['segment_dn_candidates'][0]['nominal_mm_candidate'],300);self.assertFalse(r['mapping_ready']);self.assertFalse(r['records'][0]['physical_diameter_selected']);self.assertEqual(r['unresolved_texts'][0]['text_handle'],'U')
 def test_stale_and_wrong_system_fail(self):
  with self.assertRaises(ValueError):compare(self.c,self.d,self.b,'old')
  self.b['records'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'matching bulk'):compare(self.c,self.d,self.b,'G')
 def test_ambiguous_is_not_promoted(self):
  self.b['records'][1]['status']='unique_source_line_and_graph_segment_candidate'
  with self.assertRaisesRegex(ValueError,'ambiguous text'):compare(self.c,self.d,self.b,'G',['U'])
if __name__=='__main__':unittest.main()
