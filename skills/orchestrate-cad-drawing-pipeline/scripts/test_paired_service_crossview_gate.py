import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_source_crossview


class PairedServiceGateTests(unittest.TestCase):
    def data(self):return dict(status='source_checked_paired_service_correspondence_attributes_pending',records=[{},{}],equipment_scope=['A','B'],local_graphs_mutated=False,expert_confirmation_claimed=False,human_accepted=False,hil_ready=False)
    def test_versioned_paired_entry_replays_and_keeps_attributes_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode='source_checked_paired_service_paths_v1')),encoding='utf8')
            with patch('match_paired_service_crossview_paths.verify_output',return_value=self.data()) as check:
                result=validate_source_crossview(folder);check.assert_called_once_with(folder)
            self.assertEqual(result['path_correspondence'],'native_paired_service_corridors_replayed');self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready'])
    def test_replay_failure_and_false_acceptance_are_not_suppressed(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode='source_checked_paired_service_paths_v1')),encoding='utf8')
            with patch('match_paired_service_crossview_paths.verify_output',side_effect=ValueError('source changed')):
                with self.assertRaisesRegex(ValueError,'source changed'):validate_source_crossview(folder)
            for key in ('local_graphs_mutated','expert_confirmation_claimed','human_accepted','hil_ready'):
                data=self.data();data[key]=True
                with patch('match_paired_service_crossview_paths.verify_output',return_value=data):
                    with self.assertRaises(ValueError):validate_source_crossview(folder)
    def test_legacy_dispatch_stays_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'source-mapping-receipt.json').write_text('{}',encoding='utf8')
            with patch('match_source_checked_crossview_paths.verify_output',return_value=self.data()) as legacy,patch('match_paired_service_crossview_paths.verify_output') as newer:
                validate_source_crossview(folder);legacy.assert_called_once_with(folder);newer.assert_not_called()
    def test_unknown_entry_is_not_assumed_legacy(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode='unsupported')),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'entry mode'):validate_source_crossview(folder)
    def test_refined_junction_mapping_has_its_own_replay_and_still_no_attribute_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'source-mapping-receipt.json').write_text(json.dumps(dict(mode='paired_service_junction_refined_paths_v1')),encoding='utf8')
            data=self.data();data['status']='source_checked_junction_refined_correspondence_attributes_pending'
            with patch('refine_paired_service_path_correspondence.verify_output',return_value=data) as replay:
                r=validate_source_crossview(folder);replay.assert_called_once_with(folder)
            self.assertEqual(r['path_correspondence'],'native_branch_target_junction_refinement_replayed');self.assertEqual(r['status'],'pending');self.assertFalse(r['hil_ready'])
            with patch('refine_paired_service_path_correspondence.verify_output',side_effect=ValueError('junction target changed')):
                with self.assertRaisesRegex(ValueError,'junction target changed'):validate_source_crossview(folder)


if __name__=='__main__':unittest.main()
