import unittest
from unittest.mock import patch
from rebuild_wave_cohort_crossview_batch import MODE
from pipeline import validate_wave_main_crossview_batch


class Tests(unittest.TestCase):
    def data(self):
        return dict(mode=MODE,attributes_fused=False,human_accepted=False,hil_ready=False,
            all_axis_edges=dict(total_edges=576,states={}),current_wave_cohort=dict(floor=3,unchanged_floor_results_preserved=['1','2']),
            inventories={'3':dict(counts=dict(equipment=36,ready_for_mapping_comparison=36))})

    def test_replayed_batch_keeps_unchanged_floors_and_pending_attribute_acceptance(self):
        with patch('rebuild_wave_cohort_crossview_batch.verify_output',return_value=self.data()):
            result=validate_wave_main_crossview_batch('fixed-run')
        self.assertEqual(result['processed_axis_edges'],576);self.assertEqual(result['unchanged_floor_results_preserved'],['1','2'])
        self.assertEqual(result['status'],'pending');self.assertFalse(result['attributes_fused']);self.assertFalse(result['hil_ready'])

    def test_native_failure_or_false_human_acceptance_is_not_hidden(self):
        with patch('rebuild_wave_cohort_crossview_batch.verify_output',side_effect=ValueError('changed source')):
            with self.assertRaisesRegex(ValueError,'changed source'):validate_wave_main_crossview_batch('run')
        for key in ['attributes_fused','human_accepted','hil_ready']:
            value=self.data();value[key]=True
            with self.subTest(key=key),patch('rebuild_wave_cohort_crossview_batch.verify_output',return_value=value):
                with self.assertRaises(ValueError):validate_wave_main_crossview_batch('run')


if __name__=='__main__':unittest.main()
