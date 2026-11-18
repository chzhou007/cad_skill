import unittest
from unittest.mock import patch
from pipeline import validate_equivalent_member_bounded_batch,reconstruct_equivalent_member_bounded_batch
from rebuild_equivalent_member_bounded_batch import MODE
class Tests(unittest.TestCase):
    def good(self):return dict(mode=MODE,complete_parent_rechecked=True,old_provider_observations_preserved=True,source_graphs_mutated=False,physical_pipe_count_inferred=False,DN_used_for_mapping=False,unknown_length_filled_with_zero=False,human_accepted=False,records=[dict(nominal_mm=None,installed_length_mm=None,net_pipe_cut_length_mm=None,human_accepted=False,complete_horizontal_centerline_mm=6000,incomplete_reasons=[])],counts={})
    def test_source_gate_does_not_claim_publication_DN_or_HIL(self):
        with patch('rebuild_equivalent_member_bounded_batch.verify_output',return_value=self.good()):
            r=validate_equivalent_member_bounded_batch('new');self.assertEqual(r['native_equivalent_member_bounded_batch'],'passed');self.assertEqual(r['status'],'pending')
        for key,value in [('complete_parent_rechecked',False),('old_provider_observations_preserved',False),('physical_pipe_count_inferred',True),('DN_used_for_mapping',True),('human_accepted',True)]:
            r=self.good();r[key]=value
            with self.subTest(key=key),patch('rebuild_equivalent_member_bounded_batch.verify_output',return_value=r),self.assertRaises(ValueError):validate_equivalent_member_bounded_batch('new')
    def test_incomplete_length_and_unread_DN_are_rejected(self):
        for key,value in [('nominal_mm',150),('installed_length_mm',0),('incomplete_reasons',['crossing_omission_physical_length_unknown'])]:
            r=self.good();r['records'][0][key]=value
            with self.subTest(key=key),patch('rebuild_equivalent_member_bounded_batch.verify_output',return_value=r),self.assertRaises(ValueError):validate_equivalent_member_bounded_batch('new')
    def test_reconstruct_runs_native_owner_then_original_gate(self):
        with patch('rebuild_equivalent_member_bounded_batch.produce')as p,patch('pipeline.validate_equivalent_member_bounded_batch',return_value={}):reconstruct_equivalent_member_bounded_batch('manifest','new')
        p.assert_called_once_with('manifest','new')
if __name__=='__main__':unittest.main()
