import copy
import unittest
from cad_ceiling_native_rules import circle_connection_candidate,expert_circle_connection_candidate
from expert_circle_source_lengths import correct_circle_branch_lengths

class ExpertCircle(unittest.TestCase):
 def setUp(self):
  self.circle={'handle':'C','center':(0,0),'radius':80,'system':'supply'}
  self.segments=[{'handle':'M','system':'supply','a':(0,-500),'b':(0,500)},{'handle':'D','system':'supply','a':(0,500),'b':(0,-500)},{'handle':'B','system':'supply','a':(-500,0),'b':(-80,0)}]
  self.policy={'expert_issue':'ERR-EXAMPLE','circles':[{'circle_handle':'C','main_handle':'M','branch_handle':'B','radius':80,'system':'supply'}]}
 def test_exact_duplicate_main_is_one_source_geometry(self):
  self.assertIsNone(circle_connection_candidate(self.circle,self.segments))
  result=expert_circle_connection_candidate(self.circle,self.segments,self.policy);self.assertEqual(result[0]['handle'],'M');self.assertEqual(result[1][0]['handle'],'B')
 def test_unscoped_and_ambiguous_geometry(self):
  self.assertIsNone(expert_circle_connection_candidate(dict(self.circle,handle='other'),self.segments,self.policy))
  segments=copy.deepcopy(self.segments);segments.append({'handle':'OTHER','system':'supply','a':(0,-600),'b':(0,600)})
  with self.assertRaises(ValueError):expert_circle_connection_candidate(self.circle,segments,self.policy)
  segments=copy.deepcopy(self.segments);segments.append({'handle':'OTHER','system':'supply','a':(500,0),'b':(80,0)})
  with self.assertRaises(ValueError):expert_circle_connection_candidate(self.circle,segments,self.policy)
 def test_wrong_branch_service_and_rim_fail(self):
  for change in ({'system':'return'},{'b':(-70,0)}):
   segments=copy.deepcopy(self.segments);segments[2].update(change)
   with self.assertRaises(ValueError):expert_circle_connection_candidate(self.circle,segments,self.policy)
 def test_source_length_does_not_count_symbol_radius(self):
  nodes=[{'node_id':'T','node_type':'tee','system':'supply','x':0,'y':0}];edges=[{'edge_id':'E','system':'supply','start_node_id':'V','end_node_id':'T','source_handles':['B'],'attribute_paths':[[[-500,0],[0,0]]],'path_length':500}]
  b={'expert_issue':'ERR-EXAMPLE','semantic_endpoint':(0,0),'original_endpoint':(-80,0),'branch_handle':'B','main_handle':'M','circle_handle':'C','system':'supply'}
  correct_circle_branch_lengths(nodes,edges,[b]);self.assertEqual(edges[0]['path_length'],420);self.assertEqual(edges[0]['attribute_paths'],[[[-500,0],[-80,0]]]);self.assertFalse(edges[0]['path_length_complete'])
 def test_crossover_gap_is_not_a_native_source_path(self):
  nodes=[{'node_id':'T','node_type':'tee','system':'supply','x':0,'y':0}];edges=[{'edge_id':'E','system':'supply','start_node_id':'V','end_node_id':'T','source_handles':['B','B2'],'attribute_paths':[[[-500,0],[-300,0],[-200,0],[0,0]]],'path_length':500}]
  b={'expert_issue':'ERR-EXAMPLE','semantic_endpoint':(0,0),'original_endpoint':(-80,0),'branch_handle':'B','main_handle':'M','circle_handle':'C','system':'supply'}
  c={'a':(-300,0),'b':(-200,0),'source_handles':['B','B2'],'crossings':[{'crossed_handle':'S'}]}
  correct_circle_branch_lengths(nodes,edges,[b],crossovers=[c]);self.assertEqual(edges[0]['path_length'],320);self.assertEqual(edges[0]['attribute_paths'],[[[-500,0],[-300,0]],[[-200,0],[-80,0]]]);self.assertEqual(edges[0]['source_normalized_crossovers'][0]['physical_length'],'unknown')
