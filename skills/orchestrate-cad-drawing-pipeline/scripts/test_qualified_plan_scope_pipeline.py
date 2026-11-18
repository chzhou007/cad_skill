import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from rebuild_qualified_plan_scope_extension import MODE
from pipeline import validate_qualified_plan_scope_extension,reconstruct_qualified_plan_scope_extension,validate_qualified_plan_scope_refresh
class Tests(unittest.TestCase):
    def test_current_native_provider_pass_is_not_axis_or_human_acceptance(self):
        proof=dict(mode=MODE,specific_provider_reconstructed=True,source_graphs_mutated=False,axis_values_fused=False,physical_pipe_count_inferred=False,human_accepted=False,native_provider=dict(old_provider_receipt_accepted=False),counts=dict(new_one_to_one_main_scopes=10))
        with patch('rebuild_qualified_plan_scope_extension.verify_output',return_value=proof):r=validate_qualified_plan_scope_extension(Path('native'))
        self.assertEqual(r['native_specific_plan_provider'],'passed');self.assertEqual(r['status'],'pending');self.assertFalse(r['axis_values_fused'])
        proof['native_provider']['old_provider_receipt_accepted']=True
        with patch('rebuild_qualified_plan_scope_extension.verify_output',return_value=proof):
            with self.assertRaises(ValueError):validate_qualified_plan_scope_extension(Path('native'))
    def test_complete_reconstruction_and_versioned_viewer_entries(self):
        with patch('rebuild_qualified_plan_scope_extension.produce')as produce,patch('pipeline.validate_qualified_plan_scope_extension',return_value={'status':'pending'})as verify:reconstruct_qualified_plan_scope_extension(Path('manifest'),Path('new'))
        produce.assert_called_once_with(Path('manifest'),Path('new'));verify.assert_called_once_with(Path('new'))
        with patch('refresh_qualified_plan_scope_attributes.verify',return_value={'artifact_replay':'passed'})as verify:self.assertEqual(validate_qualified_plan_scope_refresh(Path('viewer'))['artifact_replay'],'passed')
        verify.assert_called_once_with(Path('viewer'))
if __name__=='__main__':unittest.main()
