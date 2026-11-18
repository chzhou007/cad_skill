import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
from pipeline import validate_plan_DN


class PairedDNGateTests(unittest.TestCase):
    def data(self):return dict(status='source_checked_plan_DN_scopes_human_pending',graph_sha256='G',source_sha256='S',records=[dict(nominal_mm=200),dict(nominal_mm=None)],local_graph_mutated=False,human_accepted=False)
    def test_paired_native_replay_is_separate_and_keeps_fusion_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'plan-DN-scope-receipt.json').write_text(json.dumps(dict(mode='paired_service_plan_DN_scopes_v1')),encoding='utf8')
            with patch('paired_plan_DN_scopes.verify_output',return_value=self.data()) as replay:
                r=validate_plan_DN(folder);replay.assert_called_once_with(folder)
            self.assertEqual(r['source_replay'],'passed');self.assertEqual(r['known_DN_scopes'],1);self.assertFalse(r['hil_ready']);self.assertEqual(r['status'],'pending')
    def test_changed_sources_and_false_acceptance_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'plan-DN-scope-receipt.json').write_text(json.dumps(dict(mode='paired_service_plan_DN_scopes_v1')),encoding='utf8')
            with patch('paired_plan_DN_scopes.verify_output',side_effect=ValueError('source changed')):
                with self.assertRaisesRegex(ValueError,'source changed'):validate_plan_DN(folder)
            for key in ('local_graph_mutated','human_accepted'):
                d=self.data();d[key]=True
                with patch('paired_plan_DN_scopes.verify_output',return_value=d):
                    with self.assertRaises(ValueError):validate_plan_DN(folder)
    def test_legacy_calibrated_entry_and_unknown_modes_are_not_confused(self):
        with tempfile.TemporaryDirectory() as folder:
            receipt=Path(folder)/'plan-DN-scope-receipt.json';receipt.write_text(json.dumps(dict(mode='calibrated_plan_DN_scopes')),encoding='utf8')
            with patch('plan_pipe_diameter_scopes.verify_output',return_value=self.data()) as old,patch('paired_plan_DN_scopes.verify_output') as new:
                validate_plan_DN(folder);old.assert_called_once_with(folder);new.assert_not_called()
            receipt.write_text(json.dumps(dict(mode='unknown')),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'entry mode'):validate_plan_DN(folder)
    def test_refined_DN_replays_new_entry_and_preserves_pending_physical_fusion(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'plan-DN-scope-receipt.json').write_text(json.dumps(dict(mode='paired_service_junction_refined_plan_DN_scopes_v1')),encoding='utf8')
            d=dict(self.data(),status='source_checked_junction_refined_plan_DN_scopes_human_pending',previous_checked_records_preserved=True,physical_values_fused=False)
            with patch('refined_paired_plan_DN_scopes.verify_output',return_value=d) as replay,patch('paired_plan_DN_scopes.verify_output') as old:
                r=validate_plan_DN(folder);replay.assert_called_once_with(folder);old.assert_not_called()
            self.assertEqual(r['source_replay'],'passed');self.assertEqual(r['status'],'pending');self.assertFalse(r['hil_ready'])
            for key,value in [('physical_values_fused',True),('previous_checked_records_preserved',False),('human_accepted',True)]:
                bad=dict(d,**{key:value})
                with patch('refined_paired_plan_DN_scopes.verify_output',return_value=bad):
                    with self.assertRaises(ValueError):validate_plan_DN(folder)


if __name__=='__main__':unittest.main()
