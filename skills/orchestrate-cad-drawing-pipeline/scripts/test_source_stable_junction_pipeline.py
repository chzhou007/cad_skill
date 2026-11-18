import unittest
from unittest.mock import patch
from pipeline import reconstruct_source_stable_junctions,validate_source_stable_junctions
from source_stable_junction_reapplication import MODE

class Tests(unittest.TestCase):
    def proof(self):return dict(mode=MODE,all_current_plan_Ts_screened=True,original_and_current_native_rays_replayed=True,source_graphs_changed=False,source_configuration_changed=False,DN_values_assigned=0,length_values_assigned=0,mapping_values_assigned=0,human_accepted=False,whole_goal_complete=False,counts={'held':2})
    def test_formal_batch_entry_keeps_unresolved_native_cases_explicit(self):
        with patch('source_stable_junction_reapplication.verify_output',return_value=self.proof()):self.assertEqual(validate_source_stable_junctions('output')['counts']['held'],2)
        with patch('source_stable_junction_reapplication.produce')as produce,patch('pipeline.validate_source_stable_junctions',return_value={'status':'pending'}):reconstruct_source_stable_junctions('manifest','output')
        produce.assert_called_once_with('manifest','output')
    def test_missing_native_replay_or_attribute_fill_blocks(self):
        for key,value in[('original_and_current_native_rays_replayed',False),('all_current_plan_Ts_screened',False),('source_configuration_changed',True),('DN_values_assigned',1),('length_values_assigned',1),('mapping_values_assigned',1),('human_accepted',True)]:
            proof=self.proof();proof[key]=value
            with self.subTest(key=key),patch('source_stable_junction_reapplication.verify_output',return_value=proof),self.assertRaises(ValueError):validate_source_stable_junctions('output')
if __name__=='__main__':unittest.main()
