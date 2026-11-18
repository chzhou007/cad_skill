import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
import test_adopt_current_floor_plan_scopes as fixtures
from adopt_current_floor_plan_scopes import adopt, ROOT, FIELD
from current_floor_scope_adoption_gate import check, restore
from source_comparison_gate import check as dispatch


class CurrentFloorScopeGateTests(unittest.TestCase):
    def fixture(self, folder):
        parent, scopes, evidence = fixtures.CurrentFloorAdoptionTests().fixture()
        p = folder/'parent'; p.mkdir(); old = p/'graph_with_edges.json'; old.write_text(json.dumps(parent), encoding='utf-8')
        ph = hashlib.sha256(old.read_bytes()).hexdigest(); graph, stage = adopt(parent, scopes, evidence, 2, ph)
        out = folder/'current'; out.mkdir(); target = out/'graph_with_edges.json'; target.write_text(json.dumps(graph), encoding='utf-8')
        gh = hashlib.sha256(target.read_bytes()).hexdigest(); prior = dict(graph_sha256=ph, status='pending', errors=[], pending=['KEEP UNKNOWN'], hil_ready=False, human_accepted=False)
        (p/'source-comparison-gate.json').write_text(json.dumps(prior), encoding='utf-8')
        audit = dict(stage=stage, output_graph_sha256=gh, parent_graph=dict(path=str(old), sha256=ph),
            verified_complete_parent=dict(output_graph_sha256=ph), hil_ready=False, human_accepted=False)
        return target, gh, graph, parent, prior, audit

    def test_new_root_precedes_old_roots_and_preserves_parent_issues(self):
        with tempfile.TemporaryDirectory() as temp:
            target, gh, graph, parent, prior, audit = self.fixture(Path(temp))
            with patch('adopt_current_floor_plan_scopes.verify_output', return_value=audit) as native:
                result = dispatch(prior, gh, target.parent, target)
                again = check(target.parent, result, gh, target)
            self.assertEqual(native.call_count, 2)
            self.assertEqual(result, again); self.assertEqual(result['pending'][0], 'KEEP UNKNOWN')
            self.assertEqual(result['errors'], []); self.assertFalse(result['hil_ready'])

    def test_unrelated_attribute_loss_or_sidecar_change_cannot_hide_behind_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            _, _, graph, parent, _, audit = self.fixture(Path(temp))
            for mode in ('parent', 'sidecar', 'physical'):
                bad = copy.deepcopy(graph); stage = copy.deepcopy(audit['stage'])
                if mode == 'parent': bad['edges'][0]['component_inventory'] = []
                elif mode == 'sidecar': bad['edges'][0][FIELD]['diameter']['nominal_mm'] = 10
                else: stage['whole_values_or_connections_added'] = 1; bad[ROOT] = stage
                with self.subTest(mode=mode), self.assertRaises(ValueError): restore(bad, stage, parent)

    def test_native_failure_and_changed_report_remain_blockers(self):
        with tempfile.TemporaryDirectory() as temp:
            target, gh, _, _, prior, audit = self.fixture(Path(temp))
            with patch('adopt_current_floor_plan_scopes.verify_output', side_effect=ValueError('native failed')):
                self.assertEqual(dispatch(prior, gh, target.parent, target)['status'], 'failed')
            wrong = dict(prior, pending=[])
            with patch('adopt_current_floor_plan_scopes.verify_output', return_value=audit), self.assertRaisesRegex(ValueError, 'parent issues'):
                check(target.parent, wrong, gh, target)


if __name__ == '__main__': unittest.main()
