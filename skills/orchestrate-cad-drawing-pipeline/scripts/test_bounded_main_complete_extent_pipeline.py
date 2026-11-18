import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'))
from rebuild_bounded_main_complete_extents import MODE
from pipeline import validate_bounded_main_complete_extents,reconstruct_bounded_main_complete_extents,validate_bounded_main_complete_extent_refresh
class Tests(unittest.TestCase):
    def test_native_current_scope_pass_is_not_HIL_or_installed_length(self):
        p=dict(mode=MODE,current_provider_inventory_replayed=True,bounded_ancestor_native_replayed=True,selected_old_and_current_plan_scopes_exact=True,existing_correspondences_unchanged=True,DN_observations_preserved=True,local_graphs_mutated=False,installed_lengths_assigned=0,human_accepted=False,counts={})
        with patch('rebuild_bounded_main_complete_extents.verify_output',return_value=p):r=validate_bounded_main_complete_extents(Path('native'))
        self.assertEqual(r['native_bounded_complete_extents'],'passed');self.assertEqual(r['status'],'pending')
        p['DN_observations_preserved']=False
        with patch('rebuild_bounded_main_complete_extents.verify_output',return_value=p),self.assertRaises(ValueError):validate_bounded_main_complete_extents(Path('native'))
    def test_complete_and_viewer_entries_dispatch_to_original_native_verifiers(self):
        with patch('rebuild_bounded_main_complete_extents.produce')as p,patch('pipeline.validate_bounded_main_complete_extents',return_value={})as v:reconstruct_bounded_main_complete_extents(Path('manifest'),Path('new'))
        p.assert_called_once_with(Path('manifest'),Path('new'));v.assert_called_once_with(Path('new'))
        with patch('refresh_bounded_main_complete_extents.verify',return_value={'artifact_replay':'passed'})as v:self.assertEqual(validate_bounded_main_complete_extent_refresh(Path('viewer'))['artifact_replay'],'passed')
        v.assert_called_once_with(Path('viewer'))
if __name__=='__main__':unittest.main()
