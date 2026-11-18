import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'))
from test_external_feed_plan_viewer_evidence import fixture
from external_feed_plan_fusion_gate import check
from source_comparison_gate import check as dispatch


class Tests(unittest.TestCase):
    def test_actual_source_dispatch_replays_new_root_before_old_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            g,graph,audit=fixture(Path(temp));p=Path(audit['parent_graph']['path']);previous=dict(status='pending',errors=[],pending=['old_pending'],graph_sha256=audit['parent_graph']['sha256'])
            (p.parent/'source-comparison-gate.json').write_text(json.dumps(previous),encoding='utf-8')
            with patch('attach_external_feed_plan_attributes.verify_output',return_value=audit) as native,patch('network_named_lower_plan_fusion_gate.check') as old:result=dispatch(previous,audit['output_graph_sha256'],g.parent,g)
            native.assert_called_once();old.assert_not_called();self.assertEqual(result['external_feed_plan_attribute_stage']['source_replay'],'passed');self.assertEqual(result['pending'][0],'old_pending')
    def test_full_parent_errors_and_pending_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            g,graph,audit=fixture(Path(temp));p=Path(audit['parent_graph']['path']);previous=dict(status='failed',errors=['old_error'],pending=['old_pending'],graph_sha256=audit['parent_graph']['sha256'])
            (p.parent/'source-comparison-gate.json').write_text(json.dumps(previous),encoding='utf-8')
            with patch('attach_external_feed_plan_attributes.verify_output',return_value=audit) as native:result=check(g.parent,previous,audit['output_graph_sha256'],g)
            native.assert_called_once();self.assertEqual(result['errors'],['old_error']);self.assertEqual(result['pending'][0],'old_pending');self.assertFalse(result['hil_ready']);self.assertEqual(result['external_feed_plan_attribute_stage']['added_external_pipe_scopes'],4)
            with patch('attach_external_feed_plan_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):check(g.parent,dict(previous,pending=[]),audit['output_graph_sha256'],g)
    def test_native_failure_does_not_clear_parent_issues(self):
        with patch('attach_external_feed_plan_attributes.verify_output',side_effect=ValueError('original port moved')),self.assertRaisesRegex(ValueError,'original port moved'):check('RUN',{},'hash','RUN/graph_with_edges.json')

if __name__=='__main__':unittest.main()
