import copy
import unittest
from edge_endpoint_semantics import reconcile


class EndpointSemanticsTest(unittest.TestCase):
    def setUp(self):
        self.graph = {'nodes': [{'node_id': 'T', 'node_type': 'tee', 'subtype': 'physical_tee'},
                                {'node_id': 'R', 'node_type': 'virtual_equipment', 'subtype': 'out_of_plane_riser'},
                                {'node_id': 'U', 'node_type': 'virtual_equipment', 'subtype': 'unresolved_source_terminal'}],
                      'boundary_anchors': [{'boundary_id': 'B', 'system': 'supply', 'source_pipe_handle': 'H',
                                            'kind': 'expert_non_node_source_boundary'}],
                      'edges': [{'edge_id': 'E1', 'start_node_id': 'T', 'end_node_id': 'R',
                                 'system': 'supply', 'edge_type': 'tee_to_tee', 'source_handles': ['H']},
                                {'edge_id': 'E2', 'start_node_id': 'U', 'end_node_id': None,
                                 'end_boundary_id': 'B', 'system': 'supply', 'edge_type': 'tee_to_tee',
                                 'source_handles': ['H']}], 'metadata': {'hil_ready': True}}

    def test_preserves_topology_and_marks_interfaces_and_boundary(self):
        before = copy.deepcopy(self.graph)
        result, audit = reconcile(self.graph)
        self.assertEqual(self.graph, before)
        self.assertEqual(result['edges'][0]['edge_type'], 'tee_to_virtual_equipment')
        self.assertEqual(result['edges'][0]['endpoint_semantics']['end']['subtype'], 'out_of_plane_riser')
        self.assertEqual(result['edges'][1]['edge_type'], 'source_boundary_edge')
        self.assertEqual(result['edges'][1]['endpoint_semantics']['end']['id'], 'B')
        self.assertEqual(result['edges'][1]['end_boundary_id'], 'B')
        self.assertFalse(result['metadata']['hil_ready'])
        self.assertEqual(len(audit), 2)
        self.assertEqual(result['nodes'], before['nodes'])

    def test_dangling_or_inconsistent_boundary_fails(self):
        for mutation in ('missing', 'both', 'wrong_system', 'wrong_source'):
            graph = copy.deepcopy(self.graph)
            if mutation == 'missing': graph['edges'][1]['end_boundary_id'] = 'NO'
            if mutation == 'both': graph['edges'][1]['end_node_id'] = 'T'
            if mutation == 'wrong_system': graph['boundary_anchors'][0]['system'] = 'return'
            if mutation == 'wrong_source': graph['edges'][1]['source_handles'] = ['other']
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): reconcile(graph)

    def test_second_pass_preserves_classification(self):
        result, _ = reconcile(self.graph)
        second, changes = reconcile(result)
        self.assertEqual(second, result)
        self.assertEqual(changes, [])


if __name__ == '__main__':
    unittest.main()
