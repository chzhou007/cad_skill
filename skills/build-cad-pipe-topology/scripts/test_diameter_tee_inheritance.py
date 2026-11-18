import copy
import unittest
from diameter_tee_inheritance import infer


def edge(i, a, b, system='supply'):
    return {'edge_id': i, 'start_node_id': a, 'end_node_id': b, 'system': system}


class DiameterInheritanceTest(unittest.TestCase):
    def setUp(self):
        self.graph = {'nodes': [{'node_id': i, 'node_type': t} for i, t in [
            ('A', 'equipment'), ('T', 'physical_junction'), ('B', 'equipment'),
            ('C', 'equipment'), ('R', 'physical_junction'), ('U', 'equipment'), ('D', 'equipment'), ('F', 'equipment')]],
            'edges': [edge('E1', 'A', 'T'), edge('E2', 'T', 'B'),
                      edge('E3', 'T', 'C'), edge('E4', 'R', 'U', 'return'),
                      edge('E5', 'R', 'D', 'return'), edge('E6', 'R', 'F', 'return')]}
        self.ids = {e['edge_id'] for e in self.graph['edges']}

    def test_verified_tee_inherits_without_crossing_system(self):
        before = copy.deepcopy(self.graph)
        rows = {r['edge_id']: r for r in infer(self.graph,
                 [{'edge_id': 'E1', 'nominal_mm': 100, 'evidence_id': 'DN100:handle'}], self.ids, {'T', 'R'})}
        self.assertEqual(rows['E2']['nominal_mm'], 100)
        self.assertEqual(rows['E3']['candidates'][0]['evidence'][0]['edge_path'], ['E1', 'E3'])
        self.assertEqual(rows['E4']['status'], 'unknown')
        self.assertEqual(rows['E5']['status'], 'unknown')
        self.assertEqual(before, self.graph)

    def test_conflict_is_not_arbitrarily_resolved(self):
        rows = {r['edge_id']: r for r in infer(self.graph,
                 [{'edge_id': 'E1', 'nominal_mm': 100, 'evidence_id': 'one'},
                  {'edge_id': 'E2', 'nominal_mm': 80, 'evidence_id': 'two'}], self.ids, {'T'})}
        self.assertEqual(rows['E3']['status'], 'conflict')
        self.assertIsNone(rows['E3']['nominal_mm'])
        self.assertEqual(rows['E1']['nominal_mm'], 100)
        self.assertEqual(rows['E2']['nominal_mm'], 80)

    def test_unverified_tee_and_excluded_edge_do_not_propagate(self):
        rows = {r['edge_id']: r for r in infer(self.graph,
                 [{'edge_id': 'E1', 'nominal_mm': 100, 'evidence_id': 'one'}], self.ids - {'E3'}, set())}
        self.assertEqual(rows['E2']['status'], 'unknown')
        self.assertNotIn('E3', rows)

    def test_equipment_unknown_system_and_bad_seeds_rejected(self):
        with self.assertRaises(ValueError): infer(self.graph, [], self.ids, {'A'})
        graph = copy.deepcopy(self.graph); graph['edges'][0]['system'] = 'unknown'
        with self.assertRaises(ValueError): infer(graph, [], self.ids, set())
        for value in [0, float('nan'), True]:
            with self.assertRaises(ValueError):
                infer(self.graph, [{'edge_id': 'E1', 'nominal_mm': value, 'evidence_id': 'x'}], self.ids, {'T'})

    def test_existing_annotation_blocks_transit(self):
        graph = {'nodes': [{'node_id': i, 'node_type': 'physical_junction' if i in 'TU' else 'equipment'} for i in 'ATUB'],
                 'edges': [edge('E1', 'A', 'T'), edge('E2', 'T', 'U'), edge('E3', 'U', 'B'),
                           edge('E4', 'T', 'C'), edge('E5', 'U', 'D')]}
        graph['nodes'].extend([{'node_id': 'C', 'node_type': 'equipment'}, {'node_id': 'D', 'node_type': 'equipment'}])
        rows = {r['edge_id']: r for r in infer(graph,
                 [{'edge_id': 'E1', 'nominal_mm': 100, 'evidence_id': 'one'},
                  {'edge_id': 'E2', 'nominal_mm': 80, 'evidence_id': 'two'}], {'E1', 'E2', 'E3', 'E4', 'E5'}, {'T', 'U'})}
        self.assertEqual(rows['E3']['nominal_mm'], 80)
        self.assertEqual(rows['E3']['status'], 'inherited_candidate')

    def test_mixed_edge_and_reused_evidence_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'segment-level'):
            infer(self.graph, [{'edge_id': 'E1', 'nominal_mm': 450, 'evidence_id': 'vertical'},
                               {'edge_id': 'E1', 'nominal_mm': 300, 'evidence_id': 'horizontal'}],
                  self.ids, {'T'})
        with self.assertRaisesRegex(ValueError, 'multiple edges'):
            infer(self.graph, [{'edge_id': 'E1', 'nominal_mm': 100, 'evidence_id': 'same'},
                               {'edge_id': 'E2', 'nominal_mm': 100, 'evidence_id': 'same'}],
                  self.ids, {'T'})



    def test_source_boundary_terminates_inheritance_without_crossing(self):
        graph = copy.deepcopy(self.graph)
        graph['boundary_anchors'] = [{'boundary_id': 'X', 'system': 'supply'}]
        for edge_id, side in [('E3', 'end'), ('E1', 'start')]:
            e = next(e for e in graph['edges'] if e['edge_id'] == edge_id)
            e.pop(side + '_node_id')  # compact inputs may omit the null node key
            e[side + '_boundary_id'] = 'X'
        rows = {r['edge_id']: r for r in infer(graph,
                [{'edge_id': 'E3', 'nominal_mm': 100, 'evidence_id': 'native-label'}], self.ids, {'T'})}
        self.assertEqual(rows['E1']['nominal_mm'], 100)  # through verified T, not X
        rows = {r['edge_id']: r for r in infer(graph,
                [{'edge_id': 'E3', 'nominal_mm': 100, 'evidence_id': 'native-label'}], self.ids, set())}
        self.assertEqual(rows['E1']['status'], 'unknown')  # shared X is not a graph connection

    def test_bad_or_ambiguous_source_boundary_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph['boundary_anchors'] = [{'boundary_id': 'X', 'system': 'return'}]
        e = graph['edges'][0]; e['start_node_id'] = None; e['start_boundary_id'] = 'X'
        with self.assertRaisesRegex(ValueError, 'boundary system'):
            infer(graph, [], self.ids, {'T'})
        graph['boundary_anchors'][0]['system'] = 'supply'
        e['start_node_id'] = 'A'
        with self.assertRaisesRegex(ValueError, 'endpoints'):
            infer(graph, [], self.ids, {'T'})
        e['start_node_id'] = None; e['start_boundary_id'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'source boundary'):
            infer(graph, [], self.ids, {'T'})

    def test_invalid_or_mixed_junction_rejected_even_if_edges_excluded(self):
        graph = copy.deepcopy(self.graph)
        graph['edges'].append(edge('EX', 'T', 'D', 'return'))
        with self.assertRaisesRegex(ValueError, 'exactly three same-system'):
            infer(graph, [], self.ids - {'E4'}, {'T'})
        graph = copy.deepcopy(self.graph)
        graph['edges'][2]['system'] = 'return'
        with self.assertRaisesRegex(ValueError, 'exactly three same-system'):
            infer(graph, [], self.ids - {'E3'}, {'T'})
        graph = copy.deepcopy(self.graph)
        graph['edges'] = [e for e in graph['edges'] if e['edge_id'] != 'E3']
        with self.assertRaisesRegex(ValueError, 'exactly three same-system'):
            infer(graph, [], {e['edge_id'] for e in graph['edges']}, {'T'})

    def test_unresolved_branch_is_not_a_verified_tee(self):
        graph = copy.deepcopy(self.graph)
        node = next(n for n in graph['nodes'] if n['node_id'] == 'T')
        node['subtype'] = 'pending_source_junction'
        with self.assertRaisesRegex(ValueError, 'pending branch'):
            infer(graph, [], self.ids, {'T'})
        node['subtype'] = 'physical_tee'
        node['resolution_state'] = 'source_main_continuation_branch_pending'
        with self.assertRaisesRegex(ValueError, 'pending branch'):
            infer(graph, [], self.ids, {'T'})
        node['resolution_state'] = 'source_contact_reconstructed_pending_comparison'
        with self.assertRaisesRegex(ValueError, 'pending branch'):
            infer(graph, [], self.ids, {'T'})

    def test_inferred_circle_branch_blocks_even_when_excluded(self):
        graph = copy.deepcopy(self.graph)
        node = next(n for n in graph['nodes'] if n['node_id'] == 'T')
        node['source_handles'] = ['CIRCLE']
        branch = next(e for e in graph['edges'] if e['edge_id'] == 'E3')
        branch['source_expert_circle_link'] = {'circle_handle': 'CIRCLE', 'similar_location_inferred': True, 'expert_review': 'unreviewed'}
        with self.assertRaisesRegex(ValueError, 'inferred similar-circle'):
            infer(graph, [], self.ids - {'E3'}, {'T'})
        # An explicitly marked expert circle has no inferred-similar flag.
        branch['source_expert_circle_link'].pop('similar_location_inferred')
        self.assertEqual(len(infer(graph, [], self.ids, {'T'})), len(self.ids))
        # A different source circle on the same edge does not taint this end.
        branch['source_expert_circle_link'] = {'circle_handle': 'OTHER', 'similar_location_inferred': True}
        self.assertEqual(len(infer(graph, [], self.ids, {'T'})), len(self.ids))
        # Missing source identity cannot bypass the guard.
        branch['source_expert_circle_link'].pop('circle_handle')
        with self.assertRaisesRegex(ValueError, 'inferred similar-circle'):
            infer(graph, [], self.ids, {'T'})

if __name__ == '__main__':
    unittest.main()
