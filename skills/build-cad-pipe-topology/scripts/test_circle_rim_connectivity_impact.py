import copy
import unittest
from circle_rim_connectivity_impact import analyze


class CircleImpactTest(unittest.TestCase):
    def setUp(self):
        self.g = {'metadata': {'source_sha256': 's'},
                  'nodes': [{'node_id': x, 'node_type': 'equipment' if x == 'EQ' else 'tee'} for x in ('a','b','c','d','EQ')],
                  'edges': [{'edge_id':'M','system':'supply','start_node_id':'a','end_node_id':'b'},
                            {'edge_id':'B','system':'supply','start_node_id':'c','end_node_id':'d'}]}
        self.s = {'graph_sha256':'g','source_sha256':'s','status':'source_shape_comparison_not_connectivity',
                  'candidates':[{'circle_handle':'C','line_system':'supply','main_graph_edges':['M'],'branch_graph_edges':['B'],
                                 'circle_layer_matches_lines':True,'z_consistent_within_tolerance':True,'status':'source_shape_graph_connection_not_established'}],
                  'ambiguous_native_geometry':[]}
    def test_separate_and_connected(self):
        self.assertEqual(analyze(self.g,self.s,'g','s')['candidates'][0]['current_graph_relation'],'separate_components')
        self.g['edges'].append({'edge_id':'L','system':'supply','start_node_id':'b','end_node_id':'c'})
        self.assertEqual(analyze(self.g,self.s,'g','s')['candidates'][0]['current_graph_relation'],'same_component')
    def test_equipment_is_boundary(self):
        self.g['edges'].extend([{'edge_id':'L1','system':'supply','start_node_id':'b','end_node_id':'EQ'},
                                {'edge_id':'L2','system':'supply','start_node_id':'EQ','end_node_id':'c'}])
        self.assertEqual(analyze(self.g,self.s,'g','s')['candidates'][0]['current_graph_relation'],'separate_components')
    def test_systems_never_merge(self):
        self.g['edges'].append({'edge_id':'L','system':'return','start_node_id':'b','end_node_id':'c'})
        self.assertEqual(analyze(self.g,self.s,'g','s')['candidates'][0]['current_graph_relation'],'separate_components')
    def test_virtual_interface_is_boundary(self):
        self.g['nodes'][-1]['node_type']='virtual_equipment'
        self.g['edges'].extend([{'edge_id':'L1','system':'supply','start_node_id':'b','end_node_id':'EQ'},
                                {'edge_id':'L2','system':'supply','start_node_id':'EQ','end_node_id':'c'}])
        self.assertEqual(analyze(self.g,self.s,'g','s')['candidates'][0]['current_graph_relation'],'separate_components')
    def test_stale_or_wrong_system_fails(self):
        with self.assertRaises(ValueError): analyze(self.g,self.s,'stale','s')
        self.g['edges'][1]['system']='return'
        with self.assertRaises(ValueError): analyze(self.g,self.s,'g','s')
    def test_ambiguous_edge_not_assumed(self):
        self.s['candidates'][0]['branch_graph_edges']=['B','M']
        self.assertEqual(analyze(self.g,self.s,'g','s')['candidates'][0]['current_graph_relation'],'ambiguous_edge_binding')
    def test_boundary_anchor_is_terminal(self):
        self.g['boundary_anchors']=[{'boundary_id':'X','system':'supply'}]
        self.g['edges'].extend([{'edge_id':'L1','system':'supply','start_node_id':'b','end_node_id':None,'end_boundary_id':'X'},
                                {'edge_id':'L2','system':'supply','start_node_id':'c','end_node_id':None,'end_boundary_id':'X'}])
        self.assertEqual(analyze(self.g,self.s,'g','s')['candidates'][0]['current_graph_relation'],'separate_components')
        self.g['boundary_anchors'][0]['system']='return'
        with self.assertRaises(ValueError): analyze(self.g,self.s,'g','s')

if __name__ == '__main__': unittest.main()
