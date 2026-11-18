import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_compound_member_projections

class Tests(unittest.TestCase):
    def test_technical_member_replay_does_not_claim_global_completion_or_HIL(self):
        with patch('rebuild_compound_member_projections.verify_output',return_value=dict(counts=dict(member_main_intervals=32))):r=validate_compound_member_projections(Path('source-run'))
        self.assertEqual(r['native_compound_member_replay'],'passed');self.assertEqual(r['status'],'pending');self.assertFalse(r['human_accepted']);self.assertFalse(r['global_plan_topology_complete']);self.assertFalse(r['attribute_fusion_performed'])
    def test_changed_native_member_receipt_cannot_pass(self):
        with patch('rebuild_compound_member_projections.verify_output',side_effect=ValueError('native receipt changed')):
            with self.assertRaisesRegex(ValueError,'native receipt changed'):validate_compound_member_projections(Path('source-run'))
if __name__=='__main__':unittest.main()
