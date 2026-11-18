import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_crossview_inventory


class CircleJunctionInventoryGateTests(unittest.TestCase):
    def fixture(self, folder, pending=True):
        mode = 'pending_native_junction_rebased_branch_inventory_v1' if pending else 'two_arm_circle_rebased_branch_inventory_v1'
        module = 'pending_junction_branch_inventory' if pending else 'two_arm_circle_branch_inventory'
        key = 'pending_native_junction_inventory_rebase' if pending else 'two_arm_circle_inventory_rebase'
        rebase = dict(mode=mode, preserved_axis_evidence_on_identical_inputs=True, plan_graph_sha256='NEW',
            mapped_paths=0, physical_values_assigned=0, physical_ports_verified=False, human_accepted=False,
            fresh_plan_service_checks=[dict(equipment_id='DEV', system=s, ready=True) for s in ('supply', 'return')])
        if pending: rebase['resolved_native_T_ids'] = ['T1']
        result = dict(status='source_comparison_inventory_not_mapping', inventory_mode=mode, local_graphs_mutated=False,
            mapped_paths=0, human_accepted=False, hil_ready=False, records=[dict(equipment_id='DEV', ready_for_mapping_comparison=True)],
            counts=dict(equipment=1, ready_for_mapping_comparison=1), **{key: rebase})
        (folder/'inventory-receipt.json').write_text(json.dumps(dict(mode=mode)), encoding='utf-8')
        return module, key, result

    def test_both_modes_replay_native_owner_and_keep_mapping_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for pending in (False, True):
                module, _, inventory = self.fixture(folder, pending)
                with patch(module+'.verify_output', return_value=inventory) as native:
                    result = validate_crossview_inventory(folder)
                native.assert_called_once_with(folder)
                self.assertEqual(result['plan_graph_sha256'], 'NEW')
                self.assertEqual(result['plan_service_checks'], 2)
                self.assertEqual(result['mapped_paths'], 0)
                self.assertFalse(result['hil_ready'])

    def test_missing_duplicate_checks_or_acceptance_and_values_block(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            module, key, inventory = self.fixture(folder)
            for case in ('missing', 'duplicate', 'acceptance', 'values', 'axis', 'scope'):
                current = copy.deepcopy(inventory)
                rebase = current[key]
                if case == 'missing': rebase['fresh_plan_service_checks'].pop()
                elif case == 'duplicate': rebase['fresh_plan_service_checks'][1] = rebase['fresh_plan_service_checks'][0]
                elif case == 'acceptance': rebase['human_accepted'] = True
                elif case == 'values': rebase['physical_values_assigned'] = 1
                elif case == 'axis': rebase['preserved_axis_evidence_on_identical_inputs'] = False
                else: rebase['resolved_native_T_ids'] = []
                with self.subTest(case=case), patch(module+'.verify_output', return_value=current), self.assertRaises(ValueError):
                    validate_crossview_inventory(folder)

    def test_native_replay_failure_is_not_candidate_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            module, _, _ = self.fixture(folder)
            with patch(module+'.verify_output', side_effect=ValueError('native changed')), self.assertRaisesRegex(ValueError, 'native changed'):
                validate_crossview_inventory(folder)


if __name__ == '__main__':
    unittest.main()
