import copy
import unittest
from unittest.mock import patch

import test_current_graph_calibrated_dn as controls
from junction_rebased_paired_plan_attributes import MODE, seed_reader, check_result


def state():
    rows = []
    for system in ('supply', 'return'):
        rows.append(dict(mapping_id=system, kind='equipment_branch', floor=2, system=system, plan_edges=['P'+system], iso_edges=['I'+system],
            diameter=dict(edge_id='P'+system, system=system, nominal_mm=None, human_accepted=False),
            horizontal_projection=dict(status='native_plan_horizontal_projection_partial_length', value_mm=10,
                pieces=[dict(length_mm=10)], installed_whole_edge_length_mm=None, unshown_connection_length_mm=None),
            whole_axis_DN_selected=False, whole_axis_physical_length_mm=None, physical_ports_verified=False, human_accepted=False))
    return dict(mode=MODE, status='source_checked_current_paired_plan_DN_XY_not_fused', records=rows,
        local_graphs_mutated=False, physical_values_fused=False, human_accepted=False,
        previous_current_base_DN_records_preserved=True, installed_lengths_assigned=0,
        native_link_scope_extensions=[{}], graph_sha256='GRAPH')


class CurrentPairedPlanAttributesTests(unittest.TestCase):
    def test_retired_seed_reads_original_native_fragment_for_current_frontier_only(self):
        graph, original, calibration = controls.NativeControlFragmentTests().fixture()
        settings = [dict(pair_id='P01', seeds=copy.deepcopy(calibration['controls']))]
        before = copy.deepcopy((graph, original, calibration, settings))
        updated, reader, lineage = seed_reader(None, graph, original, settings, calibration, set(), 'SOURCE', 'CURRENT', 'ORIGINAL')
        self.assertEqual(updated[0]['seeds'][0]['edge_id'], 'NEW')
        native = dict(observations=[dict(edge_id='OLD', source_text=dict(handle='TEXT'), nominal_mm=200, graph_projection=[5, 0])])
        selection = dict(selections=updated[0]['seeds'])
        with patch('junction_rebased_paired_plan_attributes.strict_collect', return_value=native) as collect:
            result = reader(None, graph, selection, 'SOURCE', 'CURRENT')
        args = collect.call_args.args
        self.assertIs(args[1], original); self.assertEqual(args[-1], 'ORIGINAL')
        row = result['observations'][0]
        self.assertEqual(row['edge_id'], 'NEW'); self.assertEqual(row['graph_projection'], [5, 0])
        self.assertFalse(row['current_frontier_seed_fragment']['current_whole_edge_DN_assigned'])
        self.assertEqual((graph, original, calibration, settings), before)

    def test_fragment_exception_cannot_assign_selected_whole_edge_or_switch_graph(self):
        graph, original, calibration = controls.NativeControlFragmentTests().fixture()
        settings = [dict(pair_id='P01', seeds=copy.deepcopy(calibration['controls']))]
        with self.assertRaisesRegex(ValueError, 'nonselected frontier'):
            seed_reader(None, graph, original, settings, calibration, {'NEW'}, 'SOURCE', 'CURRENT', 'ORIGINAL')
        _, reader, _ = seed_reader(None, graph, original, settings, calibration, set(), 'SOURCE', 'CURRENT', 'ORIGINAL')
        with self.assertRaises(ValueError): reader(None, copy.deepcopy(graph), dict(selections=[]), 'SOURCE', 'CURRENT')
        selection = dict(selections=[dict(settings[0]['seeds'][0], edge_id='WRONG')])
        with self.assertRaisesRegex(ValueError, 'exact original'): reader(None, graph, selection, 'SOURCE', 'CURRENT')

    def test_unknown_DN_stays_unknown_and_metric_is_source_projection(self):
        result = check_result(state())
        self.assertEqual(result['known_DN_scopes'], 0)
        self.assertEqual(result['measured_plan_XY_scopes'], 2)
        self.assertFalse(result['physical_values_fused'])

    def test_no_zero_unknown_physical_promotion_or_duplicate_writer(self):
        for change in ('DN', 'length', 'physical', 'duplicate', 'lost_base'):
            data = state()
            if change == 'DN': data['records'][0]['diameter']['nominal_mm'] = 0
            elif change == 'length': data['records'][0]['horizontal_projection']['value_mm'] = 0
            elif change == 'physical': data['records'][0]['whole_axis_physical_length_mm'] = 10
            elif change == 'duplicate': data['records'][1]['iso_edges'] = data['records'][0]['iso_edges']
            else: data['previous_current_base_DN_records_preserved'] = False
            with self.subTest(change=change), self.assertRaises(ValueError): check_result(data)


if __name__ == '__main__': unittest.main()
