import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from project_scoped_descendant_source_gate import check_project_descendant
from confirm_crossview_paths import sha,encode


class Tests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name);parent=root/'parent/graph_with_edges.json';parent.parent.mkdir()
        parent.write_bytes(encode(dict(nodes=[],edges=[])))
        run=root/'child';run.mkdir();graph=run/'graph_with_edges.json'
        graph.write_bytes(encode(dict(nodes=[dict(node_id='REMAIN',boundary_type='unresolved_source_terminal')],edges=[])))
        proof=dict(kind='capped_roles',current_graph_sha256=sha(graph),parent_graph=parent,disposed_node_ids=['CAP'],owner_asset_sha256='A',current_mapping_snapshot_scope={'receipts_rebound':False})
        report=dict(errors=['old error'],pending=['2 graph nodes have unresolved source-terminal or equipment-overlap semantics','unrelated old issue'],
            graph_unresolved_node_blockers=[dict(node_id='CAP'),dict(node_id='REMAIN')],hil_ready=False)
        return run,graph,proof,report

    def test_only_proven_role_disposition_is_removed_old_errors_and_pending_survive(self):
        run,graph,proof,old=self.fixture();before=copy.deepcopy(old)
        with patch('project_scoped_descendant_source_gate.verify_output',return_value=proof),patch('source_comparison_gate.check',return_value=old):
            result=check_project_descendant(run,{},graph)
        self.assertEqual(old,before);self.assertEqual(result['errors'],['old error']);self.assertIn('unrelated old issue',result['pending'])
        self.assertEqual(result['status'],'failed');self.assertEqual(len(result['graph_unresolved_node_blockers']),1);self.assertFalse(result['hil_ready'])
        self.assertEqual(result['project_scoped_descendant_stage']['nodes_retired'],0);self.assertTrue(result['project_scoped_descendant_stage']['source_role_node_ids_retained'])

    def test_unrelated_node_disposition_or_wrong_current_hash_block(self):
        for mode in ('unrelated','stale'):
            run,graph,proof,old=self.fixture()
            if mode=='unrelated':proof['disposed_node_ids']=['OTHER']
            else:proof['current_graph_sha256']='OLD'
            with self.subTest(mode=mode),patch('project_scoped_descendant_source_gate.verify_output',return_value=proof),patch('source_comparison_gate.check',return_value=old):
                with self.assertRaises(ValueError):check_project_descendant(run,{},graph)

    def test_graph_directory_cannot_be_substituted(self):
        run,graph,proof,old=self.fixture()
        with self.assertRaisesRegex(ValueError,'exact declared'):check_project_descendant(run/'elsewhere',{},graph)

    def test_successful_native_scope_never_sets_whole_HIL_ready(self):
        run,graph,proof,old=self.fixture();old['errors']=[]
        with patch('project_scoped_descendant_source_gate.verify_output',return_value=proof),patch('source_comparison_gate.check',return_value=old):
            result=check_project_descendant(run,{},graph)
        self.assertEqual(result['status'],'pending');self.assertFalse(result['human_accepted']);self.assertFalse(result['project_scoped_descendant_stage']['whole_source_comparison_complete'])


if __name__=='__main__':unittest.main()
