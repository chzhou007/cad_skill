import unittest
from unittest.mock import patch
from pipeline import reconstruct_complementary_anchor_chains,validate_complementary_anchor_chains
from complementary_anchor_chains import MODE

class Pipeline(unittest.TestCase):
    def result(self):
        return dict(mode=MODE,complete_original_provider_replayed=True,all_current_floor_regions_screened=True,all_current_plans_known_exploded_ball_population_screened=True,
                    source_graphs_mutated=False,DN_used_for_matching=False,off_chain_terminal_identities_assigned=False,
                    physical_values_assigned=0,human_accepted=False,counts={}),dict(counts={})
    def test_formal_entry_and_independent_native_validation(self):
        with patch('rebuild_complementary_anchor_chains.verify_output',return_value=self.result()):
            self.assertEqual(validate_complementary_anchor_chains('run')['status'],'pending')
        with patch('rebuild_complementary_anchor_chains.produce')as produce,patch('pipeline.validate_complementary_anchor_chains',return_value={}):
            reconstruct_complementary_anchor_chains('manifest','run')
        produce.assert_called_once_with('manifest','run')
    def test_ancestor_skip_terminal_guess_or_attribute_adoption_is_blocked(self):
        for key,value in [('complete_original_provider_replayed',False),('all_current_floor_regions_screened',False),('all_current_plans_known_exploded_ball_population_screened',False),('off_chain_terminal_identities_assigned',True),('physical_values_assigned',1),('source_graphs_mutated',True)]:
            result=self.result();result[0][key]=value
            with self.subTest(key=key),patch('rebuild_complementary_anchor_chains.verify_output',return_value=result),self.assertRaises(ValueError):validate_complementary_anchor_chains('run')

if __name__=='__main__':unittest.main()
