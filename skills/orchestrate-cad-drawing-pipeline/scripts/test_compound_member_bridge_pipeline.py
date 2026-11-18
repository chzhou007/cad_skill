import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_compound_member_bridges
from rebuild_compound_member_bridges import MODE
class Tests(unittest.TestCase):
    def test_native_bridge_pass_does_not_claim_complete_lengths_or_HIL(self):
        proof=dict(mode=MODE,DN_used_for_mapping=False,source_drawing_graphs_unchanged=True,member_topology_rebuilt=True,installed_lengths_assigned=0,human_accepted=False,counts=dict(qualified_bridges=2,remaining_external_axis_edges=4))
        with patch('rebuild_compound_member_bridges.verify_output',return_value=proof):r=validate_compound_member_bridges(Path('run'))
        self.assertEqual(r['native_member_bridges'],'passed');self.assertEqual(r['status'],'pending');self.assertFalse(r['human_accepted'])
    def test_unknown_native_input_or_promoted_installed_length_fail(self):
        with patch('rebuild_compound_member_bridges.verify_output',side_effect=ValueError('source changed')):
            with self.assertRaises(ValueError):validate_compound_member_bridges(Path('run'))
        with patch('rebuild_compound_member_bridges.verify_output',return_value=dict(mode=MODE,DN_used_for_mapping=False,source_drawing_graphs_unchanged=True,member_topology_rebuilt=True,installed_lengths_assigned=1,human_accepted=False)):
            with self.assertRaises(ValueError):validate_compound_member_bridges(Path('run'))
if __name__=='__main__':unittest.main()
