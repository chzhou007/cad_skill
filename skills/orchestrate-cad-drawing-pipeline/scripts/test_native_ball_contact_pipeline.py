import unittest
from unittest.mock import patch
from pipeline import validate_native_ball_contact_owners,reconstruct_native_ball_contact_owners
from native_ball_contact_reapplication import MODE

class Tests(unittest.TestCase):
    def data(self):
        return dict(mode=MODE,original_native_inventory_replayed=True,complete_source_family_scanned=True,all_component_ids_and_counts_conserved=True,equipment_membership_retained=True,source_graph_and_symbol_geometry_unchanged=True,published_graph_changed=False,related_mapping_confirmations_inherited=False,component_aware_mapping_requalified=False,viewer_index_adopted=False,human_accepted=False,physical_parameters_assigned=0,counts=dict(reassigned_components=12))
    def test_native_correction_does_not_accept_affected_mappings(self):
        with patch('rebuild_native_ball_contact_owners.verify_output',return_value=self.data()):self.assertEqual(validate_native_ball_contact_owners('run')['status'],'pending')
        with patch('rebuild_native_ball_contact_owners.produce')as owner,patch('pipeline.validate_native_ball_contact_owners',return_value={}):reconstruct_native_ball_contact_owners('manifest','run')
        owner.assert_called_once_with('manifest','run')
    def test_source_mutation_count_loss_or_inherited_confirmation_blocks_gate(self):
        for key,value in [('all_component_ids_and_counts_conserved',False),('source_graph_and_symbol_geometry_unchanged',False),('related_mapping_confirmations_inherited',True),('physical_parameters_assigned',1)]:
            result=self.data();result[key]=value
            with self.subTest(key=key),patch('rebuild_native_ball_contact_owners.verify_output',return_value=result),self.assertRaises(ValueError):validate_native_ball_contact_owners('run')

if __name__=='__main__':unittest.main()
