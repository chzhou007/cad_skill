import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'))
from test_network_named_lower_plan_viewer_evidence import fixture
from network_named_lower_plan_fusion_gate import check
from pipeline import validate_network_named_lower_plan_fusion
from source_comparison_gate import check as dispatch


class Tests(unittest.TestCase):
    def test_complete_parent_errors_and_pending_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            g,graph,audit=fixture(Path(temp));p=Path(audit['parent_graph']['path'])
            previous=dict(status='failed',graph_sha256=audit['parent_graph']['sha256'],errors=['old_error'],pending=['old_pending'])
            (p.parent/'source-comparison-gate.json').write_text(json.dumps(previous),encoding='utf-8')
            with patch('attach_network_named_lower_plan_attributes.verify_output',return_value=audit) as replay:result=check(g.parent,previous,audit['output_graph_sha256'],g)
            replay.assert_called_once();self.assertEqual(result['errors'],previous['errors']);self.assertEqual(result['pending'][0],'old_pending');self.assertEqual(result['status'],'failed');self.assertFalse(result['hil_ready'])
            with patch('attach_network_named_lower_plan_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):check(g.parent,dict(previous,pending=[]),audit['output_graph_sha256'],g)
    def test_native_failure_does_not_clear_parent_issues(self):
        with patch('attach_network_named_lower_plan_attributes.verify_output',side_effect=ValueError('source moved')),self.assertRaisesRegex(ValueError,'source moved'):check('RUN',{},'hash',Path('RUN/graph_with_edges.json'))
    def test_formal_validator_replays_owner_and_never_accepts_whole_values(self):
        from attach_network_named_lower_plan_attributes import MODE
        audit=dict(mode=MODE,hil_ready=False,human_accepted=False,output_graph_sha256='a'*64,stage=dict(added_prefix_scopes=2,whole_mixed_edge_values_assigned=0,prior_topology_components_and_attributes_preserved=True,related_HIL_confirmation_inherited=False))
        with patch('attach_network_named_lower_plan_attributes.verify_output',return_value=audit) as native:result=validate_network_named_lower_plan_fusion('RUN')
        native.assert_called_once_with('RUN');self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
        audit['stage']['whole_mixed_edge_values_assigned']=2
        with patch('attach_network_named_lower_plan_attributes.verify_output',return_value=audit),self.assertRaises(ValueError):validate_network_named_lower_plan_fusion('RUN')
    def test_source_dispatch_precedes_retained_main(self):
        with tempfile.TemporaryDirectory() as temp:
            g,graph,audit=fixture(Path(temp));p=Path(audit['parent_graph']['path']);previous=dict(status='pending',graph_sha256=audit['parent_graph']['sha256'],errors=[],pending=['old_pending'])
            (p.parent/'source-comparison-gate.json').write_text(json.dumps(previous),encoding='utf-8')
            with patch('attach_network_named_lower_plan_attributes.verify_output',return_value=audit) as native,patch('anchored_floor_main_fusion_gate.check') as old:
                result=dispatch(previous,audit['output_graph_sha256'],g.parent,g)
            native.assert_called_once();old.assert_not_called();self.assertEqual(result['pending'][0],'old_pending');self.assertEqual(result['network_named_lower_plan_attribute_stage']['source_replay'],'passed')

if __name__=='__main__':unittest.main()
