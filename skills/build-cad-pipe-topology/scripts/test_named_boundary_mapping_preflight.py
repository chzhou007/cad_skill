import unittest
from named_boundary_mapping_preflight import preflight,localize_candidate
from test_compare_named_boundary_routes import NamedBoundaryRouteTest
class BoundaryPreflightTest(unittest.TestCase):
 def setUp(self):
  f=NamedBoundaryRouteTest();f.setUp();self.p=f.p;self.a=f.a;self.a['edges'][0].update(path_length_complete=False,physical_length='unknown');self.a['edges'][1].update(path_length_complete=False,physical_length='unknown');self.r=f.run_compare();self.r.update(plan_graph_sha256='PG',axis_graph_sha256='AG',plan_source_sha256='PS',axis_source_sha256='AS');self.n={'status':'source_near_endpoint_crossings_not_connections','source_sha256':'PS','graph_sha256':'PG','graph_mutated':False,'hil_ready':False,'counts':{'candidates':1},'candidates':[{'status':'near_endpoint_crossing_candidate_not_connection','system':'supply','source_branch_handle':'B','source_main_handle':'M','endpoint_node_id':'U','main_edge_ids':['P1']}]};self.ns={'source_sha256':'PS','graph_sha256':'PG','evidence_sha256':'NH','candidate_count':1,'hil_ready':False};self.l={'status':'partial_source_lengths_physical_unknown','source_sha256':'AS','output_graph_sha256':'AG','hil_ready':False,'review_inherited':False,'edges':[{'edge_id':'A1'},{'edge_id':'A2'}]};self.d={'source_sha256':'AS','graph_sha256':'AG','status':'drawing_anchor_datum_comparison_not_floor_assignment','hil_ready':False,'human_accepted':False,'graph_mutated':False,'records':[],'unscreened_equipment_ids':[]};self.receipt={'inputs':{'dxf':'AS'},'final_graph_sha256':'AG','hil_ready':False}
 def go(self):return preflight(self.p,self.a,self.r,self.n,self.ns,self.l,self.d,self.receipt,'PG','AG','NH')
 def test_intersecting_pending_blocks(self):
  r=self.go();self.assertFalse(r['mapping_ready']);self.assertEqual(len(r['records'][0]['plan_near_endpoint_candidates']),1);self.assertIn('plan_route_intersects_near_endpoint_candidates',r['records'][0]['reasons'])
 def test_axis_gap_joint_is_localized_and_stale_evidence_rejected(self):
  screen={'status':'missing_source_joints_candidate_screen','source_sha256':'AS','graph_sha256':'IG','policy_sha256':'P','script_sha256':'S','graph_mutated':False,'hil_ready':False,'records':[{'edge_id':'A1','system':'supply','insert_handle':'H','status':'source_calibrated_joint_unassigned_pending_review','physical_length':'unknown','human_accepted':False}]}
  stage={'status':'missing_joint_candidates_pending_source_comparison','source_sha256':'AS','final_graph_sha256':'AG','evidence_sha256':'EH','input_graph_sha256':'IG','policy_sha256':'P','script_sha256':'S','human_accepted':False,'hil_ready':False,'candidate_count':1,'candidate_handles':['H']}
  result=preflight(self.p,self.a,self.r,self.n,self.ns,self.l,self.d,self.receipt,'PG','AG','NH',None,(screen,stage,'EH'))
  self.assertEqual(result['records'][0]['axis_gap_joint_candidates'][0]['source_handle'],'H');self.assertIn('axis_route_contains_unassigned_joint_candidates',result['records'][0]['reasons']);self.assertFalse(result['mapping_ready'])
  stage['final_graph_sha256']='stale'
  with self.assertRaisesRegex(ValueError,'stale axis gap'):preflight(self.p,self.a,self.r,self.n,self.ns,self.l,self.d,self.receipt,'PG','AG','NH',None,(screen,stage,'EH'))
 def test_applied_tee_is_still_a_route_blocker(self):
  self.p['nodes'].append({'node_id':'C','node_type':'virtual_equipment'});self.p['edges'].append({'edge_id':'P3','system':'supply','start_node_id':'T','end_node_id':'C'})
  applied={'status':'applied_near_tees_pending_review','source_sha256':'PS','graph_sha256':'PG','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':[{'node_id':'T','system':'supply','branch_handle':'B','main_handle':'M','incident_edge_ids':['P1','P2','P3'],'status':'source_normalized_tee_not_human_accepted'}]}
  r=preflight(self.p,self.a,self.r,self.n,self.ns,self.l,self.d,self.receipt,'PG','AG','NH',applied);self.assertIn('plan_route_crosses_unreviewed_normalized_tee',r['records'][0]['reasons']);self.assertEqual(r['records'][0]['plan_unreviewed_normalized_tees'][0]['node_id'],'T')
  applied['records'][0]['incident_edge_ids']=['P1','P2']
  with self.assertRaisesRegex(ValueError,'invalid applied'):preflight(self.p,self.a,self.r,self.n,self.ns,self.l,self.d,self.receipt,'PG','AG','NH',applied)
 def test_crossing_localizes_to_actual_segment_and_fails_safe(self):
  edges={'A':{'system':'supply','source_handles':['M'],'attribute_paths':[[[0,0],[10,0]]]},'B':{'system':'supply','source_handles':['M'],'attribute_paths':[[[10,0],[20,0]]]}}
  candidate={'system':'supply','source_main_handle':'M','main_edge_ids':['A','B'],'crossing':[5,0]};self.assertEqual(localize_candidate(candidate,edges),({'A'},'crossing_on_graph_path'))
  candidate['crossing']=[10,0];self.assertEqual(localize_candidate(candidate,edges),({'A','B'},'crossing_on_graph_path'))
  candidate['crossing']=[50,0];self.assertEqual(localize_candidate(candidate,edges),({'A','B'},'localization_unresolved'))
 def test_stale_and_promoted_evidence_fail(self):
  self.ns['evidence_sha256']='wrong'
  with self.assertRaises(ValueError):self.go()
  self.ns['evidence_sha256']='NH';self.a['edges'][0]['physical_length']=0
  with self.assertRaises(ValueError):self.go()
 def test_edited_route_fails(self):
  self.r['comparisons'][0]['axis_shortest_paths_excluding_anchor_edges']=[]
  with self.assertRaises(ValueError):self.go()
 def test_unidentified_equipment_reported_without_claiming_route_incidence(self):
  self.p['nodes'].append({'node_id':'EQ-SOURCE-1','node_type':'equipment','identity_status':'unresolved'})
  result=self.go()
  self.assertEqual(result['plan_global_unidentified_equipment_ids'],['EQ-SOURCE-1'])
  self.assertFalse(result['mapping_ready'])
  self.assertNotIn('plan_route_intersects_unidentified_equipment',result['records'][0]['reasons'])
 def test_pair_labels_remain_global_and_stale_axis_is_rejected(self):
  self.p['nodes'].append({'node_id':'EQ','node_type':'equipment','identity_status':'unresolved','source_label_candidates':['CRAH-1','CRAH-2'],'source_label_pair_evidence':{'plan_source_sha256':'PS','axis_source_sha256':'AS','axis_graph_sha256':'AG','group_id':'P','identity_confirmed':False,'alternatives':[{'label':'CRAH-1'},{'label':'CRAH-2'}]}})
  result=self.go();self.assertEqual(result['plan_global_equipment_pair_candidates'][0]['candidate_labels'],['CRAH-1','CRAH-2']);self.assertFalse(result['mapping_ready']);self.assertNotIn('plan_route_intersects_unidentified_equipment',result['records'][0]['reasons'])
  self.p['nodes'][-1]['source_label_pair_evidence']['axis_graph_sha256']='old'
  with self.assertRaisesRegex(ValueError,'equipment pair'):self.go()
 def test_local_dn_is_reported_without_promoting_edge_value(self):
  edge=next(e for e in self.p['edges'] if e['edge_id']=='P1')
  edge['pipe_diameter']={'status':'local_source_observation_edgewide_unverified','nominal_mm':None,'display':'DN80（标注处；整边待核）','observations':[{'text':{'handle':'D'}}]}
  result=self.go();self.assertEqual(result['records'][0]['plan_local_dn_observations'][0]['edge_id'],'P1')
  self.assertFalse(result['mapping_ready'])
  edge['pipe_diameter']['nominal_mm']=80
  with self.assertRaisesRegex(ValueError,'invalid local DN'):self.go()
 def test_refreshed_pair_screen_rebinds_evidence_without_accepting_identity(self):
  alternatives=[{'label':'L1','plan_text_handle':'P1','axis_text_handle':'A1'},{'label':'L2','plan_text_handle':'P2','axis_text_handle':'A2'}]
  for nid in ('X','Y'):
   self.p['nodes'].append({'node_id':nid,'node_type':'equipment','identity_status':'unresolved','source_label_candidates':['L1','L2'],'source_label_pair_evidence':{'plan_source_sha256':'PS','axis_source_sha256':'AS','axis_graph_sha256':'old','group_id':'G','identity_confirmed':False,'alternatives':alternatives}})
  def a(n,l,p,h):return {'plan_node_id':n,'label':l,'plan_text_handle':p,'axis_text_handle':h}
  screen={'status':'equipment_label_pair_candidates_not_mapping','plan_graph_sha256':'PG','axis_graph_sha256':'AG','plan_source_sha256':'PS','axis_source_sha256':'AS','graph_mutated':False,'mapping_ready':False,'human_accepted':False,'hil_ready':False,'groups':[{'group_id':'G','selected_candidate':None,'status':'pair_identity_not_confirmed','candidates':[{'assignments':[a('X','L1','P1','A1'),a('Y','L2','P2','A2')]},{'assignments':[a('X','L2','P2','A2'),a('Y','L1','P1','A1')]}]}]}
  def run():return preflight(self.p,self.a,self.r,self.n,self.ns,self.l,self.d,self.receipt,'PG','AG','NH',None,None,screen)
  result=run();self.assertEqual(len(result['plan_global_equipment_pair_candidates']),2);self.assertFalse(result['mapping_ready'])
  screen['groups'][0]['candidates'][1]['assignments'][0]['axis_text_handle']='wrong'
  with self.assertRaises(ValueError):run()
 def test_evidence_only_axis_attachment_preserves_old_length_audit(self):
  self.l['output_graph_sha256']='before';attachment={'status':'partial_line_evidence_attached_not_accepted','source_sha256':'AS','input_graph_sha256':'before','output_graph_sha256':'AG','connectivity_changed':False,'physical_length_changed':False,'review_inherited':False,'hil_ready':False}
  result=preflight(self.p,self.a,self.r,self.n,self.ns,self.l,self.d,self.receipt,'PG','AG','NH',None,None,None,attachment);self.assertFalse(result['mapping_ready'])
  attachment['connectivity_changed']=True
  with self.assertRaisesRegex(ValueError,'axis attribute attachment'):preflight(self.p,self.a,self.r,self.n,self.ns,self.l,self.d,self.receipt,'PG','AG','NH',None,None,None,attachment)
 def test_datum_extent_groups_are_pending_and_do_not_claim_floor_error(self):
  self.d['records']=[{'equipment_id':'OUT','status':'below_first_known_datum','graph_floor_label':1,'drawing_anchor_band_floor':None,'anchor_x_within_claimed_native_baseline':False},{'equipment_id':'IN','status':'anchor_band_differs_from_graph_label','graph_floor_label':2,'drawing_anchor_band_floor':1,'anchor_x_within_claimed_native_baseline':True},{'equipment_id':'UNKNOWN','status':'on_datum','anchor_x_within_claimed_native_baseline':None},{'equipment_id':'OK','status':'anchor_band_matches_graph_label'}];self.d['unscreened_equipment_ids']=['UNSCREENED']
  r=self.go();groups=r['axis_datum_pending_by_extent'];self.assertEqual(r['axis_datum_global_pending_count'],4);self.assertEqual(groups['outside_claimed_baseline_extent'][0]['equipment_id'],'OUT');self.assertEqual(groups['inside_claimed_baseline_extent'][0]['equipment_id'],'IN');self.assertEqual(groups['extent_unknown'][0]['equipment_id'],'UNKNOWN');self.assertEqual(groups['unscreened'],['UNSCREENED']);self.assertFalse(groups['inside_claimed_baseline_extent'][0]['physical_floor_verified']);self.assertFalse(r['mapping_ready'])
if __name__=='__main__':unittest.main()
