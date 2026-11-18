import unittest
from unittest.mock import patch
from pipeline import validate_equivalent_member_plan_attributes,validate_cohort_member_provider_inventory,reconstruct_cohort_member_provider_inventory
class Tests(unittest.TestCase):
    def good(self):
        from apply_equivalent_member_plan_attributes import MODE
        r=dict(mode=MODE,counts={},vertical_values_assigned=0,installed_lengths_assigned=0)
        r.update({k:True for k in('complete_source_batch_replayed','existing_complete_DN_provider_retained','specific_calibrated_and_F_readers_reapplied','all_horizontal_values_from_plan')})
        r.update({k:False for k in('source_graphs_mutated','DN_used_for_mapping','physical_pipe_count_inferred','unknown_length_filled_with_zero','human_accepted')});return r
    def test_native_attribute_success_still_pending_publication_and_HIL(self):
        with patch('apply_equivalent_member_plan_attributes.verify_output',return_value=self.good()):r=validate_equivalent_member_plan_attributes('new')
        self.assertEqual(r['status'],'pending');self.assertFalse(r['human_accepted'])
        for key in('vertical_values_assigned','installed_lengths_assigned','physical_pipe_count_inferred','human_accepted'):
            v=self.good();v[key]=True
            with self.subTest(key=key),patch('apply_equivalent_member_plan_attributes.verify_output',return_value=v),self.assertRaises(ValueError):validate_equivalent_member_plan_attributes('new')
    def test_provider_checks_complete_ancestry_and_reconstruct_dispatch(self):
        from cohort_member_provider_inventory import MODE
        r=dict(mode=MODE,current_viewer_and_complete_original_inventory_replayed=True,all_old_provider_observations_preserved=True,member_namespaces_preserved=True,human_accepted=False,new_correspondences_assigned=0,DN_or_length_values_assigned=0,counts={})
        with patch('cohort_member_provider_inventory.verify_output',return_value=r):self.assertEqual(validate_cohort_member_provider_inventory('new')['status'],'pending')
        r['member_namespaces_preserved']=False
        with patch('cohort_member_provider_inventory.verify_output',return_value=r),self.assertRaises(ValueError):validate_cohort_member_provider_inventory('new')
        with patch('cohort_member_provider_inventory.produce')as p,patch('pipeline.validate_cohort_member_provider_inventory',return_value={}):reconstruct_cohort_member_provider_inventory('manifest','new')
        p.assert_called_once_with('manifest','new')
if __name__=='__main__':unittest.main()
