import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_axis_vertical_DN_batch
from axis_vertical_DN_batch import MODE
class Tests(unittest.TestCase):
    def test_native_local_dn_does_not_claim_whole_edge_or_length_completion(self):
        proof=dict(mode=MODE,graph_mutated=False,horizontal_plan_attributes_changed=False,whole_edge_DN_assigned=0,physical_lengths_assigned=0,human_accepted=False,counts=dict(qualified_vertical_segments=146))
        with patch('axis_vertical_DN_batch.verify_output',return_value=proof):r=validate_axis_vertical_DN_batch(Path('run'))
        self.assertEqual(r['native_axis_vertical_DN_batch'],'passed');self.assertEqual(r['status'],'pending');self.assertFalse(r['whole_edge_attributes_complete']);self.assertFalse(r['human_accepted'])
    def test_stale_source_and_whole_length_promotions_fail(self):
        with patch('axis_vertical_DN_batch.verify_output',side_effect=ValueError('source changed')):
            with self.assertRaises(ValueError):validate_axis_vertical_DN_batch(Path('run'))
        with patch('axis_vertical_DN_batch.verify_output',return_value=dict(mode=MODE,graph_mutated=False,horizontal_plan_attributes_changed=False,whole_edge_DN_assigned=1,physical_lengths_assigned=0,human_accepted=False)):
            with self.assertRaises(ValueError):validate_axis_vertical_DN_batch(Path('run'))
if __name__=='__main__':unittest.main()
