import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from source_comparison_gate import check,check_native_block_branch_graph


class NativeBlockBranchGateTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder)/'child';root.mkdir();parent=Path(folder)/'parent.json';parent.write_text('{}')
        graph=root/'graph_with_edges.json';graph.write_text(json.dumps(dict(sourceConfirmedGapJoints={'historical':True},sourceNativeBlockBranchReconstruction={'records':[{'edge_id':'E'}],'pending':[{'edge_id':'P','reason':'native joint ambiguous'}]})))
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        audit=dict(parent_graph=dict(path=str(parent),sha256=sha(parent)),output_graph_sha256=sha(graph))
        return root,parent,graph,audit,sha

    def test_changed_geometry_keeps_parent_blockers_and_explicit_recalculation(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,sha=self.fixture(folder);report={'graph_sha256':'original-screen'}
            with patch('reconstruct_native_block_branches.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=dict(errors=[],pending=['old DN ambiguity'])) as prior:
                result=check_native_block_branch_graph(root,report,sha(graph),graph)
            prior.assert_called_once_with(report,sha(parent),parent.parent,parent)
            self.assertIn('old DN ambiguity',result['pending']);self.assertFalse(result['hil_ready']);self.assertEqual(result['native_block_branch_stage']['reconstructed_edges'],['E'])
            self.assertTrue(any('recompute' in p for p in result['pending']));self.assertTrue(any('1 selected block endpoint' in p for p in result['pending']))

    def test_native_replay_dispatch_precedes_inherited_gap_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,sha=self.fixture(folder)
            with patch('reconstruct_native_block_branches.verify_output',side_effect=ValueError('native paths differ')),patch('attach_confirmed_gap_joints.verify_output') as wrong:
                result=check({},sha(graph),root,graph)
            self.assertEqual(result['status'],'failed');self.assertIn('native paths differ',result['errors'][0]);wrong.assert_not_called()

    def test_changed_parent_and_stale_output_are_rejected(self):
        for variant in ('parent','output'):
            with tempfile.TemporaryDirectory() as folder:
                root,parent,graph,audit,sha=self.fixture(folder)
                if variant=='parent':parent.write_text('{"changed":true}')
                else:audit['output_graph_sha256']='wrong'
                with patch('reconstruct_native_block_branches.verify_output',return_value=audit):
                    with self.assertRaises(ValueError):check_native_block_branch_graph(root,{},sha(graph),graph)

    def test_later_attribute_fusion_replays_before_its_inherited_block_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,sha=self.fixture(folder);g=json.loads(graph.read_text());g['crossViewAttributeFusion']={'newer':True};graph.write_text(json.dumps(g))
            with patch('source_comparison_gate.check_crossview_attribute_graph',return_value={'status':'attribute-first'}) as fusion,patch('reconstruct_native_block_branches.verify_output') as wrong:
                result=check({},sha(graph),root,graph)
            self.assertEqual(result['status'],'attribute-first');fusion.assert_called_once();wrong.assert_not_called()


if __name__=='__main__':unittest.main()
