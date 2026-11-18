import unittest
from unittest.mock import patch
from pipeline import validate_native_contact_application,reconstruct_native_contact_application,validate_contact_owner_provider_inventory
from rebuild_native_contact_application import MODE

class Tests(unittest.TestCase):
    def data(self):
        return dict(mode=MODE,complete_current_parent_replayed=True,native_owner_inventory_replayed=True,all_affected_old_scopes_requalified=True,pipe_graph_restoration_exact=True,source_graphs_mutated=False,DN_used_for_mapping=False,physical_pipe_count_inferred=False,related_confirmation_inherited=False,human_accepted=False,unknown_physical_parameters_filled=0,counts={})
    def test_native_requalification_still_leaves_UI_and_HIL_pending(self):
        with patch('rebuild_native_contact_application.verify_output',return_value=self.data()):self.assertEqual(validate_native_contact_application('run')['status'],'pending')
        with patch('rebuild_native_contact_application.produce')as p,patch('pipeline.validate_native_contact_application',return_value={}):reconstruct_native_contact_application('manifest','run')
        p.assert_called_once_with('manifest','run')
    def test_missing_old_scope_replay_changed_graph_or_filled_parameters_blocks(self):
        for key,value in [('all_affected_old_scopes_requalified',False),('pipe_graph_restoration_exact',False),('source_graphs_mutated',True),('unknown_physical_parameters_filled',1)]:
            result=self.data();result[key]=value
            with self.subTest(key=key),patch('rebuild_native_contact_application.verify_output',return_value=result),self.assertRaises(ValueError):validate_native_contact_application('run')
    def test_complete_provider_must_preserve_prior_namespaces(self):
        from contact_owner_provider_inventory import MODE as PM
        result=dict(mode=PM,current_viewer_and_complete_original_provider_replayed=True,all_prior_providers_and_member_namespaces_preserved=True,all_affected_old_scopes_requalified=True,human_accepted=False,counts={})
        with patch('contact_owner_provider_inventory.verify_output',return_value=result):self.assertEqual(validate_contact_owner_provider_inventory('run')['status'],'pending')
        result['all_prior_providers_and_member_namespaces_preserved']=False
        with patch('contact_owner_provider_inventory.verify_output',return_value=result),self.assertRaises(ValueError):validate_contact_owner_provider_inventory('run')

if __name__=='__main__':unittest.main()
