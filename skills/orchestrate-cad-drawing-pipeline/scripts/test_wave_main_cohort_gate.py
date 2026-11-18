import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from confirm_crossview_paths import encode,sha
from reconstruct_wave_main_cohorts import MODE
from wave_main_cohort_gate import check


class Tests(unittest.TestCase):
    def fixture(self,root):
        old=root/'parent'/'graph_with_edges.json';old.parent.mkdir();old.write_bytes(encode({'nodes':[]}))
        scope=dict(input_graph_sha256=sha(old),human_accepted=False,physical_lengths_assigned=0,supply_return_independent=True,
            records=[dict(equipment_id='D')],retired_terminal_snapshots=[dict(node_id='OLD')])
        current=root/'graph_with_edges.json';current.write_bytes(encode(dict(metadata=dict(hil_ready=False),nodes=[],edges=[],sourceWaveMainCohort=scope)))
        audit=dict(mode=MODE,output_graph_sha256=sha(current),inputs=dict(graph=dict(path=str(old),sha256=sha(old))))
        return current,audit

    def test_new_stage_preserves_parent_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);current,audit=self.fixture(root)
            with patch('reconstruct_wave_main_cohorts.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=dict(errors=['prior error'],pending=['prior pending'],status='failed')):
                result=check(root,{},sha(current),current)
            self.assertEqual(result['errors'],['prior error']);self.assertEqual(result['pending'],['prior pending']);self.assertEqual(result['status'],'failed')

    def test_only_reconstructed_terminal_blocker_is_retired(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);current,audit=self.fixture(root)
            parent=dict(errors=[],pending=['prior pending','1 graph nodes have unresolved source-terminal or equipment-overlap semantics'],graph_unresolved_node_blockers=[dict(node_id='OLD')])
            with patch('reconstruct_wave_main_cohorts.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=parent),patch('source_comparison_gate.graph_comparison_blockers',return_value=([],{})):
                result=check(root,{},sha(current),current)
            self.assertEqual(result['graph_unresolved_node_blockers'],[]);self.assertIn('prior pending',result['pending']);self.assertFalse(result['hil_ready'])

    def test_unrelated_new_blockers_and_native_failure_are_not_masked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);current,audit=self.fixture(root)
            with patch('reconstruct_wave_main_cohorts.verify_output',side_effect=ValueError('native changed')):
                with self.assertRaisesRegex(ValueError,'native changed'):check(root,{},sha(current),current)
            parent=dict(errors=[],pending=[],graph_unresolved_node_blockers=[])
            with patch('reconstruct_wave_main_cohorts.verify_output',return_value=audit),patch('source_comparison_gate.check',return_value=parent),patch('source_comparison_gate.graph_comparison_blockers',return_value=([dict(node_id='UNRELATED')],{})):
                with self.assertRaisesRegex(ValueError,'unrelated unresolved'):check(root,{},sha(current),current)


if __name__=='__main__':unittest.main()
