import unittest
from unittest.mock import patch
from pipeline import validate_riser_header_interval_application,reconstruct_riser_header_interval_application,validate_riser_header_attribute_viewer
from riser_header_interval_application import MODE
class Tests(unittest.TestCase):
    def test_adoption_keeps_riser_length_and_vertical_rules_separate(self):
        r=dict(mode=MODE,independent_gate_ancestry_replayed=True,member_and_origin_native_sources_replayed=True,old_graphs_unchanged=True,all_horizontal_values_from_plan=True,vertical_values_assigned=0,installed_lengths_assigned=0,lower_terminal_identities_assigned=0,human_accepted=False,member_records=[dict(member_kind='riser',complete_horizontal_centerline_mm=None)],counts={},pending=[])
        with patch('riser_header_interval_application.verify_output',return_value=r):self.assertEqual(validate_riser_header_interval_application('native')['native_riser_header_interval_application'],'passed')
        for k,v in [('independent_gate_ancestry_replayed',False),('vertical_values_assigned',1),('lower_terminal_identities_assigned',1),('human_accepted',True),('member_records',[dict(member_kind='riser',complete_horizontal_centerline_mm=225)])]:
            with self.subTest(key=k),patch('riser_header_interval_application.verify_output',return_value=dict(r,**{k:v})),self.assertRaises(ValueError):validate_riser_header_interval_application('native')
    def test_reconstruction_and_viewer_use_native_owners(self):
        with patch('riser_header_interval_application.produce')as p,patch('pipeline.validate_riser_header_interval_application',return_value={}):reconstruct_riser_header_interval_application('manifest','new')
        p.assert_called_once_with('manifest','new')
        with patch('refresh_riser_header_attributes.verify',return_value={'artifact_replay':'passed'})as p:self.assertEqual(validate_riser_header_attribute_viewer('viewer')['artifact_replay'],'passed')
        p.assert_called_once_with('viewer')
if __name__=='__main__':unittest.main()
