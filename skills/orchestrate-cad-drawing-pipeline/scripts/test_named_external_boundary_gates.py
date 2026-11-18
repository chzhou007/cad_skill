import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_native_external_port_destinations,validate_named_external_boundary_paths
from test_native_external_port_destination import fixture as port_fixture
from native_external_port_destination import collect
from test_match_named_external_boundary_paths import fixture as mapping_fixture
from match_named_external_boundary_paths import match


class Tests(unittest.TestCase):
    def test_native_port_owner_is_replayed_without_claiming_hydraulic_connection(self):
        data=collect(*port_fixture())
        with patch('native_external_port_destination.verify_output',return_value=data) as replay:result=validate_native_external_port_destinations('RUN')
        replay.assert_called_once_with('RUN');self.assertEqual(result['separate_named_ports'],4);self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
        data['records'][0]['physical_length_mm']=0
        with patch('native_external_port_destination.verify_output',return_value=data),self.assertRaises(ValueError):validate_native_external_port_destinations('RUN')
    def test_external_mapper_replayed_and_partial_acceptance_is_not_HIL(self):
        data=match(*mapping_fixture())
        with patch('match_named_external_boundary_paths.verify_output',return_value=data) as replay:result=validate_named_external_boundary_paths('RUN')
        replay.assert_called_once_with('RUN');self.assertEqual(result['external_paths'],4);self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
        for mutate in (lambda d:d['records'][0].update(whole_edge_DN_assigned=True),lambda d:d['records'][0].update(external_ports_connected_to_each_other=True),lambda d:d['records'].append(copy.deepcopy(d['records'][0]))):
            changed=copy.deepcopy(data);mutate(changed)
            with patch('match_named_external_boundary_paths.verify_output',return_value=changed),self.assertRaises(ValueError):validate_named_external_boundary_paths('RUN')
    def test_native_failure_propagates(self):
        with patch('match_named_external_boundary_paths.verify_output',side_effect=ValueError('native source changed')),self.assertRaisesRegex(ValueError,'native source changed'):validate_named_external_boundary_paths('RUN')

if __name__=='__main__':unittest.main()
