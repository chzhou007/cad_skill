import copy
import unittest
from unittest.mock import patch
from pipeline import validate_known_rule_batch
from batch_apply_crossview_rules import MODE


class Tests(unittest.TestCase):
    def data(self):
        return dict(mode=MODE,attributes_fused=False,human_accepted=False,hil_ready=False,
            all_axis_edges=dict(total_edges=2,states={'unmatched_local_or_main_detail_path':2},
                records=[dict(edge_id='E1'),dict(edge_id='E2')]))

    def test_independent_batch_replay_retains_unmatched_scope_and_pending_acceptance(self):
        with patch('apply_crossview_rule_batch.verify_output',return_value=self.data()) as replay:
            out=validate_known_rule_batch('fixed-run');replay.assert_called_once_with('fixed-run')
        self.assertEqual(out['processed_axis_edges'],2);self.assertEqual(out['status'],'pending')
        self.assertFalse(out['attributes_fused']);self.assertFalse(out['hil_ready'])

    def test_replay_failure_or_false_acceptance_cannot_be_masked(self):
        with patch('apply_crossview_rule_batch.verify_output',side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError,'source changed'):validate_known_rule_batch('run')
        for key in ['attributes_fused','human_accepted','hil_ready']:
            value=self.data();value[key]=True
            with self.subTest(key=key),patch('apply_crossview_rule_batch.verify_output',return_value=value):
                with self.assertRaises(ValueError):validate_known_rule_batch('run')

    def test_dropped_or_duplicate_axis_edges_are_rejected(self):
        value=self.data();value['all_axis_edges']['records'][1]['edge_id']='E1'
        with patch('apply_crossview_rule_batch.verify_output',return_value=value):
            with self.assertRaises(ValueError):validate_known_rule_batch('run')


if __name__=='__main__':unittest.main()
