import unittest
from pathlib import Path
from unittest.mock import patch
from bridge_aware_provider_inventory import MODE
from pipeline import validate_alias_member_bridge_viewer,validate_bridge_aware_provider_inventory,reconstruct_bridge_aware_provider_inventory
class Tests(unittest.TestCase):
    def test_viewer_uses_new_native_owner(self):
        with patch('refresh_alias_member_bridge_attributes.verify',return_value={'artifact_replay':'passed'})as verify:
            self.assertEqual(validate_alias_member_bridge_viewer(Path('bundle'))['artifact_replay'],'passed')
        verify.assert_called_once_with(Path('bundle'))
    def test_complete_inventory_is_not_value_generation_or_HIL(self):
        proof=dict(mode=MODE,current_bridge_viewer_native_replayed=True,complete_original_alias_inventory_replayed=True,ordinary_junction_mappings_unchanged=True,
            vertical_segments_routed_to_plan=0,DN_or_length_values_assigned=0,human_accepted=False,counts={})
        with patch('bridge_aware_provider_inventory.verify_output',return_value=proof):r=validate_bridge_aware_provider_inventory(Path('inventory'))
        self.assertEqual(r['status'],'pending');self.assertEqual(r['native_bridge_aware_provider_inventory'],'passed')
        proof['vertical_segments_routed_to_plan']=1
        with patch('bridge_aware_provider_inventory.verify_output',return_value=proof),self.assertRaises(ValueError):validate_bridge_aware_provider_inventory(Path('inventory'))
    def test_formal_reconstruction_replays_original_complete_inventory(self):
        with patch('bridge_aware_provider_inventory.produce')as produce,patch('pipeline.validate_bridge_aware_provider_inventory',return_value={})as verify:
            reconstruct_bridge_aware_provider_inventory(Path('manifest'),Path('output'))
        produce.assert_called_once_with(Path('manifest'),Path('output'));verify.assert_called_once_with(Path('output'))
if __name__=='__main__':unittest.main()
