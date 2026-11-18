import unittest,copy
from source_labeled_equipment_pairs import attach
class GroupTest(unittest.TestCase):
 def setUp(self):
  self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'EQ','node_type':'equipment','source_ports':[{'edge_id':'E1','system':'supply','status':'applied','port_id':'P1'},{'edge_id':'E2','system':'return','status':'applied','port_id':'P2'}]},{'node_id':'U1','source_annotation_reference':{'label':'3F-A1','system':'supply','target_edge_id':'T1','hydraulic_connection_confirmed':False}},{'node_id':'U2','source_annotation_reference':{'label':'3F-A1','system':'return','target_edge_id':'T2','hydraulic_connection_confirmed':False}}],'edges':[{'edge_id':'E1','start_node_id':'U1','end_node_id':'EQ','system':'supply'},{'edge_id':'E2','start_node_id':'U2','end_node_id':'EQ','system':'return'}],'sourceAnnotationReferenceGroups':[{'label':'3F-A1','endpoint_node_ids':['U1','U2'],'target_edge_ids':['T1','T2'],'source_note_handle':'H'}]}
 def test_group_preserves_hydraulic_edges(self):
  o,a=attach(self.g,'S');self.assertEqual(a['groups'],1);self.assertEqual(o['edges'],self.g['edges']);self.assertEqual(o['nodes'][0]['source_labeled_equipment_pair']['services']['return']['equipment_port_id'],'P2');self.assertNotIn('source_labeled_equipment_pair',self.g['nodes'][0])
 def test_refuses_mismatched_equipment_or_port(self):
  self.g['nodes'][0]['source_ports'].pop()
  with self.assertRaises(ValueError):attach(self.g,'S')
 def test_refuses_changed_source_or_targets(self):
  with self.assertRaises(ValueError):attach(self.g,'wrong')
  self.g['sourceAnnotationReferenceGroups'][0]['target_edge_ids']=['T1','X']
  with self.assertRaises(ValueError):attach(self.g,'S')
if __name__=='__main__':unittest.main()
