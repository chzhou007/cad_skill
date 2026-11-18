import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from confirm_crossview_paths import encode,sha
from plan_pipe_diameter_scopes import verify_output
from plan_calibrated_DN_scopes import MODE,compute as calibrated_compute
from attach_source_checked_plan_attributes import compute
from test_attach_source_checked_plan_attributes import SourcePlanAttributeTests


class CalibratedDNEntryTests(unittest.TestCase):
    def test_receipt_mode_dispatch_does_not_assume_the_old_circle_normalization_parent(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            with patch('plan_pipe_diameter_scopes.load',return_value=dict(mode=MODE)),patch('plan_calibrated_DN_scopes.verify_output',return_value=dict(mode=MODE,human_accepted=False)) as native:
                self.assertEqual(verify_output(folder)['mode'],MODE);native.assert_called_once_with(folder)

    def test_changed_plan_or_calibration_policy_fails_before_source_processing(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);paths={k:root/k for k in ('source','graph','calibration_policy')}
            for p in paths.values():p.write_bytes(b'pinned')
            policy={k+'_sha256':sha(p) for k,p in paths.items()};paths['calibration_policy'].write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'calibration_policy'):calibrated_compute(paths,policy)

    def test_single_mapping_consumes_verified_plan_DN_without_upgrading_unseen_branch(self):
        helper=SourcePlanAttributeTests();doc,parent,mapping,plan,coverage,units,dn=helper.fixture()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'mapping';run.mkdir();dp=root/'dn';dp.mkdir()
            source=root/'plan.dxf';doc.saveas(source);plan_path=root/'plan.json';plan_path.write_bytes(encode(plan));parent_path=root/'parent.json';parent_path.write_bytes(encode(parent))
            devices=root/'devices.csv';devices.write_bytes(b'canonical components')
            mapping.update(plan_graph_sha256=sha(plan_path),iso_graph_sha256=sha(parent_path),source_sha256=dict(plan=sha(source),iso='AXIS'))
            mp=run/'mapping.json';mp.write_bytes(encode(mapping));mr=run/'source-mapping-receipt.json';mr.write_bytes(encode(dict(inputs=dict(plan_graph=dict(path=str(plan_path)),plan_source=dict(path=str(source))))))
            evidence=dp/'plan-DN-scopes.json';evidence.write_bytes(b'verified DN stage');receipt=dp/'plan-DN-scope-receipt.json';receipt.write_bytes(b'verified DN receipt')
            paths=dict(mapping=mp,mapping_receipt=mr,parent_graph=parent_path,devices=devices,diameter_evidence=evidence,diameter_receipt=receipt)
            policy={k+'_sha256':sha(p) for k,p in paths.items()};policy.update(view_kind='floor_plan',plan_window=units['plan_window'],floor_title=units['floor_title'],floor_title_handle=units['floor_title_handle'],unit_dimensions=[{k:r[k] for k in ('handle','text_handle','text')} for r in units['unit_dimensions']])
            verified=dict(source_sha256=sha(source),graph_sha256=sha(plan_path),local_graph_mutated=False,human_accepted=False,records=[dict(edge_id='P',system='supply',nominal_mm=80,scope_paths=plan['edges'][0]['attribute_paths'],scope='native_plan_drawn_pipe_paths_only',human_accepted=False)])
            parent_audit=dict(output_graph_sha256=sha(parent_path),parent_graph=dict(sha256=sha(parent_path)),inputs=dict(devices=dict(sha256=sha(devices))))
            with patch('attach_source_checked_plan_attributes.verify_mapping',return_value=mapping),patch('attach_source_checked_plan_attributes.verify_parent',return_value=parent_audit),patch('plan_pipe_diameter_scopes.verify_output',return_value=verified):
                out,proof=compute(paths,policy)
                c=out['edges'][0]['cross_view_attributes'];self.assertEqual(c['diameter']['plan_drawn_nominal_mm'],80);self.assertIsNone(c['diameter']['nominal_mm']);self.assertIsNone(c['whole_edge_physical_length_mm']);self.assertIn('plan_DN_scope_fusion',proof)
                bad=copy.deepcopy(verified);bad['graph_sha256']='STALE'
                with patch('plan_pipe_diameter_scopes.verify_output',return_value=bad),self.assertRaisesRegex(ValueError,'differs from mapped source'):compute(paths,policy)


if __name__=='__main__':unittest.main()
