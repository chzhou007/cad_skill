import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_inline_joint_path_coverage
def fixture():
    joint=dict(source_handle='J',edge_id='E',physical_length_mm=None,physical_port_verified=False)
    return dict(mode='native_inline_joint_path_coverage_v1',graph_mutated=False,human_accepted=False,hil_ready=False,new_connections_added=0,physical_lengths_assigned=0,
        source_sha256='S',graph_sha256='G',records=[dict(edge_id='E',status='native_pipe_and_inline_joint_chain_source_checked',joint_spans_excluded_from_pipe_length=True,
        physical_length_mm=None,physical_ports_verified=False,human_accepted=False,joints=[joint],native_path_proofs=[{}],private_ordered_pieces=[{}])])
class Tests(unittest.TestCase):
    def test_dispatch_independently_replays_and_keeps_mapping_length_and_HIL_pending(self):
        with patch('native_inline_joint_path_coverage.verify_output',return_value=fixture()) as replay:
            result=validate_inline_joint_path_coverage('RUN')
        replay.assert_called_once_with('RUN');self.assertEqual(result['source_replay'],'passed');self.assertEqual(result['status'],'pending')
        self.assertEqual(result['source_checked_inline_instances'],1);self.assertFalse(result['hil_ready'])
    def test_native_failure_propagates(self):
        with patch('native_inline_joint_path_coverage.verify_output',side_effect=ValueError('source marker moved')),self.assertRaisesRegex(ValueError,'source marker moved'):
            validate_inline_joint_path_coverage('RUN')
    def test_forged_lengths_ports_duplicate_or_mutation_are_rejected(self):
        for case in ('length','ports','duplicate','mutated','no_proof','wrong_mode','joint_length'):
            data=fixture();row=data['records'][0]
            if case=='length':row['physical_length_mm']=0
            elif case=='ports':row['physical_ports_verified']=True
            elif case=='duplicate':data['records'].append(copy.deepcopy(row))
            elif case=='mutated':data['graph_mutated']=True
            elif case=='no_proof':row['native_path_proofs']=[]
            elif case=='joint_length':row['joints'][0]['physical_length_mm']=300
            else:data['mode']='old'
            with self.subTest(case=case),patch('native_inline_joint_path_coverage.verify_output',return_value=data),self.assertRaises(ValueError):validate_inline_joint_path_coverage('RUN')
if __name__=='__main__':unittest.main()
