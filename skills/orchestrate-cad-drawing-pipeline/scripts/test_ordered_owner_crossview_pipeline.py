import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from rebuild_ordered_owner_crossview import MODE
from pipeline import validate_ordered_owner_crossview,reconstruct_ordered_owner_crossview,validate_ordered_owner_plan_refresh
class Tests(unittest.TestCase):
    def test_native_mapping_not_whole_goal_or_attribute_completion(self):
        proof=dict(mode=MODE,DN_used_for_mapping=False,local_graphs_mutated=False,attributes_fused=False,human_accepted=False,counts=dict(new_correspondences=8))
        with patch('rebuild_ordered_owner_crossview.verify_output',return_value=proof):r=validate_ordered_owner_crossview(Path('native'))
        self.assertEqual(r['native_ordered_owner_crossview'],'passed');self.assertEqual(r['status'],'pending');self.assertFalse(r['attributes_fused'])
        proof['DN_used_for_mapping']=True
        with patch('rebuild_ordered_owner_crossview.verify_output',return_value=proof):
            with self.assertRaises(ValueError):validate_ordered_owner_crossview(Path('native'))
    def test_complete_entry_and_viewer_gate_dispatch_to_native_owners(self):
        with patch('rebuild_ordered_owner_crossview.produce')as produce,patch('pipeline.validate_ordered_owner_crossview',return_value={'status':'pending'})as check:reconstruct_ordered_owner_crossview(Path('manifest'),Path('new'))
        produce.assert_called_once_with(Path('manifest'),Path('new'));check.assert_called_once_with(Path('new'))
        with patch('refresh_ordered_owner_plan_attributes.verify',return_value={'artifact_replay':'passed'})as check:self.assertEqual(validate_ordered_owner_plan_refresh(Path('viewer'))['artifact_replay'],'passed')
        check.assert_called_once_with(Path('viewer'))
if __name__=='__main__':unittest.main()
