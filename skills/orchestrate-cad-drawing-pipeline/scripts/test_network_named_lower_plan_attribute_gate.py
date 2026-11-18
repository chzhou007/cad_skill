import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from network_named_lower_plan_attributes import MODE
from pipeline import validate_network_named_lower_plan_attributes

def fixture():
    rows=[]
    for i,system in enumerate(('supply','return')):
        rows.append(dict(mapping_id='M'+str(i),system=system,plan_edges=['P'+str(i)],iso_edges=['I'+str(i)],
            diameter=dict(edge_id='P'+str(i),system=system,nominal_mm=200,status='T_inherited_plan_DN',lineage=[dict(source='native')],scope='native_plan_drawn_pipe_paths_only'),
            horizontal_projection=dict(value_mm=1000,pieces=[dict(length_mm=1000)],installed_whole_edge_length_mm=None,unshown_connection_length_mm=None),
            whole_axis_DN_selected=False,whole_axis_DN_assigned=False,physical_port_verified=False,plan_glyph_radius_added_to_length=False,human_accepted=False,
            whole_axis_physical_length_mm=None,installed_whole_edge_length_mm=None))
    return dict(mode=MODE,status='source_checked_network_named_lower_plan_DN_XY_not_fused',records=rows,local_graphs_mutated=False,physical_values_fused=False,physical_ports_verified=False,
        human_accepted=False,hil_ready=False,installed_lengths_assigned=0,known_DN_records=2,unresolved_DN_records=0,source_sha256={},graph_sha256={})
class Tests(unittest.TestCase):
    def test_actual_owner_replayed_and_two_prefix_values_remain_unfused(self):
        with patch('network_named_lower_plan_attributes.verify_output',return_value=fixture()) as replay:result=validate_network_named_lower_plan_attributes('RUN')
        replay.assert_called_once_with('RUN');self.assertEqual(result['prefix_records'],2);self.assertEqual(result['known_DN_records'],2);self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_unknown_DN_remains_unknown_and_native_failure_propagates(self):
        data=fixture();data['records'][0]['diameter'].update(nominal_mm=None,status='conflict');data.update(known_DN_records=1,unresolved_DN_records=1)
        with patch('network_named_lower_plan_attributes.verify_output',return_value=data):self.assertEqual(validate_network_named_lower_plan_attributes('RUN')['unresolved_DN_records'],1)
        with patch('network_named_lower_plan_attributes.verify_output',side_effect=ValueError('source label moved')),self.assertRaisesRegex(ValueError,'source label moved'):validate_network_named_lower_plan_attributes('RUN')
    def test_zero_wrong_service_circle_radius_whole_length_and_summary_block(self):
        for case in ('zero_DN','zero_XY','service','circle','whole','summary','mutated'):
            data=fixture();row=data['records'][0]
            if case=='zero_DN':row['diameter']['nominal_mm']=0
            elif case=='zero_XY':row['horizontal_projection']['value_mm']=0
            elif case=='service':row['diameter']['system']='return'
            elif case=='circle':row['plan_glyph_radius_added_to_length']=True
            elif case=='whole':row['whole_axis_physical_length_mm']=1000
            elif case=='summary':data['known_DN_records']=1
            else:data['local_graphs_mutated']=True
            with self.subTest(case=case),patch('network_named_lower_plan_attributes.verify_output',return_value=data),self.assertRaises(ValueError):validate_network_named_lower_plan_attributes('RUN')
if __name__=='__main__':unittest.main()
