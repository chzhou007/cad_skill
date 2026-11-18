import unittest
from pathlib import Path
from unittest.mock import patch
from rebuild_axis_unbranched_vertical_DN import MODE
from pipeline import validate_axis_unbranched_vertical_DN,reconstruct_axis_unbranched_vertical_DN
class Tests(unittest.TestCase):
    def test_original_owners_replayed_and_only_vertical_scopes_published(self):
        proof=dict(mode=MODE,original_native_annotations_independently_replayed=True,original_direction_routing_independently_replayed=True,original_annotation_records_preserved=True,original_axis_graphs_unchanged=True,all_vertical_values_from11=True,
            horizontal_plan_attributes_changed=False,crossed_physical_Ts=0,whole_edge_DN_assigned=0,physical_lengths_assigned=0,human_accepted=False,counts={})
        with patch('rebuild_axis_unbranched_vertical_DN.verify_output',return_value=proof):r=validate_axis_unbranched_vertical_DN(Path('native'))
        self.assertEqual(r['status'],'pending');self.assertEqual(r['native_axis_unbranched_vertical_DN'],'passed');self.assertFalse(r['human_accepted'])
        for key,value in [('horizontal_plan_attributes_changed',True),('crossed_physical_Ts',1),('whole_edge_DN_assigned',1),('physical_lengths_assigned',1)]:
            changed=dict(proof,**{key:value})
            with self.subTest(key=key),patch('rebuild_axis_unbranched_vertical_DN.verify_output',return_value=changed),self.assertRaises(ValueError):validate_axis_unbranched_vertical_DN(Path('native'))
    def test_formal_reconstruction_calls_versioned_native_owner_and_validation(self):
        with patch('rebuild_axis_unbranched_vertical_DN.produce')as produce,patch('pipeline.validate_axis_unbranched_vertical_DN',return_value={})as validate:
            reconstruct_axis_unbranched_vertical_DN(Path('manifest'),Path('new'))
        produce.assert_called_once_with(Path('manifest'),Path('new'));validate.assert_called_once_with(Path('new'))
if __name__=='__main__':unittest.main()
