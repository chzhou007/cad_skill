import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from native_external_pipe_destination import MODE
from pipeline import validate_native_external_destinations

def fixture():
    rows=[dict(node_id='U'+str(i),identifier='NAME'+str(i),source_line_handle='LINE'+str(i),system=system,destination='室外冷冻站',destination_status='source_declared_external_destination',
        physical_length_mm=None,whole_edge_DN_verified=False,physical_external_connection_verified=False,physical_port_verified=False,human_accepted=False) for i,system in enumerate(('supply','return'))]
    return dict(mode=MODE,status='source_declared_destinations_not_hydraulic_connection',records=rows,destination='室外冷冻站',source_sha256='S',graph_sha256='G',
        common_marker_creates_pipe_connection=False,graph_mutated=False,human_accepted=False,hil_ready=False,nodes_merged=0,new_connections_added=0,physical_values_assigned=0)
class Tests(unittest.TestCase):
    def test_known_destination_is_replayed_without_promoting_ports_or_connections(self):
        with patch('native_external_pipe_destination.verify_output',return_value=fixture()) as replay:result=validate_native_external_destinations('RUN')
        replay.assert_called_once_with('RUN');self.assertEqual(result['destination'],'室外冷冻站');self.assertEqual(result['status'],'pending');self.assertEqual(result['new_connections_added'],0);self.assertFalse(result['hil_ready'])
    def test_native_failure_propagates(self):
        with patch('native_external_pipe_destination.verify_output',side_effect=ValueError('leader moved')),self.assertRaisesRegex(ValueError,'leader moved'):validate_native_external_destinations('RUN')
    def test_shared_marker_cannot_merge_systems_or_fill_unknowns(self):
        for case in ('merge','connection','port','DN','length','duplicate','HIL'):
            data=fixture()
            if case=='merge':data['nodes_merged']=1
            elif case=='connection':data['common_marker_creates_pipe_connection']=True
            elif case=='port':data['records'][0]['physical_port_verified']=True
            elif case=='DN':data['records'][0]['whole_edge_DN_verified']=True
            elif case=='length':data['records'][0]['physical_length_mm']=0
            elif case=='duplicate':data['records'][1]['node_id']=data['records'][0]['node_id']
            else:data['hil_ready']=True
            with self.subTest(case=case),patch('native_external_pipe_destination.verify_output',return_value=data),self.assertRaises(ValueError):validate_native_external_destinations('RUN')
if __name__=='__main__':unittest.main()
