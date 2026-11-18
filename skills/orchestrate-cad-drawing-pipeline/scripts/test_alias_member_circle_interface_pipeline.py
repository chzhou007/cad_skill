import unittest
from pathlib import Path
from unittest.mock import patch
from alias_member_circle_interfaces import MODE
from pipeline import validate_alias_member_circle_interfaces,reconstruct_alias_member_circle_interfaces

class Tests(unittest.TestCase):
    def test_native_source_pass_never_promotes_plan_vertical_values_or_HIL(self):
        proof=dict(mode=MODE,confirmed_alias_member_cohort_native_replayed=True,original_local_graphs_mutated=False,ordinary_junction_mapping_extended=False,vertical_attributes_assigned_from_plan=0,installed_lengths_assigned=0,human_accepted=False,counts={},pending=[])
        with patch('rebuild_alias_member_circle_interfaces.verify_output',return_value=proof):r=validate_alias_member_circle_interfaces(Path('native'))
        self.assertEqual(r['status'],'pending');self.assertEqual(r['native_alias_member_interfaces'],'passed');self.assertFalse(r['human_accepted'])
        proof['vertical_attributes_assigned_from_plan']=1
        with patch('rebuild_alias_member_circle_interfaces.verify_output',return_value=proof),self.assertRaises(ValueError):validate_alias_member_circle_interfaces(Path('native'))
    def test_reconstruction_and_validation_use_versioned_source_owner(self):
        with patch('rebuild_alias_member_circle_interfaces.produce')as produce,patch('pipeline.validate_alias_member_circle_interfaces',return_value={})as validate:reconstruct_alias_member_circle_interfaces(Path('manifest'),Path('new'))
        produce.assert_called_once_with(Path('manifest'),Path('new'));validate.assert_called_once_with(Path('new'))
if __name__=='__main__':unittest.main()
