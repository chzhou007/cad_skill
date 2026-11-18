import copy
import unittest
from expert_riser_connection import apply_source_riser_connections,separate_riser_source_path

class ExpertRiser(unittest.TestCase):
 def setUp(self):
  self.c=[{'handle':'C','center':(0,0),'radius':100,'system':'supply'}]
  self.s=[{'handle':'A','system':'supply','a':(0,0),'b':(-500,0)},{'handle':'B','system':'supply','a':(0,100),'b':(0,600)}]
  self.p={'expert_issue':'ERR-TEST','connections':[{'circle_handle':'C','center_line':'A','rim_line':'B','radius':100,'system':'supply'}]}
 def test_source_repair_preserves_two_native_paths(self):
  evidence=apply_source_riser_connections(self.c,self.s,self.p);self.assertEqual(self.s[1]['a'],(0,0));self.assertEqual(self.s[1]['original_a'],(0,100))
  edge={'edge_id':'E','system':'supply','source_handles':['A','B'],'attribute_paths':[[[-500,0],[0,0],[0,600]]],'path_length':1100}
  separate_riser_source_path([edge],evidence);self.assertEqual(edge['attribute_paths'],[[[-500,0],[0,0]],[[0,100],[0,600]]]);self.assertEqual(edge['path_length'],1000);self.assertFalse(edge['path_length_complete'])
 def test_conflicting_service_or_extra_contact_fails(self):
  s=copy.deepcopy(self.s);s[1]['system']='return'
  with self.assertRaises(ValueError):apply_source_riser_connections(self.c,s,self.p)
  s=copy.deepcopy(self.s);s.append({'handle':'extra','system':'supply','a':(0,0),'b':(300,0)})
  with self.assertRaises(ValueError):apply_source_riser_connections(self.c,s,self.p)
  s=copy.deepcopy(self.s);s.append({'handle':'through','system':'supply','a':(-300,0),'b':(300,0)})
  with self.assertRaises(ValueError):apply_source_riser_connections(self.c,s,self.p)
