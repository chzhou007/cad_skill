import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_compound_member_interfaces
from compound_member_interfaces import MODE
class Tests(unittest.TestCase):
    def test_native_scope_replay_does_not_claim_entire_plan_or_human_acceptance(self):
        source=dict(mode=MODE,member_topology_rebuilt=True,source_drawing_graphs_unchanged=True,installed_lengths_assigned=0,human_accepted=False,counts=dict(new_axis_correspondences=12),parent_qualification=dict(qualification_policy='original_complete_verifier_or_current_content_checked_artifact_application'))
        with patch('rebuild_compound_member_interfaces.verify_output',return_value=source):result=validate_compound_member_interfaces(Path('run'))
        self.assertEqual(result['status'],'pending');self.assertEqual(result['native_member_interface_reconstruction'],'passed');self.assertFalse(result['human_accepted']);self.assertFalse(result['attribute_composition_performed'])
    def test_stale_parent_or_native_source_failure_propagates(self):
        with patch('rebuild_compound_member_interfaces.verify_output',side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError,'source changed'):validate_compound_member_interfaces(Path('run'))
if __name__=='__main__':unittest.main()
