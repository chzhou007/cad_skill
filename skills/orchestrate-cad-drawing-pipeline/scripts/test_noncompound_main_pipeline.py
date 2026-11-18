import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_noncompound_main_extents

class Tests(unittest.TestCase):
    def test_replay_is_technical_length_evidence_not_new_topology_or_human_acceptance(self):
        with patch('rebuild_noncompound_main_extents.verify_output',return_value=dict(counts=dict(requalified_main_edges=10))):r=validate_noncompound_main_extents(Path('run'))
        self.assertEqual(r['native_noncompound_main_replay'],'passed');self.assertEqual(r['status'],'pending');self.assertFalse(r['local_topology_changed']);self.assertFalse(r['attribute_fusion_performed']);self.assertFalse(r['human_accepted']);self.assertEqual(r['installed_lengths_assigned'],0)
    def test_changed_source_cannot_be_reported_as_replayed(self):
        with patch('rebuild_noncompound_main_extents.verify_output',side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError,'source changed'):validate_noncompound_main_extents(Path('run'))
if __name__=='__main__':unittest.main()
