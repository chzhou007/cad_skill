import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_plan_DN


class CurrentPlanDNGateTests(unittest.TestCase):
    def fixture(self):
        controls = dict(controls=[{}], current_graph_sha256='NEW', original_graph_sha256='OLD',
            source_controls_replayed=True, current_targets_replayed=True, target_annotation_guards_unchanged=True,
            original_policy_or_graph_mutated=False, collector_globals_changed=False, human_accepted=False, current_whole_edge_DN_assigned=0)
        return dict(mode='junction_rebased_calibrated_plan_DN_scopes_v1', status='source_checked_plan_DN_scopes_human_pending',
            graph_sha256='NEW', original_graph_sha256='OLD', source_sha256='SOURCE', local_graph_mutated=False,
            human_accepted=False, physical_values_fused=False, calibrated_direct_binding=dict(native_calibration_control_rebase=controls),
            records=[dict(nominal_mm=100), dict(nominal_mm=None)])

    def run_case(self, folder, result):
        (folder/'plan-DN-scope-receipt.json').write_text(json.dumps(dict(mode=result['mode'])), encoding='utf-8')
        with patch('junction_rebased_plan_DN_scopes.verify_output', return_value=result) as native:
            gate = validate_plan_DN(folder)
        native.assert_called_once_with(folder)
        return gate

    def test_actual_dispatch_preserves_unknowns_and_pending_physical_fusion(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_case(Path(temp), self.fixture())
        self.assertEqual(result['known_DN_scopes'], 1)
        self.assertEqual(result['plan_drawn_pipe_scopes'], 2)
        self.assertFalse(result['hil_ready'])

    def test_widened_control_stale_graph_or_unreplayed_target_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            for field, value in [('current_graph_sha256', 'OTHER'), ('target_annotation_guards_unchanged', False),
                                 ('current_targets_replayed', False), ('current_whole_edge_DN_assigned', 1), ('collector_globals_changed', True)]:
                current = self.fixture()
                current['calibrated_direct_binding']['native_calibration_control_rebase'][field] = value
                with self.subTest(field=field), self.assertRaises(ValueError): self.run_case(Path(temp), current)

    def test_native_failures_propagate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'plan-DN-scope-receipt.json').write_text(json.dumps(dict(mode=self.fixture()['mode'])), encoding='utf-8')
            with patch('junction_rebased_plan_DN_scopes.verify_output', side_effect=ValueError('native changed')), self.assertRaisesRegex(ValueError, 'native changed'):
                validate_plan_DN(root)


if __name__ == '__main__': unittest.main()
