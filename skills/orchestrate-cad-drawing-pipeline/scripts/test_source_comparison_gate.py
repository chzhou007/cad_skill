import unittest,tempfile,hashlib,json
from pathlib import Path
from source_comparison_gate import check,segment_dn_withheld_blockers,bulk_dn_screen_blockers

class BulkDNGate(unittest.TestCase):
 def test_pattern_annotations_keep_every_blocker_and_reject_tampering(self):
  import importlib.util
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts';script=owner/'group_ambiguous_dn_patterns.py'
   spec=importlib.util.spec_from_file_location('patterns_test',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
   rows=[{'text_handle':h,'text':'DN80','status':'ambiguous_source_lines','height':350,'rotation_degrees':0,'native_line_candidates':[{'system':'supply','provenance':{'scope':'modelspace'},'distance_drawing_units':10},{'system':'return','provenance':{'scope':'modelspace'},'distance_drawing_units':20}]} for h in ('A','B')]
   data={'script_sha256':sha(owner/'source_dn_bulk_screen.py'),'text_guard_sha256':sha(owner/'native_dn_text_position.py'),'status':'native_dn_bulk_screen_candidates_only','source_sha256':'S','graph_sha256':'G','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':rows,'summary':{'ambiguous_source_lines':2},'nested_scope':{'failed_roots':[]}}
   screen=root/'source_dn_bulk_screen_final.json';screen.write_text(json.dumps(data),encoding='utf8');pattern=root/'source_dn_ambiguity_patterns_final.json'
   report=module.group(data,{'groups':[{'text_handles':['A','B']}]});report.update(script_sha256=sha(script),source_sha256='S',graph_sha256='G',bulk_screen_sha256=sha(screen),policy_sha256='P');pattern.write_text(json.dumps(report),encoding='utf8')
   receipt={'final_graph_sha256':'G','final_bulk_dn_sha256':sha(screen),'final_dn_pattern_sha256':sha(pattern),'final_dn_pattern_policy_sha256':'P','inputs':{'dxf':'S'}};rp=root/'rebuild-receipt.json';rp.write_text(json.dumps(receipt),encoding='utf8')
   blockers=bulk_dn_screen_blockers(root,'G');self.assertEqual([x['source_text_handle'] for x in blockers],['A','B']);self.assertEqual([x['ambiguity_pattern'] for x in blockers],[1,1])
   report['groups'][0]['selected_owner']='supply';pattern.write_text(json.dumps(report),encoding='utf8');receipt['final_dn_pattern_sha256']=sha(pattern);rp.write_text(json.dumps(receipt),encoding='utf8')
   with self.assertRaisesRegex(ValueError,'do not match'):bulk_dn_screen_blockers(root,'G')
   pattern.unlink()
   with self.assertRaisesRegex(ValueError,'missing'):bulk_dn_screen_blockers(root,'G')
 def test_ambiguous_and_unmatched_not_silent_and_tampering_fails(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
   extractor=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts/source_dn_bulk_screen.py'
   rows=[{'text_handle':'A','text':'DN450','status':'ambiguous_source_lines'},{'text_handle':'B','text':'DN80','status':'no_source_line_in_local_scope'},{'text_handle':'C','text':'DN200','status':'unique_source_line_and_graph_segment_candidate'}]
   data={'script_sha256':sha(extractor),'text_guard_sha256':sha(extractor.with_name('native_dn_text_position.py')),'status':'native_dn_bulk_screen_candidates_only','source_sha256':'S','graph_sha256':'G','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':rows,'summary':{x['status']:1 for x in rows},'nested_scope':{'failed_roots':[]}}
   screen=root/'source_dn_bulk_screen_final.json';receipt=root/'rebuild-receipt.json'
   def write():
    screen.write_text(json.dumps(data),encoding='utf8');receipt.write_text(json.dumps({'final_graph_sha256':'G','final_bulk_dn_sha256':sha(screen),'inputs':{'dxf':'S'}}),encoding='utf8')
   write();self.assertEqual({r['source_text_handle'] for r in bulk_dn_screen_blockers(root,'G')},{'A','B'})
   data['text_guard_sha256']='stale';write()
   with self.assertRaisesRegex(ValueError,'stale'):bulk_dn_screen_blockers(root,'G')
   data['text_guard_sha256']=sha(extractor.with_name('native_dn_text_position.py'))
   data['summary']['ambiguous_source_lines']=0;write()
   with self.assertRaisesRegex(ValueError,'count mismatch'):bulk_dn_screen_blockers(root,'G')
   screen.unlink()
   with self.assertRaisesRegex(ValueError,'missing'):bulk_dn_screen_blockers(root,'G')
 def test_detail_scope_groups_without_suppressing_pending(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
   rows=[{'text_handle':h,'text':'DN80','status':'no_source_line_in_local_scope'} for h in ('A','B')]
   data={'script_sha256':sha(owner/'source_dn_bulk_screen.py'),'text_guard_sha256':sha(owner/'native_dn_text_position.py'),'status':'native_dn_bulk_screen_candidates_only','source_sha256':'S','graph_sha256':'G','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':rows,'summary':{'no_source_line_in_local_scope':2},'nested_scope':{'failed_roots':[]}}
   screen=root/'source_dn_bulk_screen_final.json';screen.write_text(json.dumps(data),encoding='utf8');detail=root/'source_dn_detail_scope_final.json'
   scope={'script_sha256':sha(owner/'isometric_detail_dn_scope.py'),'legacy_geometry_sha256':sha(owner/'legacy_v17/analyze_graph.py'),'status':'excluded_scope_not_main_assignment','source_sha256':'S','graph_sha256':'G','bulk_screen_sha256':sha(screen),'graph_mutated':False,'detail_mapping_ready':False,'hil_ready':False,'records':[{'text_handle':h,'text':'DN80','status':'excluded_left_scope_detail_correspondence_pending'} for h in ('A','B')]};detail.write_text(json.dumps(scope),encoding='utf8')
   receipt={'final_graph_sha256':'G','final_bulk_dn_sha256':sha(screen),'final_dn_detail_scope_sha256':sha(detail),'inputs':{'dxf':'S'}};(root/'rebuild-receipt.json').write_text(json.dumps(receipt),encoding='utf8')
   blockers=bulk_dn_screen_blockers(root,'G');self.assertEqual(len(blockers),1);self.assertEqual(blockers[0]['source_text_handles'],['A','B']);self.assertEqual(blockers[0]['status'],'excluded_detail_scope_correspondence_pending')
   scope['records'][1].update(scope_id='right',status='excluded_right_scope_detail_correspondence_pending');detail.write_text(json.dumps(scope),encoding='utf8');receipt['final_dn_detail_scope_sha256']=sha(detail);(root/'rebuild-receipt.json').write_text(json.dumps(receipt),encoding='utf8');self.assertEqual(len(bulk_dn_screen_blockers(root,'G')),2)
   detail.unlink()
   with self.assertRaisesRegex(ValueError,'missing'):bulk_dn_screen_blockers(root,'G')

class SegmentDNWithheldGate(unittest.TestCase):
 def test_withheld_and_stale_extractor_fail_closed(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
   graph=root/'graph_with_edges.json';graph.write_text('{}',encoding='utf8');line=root/'native_line_path_evidence.json';line.write_text('{}',encoding='utf8')
   extractor=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts/native_segment_dn_candidates.py'
   stage={'script_sha256':sha(extractor),'text_guard_sha256':sha(extractor.with_name('native_dn_text_position.py')),'status':'segment_candidates_not_accepted','graph_mutated':False,'hil_ready':False,'graph_sha256':sha(graph),'line_evidence_sha256':sha(line),'source_sha256':'S','policy_sha256':'P','withheld_observations':[{'status':'withheld_not_attributed','source_text':{'source_sha256':'S','handle':'H','text':'DN450'},'reason':'competing source'}]}
   receipt={'inputs':{'dxf':'S','segment-dn-policy':'P'},'final_graph_sha256':'FINAL'}
   (root/'native_segment_dn_candidates.json').write_text(json.dumps(stage),encoding='utf8');(root/'rebuild-receipt.json').write_text(json.dumps(receipt),encoding='utf8')
   self.assertEqual(segment_dn_withheld_blockers(root,'FINAL')[0]['source_text_handle'],'H')
   stage['script_sha256']='stale';(root/'native_segment_dn_candidates.json').write_text(json.dumps(stage),encoding='utf8')
   with self.assertRaisesRegex(ValueError,'stale'):segment_dn_withheld_blockers(root,'FINAL')
   stage['script_sha256']=sha(extractor);del stage['withheld_observations'];(root/'native_segment_dn_candidates.json').write_text(json.dumps(stage),encoding='utf8')
   with self.assertRaisesRegex(ValueError,'stale'):segment_dn_withheld_blockers(root,'FINAL')
   (root/'native_segment_dn_candidates.json').unlink()
   with self.assertRaisesRegex(ValueError,'missing'):segment_dn_withheld_blockers(root,'FINAL')

class GateTests(unittest.TestCase):
 def test_graph_detail_alternative_blocks_even_when_receipt_says_resolved(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); evidence=root/'native.png';evidence.write_bytes(b'evidence')
   gp=root/'graph_with_edges.json'
   graph={'nodes':[],'edges':[],'sourceDetailComparison':{'expert_issue':'ERR-15B0E8','status':'candidate_mapping_equipment_and_boundaries_pending'}}
   def run():
    gp.write_text(json.dumps(graph),encoding='utf8');h=hashlib.sha256(gp.read_bytes()).hexdigest()
    report={'graph_sha256':h,'rounds_completed':1,'families':[{'id':'detail','status':'resolved','source_handles':['H'],'disposition':'claimed resolved'}],'native_comparisons':[{'path':evidence.name,'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}]}
    return check(report,h,root,gp)
   result=run();self.assertEqual(result['status'],'pending');self.assertFalse(result['hil_ready']);self.assertEqual(result['source_detail_comparison_blockers'][0]['expert_issue'],'ERR-15B0E8')
   graph['sourceDetailComparison']={};self.assertEqual(run()['status'],'pending')
   graph['sourceDetailComparison']='invalid';self.assertEqual(run()['status'],'failed')
   del graph['sourceDetailComparison'];self.assertTrue(run()['hil_ready'])
 def test_current_graph_evidence_must_match_internal_graph_hash(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); p=root/'audit.json'; p.write_text(json.dumps({'graph_sha256':'OLD'}),encoding='utf8')
   item={'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'binding':'current_graph'}
   report={'graph_sha256':'NEW','rounds_completed':1,'families':[{'id':'x','status':'resolved','source_handles':['H'],'disposition':'checked'}],'native_comparisons':[item]}
   self.assertEqual(check(report,'NEW',root)['status'],'failed')
   item['binding']='historical';self.assertTrue(check(report,'NEW',root)['hil_ready'])
   item['binding']='current_graph';p.write_text(json.dumps({'graph_sha256':'NEW'}),encoding='utf8');item['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
   self.assertTrue(check(report,'NEW',root)['hil_ready'])
   p.write_text('not json',encoding='utf8');item['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
   self.assertEqual(check(report,'NEW',root)['status'],'failed')
 def test_missing_and_stale_comparison_cannot_pass(self):
  r=check({},'G',Path('.'));self.assertFalse(r['hil_ready']);self.assertEqual(r['status'],'failed')
 def test_family_blockers_and_exact_evidence_hash(self):
  with tempfile.TemporaryDirectory()as t:
   p=Path(t)/'native.png';p.write_bytes(b'native evidence fixture')
   r={'graph_sha256':'G','rounds_completed':1,'families':[{'id':'circle','status':'algorithm_pending','source_handles':['C'],'disposition':'calibration pending'}],'native_comparisons':[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
   self.assertEqual(check(r,'G',t)['status'],'pending')
   r['families'][0]['status']='resolved';self.assertTrue(check(r,'G',t)['hil_ready'])
   p.write_bytes(b'changed');self.assertEqual(check(r,'G',t)['status'],'failed')
 def test_graph_source_port_blockers_override_resolved_report(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); p=root/'native.png';p.write_bytes(b'evidence')
   graph={'nodes':[{'node_id':'tower','node_type':'equipment','source_port_completeness':'unbound_source_contacts_require_comparison','source_port_candidates':[{'status':'source_mark_candidate_not_bound'}]},{'node_id':'virtual','node_type':'virtual_equipment','source_port_completeness':'unbound_source_contacts_require_comparison'}], 'edges':[]}
   gp=root/'graph_with_edges.json';gp.write_text(json.dumps(graph),encoding='utf8');h=hashlib.sha256(gp.read_bytes()).hexdigest()
   r={'graph_sha256':h,'rounds_completed':1,'families':[{'id':'tower','status':'resolved','source_handles':['C'],'disposition':'claimed resolved'}], 'native_comparisons':[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
   result=check(r,h,root);self.assertFalse(result['hil_ready']);self.assertEqual([x['node_id'] for x in result['equipment_source_port_blockers']],['tower'])
   graph['nodes'][0]['source_port_completeness']='local_contacts_proven_all_expected_ports_unconfirmed';graph['nodes'][0]['source_port_candidates']=[]
   gp.write_text(json.dumps(graph),encoding='utf8');newh=hashlib.sha256(gp.read_bytes()).hexdigest();r['graph_sha256']=newh
   self.assertTrue(check(r,newh,root)['hil_ready'])
   self.assertEqual(check(r,h,root)['status'],'failed')
 def test_graph_unresolved_nodes_and_families_override_resolved_report(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); evidence=root/'native.png';evidence.write_bytes(b'evidence')
   graph={'nodes':[{'node_id':'U1','node_type':'virtual_equipment','boundary_type':'unresolved_source_terminal'}, {'node_id':'U2','node_type':'virtual_equipment','resolution_state':'local_symbol_form_equipment_overlap_pending'}, {'node_id':'U3','node_type':'virtual_equipment','resolution_state':'local_symbol_identified_remote_continuation_not_shown'}], 'edges':[], 'preHilComparison':{'families':[{'id':'repeated-error','status':'algorithm_pending'}]}}
   gp=root/'graph_with_edges.json';gp.write_text(json.dumps(graph),encoding='utf8');h=hashlib.sha256(gp.read_bytes()).hexdigest()
   report={'graph_sha256':h,'rounds_completed':1,'families':[{'id':'fixture','status':'resolved','source_handles':['C'],'disposition':'claimed resolved'}], 'native_comparisons':[{'path':evidence.name,'sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}], 'unclassified_terminal_count':0,'algorithm_blockers':[]}
   result=check(report,h,root,gp);self.assertEqual(result['status'],'pending');self.assertEqual([x['node_id'] for x in result['graph_unresolved_node_blockers']],['U1','U2']);self.assertEqual(result['graph_algorithm_family_blockers'],['repeated-error'])
   graph['nodes']=graph['nodes'][2:];graph['preHilComparison']['families'][0]['status']='source_ambiguity';gp.write_text(json.dumps(graph),encoding='utf8');h=hashlib.sha256(gp.read_bytes()).hexdigest();report['graph_sha256']=h
   self.assertTrue(check(report,h,root,gp)['hil_ready'])
 def test_source_declared_route_remains_pending(self):
  from source_comparison_gate import graph_comparison_blockers
  nodes=[{'node_id':'U','boundary_type':'source_declared_connection_interface','resolution_state':'source_declared_connection_route_pending'}]
  unresolved,_=graph_comparison_blockers({'nodes':nodes});self.assertEqual([n['node_id'] for n in unresolved],['U'])
 def test_unmapped_reference_components_remain_blocked(self):
  from source_comparison_gate import reference_component_blockers
  graph={'sourceInlineEndpointGroups':[{'group_id':'G','source_provenance':{'reference_insert_handle':'H','individual_primary_proxy_identity':'not_established'}},{'group_id':'K','source_provenance':{'individual_primary_proxy_identity':'verified'}}]}
  self.assertEqual(reference_component_blockers(graph),[{'group_id':'G','reference_insert_handle':'H'}])
 def test_unbound_candidate_blocks_even_if_completeness_claims_otherwise(self):
  from source_comparison_gate import equipment_comparison_blockers
  nodes=[{'node_id':'a','node_type':'equipment','source_port_completeness':'complete','source_port_candidates':[{'status':'source_mark_candidate_not_bound'}]}, {'node_id':'b','node_type':'equipment','source_port_candidates':[{'status':'bound'}]}]
  self.assertEqual([x['node_id'] for x in equipment_comparison_blockers({'nodes':nodes})],['a'])
class CircleRimGate(unittest.TestCase):
 def test_pending_shapes_override_resolved_receipt_and_stale_evidence_fails(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);gp=root/'graph.json';gp.write_text(json.dumps({'metadata':{'source_sha256':'SRC'},'nodes':[],'edges':[]}),encoding='utf8');h=hashlib.sha256(gp.read_bytes()).hexdigest();ep=root/'circles.json';e={'graph_sha256':h,'source_sha256':'SRC','status':'source_shape_comparison_not_connectivity','candidates':[{'circle_handle':'C','line_system':'supply','status':'source_shape_graph_connection_not_established'}],'ambiguous_native_geometry':[],'unsupported_circle_transforms':[]};ep.write_text(json.dumps(e),encoding='utf8');item={'path':ep.name,'sha256':hashlib.sha256(ep.read_bytes()).hexdigest(),'binding':'current_graph','kind':'source_circle_rim_screen'};r={'graph_sha256':h,'rounds_completed':1,'families':[{'id':'circle','status':'resolved','source_handles':['C'],'disposition':'claimed resolved'}],'native_comparisons':[item]};result=check(r,h,root,gp);self.assertEqual(result['status'],'pending');self.assertEqual(result['circle_rim_screen_blockers'][0]['circle_handle'],'C')
   e['candidates'][0]['status']='existing_graph_connection_unreviewed';ep.write_text(json.dumps(e),encoding='utf8');item['sha256']=hashlib.sha256(ep.read_bytes()).hexdigest();self.assertTrue(check(r,h,root,gp)['hil_ready'])
   e['source_sha256']='wrong';ep.write_text(json.dumps(e),encoding='utf8');item['sha256']=hashlib.sha256(ep.read_bytes()).hexdigest();self.assertEqual(check(r,h,root,gp)['status'],'failed')
   item['binding']='historical';self.assertEqual(check(r,h,root,gp)['status'],'failed')
 def test_pipeline_screen_is_consumed_even_if_receipt_omits_it(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);gp=root/'graph.json';gp.write_text(json.dumps({'metadata':{'source_sha256':'SRC'},'nodes':[],'edges':[]}),encoding='utf8');h=hashlib.sha256(gp.read_bytes()).hexdigest();rd=root/'reports';rd.mkdir();ep=rd/'source-circle-rim-screen.json';ep.write_text(json.dumps({'graph_sha256':h,'source_sha256':'SRC','status':'source_shape_comparison_not_connectivity','candidates':[{'circle_handle':'C','line_system':'return','status':'source_shape_graph_connection_not_established'}],'ambiguous_native_geometry':[],'unsupported_circle_transforms':[]}),encoding='utf8');stage=rd/'source-circle-rim-screen-stage.json';stage.write_text(json.dumps({'graph_sha256':h,'evidence_sha256':hashlib.sha256(ep.read_bytes()).hexdigest()}),encoding='utf8');other=root/'native.png';other.write_bytes(b'source');report={'graph_sha256':h,'rounds_completed':1,'families':[{'id':'x','status':'resolved','source_handles':['C'],'disposition':'claimed done'}],'native_comparisons':[{'path':other.name,'sha256':hashlib.sha256(other.read_bytes()).hexdigest()}]};result=check(report,h,root,gp);self.assertEqual(result['status'],'pending');self.assertEqual(result['circle_rim_screen_blockers'][0]['circle_handle'],'C')
   stage.unlink();self.assertEqual(check(report,h,root,gp)['status'],'failed')
class NearEndpointScreenGate(unittest.TestCase):
 def test_automatic_screen_blocks_and_stale_stage_fails(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);gp=root/'graph.json';gp.write_text(json.dumps({'metadata':{'source_sha256':'SRC'},'nodes':[],'edges':[]}),encoding='utf8');h=hashlib.sha256(gp.read_bytes()).hexdigest();rd=root/'reports';rd.mkdir();ep=rd/'near-endpoint-crossing-screen.json';stage=rd/'near-endpoint-crossing-screen-stage.json';other=root/'source.png';other.write_bytes(b'source')
   row={'source_branch_handle':'B','source_main_handle':'M','endpoint_node_id':'U','system':'supply','status':'near_endpoint_crossing_candidate_not_connection'};e={'graph_sha256':h,'source_sha256':'SRC','status':'source_near_endpoint_crossings_not_connections','graph_mutated':False,'hil_ready':False,'counts':{'candidates':1},'candidates':[row]}
   report={'graph_sha256':h,'rounds_completed':1,'families':[{'id':'x','status':'resolved','source_handles':['B'],'disposition':'claimed done'}],'native_comparisons':[{'path':other.name,'sha256':hashlib.sha256(other.read_bytes()).hexdigest()}]}
   def write():
    ep.write_text(json.dumps(e),encoding='utf8');stage.write_text(json.dumps({'graph_sha256':h,'source_sha256':'SRC','candidate_count':len(e['candidates']),'evidence_sha256':hashlib.sha256(ep.read_bytes()).hexdigest()}),encoding='utf8')
   write();r=check(report,h,root,gp);self.assertEqual(r['status'],'pending');self.assertTrue(any('near-endpoint crossings' in x for x in r['pending']))
   e['candidates']=[];e['counts']['candidates']=0;write();self.assertTrue(check(report,h,root,gp)['hil_ready'])
   stage.unlink();self.assertEqual(check(report,h,root,gp)['status'],'failed')
class NamedEndpointLeaderGate(unittest.TestCase):
 def test_candidate_blocks_and_stale_or_forged_receipt_fails(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);gp=root/'graph.json';gp.write_text(json.dumps({'metadata':{'source_sha256':'SRC'},'nodes':[{'node_id':'U','node_type':'virtual_equipment','system':'supply','source_handles':['P']}],'edges':[]}),encoding='utf8');h=hashlib.sha256(gp.read_bytes()).hexdigest();rd=root/'reports';rd.mkdir();ep=rd/'named-endpoint-leader-screen.json';stage=rd/'named-endpoint-leader-screen-stage.json';other=root/'source.png';other.write_bytes(b'source')
   row={'node_id':'U','pipe_handle':'P','leader_handle':'L','text_handle':'T','system':'supply','status':'source_geometry_candidate_not_binding'};e={'graph_sha256':h,'source_sha256':'SRC','status':'scoped_leader_candidates_not_binding','graph_mutated':False,'mapping_ready':False,'hil_ready':False,'selections':[row]};report={'graph_sha256':h,'rounds_completed':1,'families':[{'id':'x','status':'resolved','source_handles':['P'],'disposition':'claimed done'}],'native_comparisons':[{'path':other.name,'sha256':hashlib.sha256(other.read_bytes()).hexdigest()}]}
   def write():
    ep.write_text(json.dumps(e),encoding='utf8');stage.write_text(json.dumps({'graph_sha256':h,'source_sha256':'SRC','candidate_count':len(e['selections']),'evidence_sha256':hashlib.sha256(ep.read_bytes()).hexdigest(),'hil_ready':False}),encoding='utf8')
   write();r=check(report,h,root,gp);self.assertEqual(r['status'],'pending');self.assertTrue(any('named endpoint leader' in x for x in r['pending']))
   e['selections'][0]['pipe_handle']='wrong';write();self.assertEqual(check(report,h,root,gp)['status'],'failed')
   e['selections'][0]['pipe_handle']='P';write();stage.unlink();self.assertEqual(check(report,h,root,gp)['status'],'failed')
class EquipmentDatumScreenGate(unittest.TestCase):
 def test_partial_screen_blocks_unscreened_equipment(self):
  from source_comparison_gate import equipment_datum_screen_blockers
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);graph={'nodes':[{'node_id':'D','node_type':'equipment','floor':2,'x':5,'y':9},{'node_id':'OTHER','node_type':'equipment','floor':2,'x':6,'y':9}]};row={'equipment_id':'D','graph_floor_label':2,'anchor':[5,9],'status':'anchor_band_matches_graph_label','physical_floor_verified':False};e={'graph_sha256':'g','source_sha256':'s','status':'drawing_anchor_datum_comparison_not_floor_assignment','policy_sha256':'p','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':[row],'eligible_equipment_count':2,'unscreened_equipment_ids':['OTHER'],'scope_complete':False};p=root/'equipment_datum_position_screen_final.json';p.write_text(json.dumps(e),encoding='utf8');(root/'equipment_datum_position_screen_stage.json').write_text(json.dumps({'graph_sha256':'g','source_sha256':'s','evidence_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'candidate_count':1,'hil_ready':False,'status':'screened_floor_interpretation_pending','policy_sha256':'p'}),encoding='utf8');self.assertEqual(equipment_datum_screen_blockers(root,'g',graph),[{'equipment_id':'OTHER','status':'equipment_not_in_datum_screen'}])
 def test_screen_cannot_be_silently_accepted_or_reused_on_changed_graph(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);gp=root/'graph.json';graph={'nodes':[{'node_id':'D','node_type':'equipment','floor':2,'x':5,'y':9}],'edges':[]};gp.write_text(json.dumps(graph),encoding='utf8');h=hashlib.sha256(gp.read_bytes()).hexdigest();other=root/'source.png';other.write_bytes(b'source');ep=root/'equipment_datum_position_screen_final.json';stage=root/'equipment_datum_position_screen_stage.json'
   row={'equipment_id':'D','graph_floor_label':2,'anchor':[5,9],'status':'anchor_band_differs_from_graph_label','physical_floor_verified':False,'anchor_x_within_claimed_native_baseline':True};e={'graph_sha256':h,'source_sha256':'SRC','status':'drawing_anchor_datum_comparison_not_floor_assignment','policy_sha256':'p','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':[row],'eligible_equipment_count':1,'unscreened_equipment_ids':[],'scope_complete':True};report={'graph_sha256':h,'rounds_completed':1,'families':[{'id':'fixture','status':'resolved','source_handles':['A'],'disposition':'claimed done'}],'native_comparisons':[{'path':other.name,'sha256':hashlib.sha256(other.read_bytes()).hexdigest()}]}
   def write():
    ep.write_text(json.dumps(e),encoding='utf8');stage.write_text(json.dumps({'graph_sha256':h,'source_sha256':'SRC','evidence_sha256':hashlib.sha256(ep.read_bytes()).hexdigest(),'candidate_count':sum(x['status']!='anchor_band_matches_graph_label' for x in e['records']),'hil_ready':False,'policy_sha256':'p','status':'screened_floor_interpretation_pending' if any(x['status']!='anchor_band_matches_graph_label' for x in e['records']) else 'screened_not_physical_floor_confirmation'}),encoding='utf8')
   write();result=check(report,h,root,gp);self.assertEqual(result['status'],'pending');self.assertEqual(result['equipment_datum_screen_blockers'][0]['equipment_id'],'D')
   e['interpretation_families']=[{'id':'DATUM-IN-SPAN','member_equipment_ids':['D'],'unresolved_equipment_ids':['D'],'numeric_match_control_ids':[],'status':'technical_anchor_interpretation_not_expert_errors','physical_floor_verified':False,'human_accepted':False}]
   write();grouped=check(report,h,root,gp);self.assertEqual(grouped['status'],'pending');self.assertEqual(grouped['equipment_datum_screen_blockers'][0]['interpretation_family'],'DATUM-IN-SPAN')
   e['interpretation_families'][0]['unresolved_equipment_ids']=[];write();self.assertEqual(check(report,h,root,gp)['status'],'failed');del e['interpretation_families']
   e['records'][0]['anchor']=[6,9];write();self.assertEqual(check(report,h,root,gp)['status'],'failed')
   e['records'][0]['anchor']=[5,9];e['records'][0]['status']='anchor_band_matches_graph_label';write();self.assertTrue(check(report,h,root,gp)['hil_ready']);e['unscreened_equipment_ids']=['fake'];write();self.assertEqual(check(report,h,root,gp)['status'],'failed');stage.unlink();self.assertEqual(check(report,h,root,gp)['status'],'failed')
class ComparisonHistoryGate(unittest.TestCase):
 def test_wrapped_old_pending_families_remain_blockers(self):
  from source_comparison_gate import graph_comparison_blockers
  graph={'nodes':[],'preHilComparison':{'status':'pending','previous_comparison':{'families':[{'id':'old-shape','status':'algorithm_pending'}]}}};_,families=graph_comparison_blockers(graph);self.assertIn('source_comparison_status:pending',families);self.assertIn('old-shape',families)
  graph['preHilComparison']['status']='resolved';_,families=graph_comparison_blockers(graph);self.assertEqual(families,['old-shape'])
 def test_invalid_or_cyclic_history_cannot_pass(self):
  from source_comparison_gate import graph_comparison_blockers
  x={'status':'pending'};x['previous_comparison']=x
  with self.assertRaises(ValueError):graph_comparison_blockers({'nodes':[],'preHilComparison':x})
  with self.assertRaises(ValueError):graph_comparison_blockers({'nodes':[],'preHilComparison':{'families':'invalid'}})
if __name__=='__main__':unittest.main()
