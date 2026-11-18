import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_plan_DN


class PlanDNScopeGateTests(unittest.TestCase):
    def test_native_replay_reports_drawn_scope_without_mapping_or_hil_claim(self):
        data=dict(status='source_checked_plan_DN_scopes_human_pending',local_graph_mutated=False,human_accepted=False,graph_sha256='G',source_sha256='S',records=[{'nominal_mm':80},{'nominal_mm':None}])
        with patch('plan_pipe_diameter_scopes.verify_output',return_value=data) as replay:
            out=validate_plan_DN(Path('stage'));replay.assert_called_once_with(Path('stage'))
        self.assertEqual(out['known_DN_scopes'],1);self.assertEqual(out['plan_drawn_pipe_scopes'],2);self.assertFalse(out['hil_ready']);self.assertEqual(out['status'],'pending')

    def test_replay_error_or_acceptance_mutation_is_not_suppressed(self):
        with patch('plan_pipe_diameter_scopes.verify_output',side_effect=ValueError('stale source')):
            with self.assertRaisesRegex(ValueError,'stale source'):validate_plan_DN('stage')
        with patch('plan_pipe_diameter_scopes.verify_output',return_value=dict(status='source_checked_plan_DN_scopes_human_pending',local_graph_mutated=True,human_accepted=False)):
            with self.assertRaisesRegex(ValueError,'unsupported'):validate_plan_DN('stage')


if __name__=='__main__':unittest.main()
