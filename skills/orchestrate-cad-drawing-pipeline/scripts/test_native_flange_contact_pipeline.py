import unittest
from unittest.mock import patch
from pipeline import validate_native_flange_contact_ownership,reconstruct_native_flange_contact_ownership
from native_flange_contact_ownership import MODE

class Tests(unittest.TestCase):
    def data(self):
        return dict(mode=MODE,original_native_owner_replayed=True,flange_population_complete=True,prior_components_unchanged=True,source_graph_unchanged=True,source_symbol_geometry_unchanged=True,published_graph_changed=False,component_aware_mapping_requalified=False,viewer_index_adopted=False,human_accepted=False,unknown_physical_parameters_filled=0,counts=dict(prior_components=1),components=[dict(id='OLD'),dict(id='NEW')],added_components=[dict(id='NEW')])
    def test_source_gate_does_not_claim_viewer_or_HIL(self):
        with patch('rebuild_native_flange_contact_ownership.verify_output',return_value=self.data()):self.assertEqual(validate_native_flange_contact_ownership('run')['status'],'pending')
        with patch('rebuild_native_flange_contact_ownership.produce')as owner,patch('pipeline.validate_native_flange_contact_ownership',return_value={}):reconstruct_native_flange_contact_ownership('manifest','run')
        owner.assert_called_once_with('manifest','run')
    def test_missing_native_replay_source_mutation_or_filled_parameters_are_blocked(self):
        for key,value in [('original_native_owner_replayed',False),('source_graph_unchanged',False),('unknown_physical_parameters_filled',1),('viewer_index_adopted',True)]:
            result=self.data();result[key]=value
            with self.subTest(key=key),patch('rebuild_native_flange_contact_ownership.verify_output',return_value=result),self.assertRaises(ValueError):validate_native_flange_contact_ownership('run')

if __name__=='__main__':unittest.main()
