import copy
import unittest

from attribute_scope_inventory import inventory


class AttributeScopeInventoryTests(unittest.TestCase):
    def graph(self):
        return dict(edges=[dict(edge_id='A', cross_view_attributes=dict(floor=2, DN=None),
            plan_segment_attributes=[dict(floor=1, DN=200), dict(floor=3, DN=250)],
            axis_riser_attributes=[dict(DN=450)],
            current_floor_plan_scope_evidence=dict(floor=2)),
            dict(edge_id='B', external_feed_plan_attributes=dict(DN=450),
                 anchored_floor_main_attributes=dict(DN=None),
                 network_named_lower_plan_attributes=dict(DN=200))])

    def test_mixed_carriers_count_records_separately_from_edges(self):
        result = inventory(self.graph())
        self.assertEqual(result['plan']['records'], 6)
        self.assertEqual(result['plan']['edges'], 2)
        self.assertEqual(result['plan']['by_field']['cross_view_attributes'], 1)
        self.assertEqual(result['plan']['by_field']['plan_segment_attributes'], 2)

    def test_current_evidence_does_not_duplicate_plan_records_or_vertical_records(self):
        graph = self.graph()
        graph['edges'][1]['current_plan_scope_evidence'] = dict(version='new')
        result = inventory(graph)
        self.assertEqual(result['plan']['records'], 6)
        self.assertEqual(result['axis']['records'], 1)
        self.assertEqual(result['evidence']['records'], 2)

    def test_null_DN_is_still_a_record_not_a_known_value(self):
        result = inventory(dict(edges=[dict(edge_id='A', cross_view_attributes=dict(nominal_mm=None))]))
        self.assertEqual(result['plan']['records'], 1)
        self.assertNotIn('known_DN', result['plan'])
        self.assertIn('not_source_or_physical_acceptance', result['status'])

    def test_unchanged_totals_do_not_hide_payload_changes(self):
        first = self.graph(); second = copy.deepcopy(first)
        second['edges'][0]['plan_segment_attributes'][0]['DN'] = 300
        a, b = inventory(first), inventory(second)
        self.assertEqual(a['plan'], b['plan'])
        self.assertNotEqual(a['records'], b['records'])

    def test_duplicate_edge_ids_and_wrong_carrier_shapes_are_rejected(self):
        invalid = [dict(edges=[dict(edge_id='A'), dict(edge_id='A')]),
                   dict(edges=[dict(edge_id='A', cross_view_attributes=[])]),
                   dict(edges=[dict(edge_id='A', plan_segment_attributes=dict(DN=200))]),
                   dict(edges=[dict(edge_id='A', plan_segment_attributes=[None])])]
        for graph in invalid:
            with self.subTest(graph=graph), self.assertRaises(ValueError):
                inventory(graph)

    def test_reordered_edges_preserve_inventory_and_input_is_unchanged(self):
        first = self.graph(); original = copy.deepcopy(first)
        self.assertEqual(inventory(first), inventory(dict(edges=list(reversed(first['edges'])))))
        self.assertEqual(first, original)

    def test_missing_attributes_do_not_produce_zero_filled_physical_records(self):
        result = inventory(dict(edges=[dict(edge_id='A', plan_segment_attributes=[], axis_riser_attributes=None)]))
        self.assertEqual(result['plan']['records'], 0)
        self.assertEqual(result['records'], [])


if __name__ == '__main__':
    unittest.main()
