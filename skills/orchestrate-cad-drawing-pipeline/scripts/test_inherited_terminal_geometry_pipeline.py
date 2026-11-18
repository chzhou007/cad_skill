import unittest
from unittest.mock import patch
import pipeline
from reapply_inherited_terminal_geometry import MODE

class InheritedTerminalPipeline(unittest.TestCase):
    def proof(self):
        return dict(mode=MODE,records=[],original_published_records=[],complete_published_parent_replayed=True,all_current_marker_interfaces_screened=True,all_current_main_third_arms_screened=True,old_published_records_unchanged=True,source_graphs_mutated=False,crossed_pipes_connected=False,human_accepted=False,new_physical_nodes_created=0,whole_axis_DN_assigned=0,whole_axis_lengths_assigned=0,vertical_values_assigned=0,counts={'new_branch_contexts':6})
    def test_validator_replays_native_owner_and_retains_publication_gate(self):
        with patch('reapply_inherited_terminal_geometry.verify_output',return_value=self.proof())as replay:
            result=pipeline.validate_inherited_terminal_geometry('run');replay.assert_called_once_with('run')
        self.assertEqual(result['status'],'pending');self.assertFalse(result['viewer_adopted']);self.assertFalse(result['human_accepted'])
    def test_source_production_does_not_silently_claim_independent_validation(self):
        with patch('reapply_inherited_terminal_geometry.produce',return_value=self.proof())as produce:
            result=pipeline.reconstruct_inherited_terminal_geometry('manifest','out');produce.assert_called_once_with('manifest','out')
        self.assertEqual(result['native_inherited_terminal_geometry'],'produced_independent_validation_required')
    def test_crossed_pipe_join_graph_mutation_or_whole_value_cannot_pass(self):
        for key in('source_graphs_mutated','crossed_pipes_connected','new_physical_nodes_created','whole_axis_DN_assigned','whole_axis_lengths_assigned','vertical_values_assigned'):
            p=self.proof();p[key]=True if isinstance(p[key],bool)else 1
            with patch('reapply_inherited_terminal_geometry.verify_output',return_value=p),self.assertRaises(ValueError):pipeline.validate_inherited_terminal_geometry('run')

if __name__=='__main__':unittest.main()
