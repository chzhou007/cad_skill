import copy,unittest
from unittest.mock import patch
import pipeline
from anchored_terminal_branch_reapplication import MODE
class PipelineBranchReuse(unittest.TestCase):
    def proof(self):return dict(mode=MODE,complete_published_parent_replayed=True,all_current_independent_main_third_arms_screened=True,graph_mutated=False,old_providers_replaced=False,human_accepted=False,remote_equipment_identities_assigned=0,physical_ports_created=0,whole_axis_DN_assigned=0,whole_axis_lengths_assigned=0,vertical_values_assigned=0,counts=dict(considered_third_arms=18,source_qualified_branch_contexts=10,pending=8))
    def test_formal_validator_calls_native_replay_and_keeps_viewer_and_HIL_pending(self):
        with patch('reapply_anchored_terminal_branches.verify_output',return_value=self.proof())as replay:
            result=pipeline.validate_anchored_terminal_branches('run');replay.assert_called_once_with('run')
        self.assertEqual(result['status'],'pending');self.assertFalse(result['viewer_adopted']);self.assertFalse(result['human_accepted'])
    def test_no_remote_physical_port_or_whole_mixed_value_can_pass(self):
        for key in('remote_equipment_identities_assigned','physical_ports_created','whole_axis_DN_assigned','whole_axis_lengths_assigned','vertical_values_assigned'):
            p=self.proof();p[key]=1
            with patch('reapply_anchored_terminal_branches.verify_output',return_value=p),self.assertRaises(ValueError):pipeline.validate_anchored_terminal_branches('run')
    def test_reconstruction_does_not_claim_independent_validation_or_repeat_whole_parent_for_free(self):
        with patch('reapply_anchored_terminal_branches.produce',return_value=self.proof())as produce:
            result=pipeline.reconstruct_anchored_terminal_branches('manifest','output');produce.assert_called_once_with('manifest','output')
        self.assertEqual(result['native_anchored_terminal_branches'],'produced_independent_validation_required')
if __name__=='__main__':unittest.main()
