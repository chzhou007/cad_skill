import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from source_comparison_gate import check,check_source_checked_attribute_graph


class SourceCheckedCrossviewGateTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder)/'child';root.mkdir();parent=Path(folder)/'parent.json';parent.write_text('{}')
        graph=root/'graph_with_edges.json';graph.write_text(json.dumps(dict(sourceCheckedCrossViewAttributeFusion={'records':[1]},crossViewAttributeFusion={'inherited':True})))
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        audit=dict(parent_graph=dict(path=str(parent),sha256=sha(parent)),output_graph_sha256=sha(graph),records=[dict(mapping_id='SC-1')])
        return root,parent,graph,audit,sha

    def test_native_source_fusion_retains_prior_issues_and_does_not_claim_expert_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,sha=self.fixture(folder);report={'graph_sha256':'original-local-screen'}
            with patch('attach_source_checked_plan_attributes.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=dict(errors=[],pending=['old DN scope'])) as previous:
                result=check_source_checked_attribute_graph(root,report,sha(graph),graph)
            previous.assert_called_once_with(report,sha(parent),parent.parent,parent)
            self.assertIn('old DN scope',result['pending']);self.assertFalse(result['hil_ready']);self.assertFalse(result['source_checked_crossview_attribute_stage']['expert_confirmation_claimed'])

    def test_newest_source_fusion_runs_before_inherited_legacy_fusion(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,sha=self.fixture(folder)
            with patch('attach_source_checked_plan_attributes.verify_output',side_effect=ValueError('changed source correspondence')),patch('attach_crossview_plan_attributes.verify_output') as wrong:
                result=check({},sha(graph),root,graph)
            self.assertEqual(result['status'],'failed');self.assertIn('changed source correspondence',result['errors'][0]);wrong.assert_not_called()

    def test_changed_parent_or_output_fails_closed(self):
        for variant in ('parent','output'):
            with tempfile.TemporaryDirectory() as folder:
                root,parent,graph,audit,sha=self.fixture(folder)
                if variant=='parent':parent.write_text('{"changed":true}')
                else:audit['output_graph_sha256']='wrong'
                with patch('attach_source_checked_plan_attributes.verify_output',return_value=audit):
                    with self.assertRaises(ValueError):check_source_checked_attribute_graph(root,{},sha(graph),graph)

    def test_checked_dn_receipt_reports_scopes_and_preserves_unrelated_parent_blockers(self):
        with tempfile.TemporaryDirectory() as folder:
            root,parent,graph,audit,sha=self.fixture(folder)
            audit['plan_DN_scope_fusion']=[dict(plan_drawn_nominal_mm=80,whole_main_DN_and_centerline_route=True),dict(plan_drawn_nominal_mm=200,whole_main_DN_and_centerline_route=False)]
            with patch('attach_source_checked_plan_attributes.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=dict(errors=[],pending=['unrelated native datum'])):
                result=check_source_checked_attribute_graph(root,{},sha(graph),graph)
            stage=result['source_checked_crossview_attribute_stage']
            self.assertEqual(stage['plan_drawn_DN_edges'],2);self.assertEqual(stage['complete_horizontal_main_DN_and_centerline_edges'],1)
            self.assertIn('unrelated native datum',result['pending']);self.assertFalse(result['hil_ready']);self.assertFalse(stage['net_pipe_cut_lengths_complete'])


if __name__=='__main__':unittest.main()
