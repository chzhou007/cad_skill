import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from junction_rebased_corridor_gate import validate
from pipeline import validate_source_crossview


class CurrentCorridorGateTests(unittest.TestCase):
    def fixture(self):
        group = dict(group_id='G1', equipment_scope=['D1', 'D2', 'D3'], plan_graph_sha256='PLAN', iso_graph_sha256='AXIS',
            source_sha256=dict(plan='PS', iso='IS'), local_graphs_mutated=False, expert_confirmation_claimed=False,
            human_accepted=False, hil_ready=False, records=[], historical_mapping_lineage=[],
            evidence=dict(main_topology={s: dict(pairwise_order_checks=[{}, {}, {}], adjacent=[{}, {}]) for s in ('supply', 'return')}))
        for system in ('supply', 'return'):
            for i in range(5):
                number = len(group['records'])+1
                group['records'].append(dict(mapping_id='M'+str(number), system=system,
                    kind='equipment_branch' if i < 3 else 'main_between_equipment_branches',
                    plan_edges=['P'+str(number)], iso_edges=['I'+str(number)]))
                group['historical_mapping_lineage'].append(dict(local_paths_and_snapshots_preserved=True, human_confirmation_transferred=False))
        return dict(mode='source_checked_junction_rebased_corridor_groups_v1', status='source_checked_path_correspondence_attributes_pending',
            evidence=dict(inherited_pending_scope=dict(mode='pending_native_junction_rebased_branch_inventory_v1',
                plan_graph_sha256='PLAN', preserved_axis_evidence_on_identical_inputs=True)),
            plan_graph_sha256='PLAN', iso_graph_sha256='AXIS', source_sha256=group['source_sha256'], groups=[group],
            records=[dict(r, group_id='G1') for r in group['records']], equipment_scope=['D1', 'D2', 'D3'],
            local_graphs_mutated=False, expert_confirmation_claimed=False, whole_floor_connectivity_confirmed=False,
            physical_values_assigned=0, human_accepted=False, hil_ready=False)

    def test_complete_source_groups_stay_pending_for_attributes_and_whole_network(self):
        result = validate(self.fixture())
        self.assertEqual(result['mapped_paths'], 10)
        self.assertFalse(result['whole_floor_connectivity_confirmed'])
        self.assertFalse(result['hil_ready'])
        self.assertEqual(result['physical_values_assigned'], 0)

    def test_stale_local_proof_or_promoted_history_and_values_block(self):
        for case in ('graph', 'history', 'order', 'service', 'physical', 'HIL'):
            mapping = self.fixture()
            if case == 'graph': mapping['evidence']['inherited_pending_scope']['plan_graph_sha256'] = 'OLD'
            elif case == 'history': mapping['groups'][0]['historical_mapping_lineage'][0]['human_confirmation_transferred'] = True
            elif case == 'order': mapping['groups'][0]['evidence']['main_topology']['supply']['adjacent'].pop()
            elif case == 'service': mapping['groups'][0]['records'][-1]['system'] = 'supply'
            elif case == 'physical': mapping['physical_values_assigned'] = 1
            else: mapping['human_accepted'] = True
            with self.subTest(case=case), self.assertRaises(ValueError): validate(mapping)

    def test_group_writers_cannot_overlap(self):
        mapping = self.fixture()
        group = copy.deepcopy(mapping['groups'][0]); group['group_id'] = 'G2'; group['equipment_scope'] = ['D4', 'D5', 'D6']
        mapping['groups'].append(group)
        with self.assertRaisesRegex(ValueError, 'repeats local graph writers'): validate(mapping)

    def test_actual_pipeline_dispatch_replays_current_owner(self):
        mapping = self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'source-mapping-receipt.json').write_text(json.dumps(dict(mode=mapping['mode'])), encoding='utf-8')
            with patch('match_junction_rebased_corridors.verify_output', return_value=mapping) as native:
                result = validate_source_crossview(root)
            native.assert_called_once_with(root)
            self.assertEqual(result['mapped_paths'], 10)
            with patch('match_junction_rebased_corridors.verify_output', side_effect=ValueError('source changed')):
                with self.assertRaisesRegex(ValueError, 'source changed'): validate_source_crossview(root)


if __name__ == '__main__': unittest.main()
