import unittest
from unittest.mock import patch
from pipeline import validate_riser_header_provider_inventory,reconstruct_riser_header_provider_inventory
from riser_header_provider_inventory import MODE
class Tests(unittest.TestCase):
    def test_provider_inventory_does_not_reassign_values_or_flatten_members(self):
        r=dict(mode=MODE,current_viewer_and_original_provider_inventory_replayed=True,member_namespaces_preserved=True,old_member_observations_prefix_unchanged=True,new_correspondences_assigned=0,DN_or_length_values_assigned=0,human_accepted=False,counts={})
        with patch('riser_header_provider_inventory.verify_output',return_value=r):self.assertEqual(validate_riser_header_provider_inventory('inventory')['riser_header_provider_inventory'],'passed')
        for k,v in [('member_namespaces_preserved',False),('old_member_observations_prefix_unchanged',False),('new_correspondences_assigned',1),('human_accepted',True)]:
            with self.subTest(key=k),patch('riser_header_provider_inventory.verify_output',return_value=dict(r,**{k:v})),self.assertRaises(ValueError):validate_riser_header_provider_inventory('inventory')
        with patch('riser_header_provider_inventory.produce')as p,patch('pipeline.validate_riser_header_provider_inventory',return_value={}):reconstruct_riser_header_provider_inventory('manifest','new')
        p.assert_called_once_with('manifest','new')
if __name__=='__main__':unittest.main()
