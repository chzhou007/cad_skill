import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_touching_plan_chunks


class Tests(unittest.TestCase):
    def data(self):
        return dict(status='native_touching_chunks_read_only_geometry_replayed_not_connectivity_acceptance',source_sha256='S',graph_sha256='G',
            local_graph_mutated=False,human_accepted=False,physical_connections_added=0,installed_lengths_assigned=0,
            normalizations=[dict(edge_id='P',join_points=[[10,0]],added_span_units=0,physical_nodes_added=0,physical_edges_added=0)],
            measured_scopes=[dict(installed_whole_edge_length_mm=None,human_accepted=False,horizontal_projection=dict(value_mm=300,installed_whole_edge_length_mm=None))])
    def test_independent_native_replay_stays_partial_and_does_not_add_connectivity(self):
        with patch('native_touching_plan_path_chunks.verify_output',return_value=self.data()) as verify:
            result=validate_touching_plan_chunks('RUN')
        verify.assert_called_once_with('RUN');self.assertEqual(result['source_replay'],'passed');self.assertEqual(result['exact_join_edges'],['P'])
        self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_false_spans_connections_or_installed_lengths_block(self):
        for case in ('span','node','edge','connection','mutation','HIL','length','nan'):
            data=self.data()
            if case=='span':data['normalizations'][0]['added_span_units']=1
            elif case=='node':data['normalizations'][0]['physical_nodes_added']=1
            elif case=='edge':data['normalizations'][0]['physical_edges_added']=1
            elif case=='connection':data['physical_connections_added']=1
            elif case=='mutation':data['local_graph_mutated']=True
            elif case=='HIL':data['human_accepted']=True
            elif case=='length':data['measured_scopes'][0]['installed_whole_edge_length_mm']=300
            else:data['measured_scopes'][0]['horizontal_projection']['value_mm']=float('nan')
            with self.subTest(case=case),patch('native_touching_plan_path_chunks.verify_output',return_value=data),self.assertRaises(ValueError):validate_touching_plan_chunks('RUN')
        with patch('native_touching_plan_path_chunks.verify_output',side_effect=ValueError('source changed')),self.assertRaises(ValueError):validate_touching_plan_chunks('RUN')


if __name__=='__main__':unittest.main()
