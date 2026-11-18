import copy
import unittest

from current_graph_calibrated_dn import control_lineage


class NativeControlFragmentTests(unittest.TestCase):
    def fixture(self):
        edge = dict(edge_id='OLD', system='supply', source_handles=['LINE1'], path=[[0, 0], [10, 0]],
                    path_points=[[0, 0], [10, 0]], attribute_paths=[[[0, 0], [10, 0]]], path_length=10)
        original = dict(metadata=dict(source_sha256='SOURCE'), edges=[edge])
        merged = dict(edge_id='NEW', system='supply', source_handles=['LINE1', 'LINE2'],
                      source_circle_continuity=dict(prior_edge_snapshots=[copy.deepcopy(edge)]))
        current = dict(metadata=dict(source_sha256='SOURCE'), edges=[merged],
                       sourceTwoArmCircleContinuity=dict(edge_id_aliases=dict(OLD='NEW')))
        policy = dict(source_sha256='SOURCE', graph_sha256='ORIGINAL', controls=[dict(text_handle='TEXT', edge_id='OLD', source_line_handle='LINE1')], selections=[])
        return current, original, policy

    def test_original_fragment_scope_retained_without_promoting_merged_DN(self):
        current, original, policy = self.fixture()
        before = copy.deepcopy((current, original, policy))
        row = control_lineage(current, original, policy, 'SOURCE', 'CURRENT', 'ORIGINAL')[0]
        self.assertEqual(row['original_edge_id'], 'OLD')
        self.assertEqual(row['current_edge_id'], 'NEW')
        self.assertFalse(row['current_whole_edge_DN_assigned'])
        self.assertEqual((current, original, policy), before)

    def test_changed_fragment_wrong_source_or_owner_block(self):
        for case in ('fragment', 'source', 'owner'):
            current, original, policy = self.fixture()
            if case == 'fragment': current['edges'][0]['source_circle_continuity']['prior_edge_snapshots'][0]['path_length'] = 99
            elif case == 'source': policy['source_sha256'] = 'WRONG'
            else: current['edges'][0]['source_handles'] = ['OTHER']
            with self.subTest(case=case), self.assertRaises(ValueError):
                control_lineage(current, original, policy, 'SOURCE', 'CURRENT', 'ORIGINAL')

    def test_target_cannot_use_control_fragment_exception(self):
        current, original, policy = self.fixture()
        policy['selections'] = [dict(text_handle='TARGET', edge_id='OLD', source_line_handle='LINE1')]
        with self.assertRaisesRegex(ValueError, 'Changed target'):
            control_lineage(current, original, policy, 'SOURCE', 'CURRENT', 'ORIGINAL')


if __name__ == '__main__': unittest.main()
