import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_axis_riser_DN


class Tests(unittest.TestCase):
    def data(self):return dict(status='source_checked_axis_through_riser_segment_DN_human_pending',source_sha256='S',graph_sha256='G',
        local_graph_mutated=False,physical_values_fused=False,floor_interface_correspondence_confirmed=False,human_accepted=False,installed_lengths_assigned=0,whole_edge_DN_assigned=0,
        records=[dict(nominal_mm=450,scope='native_axis_through_riser_drawn_vertical_segment_only',whole_local_edge_DN_assigned=False,physical_length_mm=None)])
    def test_fresh_native_scope_replay_is_pending_whole_edge_and_mapping(self):
        with patch('native_axis_riser_DN_scopes.verify_output',return_value=self.data()) as verify:q=validate_axis_riser_DN('RUN')
        verify.assert_called_once_with('RUN');self.assertEqual(q['known_DN_scopes'],1);self.assertEqual(q['status'],'pending');self.assertFalse(q['hil_ready'])
    def test_false_mapping_whole_edge_physical_length_or_acceptance_claims_block(self):
        for key in ['local_graph_mutated','physical_values_fused','floor_interface_correspondence_confirmed','human_accepted','installed_lengths_assigned','whole_edge_DN_assigned']:
            data=self.data();data[key]=True
            with self.subTest(key=key),patch('native_axis_riser_DN_scopes.verify_output',return_value=data),self.assertRaises(ValueError):validate_axis_riser_DN('RUN')
        for key,value in [('whole_local_edge_DN_assigned',True),('physical_length_mm',0),('scope','whole_edge')]:
            data=self.data();data['records'][0][key]=value
            with self.subTest(key=key),patch('native_axis_riser_DN_scopes.verify_output',return_value=data),self.assertRaises(ValueError):validate_axis_riser_DN('RUN')
        with patch('native_axis_riser_DN_scopes.verify_output',side_effect=ValueError('native source changed')),self.assertRaises(ValueError):validate_axis_riser_DN('RUN')


if __name__=='__main__':unittest.main()
