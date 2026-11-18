import unittest
from pathlib import Path
from unittest.mock import patch
from pipeline import validate_alias_member_interface_viewer,validate_alias_aware_provider_inventory,reconstruct_alias_aware_provider_inventory
from alias_aware_provider_inventory import MODE

class Tests(unittest.TestCase):
    def test_viewer_and_inventory_dispatch_remain_native_and_not_HIL(self):
        with patch('refresh_alias_member_interface_attributes.verify',return_value={'artifact_replay':'passed'})as verify:self.assertEqual(validate_alias_member_interface_viewer(Path('viewer'))['artifact_replay'],'passed')
        verify.assert_called_once_with(Path('viewer'))
        proof=dict(mode=MODE,current_alias_viewer_native_replayed=True,ordinary_junction_mappings_unchanged=True,vertical_segments_routed_to_plan=0,DN_or_length_values_assigned=0,human_accepted=False,counts={})
        with patch('alias_aware_provider_inventory.verify_output',return_value=proof):r=validate_alias_aware_provider_inventory(Path('inventory'))
        self.assertEqual(r['status'],'pending');self.assertFalse(r['human_accepted']);proof['ordinary_junction_mappings_unchanged']=False
        with patch('alias_aware_provider_inventory.verify_output',return_value=proof),self.assertRaises(ValueError):validate_alias_aware_provider_inventory(Path('inventory'))
    def test_reconstruction_replays_declared_inventory_owner(self):
        with patch('alias_aware_provider_inventory.produce')as produce,patch('pipeline.validate_alias_aware_provider_inventory',return_value={})as verify:reconstruct_alias_aware_provider_inventory(Path('manifest'),Path('new'))
        produce.assert_called_once_with(Path('manifest'),Path('new'));verify.assert_called_once_with(Path('new'))
if __name__=='__main__':unittest.main()
