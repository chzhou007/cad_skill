import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_axis_attribute_source_routing
from axis_attribute_source_routing import MODE
class Tests(unittest.TestCase):
    def test_routing_inventory_never_claims_attribute_or_mapping_completion(self):
        result=dict(mode=MODE,graph_mutated=False,physical_lengths_assigned=0,whole_edge_DN_assigned=0,human_accepted=False,
            edge_counts={'mixed_horizontal_vertical':1},segment_counts={'horizontal':1,'vertical':1},native_segment_status_counts={'single_source_line_covers':2})
        with patch('axis_attribute_source_routing.verify_output',return_value=result):r=validate_axis_attribute_source_routing(Path('run'))
        self.assertEqual(r['native_segment_source_routing'],'passed');self.assertEqual(r['status'],'pending');self.assertFalse(r['mapping_or_attribute_completion_claimed']);self.assertFalse(r['human_accepted'])
    def test_stale_source_and_invented_length_are_rejected(self):
        with patch('axis_attribute_source_routing.verify_output',side_effect=ValueError('native input changed')):
            with self.assertRaises(ValueError):validate_axis_attribute_source_routing(Path('run'))
        with patch('axis_attribute_source_routing.verify_output',return_value=dict(mode=MODE,graph_mutated=False,physical_lengths_assigned=1,whole_edge_DN_assigned=0,human_accepted=False)):
            with self.assertRaises(ValueError):validate_axis_attribute_source_routing(Path('run'))
if __name__=='__main__':unittest.main()
