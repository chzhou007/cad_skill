import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from feature_impact import impact,load_registry,run_selected,ROOT

class FeatureImpactTests(unittest.TestCase):
 def setUp(self):self.data,self.features=load_registry()
 def test_ownership_scope_composition_and_historical_erratum_keep_old_rules_in_regression(self):
  for name,fid in [('calibrated_ownership_scope_composition.py','ownership_prior_source_scope_composition'),('apply_known_project_pipe_erratum.py','project_known_erratum_formal_entry')]:
   r=impact(self.features,['build-cad-pipe-topology/scripts/'+name]);self.assertIn(fid,r['direct_features']);self.assertFalse(r['fallback_full_suites']);self.assertIn('visualize-cad-pipe-topology/scripts/test_builder.py',r['tests'])
  r=impact(self.features,['build-cad-pipe-topology/scripts/calibrated_ownership_scope_composition.py'])
  self.assertIn('build-cad-pipe-topology/scripts/test_correct_plan_crossover_lengths.py',r['tests']);self.assertIn('build-cad-pipe-topology/scripts/test_repair_calibrated_wave_omissions.py',r['tests'])
 def test_plan_dn_extents_reuse_historical_F_inheritance_and_viewer_regressions(self):
  for name in ('plan_pipe_diameter_scopes.py','native_line_f_diameter_evidence.py','fuse_plan_DN_scopes.py'):
   r=impact(self.features,['build-cad-pipe-topology/scripts/'+name]);self.assertIn('plan_DN_inheritance_and_extents',r['direct_features']);self.assertFalse(r['fallback_full_suites'])
   for path in ('build-cad-pipe-topology/scripts/test_dn_source_annotations.py','build-cad-pipe-topology/scripts/test_diameter_tee_inheritance.py','visualize-cad-pipe-topology/scripts/test_crossview_edge_attributes.mjs','orchestrate-cad-drawing-pipeline/scripts/test_plan_DN_scope_gate.py'):self.assertIn(path,r['tests'])
 def test_rotated_equipment_identity_keeps_native_preservation_and_entry_regressions(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/resolve_rotated_equipment_labels.py'])
  self.assertIn('rotated_equipment_caption_identity',r['direct_features']);self.assertFalse(r['fallback_full_suites'])
  for path in ('build-cad-pipe-topology/scripts/test_preserve_unidentified_equipment.py','orchestrate-cad-drawing-pipeline/scripts/test_rotated_equipment_identity_gate.py','visualize-cad-pipe-topology/scripts/test_rotated_identity_viewer.py'):self.assertIn(path,r['tests'])
 def test_plan_projection_and_batch_branch_inventory_are_registered(self):
  for changed,fid,test in [('build-cad-pipe-topology/scripts/native_plan_projection_lengths.py','crossview_plan_projection_attributes','visualize-cad-pipe-topology/scripts/test_crossview_edge_attributes.mjs'),('build-cad-pipe-topology/scripts/crossview_equipment_branch_inventory.py','crossview_equipment_branch_inventory','orchestrate-cad-drawing-pipeline/scripts/test_crossview_inventory_gate.py')]:
   r=impact(self.features,[changed]);self.assertIn(fid,r['direct_features']);self.assertIn(test,r['tests']);self.assertFalse(r['fallback_full_suites'])
 def test_confirmed_sideviews_include_old_length_and_stage_replay_tests(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/canonicalize_confirmed_sideviews.py'])
  self.assertIn('confirmed_sideview_canonicalization',r['direct_features']);self.assertFalse(r['fallback_full_suites'])
  self.assertIn('build-cad-pipe-topology/scripts/test_source_detail_branch_lengths.py',r['tests'])
  self.assertIn('orchestrate-cad-drawing-pipeline/scripts/test_confirmed_sideview_stage_gate.py',r['tests'])
 def test_new_source_screens_are_registered_without_full_fallback(self):
  for script,feature,test in [('correct_plan_crossover_lengths.py','plan_crossover_length_exclusion','test_correct_plan_crossover_lengths.py'),('inventory_route_dn_text.py','route_dn_text_inventory','test_inventory_route_dn_text.py'),('classify_device_anchor_spans.py','device_anchor_span_diagnostic','test_classify_device_anchor_spans.py'),('screen_equipment_datum_positions.py','equipment_datum_position_screen','test_screen_equipment_datum_positions.py')]:
   r=impact(self.features,['build-cad-pipe-topology/scripts/'+script]);self.assertIn(feature,r['direct_features']);self.assertIn('build-cad-pipe-topology/scripts/'+test,r['tests']);self.assertFalse(r['fallback_full_suites'])
 def test_recent_source_evidence_assets_trigger_their_tests(self):
  cases=[('build-cad-pipe-topology/scripts/audit_calibrated_joint_inventory.py','build-cad-pipe-topology/scripts/test_audit_calibrated_joint_inventory.py'),('build-cad-pipe-topology/scripts/reconcile_joint_inventory_contacts.py','build-cad-pipe-topology/scripts/test_reconcile_joint_inventory_contacts.py'),('build-cad-pipe-topology/scripts/screen_missing_gap_joints.py','build-cad-pipe-topology/scripts/test_screen_missing_gap_joints.py'),('build-cad-pipe-topology/scripts/audit_graph_id_reuse.py','build-cad-pipe-topology/scripts/test_audit_graph_id_reuse.py'),('build-cad-pipe-topology/scripts/source_detail_frame_links.py','build-cad-pipe-topology/scripts/test_source_detail_frame_links.py'),('build-cad-pipe-topology/scripts/detail_frame_relative_candidates.py','build-cad-pipe-topology/scripts/test_detail_frame_relative_candidates.py'),('build-cad-pipe-topology/scripts/detail_frame_boundary_candidates.py','build-cad-pipe-topology/scripts/test_detail_frame_boundary_candidates.py'),('visualize-cad-pipe-topology/scripts/gap_joint_viewer_evidence.py','visualize-cad-pipe-topology/scripts/test_gap_joint_viewer_evidence.py'),('visualize-cad-pipe-topology/scripts/near_tee_viewer_evidence.py','visualize-cad-pipe-topology/scripts/test_near_tee_viewer_evidence.py'),('visualize-cad-pipe-topology/scripts/equipment_label_source_annotations.py','visualize-cad-pipe-topology/scripts/test_equipment_label_source_annotations.py'),('visualize-cad-pipe-topology/assets/viewer/public/equipment-identity-candidates.js','visualize-cad-pipe-topology/scripts/test_equipment_identity_candidates.mjs')]
  for changed,test in cases:
   with self.subTest(changed=changed):
    r=impact(self.features,[changed]);self.assertFalse(r['fallback_full_suites']);self.assertIn(test,r['tests'])
  for changed,gate in [('build-cad-pipe-topology/scripts/screen_missing_gap_joints.py','test_missing_gap_joint_gate.py'),('build-cad-pipe-topology/scripts/source_detail_frame_links.py','test_detail_frame_context_gate.py')]:
   r=impact(self.features,[changed]);self.assertIn('orchestrate-cad-drawing-pipeline/scripts/'+gate,r['tests'])
 def test_shared_geometry_covers_existing_and_new_consumers(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/pipe_geometry.py'])
  self.assertIn('geometry',r['direct_features']);self.assertTrue({'equipment','source_lengths','overlaid_supply','viewer','pipeline'}<=set(r['impacted_features']))
  self.assertIn('build-cad-pipe-topology/scripts/test_hydraulic_projection.py',r['tests'])
  self.assertIn('visualize-cad-pipe-topology/scripts/test_system_boundaries.mjs',r['tests'])
  self.assertFalse(r['fallback_full_suites'])
 def test_local_dn_and_confirmed_interfaces_are_registered(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/attach_local_dn_observations.py']);self.assertIn('diameter_floor',r['direct_features']);self.assertIn('build-cad-pipe-topology/scripts/test_attach_local_dn_observations.py',r['tests']);self.assertFalse(r['fallback_full_suites'])
  r=impact(self.features,['build-cad-pipe-topology/scripts/confirmed_equipment_interfaces.py']);self.assertIn('equipment',r['direct_features']);self.assertIn('build-cad-pipe-topology/scripts/test_confirmed_equipment_interfaces.py',r['tests']);self.assertFalse(r['fallback_full_suites'])
 def test_diameter_candidate_and_viewer_assets_trigger_regression(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/infer_local_dn_candidates.py','visualize-cad-pipe-topology/assets/viewer/public/edge-attributes.js']);self.assertTrue({'diameter_floor','viewer'}<=set(r['direct_features']));self.assertIn('build-cad-pipe-topology/scripts/test_infer_local_dn_candidates.py',r['tests']);self.assertIn('visualize-cad-pipe-topology/scripts/test_edge_attributes.mjs',r['tests']);self.assertFalse(r['fallback_full_suites'])
 def test_diameter_change_includes_boundary_regression(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/diameter_tee_inheritance.py'])
  self.assertIn('riser_boundary',r['impacted_features'])
  self.assertIn('build-cad-pipe-topology/scripts/test_convert_expert_non_node_boundaries.py',r['tests'])
  self.assertIn('build-cad-pipe-topology/scripts/test_diameter_tee_inheritance.py',r['tests'])
 def test_boundary_change_includes_diameter_regression(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/convert_expert_non_node_boundaries.py'])
  self.assertIn('diameter_floor',r['impacted_features'])
  self.assertIn('build-cad-pipe-topology/scripts/test_diameter_tee_inheritance.py',r['tests'])
 def test_unknown_file_triggers_full_suites(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/new_unmapped_rule.py'])
  self.assertTrue(r['fallback_full_suites']);self.assertEqual(set(r['impacted_features']),set(self.features))
 def test_source_reviewed_circle_includes_historical_lengths(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/source_reviewed_circle_connections.py'])
  self.assertIn('source_reviewed_circle_connections',r['direct_features'])
  self.assertIn('build-cad-pipe-topology/scripts/test_expert_circle_connection.py',r['tests'])
  self.assertIn('build-cad-pipe-topology/scripts/test_source_reviewed_circle_connections.py',r['tests'])
  self.assertFalse(r['fallback_full_suites'])
 def test_unmapped_new_test_triggers_full_suites(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);scripts=root/'build-cad-pipe-topology'/'scripts';scripts.mkdir(parents=True)
   (scripts/'test_future_rule.py').write_text('',encoding='utf8')
   r=impact(self.features,['build-cad-pipe-topology/scripts/pipe_geometry.py'],root)
   self.assertTrue(r['fallback_full_suites']);self.assertIn('build-cad-pipe-topology/scripts/test_future_rule.py',r['unmapped_test_paths'])
 def test_expert_circle_change_includes_prior_regressions(self):
  r=impact(self.features,['build-cad-pipe-topology/scripts/confirmed_circle_junctions.py'])
  self.assertTrue({'confirmed_circles','overlaid_supply','tangent_pairs','composition'}<=set(r['impacted_features']))
  self.assertIn('build-cad-pipe-topology/scripts/test_proven_contacts.py',r['tests'])
 def test_bad_paths_and_dependency_cycles_fail(self):
  with self.assertRaises(ValueError):impact(self.features,['../other.py'])
  data=copy.deepcopy(self.data);data['features'][0]['depends_on']=['pipeline']
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'registry.json';path.write_text(json.dumps(data),encoding='utf8')
   with self.assertRaisesRegex(ValueError,'cycle'):load_registry(path,ROOT)
 def test_test_runner_executes_both_python_and_node(self):
  r=impact(self.features,['visualize-cad-pipe-topology/assets/viewer/public/app.js'])
  with patch('feature_impact.subprocess.run') as run:
   run.return_value.returncode=0;run.return_value.stdout='';run.return_value.stderr=''
   results=run_selected(r)
  cmds=[x['command'] for x in results]
  self.assertTrue(any('-m' in c and 'unittest' in c for c in cmds))
  self.assertTrue(any('--test' in c and any(x.endswith('.mjs') for x in c) for c in cmds))
 def test_unreadable_test_output_cannot_be_reported_as_pass(self):
  r=impact(self.features,['visualize-cad-pipe-topology/assets/viewer/public/app.js'])
  with patch('feature_impact.subprocess.run',side_effect=UnicodeDecodeError('utf-8',b'\xff',0,1,'bad')):
   results=run_selected(r)
  self.assertTrue(results);self.assertTrue(all(x['exit_code']!=0 for x in results))

if __name__=='__main__':unittest.main()
