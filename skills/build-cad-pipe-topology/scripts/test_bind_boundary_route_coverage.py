import copy
import unittest

from bind_boundary_route_coverage import bind


class BindCoverageTest(unittest.TestCase):
    def setUp(self):
        self.preflight = {'status': 'boundary_mapping_preflight_not_mapping', 'axis_graph_sha256': 'g',
                          'mapping_ready': False, 'hil_ready': False,
                          'records': [{'system': 'supply', 'axis_paths': [['e1', 'e2']]}]}
        self.coverage = {'source_sha256': 's', 'graph_sha256': 'g', 'graph_mutated': False,
                         'hil_ready': False, 'status': 'partial_source_coverage_not_physical_length',
                         'edges': [{'edge_id': e, 'system': 'supply', 'segments': [{'status': 'single_source_line_covers'}]} for e in ('e1', 'e2')]}

    def test_witness_is_not_mapping_or_length(self):
        result = bind(self.preflight, self.coverage, copy.deepcopy(self.coverage), 'g', 's')
        self.assertTrue(result['records'][0]['all_segments_single_line_witnessed'])
        self.assertFalse(result['mapping_ready'])
        self.assertEqual(result['records'][0]['physical_length'], 'unknown')

    def test_missing_witness_is_reported(self):
        self.coverage['edges'][1]['segments'][0]['status'] = 'no_witness_in_scoped_search'
        result = bind(self.preflight, self.coverage, copy.deepcopy(self.coverage), 'g', 's')
        self.assertEqual(result['records'][0]['unverified_edge_ids'], ['e2'])

    def test_stale_or_tampered_data_rejected(self):
        recomputed = copy.deepcopy(self.coverage)
        self.coverage['edges'][0]['segments'][0]['status'] = 'ambiguous_multiple_witnesses'
        with self.assertRaises(ValueError):
            bind(self.preflight, self.coverage, recomputed, 'g', 's')
        with self.assertRaises(ValueError):
            bind(self.preflight, recomputed, recomputed, 'changed', 's')

    def test_missing_and_cross_system_edges_rejected(self):
        self.coverage['edges'].pop()
        with self.assertRaises(ValueError):
            bind(self.preflight, self.coverage, copy.deepcopy(self.coverage), 'g', 's')
        self.coverage['edges'].append({'edge_id': 'e2', 'system': 'return', 'segments': []})
        with self.assertRaises(ValueError):
            bind(self.preflight, self.coverage, copy.deepcopy(self.coverage), 'g', 's')


if __name__ == '__main__':
    unittest.main()
