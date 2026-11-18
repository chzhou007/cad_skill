import unittest
from unittest.mock import patch
from pipeline import validate_native_main_chain_batch
from batch_native_main_chains import MODE

class Tests(unittest.TestCase):
    def data(self):return dict(mode=MODE,attributes_fused=False,human_accepted=False,hil_ready=False,
        all_axis_edges=dict(total_edges=576,states={}),native_main_chain_extension={'3':dict(records=[dict(iso_edges=['A','B'])])})
    def test_source_replayed_chains_are_not_fused_or_per_edge_metrics(self):
        with patch('extend_native_main_chain_batch.verify_output',return_value=self.data()):r=validate_native_main_chain_batch('run')
        self.assertEqual(r['additional_axis_edge_candidates'],2);self.assertFalse(r['attributes_fused'])
        self.assertFalse(r['per_axis_edge_metric_allocation_known']);self.assertFalse(r['hil_ready'])
    def test_source_failure_or_false_acceptance_is_rejected(self):
        with patch('extend_native_main_chain_batch.verify_output',side_effect=ValueError('native path changed')):
            with self.assertRaises(ValueError):validate_native_main_chain_batch('run')
        for key in ['attributes_fused','human_accepted','hil_ready']:
            value=self.data();value[key]=True
            with patch('extend_native_main_chain_batch.verify_output',return_value=value):
                with self.assertRaises(ValueError):validate_native_main_chain_batch('run')

if __name__=='__main__':unittest.main()
