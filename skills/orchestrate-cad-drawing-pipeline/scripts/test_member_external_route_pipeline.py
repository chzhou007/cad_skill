import unittest
from unittest.mock import patch
from pipeline import reconstruct_member_external_routes,validate_member_external_routes
from rebuild_member_external_routes import MODE

class Tests(unittest.TestCase):
    def data(self):
        proof=dict(mode=MODE,complete_current_provider_natively_replayed=True,complete_external_port_cohort_screened=True,new_native_routes_and_junctions_replayed=True,all_old_provider_observations_preserved=True,source_graphs_mutated=False,component_owners_changed=False,DN_used_for_mapping=False,global_plan_topology_complete=False,human_accepted=False,physical_values_assigned=0,counts={})
        return proof,dict(counts={}),dict(nodes=[],edges=[])
    def test_reconstruct_and_independent_native_validator_leave_HIL_pending(self):
        with patch('rebuild_member_external_routes.verify_output',return_value=self.data()):self.assertEqual(validate_member_external_routes('run')['status'],'pending')
        with patch('rebuild_member_external_routes.produce')as produce,patch('pipeline.validate_member_external_routes',return_value={}):reconstruct_member_external_routes('manifest','output')
        produce.assert_called_once_with('manifest','output')
    def test_incomplete_parent_global_claim_or_attribute_fill_blocks(self):
        for key,value in [('complete_current_provider_natively_replayed',False),('complete_external_port_cohort_screened',False),('new_native_routes_and_junctions_replayed',False),('component_owners_changed',True),('physical_values_assigned',1),('global_plan_topology_complete',True)]:
            data=self.data();data[0][key]=value
            with self.subTest(key=key),patch('rebuild_member_external_routes.verify_output',return_value=data),self.assertRaises(ValueError):validate_member_external_routes('run')

if __name__=='__main__':unittest.main()
