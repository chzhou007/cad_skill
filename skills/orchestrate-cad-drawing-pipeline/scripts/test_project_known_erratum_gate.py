import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from source_comparison_gate import check,check_known_project_erratum_graph


class ProjectKnownErratumGateTests(unittest.TestCase):
    def fixture(self,temp):
        root=Path(temp)/'repair';root.mkdir();parent=Path(temp)/'parent.json';parent.write_text('{}');graph=root/'graph_with_edges.json';graph.write_text(json.dumps({'sourceDraftingErrata':{'records':[1]}}));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        audit=dict(output_graph_sha256=sha(graph),parent_graph=dict(path=str(parent),sha256=sha(parent)),records=[{'system':'supply'}])
        return root,parent,graph,audit,sha

    def test_replays_original_parent_and_preserves_unrelated_native_blockers(self):
        with tempfile.TemporaryDirectory() as temp:
            root,parent,graph,audit,sha=self.fixture(temp);report={'original':'report'}
            with patch('apply_known_project_pipe_erratum.verify_output',return_value=audit) as replay,patch('source_comparison_gate.check',return_value=dict(errors=[],pending=['old unknown length'])) as inherited:
                result=check_known_project_erratum_graph(root,report,sha(graph),graph)
            replay.assert_called_once_with(graph.parent);inherited.assert_called_once_with(report,sha(parent),parent.parent,parent)
            self.assertIn('old unknown length',result['pending']);self.assertFalse(result['hil_ready']);self.assertFalse(result['project_known_erratum_stage']['general_circle_rule_added'])

    def test_changed_output_or_parent_and_unverified_drawing_flags_fail_closed(self):
        for variant in ('parent','output'):
            with tempfile.TemporaryDirectory() as temp:
                root,parent,graph,audit,sha=self.fixture(temp)
                if variant=='parent':parent.write_text('{"changed":true}')
                else:audit['output_graph_sha256']='bad'
                with patch('apply_known_project_pipe_erratum.verify_output',return_value=audit):
                    with self.assertRaises(ValueError):check_known_project_erratum_graph(root,{},sha(graph),graph)
        with tempfile.TemporaryDirectory() as temp:
            root,parent,graph,audit,sha=self.fixture(temp)
            with patch('apply_known_project_pipe_erratum.verify_output',side_effect=ValueError('changed source')):
                result=check({},sha(graph),root,graph)
            self.assertEqual(result['status'],'failed');self.assertIn('changed source',result['errors'][0])


if __name__=='__main__':unittest.main()
