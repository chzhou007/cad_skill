import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
import plan_circle_continuity_source_gate as gate
import source_comparison_gate as dispatcher


class CircleSourceGateTests(unittest.TestCase):
    def fixture(self, root):
        parent = root/'parent.json'
        parent.write_text('{}', encoding='utf-8')
        graph = dict(nodes=[], edges=[], metadata=dict(hil_ready=False),
            derivedEvidenceInvalidation=dict(historical_annotations_preserved=True),
            sourceSideviewEquipmentOwnership=dict(records=[]),
            sourceTwoArmCircleContinuity=dict(records=[{}], retired_nodes=[dict(node_id='U1'), dict(node_id='U2')],
                physical_Ts_added=0, physical_connector_lengths_assigned=0, human_accepted=False))
        target = root/'graph_with_edges.json'
        target.write_text(json.dumps(graph), encoding='utf-8')
        audit = dict(output_graph_sha256=gate.digest(target), inputs=dict(graph=dict(path=str(parent), sha256=gate.digest(parent)), source=dict(sha256='SOURCE')))
        prior = dict(errors=[], pending=['unrelated pending', '2 graph nodes have unresolved source-terminal or equipment-overlap semantics'],
                     graph_unresolved_node_blockers=[dict(node_id='U1'), dict(node_id='U2')])
        return graph, target, audit, prior

    def test_complete_native_owner_before_parent_and_only_proved_terminals_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, target, audit, prior = self.fixture(root)
            with patch('normalize_two_arm_circle_continuity.verify_output', return_value=audit) as native, patch.object(dispatcher, 'check', return_value=prior):
                result = gate.check(root, {}, gate.digest(target), target)
            native.assert_called_once_with(root)
            self.assertEqual(result['errors'], [])
            self.assertEqual(result['status'], 'pending')
            self.assertIn('unrelated pending', result['pending'])
            self.assertEqual(result['two_arm_circle_continuity_stage']['resolved_temporary_node_ids'], ['U1', 'U2'])
            self.assertFalse(result['hil_ready'])

    def test_unrelated_terminal_loss_or_native_failure_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, target, audit, prior = self.fixture(root)
            prior['graph_unresolved_node_blockers'].append(dict(node_id='REAL-UNKNOWN'))
            with patch('normalize_two_arm_circle_continuity.verify_output', return_value=audit), patch.object(dispatcher, 'check', return_value=prior):
                with self.assertRaisesRegex(ValueError, 'unrelated unresolved'): gate.check(root, {}, gate.digest(target), target)
            with patch('normalize_two_arm_circle_continuity.verify_output', side_effect=ValueError('native changed')):
                with self.assertRaisesRegex(ValueError, 'native changed'): gate.check(root, {}, gate.digest(target), target)

    def test_physical_length_or_human_acceptance_cannot_be_laundered(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            graph, target, audit, prior = self.fixture(root)
            for field, value in [('physical_connector_lengths_assigned', 1), ('human_accepted', True)]:
                current = copy.deepcopy(graph)
                current['sourceTwoArmCircleContinuity'][field] = value
                target.write_text(json.dumps(current), encoding='utf-8')
                audit['output_graph_sha256'] = gate.digest(target)
                with patch('normalize_two_arm_circle_continuity.verify_output', return_value=audit), patch.object(dispatcher, 'check', return_value=prior):
                    with self.assertRaises(ValueError): gate.check(root, {}, gate.digest(target), target)

    def test_dispatch_selects_child_before_copied_sideview_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, target, _, _ = self.fixture(root)
            with patch.object(gate, 'check', return_value=dict(status='pending', child=True)) as selected:
                self.assertTrue(dispatcher.check({}, gate.digest(target), root, target)['child'])
            selected.assert_called_once()

    def test_dispatch_native_error_has_no_ancestor_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, target, _, _ = self.fixture(root)
            with patch.object(gate, 'check', side_effect=ValueError('native changed')):
                result = dispatcher.check({}, gate.digest(target), root, target)
            self.assertEqual(result['status'], 'failed')
            self.assertTrue(any('native changed' in e for e in result['errors']))


if __name__ == '__main__':
    unittest.main()
