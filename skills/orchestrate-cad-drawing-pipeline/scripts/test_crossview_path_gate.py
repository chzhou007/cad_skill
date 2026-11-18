import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from pipeline import validate_crossview
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))

class CrossviewPathGateTests(unittest.TestCase):
    def fixture(self,folder):
        plan=Path(folder)/'plan.json';axis=Path(folder)/'axis.json'
        plan.write_text('{}');axis.write_text('{"axis":true}')
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        mapping=dict(status='confirmed_path_correspondence_attributes_pending',plan_graph_sha256=sha(plan),iso_graph_sha256=sha(axis),
            records=[{'system':'supply'},{'system':'return'}],local_graphs_mutated=False,human_accepted=False,local_scope='explicitly reviewed branches')
        return plan,axis,mapping
    def test_native_mapping_is_not_attribute_or_whole_graph_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            plan,axis,mapping=self.fixture(folder)
            with patch('confirm_crossview_paths.verify_output',return_value=mapping) as replay:
                result=validate_crossview('mapping',plan,axis);replay.assert_called_once_with('mapping')
            self.assertEqual(result['path_correspondence'],'native_replayed');self.assertEqual(result['status'],'pending')
            self.assertFalse(result['human_accepted']);self.assertFalse(result['hil_ready'])
    def test_changing_either_local_graph_invalidates_mapping(self):
        for side in ('plan','axis'):
            with tempfile.TemporaryDirectory() as folder:
                plan,axis,mapping=self.fixture(folder);(plan if side=='plan' else axis).write_text('{"changed":true}')
                with patch('confirm_crossview_paths.verify_output',return_value=mapping):
                    with self.assertRaisesRegex(ValueError,'stale'):validate_crossview('mapping',plan,axis)
    def test_native_replay_failure_cannot_be_overridden_by_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            plan,axis,mapping=self.fixture(folder)
            with patch('confirm_crossview_paths.verify_output',side_effect=ValueError('native evidence changed')):
                with self.assertRaisesRegex(ValueError,'native evidence changed'):validate_crossview('mapping',plan,axis)

if __name__=='__main__':unittest.main()
