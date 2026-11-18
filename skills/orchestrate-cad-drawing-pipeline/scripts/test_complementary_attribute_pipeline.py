import unittest
from unittest.mock import patch
from pipeline import reconstruct_complementary_plan_attributes,validate_complementary_plan_attributes,validate_complementary_attribute_viewer
from complementary_plan_attribute_application import MODE

class Pipeline(unittest.TestCase):
    def result(self):
        return dict(mode=MODE,complete_corrected_parent_replayed=True,original_complete_DN_parent_replayed=True,current_T_and_original_metric_owners_reused=True,
                    all_current_complementary_intervals_screened=True,all_original_known_plan_DN_preserved=True,all_historical_main_roles_reapplied=True,source_graphs_mutated=False,
                    source_components_reassigned=False,axis_values_used_for_horizontal_DN=False,vertical_values_assigned=0,installed_lengths_assigned=0,human_accepted=False,counts={}),{}
    def test_formal_native_owner_and_source_viewer_validator_keep_human_acceptance_separate(self):
        with patch('reapply_complementary_plan_attributes.verify_output',return_value=self.result()):self.assertEqual(validate_complementary_plan_attributes('run')['status'],'pending')
        with patch('reapply_complementary_plan_attributes.produce')as produce,patch('pipeline.validate_complementary_plan_attributes',return_value={}):reconstruct_complementary_plan_attributes('manifest','run')
        produce.assert_called_once_with('manifest','run')
        with patch('refresh_complementary_plan_attributes.verify',return_value={'artifact_replay':'passed'}):self.assertEqual(validate_complementary_attribute_viewer('bundle')['artifact_replay'],'passed')
    def test_original_source_skip_axis_substitution_or_vertical_write_blocks(self):
        for key,value in [('complete_corrected_parent_replayed',False),('original_complete_DN_parent_replayed',False),('all_original_known_plan_DN_preserved',False),('all_historical_main_roles_reapplied',False),('axis_values_used_for_horizontal_DN',True),('vertical_values_assigned',1)]:
            result=self.result();result[0][key]=value
            with self.subTest(key=key),patch('reapply_complementary_plan_attributes.verify_output',return_value=result),self.assertRaises(ValueError):validate_complementary_plan_attributes('run')

if __name__=='__main__':unittest.main()
