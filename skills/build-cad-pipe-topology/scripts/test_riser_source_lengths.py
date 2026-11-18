import copy
import unittest
from riser_source_lengths import correct_riser_source_lengths


class RiserSourceLengths(unittest.TestCase):
    def setUp(self):
        self.edge = dict(edge_id='E1', start_node_id='T1', end_node_id='R1', system='supply', source_handles=['LINE'], path_length=20, attribute_paths=[[[20, 0], [0, 0]]], path_points=[[20, 0], [0, 0]])
        self.witness = dict(interface_id='R1', graph_state='loaded_connected_interface', semantic='out_of_plane_riser_terminal', pipe_handles=['LINE'], circle_handle='C', center=[0, 0], original_endpoint=[5, 0], system='supply')

    def test_source_length_excludes_graphic_radius(self):
        edge = copy.deepcopy(self.edge)
        audit = correct_riser_source_lengths([edge], [self.witness])
        self.assertEqual(edge['attribute_paths'], [[[20, 0], [5, 0]]])
        self.assertEqual(edge['path_points'], [[20, 0], [0, 0]])
        self.assertEqual(edge['path_length'], 15)
        self.assertFalse(edge['path_length_complete'])
        self.assertEqual(audit[0]['graphic_radius_excluded'], 5)

    def test_rejects_wrong_system_and_noncollinear_endpoint(self):
        for update in ({'system': 'return'}, {'original_endpoint': [5, 3]}):
            witness = dict(self.witness, **update)
            with self.assertRaises(ValueError):
                correct_riser_source_lengths([copy.deepcopy(self.edge)], [witness])

    def test_pending_candidate_does_not_mutate_edge(self):
        edge = copy.deepcopy(self.edge)
        witness = dict(self.witness, graph_state='source_candidate_no_completed_logical_edge')
        self.assertEqual(correct_riser_source_lengths([edge], [witness]), [])
        self.assertEqual(edge, self.edge)
