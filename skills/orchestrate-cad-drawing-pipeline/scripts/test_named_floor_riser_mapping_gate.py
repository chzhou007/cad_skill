import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_named_floor_riser_paths


class Tests(unittest.TestCase):
    def data(self):return dict(status='source_checked_named_floor_riser_paths_attributes_pending',source_sha256={'plan':'P','iso':'I'},graph_sha256={'plan':'PG','iso':'IG'},
        local_graphs_mutated=False,physical_values_fused=False,physical_ports_verified=False,human_accepted=False,DN_values_assigned=0,physical_lengths_assigned=0,
        records=[dict(system=s,physical_port_verified=False,physical_length_mm=None,plan_glyph_radius_added_to_length=False) for s in ['supply','return']])
    def test_fresh_path_replay_does_not_accept_ports_or_attributes(self):
        with patch('match_named_riser_floor_paths.verify_output',return_value=self.data()) as verify:result=validate_named_floor_riser_paths('RUN')
        verify.assert_called_once_with('RUN');self.assertEqual(result['named_floor_riser_path_correspondences'],2);self.assertFalse(result['physical_ports_verified']);self.assertFalse(result['hil_ready'])
    def test_source_changes_and_false_metrics_or_system_merge_block(self):
        for key in ['local_graphs_mutated','physical_values_fused','physical_ports_verified','human_accepted','DN_values_assigned','physical_lengths_assigned']:
            data=self.data();data[key]=True
            with self.subTest(key=key),patch('match_named_riser_floor_paths.verify_output',return_value=data),self.assertRaises(ValueError):validate_named_floor_riser_paths('RUN')
        data=self.data();data['records'][0]['system']='return'
        with patch('match_named_riser_floor_paths.verify_output',return_value=data),self.assertRaises(ValueError):validate_named_floor_riser_paths('RUN')
        with patch('match_named_riser_floor_paths.verify_output',side_effect=ValueError('source changed')),self.assertRaises(ValueError):validate_named_floor_riser_paths('RUN')


if __name__=='__main__':unittest.main()
