import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_crossview_equipment_branch_inventory as historical_tests
from confirm_crossview_paths import encode, sha
from fresh_reviewed_plan_inventory import inspect_view, compare_ready, checked, verify_local_plan


class Tests(unittest.TestCase):
    def test_both_services_read_fresh_without_transplanting_old_pass(self):
        doc, graph, hashes = historical_tests.BranchInventoryTests().fixture()
        doc.modelspace().add_text('EQ', dxfattribs=dict(insert=(0, 10)))
        before = copy.deepcopy(graph)
        result = inspect_view(doc, graph, 'EQ', 2, hashes, 'plan', [])
        self.assertTrue(result['services']['supply']['ready_for_mapping_comparison'])
        self.assertFalse(result['services']['return']['ready_for_mapping_comparison'])
        self.assertEqual(result['services']['return']['trace']['status'], 'missing_service')
        self.assertEqual(graph, before)

    def test_missing_native_line_stays_pending_even_with_confirmed_owner(self):
        doc, graph, hashes = historical_tests.BranchInventoryTests().fixture()
        doc.modelspace().add_text('EQ', dxfattribs=dict(insert=(0, 10)))
        doc.modelspace().delete_entity(doc.entitydb[graph['edges'][1]['source_handles'][0]])
        result = inspect_view(doc, graph, 'EQ', 2, hashes, 'plan', [])
        self.assertFalse(result['services']['supply']['ready_for_mapping_comparison'])
        self.assertIn('reason', result['services']['supply'])

    def test_duplicate_caption_does_not_choose_a_nearby_owner(self):
        doc, graph, hashes = historical_tests.BranchInventoryTests().fixture()
        for point in [(0, 10), (1, 10)]:
            doc.modelspace().add_text('EQ', dxfattribs=dict(insert=point))
        result = inspect_view(doc, graph, 'EQ', 2, hashes, 'plan', [])
        self.assertEqual(result['status'], 'missing_or_ambiguous_native_caption')

    def test_history_comparison_reports_gains_and_blocks_regression_without_changing_evidence(self):
        def record(supply, return_):
            return dict(equipment_id='EQ', views=dict(plan=dict(services=dict(
                supply=dict(ready_for_mapping_comparison=supply),
                return_=dict(ready_for_mapping_comparison=return_)))))
        old = record(True, False)
        new = record(False, True)
        # Actual service key is return, not a Python keyword placeholder.
        for value in (old, new):
            services = value['views']['plan']['services']
            services['return'] = services.pop('return_')
        baseline, current = dict(records=[old]), dict(records=[new])
        before = copy.deepcopy((baseline, current))
        result = compare_ready(current, baseline)
        self.assertEqual([(x['view'], x['system']) for x in result['regressions']], [('plan', 'supply')])
        self.assertEqual([(x['view'], x['system']) for x in result['gains']], [('plan', 'return')])
        self.assertFalse(result['historical_pass_flags_reused'])
        self.assertEqual((baseline, current), before)

    def test_equipment_cannot_be_deleted_to_improve_ready_counts(self):
        with self.assertRaisesRegex(ValueError, 'preserving all native instances'):
            compare_ready(dict(records=[]), dict(records=[dict(equipment_id='EQ')]))

    def test_current_owner_child_is_verified_before_retained_circle_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'graph_with_edges.json'
            path.write_bytes(encode(dict(sourceReviewedInterfaceOwners={}, sourceCirclePathNormalization={})))
            audit = dict(output_graph_sha256=sha(path))
            with patch('attach_reviewed_interface_owners.verify_output', return_value=audit) as current, \
                    patch('normalize_plan_circle_paths.verify_output') as old:
                self.assertEqual(verify_local_plan(path, 'reviewed_interface_owners'), audit)
            current.assert_called_once_with(path.parent)
            old.assert_not_called()

    def test_gap_child_is_verified_before_retained_pending_T_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'graph_with_edges.json'
            path.write_bytes(encode(dict(sourceReviewedDrawingGapContinuity={}, sourcePendingNativeJunctionResolution={})))
            audit = dict(output_graph_sha256=sha(path))
            with patch('reconstruct_reviewed_plan_gaps.verify_output', return_value=audit) as current:
                self.assertEqual(verify_local_plan(path, 'reviewed_drawing_gaps'), audit)
            current.assert_called_once_with(path.parent)

    def test_missing_new_child_root_cannot_fall_back_to_an_old_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'graph_with_edges.json'
            path.write_bytes(encode(dict(sourceCirclePathNormalization={})))
            with patch('attach_reviewed_interface_owners.verify_output') as replay:
                with self.assertRaisesRegex(ValueError, 'lacks reviewed owner root'):
                    verify_local_plan(path, 'reviewed_interface_owners')
            replay.assert_not_called()

    def test_equal_size_changed_input_rejected_by_content_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'source'
            path.write_bytes(b'first')
            item = dict(path=str(path), sha256=sha(path))
            self.assertEqual(checked(item), path.resolve())
            path.write_bytes(b'other')
            with self.assertRaisesRegex(ValueError, 'input changed'):
                checked(item)


if __name__ == '__main__':
    unittest.main()
