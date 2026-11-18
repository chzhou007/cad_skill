import unittest
from unittest.mock import patch
from pipeline import validate_current_two_arm_routes,reconstruct_current_two_arm_routes
from current_two_arm_circle_routes import MODE
class Tests(unittest.TestCase):
    def proof(self):return dict(mode=MODE,complete_original_adopted_provider_replayed=True,current_local_topology_parents_replayed=True,all_current_pipe_circles_screened=True,original_two_arm_rule_reused=True,old_source_graphs_unchanged=True,all_old_provider_observations_preserved=True,new_pipe_attribute_values=0,physical_Ts_added=0,human_accepted=False,whole_goal_complete=False,counts={})
    def test_native_entry_and_preserved_attribute_contract(self):
        with patch('rebuild_current_two_arm_circle_routes.verify_output',return_value=(self.proof(),{},{},{})),patch('two_arm_affected_junctions.replay',return_value={'count':2}):self.assertEqual(validate_current_two_arm_routes('run')['native_current_two_arm_routes'],'passed')
        with patch('rebuild_current_two_arm_circle_routes.produce')as produce,patch('pipeline.validate_current_two_arm_routes',return_value={}):reconstruct_current_two_arm_routes('manifest','run')
        produce.assert_called_once_with('manifest','run')
    def test_no_native_parent_false_T_or_implicit_metric_assignment_blocks(self):
        for key,value in [('complete_original_adopted_provider_replayed',False),('current_local_topology_parents_replayed',False),('all_current_pipe_circles_screened',False),('old_source_graphs_unchanged',False),('new_pipe_attribute_values',1),('physical_Ts_added',1),('human_accepted',True)]:
            p=self.proof();p[key]=value
            with self.subTest(key=key),patch('rebuild_current_two_arm_circle_routes.verify_output',return_value=(p,{},{},{})),self.assertRaises(ValueError):validate_current_two_arm_routes('run')
if __name__=='__main__':unittest.main()
