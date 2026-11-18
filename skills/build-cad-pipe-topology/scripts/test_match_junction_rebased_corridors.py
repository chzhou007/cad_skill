import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import match_junction_rebased_corridors as owner


class RebasedCorridorTests(unittest.TestCase):
    def fixture(self):
        row = dict(mapping_id='OLD', kind='equipment_branch', system='supply', floor=2, equipment_id='D1',
            plan_edges=['P1'], iso_edges=['I1'], plan_start='PT', plan_end='D1', iso_start='IT', iso_end='D1',
            plan_snapshot=dict(nodes=[], edges=[]), iso_snapshot=dict(nodes=[], edges=[]))
        base = dict(plan_graph_sha256='OLDGRAPH', iso_graph_sha256='AXIS', source_sha256=dict(plan='PS', iso='IS'),
            equipment_scope=['D1', 'D2', 'D3'], records=[row])
        current = copy.deepcopy(base)
        current['plan_graph_sha256'] = 'NEWGRAPH'
        current['records'][0]['mapping_id'] = 'NEW'
        return current, base

    def test_new_proof_retains_old_identity_without_transferring_acceptance(self):
        current, old = self.fixture()
        result = owner.historical_lineage(current, old, 'OLDGRAPH')
        self.assertEqual(result[0]['previous_mapping_id'], 'OLD')
        self.assertEqual(result[0]['current_mapping_id'], 'NEW')
        self.assertFalse(result[0]['human_confirmation_transferred'])

    def test_same_labels_do_not_cover_source_or_path_changes(self):
        for field in ('plan_graph_sha256', 'iso_graph_sha256', 'source_sha256', 'plan_snapshot', 'iso_edges'):
            current, old = self.fixture()
            if field in old:
                old[field] = 'WRONG'
            else:
                old['records'][0][field] = ['WRONG']
            with self.subTest(field=field), self.assertRaises(ValueError):
                owner.historical_lineage(current, old, 'OLDGRAPH')

    def test_repeated_semantic_path_is_rejected(self):
        current, old = self.fixture()
        old['records'].append(copy.deepcopy(old['records'][0]))
        with self.assertRaisesRegex(ValueError, 'lost or duplicated'):
            owner.historical_lineage(current, old, 'OLDGRAPH')

    def test_independent_groups_cannot_double_count_the_same_equipment(self):
        current, old = self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'mapping.json'; path.write_text(json.dumps(old), encoding='utf-8')
            groups = [dict(group_id=str(i), previous_mapping=dict(path=str(path), sha256=owner.sha(path))) for i in range(2)]
            with patch.object(owner, 'correspond_group', return_value=current), self.assertRaisesRegex(ValueError, 'repeat equipment'):
                owner.groups_correspond({}, {}, {}, groups, {}, 'OLDGRAPH')

    def test_unqualified_small_or_unready_anchor_scope_blocks(self):
        for group in [dict(equipment_ids=['D1', 'D2'], floor=2, mapping_prefix='G'),
                      dict(equipment_ids=['D1', 'D2', 'D3'], floor=2, mapping_prefix='G')]:
            with self.assertRaises(ValueError):
                owner.correspond_group({}, {}, dict(records=[]), group, {})


if __name__ == '__main__': unittest.main()
