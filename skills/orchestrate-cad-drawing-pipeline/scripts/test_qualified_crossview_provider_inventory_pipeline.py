import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from qualified_crossview_provider_inventory import MODE
from pipeline import validate_qualified_crossview_provider_inventory, reconstruct_qualified_crossview_provider_inventory

class Tests(unittest.TestCase):
    def proof(self):
        return dict(mode=MODE,current_provider_artifact_replayed=True,ordered_owner_native_replayed=True,
            original_CAD_direction_replayed=True,local_graphs_mutated=False,new_correspondences_assigned=0,
            DN_or_length_values_assigned=0,vertical_segments_routed_to_plan=0,human_accepted=False,counts={})
    def test_native_inventory_does_not_complete_mapping_or_attributes(self):
        with patch('qualified_crossview_provider_inventory.verify_output',return_value=self.proof()):
            r=validate_qualified_crossview_provider_inventory(Path('native'))
        self.assertEqual(r['qualified_provider_inventory'],'passed');self.assertEqual(r['status'],'pending')
    def test_bypassed_replay_and_value_or_vertical_promotion_fail(self):
        for key,value in [('current_provider_artifact_replayed',False),('ordered_owner_native_replayed',False),
            ('original_CAD_direction_replayed',False),('new_correspondences_assigned',1),
            ('DN_or_length_values_assigned',1),('vertical_segments_routed_to_plan',1),('human_accepted',True)]:
            p=self.proof();p[key]=value
            with self.subTest(key=key),patch('qualified_crossview_provider_inventory.verify_output',return_value=p):
                with self.assertRaises(ValueError):validate_qualified_crossview_provider_inventory(Path('native'))
    def test_complete_entry_produces_then_independently_validates(self):
        with patch('qualified_crossview_provider_inventory.produce')as p,patch('pipeline.validate_qualified_crossview_provider_inventory',return_value={'status':'pending'})as v:
            reconstruct_qualified_crossview_provider_inventory(Path('manifest'),Path('new'))
        p.assert_called_once_with(Path('manifest'),Path('new'));v.assert_called_once_with(Path('new'))

if __name__=='__main__':unittest.main()
