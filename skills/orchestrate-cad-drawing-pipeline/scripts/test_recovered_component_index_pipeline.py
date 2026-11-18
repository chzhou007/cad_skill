import unittest
from unittest.mock import patch
from pipeline import validate_recovered_component_index,validate_recovered_component_provider_inventory,reconstruct_recovered_component_index,reconstruct_recovered_component_provider_inventory
class Tests(unittest.TestCase):
    def test_native_index_success_preserves_pending_publication_and_HIL(self):
        r=dict(complete_parent_and_native_inventory_replayed=True,pipe_graph_restoration_exact=True,new_correspondences_assigned=0,physical_parameters_assigned=0,human_accepted=False,component_rows_added=9)
        with patch('rebuild_recovered_component_index.verify_output',return_value=r):self.assertEqual(validate_recovered_component_index('index')['status'],'pending')
        r['physical_parameters_assigned']=1
        with patch('rebuild_recovered_component_index.verify_output',return_value=r),self.assertRaises(ValueError):validate_recovered_component_index('index')
        with patch('rebuild_recovered_component_index.produce')as p,patch('pipeline.validate_recovered_component_index',return_value={}):reconstruct_recovered_component_index('manifest','new')
        p.assert_called_once_with('manifest','new')
    def test_complete_inventory_requires_all_provider_and_namespace_guards(self):
        from recovered_component_provider_inventory import MODE
        r=dict(mode=MODE,current_viewer_and_complete_original_inventory_replayed=True,all_prior_provider_observations_exact=True,all_prior_member_and_ordinary_junction_namespaces_exact=True,all_prior_attribute_frontiers_exact=True,current_rendered_component_profiles_requalified=True,new_correspondences_assigned=0,DN_or_length_values_assigned=0,human_accepted=False,counts={})
        with patch('recovered_component_provider_inventory.verify_output',return_value=r):self.assertEqual(validate_recovered_component_provider_inventory('new')['status'],'pending')
        r['all_prior_attribute_frontiers_exact']=False
        with patch('recovered_component_provider_inventory.verify_output',return_value=r),self.assertRaises(ValueError):validate_recovered_component_provider_inventory('new')
        with patch('recovered_component_provider_inventory.produce')as p,patch('pipeline.validate_recovered_component_provider_inventory',return_value={}):reconstruct_recovered_component_provider_inventory('manifest','new')
        p.assert_called_once_with('manifest','new')
if __name__=='__main__':unittest.main()
