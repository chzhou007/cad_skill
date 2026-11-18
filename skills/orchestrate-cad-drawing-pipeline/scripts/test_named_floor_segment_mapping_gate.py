import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_named_floor_segments


class Tests(unittest.TestCase):
    def data(self):
        return dict(status='source_checked_named_upper_floor_segment_correspondence_attributes_pending',floor=3,
            source_sha256={'plan':'P','iso':'I'},graph_sha256={'plan':'PG','iso':'IG'},local_graphs_mutated=False,
            physical_values_fused=False,physical_ports_verified=False,human_accepted=False,DN_values_assigned=0,physical_lengths_assigned=0,
            floor_interface_correspondences=[dict(system=s) for s in ('supply','return')],junction_correspondences=[{}, {}, {}, {}],
            records=[dict(kind='named_riser_floor_segment_'+kind,physical_port_verified=False,physical_length_mm=None,
                whole_axis_DN_assigned=False,whole_axis_length_assigned=False,axis_bend_is_attribute_limit_not_new_physical_node=True,
                iso_segment_scopes=[dict(segment_indices=[1],whole_local_edge=kind=='network_link')]) for s in ('supply','return') for kind in ('approach','network_link')])
    def test_fresh_native_segment_replay_does_not_select_whole_mixed_edge_values(self):
        with patch('match_named_riser_floor_segments.verify_output',return_value=self.data()) as verify:result=validate_named_floor_segments('RUN')
        verify.assert_called_once_with('RUN');self.assertEqual(result['segment_correspondence_records'],4)
        self.assertEqual(result['floor_interface_correspondences'],2);self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_stale_source_whole_edge_scope_and_false_physical_claims_block(self):
        for case in ('mixed_whole','DN','length','node','HIL','system','unpaired'):
            data=self.data();row=data['records'][0]
            if case=='mixed_whole':row['iso_segment_scopes'][0]['whole_local_edge']=True
            elif case=='DN':row['whole_axis_DN_assigned']=True
            elif case=='length':row['physical_length_mm']=5000
            elif case=='node':row['axis_bend_is_attribute_limit_not_new_physical_node']=False
            elif case=='HIL':data['human_accepted']=True
            elif case=='system':data['floor_interface_correspondences'][0]['system']='return'
            else:data['records'].pop()
            with self.subTest(case=case),patch('match_named_riser_floor_segments.verify_output',return_value=data),self.assertRaises(ValueError):validate_named_floor_segments('RUN')
        with patch('match_named_riser_floor_segments.verify_output',side_effect=ValueError('source changed')),self.assertRaises(ValueError):validate_named_floor_segments('RUN')


if __name__=='__main__':unittest.main()
