import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from match_network_named_lower_approaches import MODE
from pipeline import validate_network_named_lower_approaches

def fixture():
    rows=[]
    for i,system in enumerate(('supply','return')):
        rows.append(dict(mapping_id='M'+str(i),kind='network_anchored_named_lower_floor_approach',floor=1,system=system,plan_edges=['P'+str(i)],iso_edges=['I'+str(i)],
            iso_segment_scopes=[dict(edge_id='I'+str(i),path_index=0,segment_indices=[0],scope_paths=[[[0,0],[10,0]]],whole_local_edge=False)],
            retained_vertical_scope=dict(scope_points=[[10,0],[10,100]],floor_pair=[1,2],segment_index=1),graphic_circle_radius_added_to_length=False,
            axis_bend_is_attribute_limit_not_new_physical_node=True,whole_axis_DN_assigned=False,whole_axis_length_assigned=False,physical_port_verified=False,
            human_accepted=False,physical_length_mm=None,independent_adjoining_main_mapping_id='MAIN'+str(i)))
    return dict(mode=MODE,status='source_checked_network_named_lower_approaches_attributes_pending',floor=1,records=rows,local_graphs_mutated=False,physical_values_fused=False,
        physical_ports_verified=False,human_accepted=False,hil_ready=False,DN_values_assigned=0,physical_lengths_assigned=0,graph_sha256={},source_sha256={})

class Tests(unittest.TestCase):
    def test_native_source_replay_and_two_service_prefixes_still_pending_values_and_HIL(self):
        with patch('match_network_named_lower_approaches.verify_output',return_value=fixture()) as replay:result=validate_network_named_lower_approaches('RUN')
        replay.assert_called_once_with('RUN');self.assertEqual(result['mapped_approaches'],2);self.assertEqual(result['status'],'pending');self.assertEqual(result['physical_values_assigned'],0);self.assertFalse(result['hil_ready'])
    def test_actual_native_failure_propagates(self):
        with patch('match_network_named_lower_approaches.verify_output',side_effect=ValueError('column changed')),self.assertRaisesRegex(ValueError,'column changed'):validate_network_named_lower_approaches('RUN')
    def test_duplicate_wrong_vertical_boundary_and_forged_whole_values_block(self):
        for case in ('duplicate','vertical','floor','length','whole','circle','HIL','mode'):
            data=fixture();row=data['records'][0]
            if case=='duplicate':data['records'][1]['plan_edges']=row['plan_edges']
            elif case=='vertical':row['iso_segment_scopes'][0]['scope_paths'][0][-1]=[11,0]
            elif case=='floor':row['retained_vertical_scope']['floor_pair']=[2,3]
            elif case=='length':row['physical_length_mm']=0
            elif case=='whole':row['iso_segment_scopes'][0]['whole_local_edge']=True
            elif case=='circle':row['graphic_circle_radius_added_to_length']=True
            elif case=='HIL':data['hil_ready']=True
            else:data['mode']='old'
            with self.subTest(case=case),patch('match_network_named_lower_approaches.verify_output',return_value=data),self.assertRaises(ValueError):validate_network_named_lower_approaches('RUN')
if __name__=='__main__':unittest.main()
