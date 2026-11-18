import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_inherited_wave_continuity
from inherited_wave_pair_continuity import MODE


class Tests(unittest.TestCase):
    def fixture(self,folder):
        stage=dict(mode=MODE,records=[{}],edge_id_mapping={'B':'A'},retired_node_snapshots=[{},{}],
            dependent_mapping_attributes_and_HIL_invalidated=True,unpaired_continuations_inferred=False,physical_lengths_assigned=0,human_accepted=False)
        graph=dict(nodes=[{},{}],edges=[{}],metadata=dict(hil_ready=False),sourceInheritedWavePairContinuity=stage)
        receipt=dict(mode=MODE,proof=dict(pairs=1,nodes_before=4,nodes_after=2,edges_before=2,edges_after=1,components=3),inputs=dict(source=dict(sha256='S')),output_graph_sha256='G')
        (folder/'graph_with_edges.json').write_text(json.dumps(graph),'utf8')
        return graph,receipt

    def test_formal_command_replays_root_and_retains_dependency_and_HIL_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);_,receipt=self.fixture(folder)
            with patch('inherited_wave_pair_continuity.verify_output',return_value=receipt) as verify:result=validate_inherited_wave_continuity(folder)
            verify.assert_called_once_with(folder);self.assertEqual(result['source_replay'],'passed');self.assertEqual(result['wave_pairs'],1)
            self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready']);self.assertTrue(result['dependent_mapping_attributes_and_HIL_invalidated'])

    def test_native_failures_count_loss_or_fabricated_lengths_and_acceptance_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            with patch('inherited_wave_pair_continuity.verify_output',side_effect=ValueError('source control changed')),self.assertRaisesRegex(ValueError,'source control changed'):validate_inherited_wave_continuity(folder)
            for case in ('nodes','edges','retired','length','HIL','unpaired','dependency'):
                graph,receipt=self.fixture(folder);stage=graph['sourceInheritedWavePairContinuity']
                if case=='nodes':receipt['proof']['nodes_after']=3
                elif case=='edges':receipt['proof']['edges_after']=2
                elif case=='retired':stage['retired_node_snapshots'].pop()
                elif case=='length':stage['physical_lengths_assigned']=1
                elif case=='HIL':stage['human_accepted']=True
                elif case=='unpaired':stage['unpaired_continuations_inferred']=True
                else:stage['dependent_mapping_attributes_and_HIL_invalidated']=False
                (folder/'graph_with_edges.json').write_text(json.dumps(graph),'utf8')
                with self.subTest(case=case),patch('inherited_wave_pair_continuity.verify_output',return_value=receipt),self.assertRaises(ValueError):validate_inherited_wave_continuity(folder)


if __name__=='__main__':unittest.main()
