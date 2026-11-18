import copy,unittest
from crossview_mapping_preflight import evaluate

class CrossViewPreflightTests(unittest.TestCase):
 def setUp(self):
  self.p={'metadata':{'source_sha256':'s'},'edges':[{'edge_id':'P1','system':'supply'},{'edge_id':'P2','system':'supply'},{'edge_id':'P3','system':'supply'}]};self.i={'edges':[{'edge_id':'I1','system':'supply'}]}
  self.d={'plan_graph_sha256':'pg','iso_graph_sha256':'ig','plan_source_sha256':'s','status':'diagnostic_only','comparisons':[{'equipment_id':'D','status':'crossview_diagnostic_not_mapping','plan_routes':[{'system':'supply','paths':[['P1']]}],'isometric_routes':[{'system':'supply','paths':[['I1']]}]}]};self.g={'graph_sha256':'pg','source_sha256':'s','status':'detail_correspondence_unresolved','mapping_ready':False,'records':[{'upper_edge':'P2','detail_edge':'P3'}]}
 def test_unaffected_route_is_still_unverified(self):
  before=copy.deepcopy((self.p,self.i,self.d,self.g));r=evaluate('pg','ig',self.p,self.i,self.d,self.g);self.assertFalse(r['mapping_ready']);self.assertEqual(r['records'][0]['unresolved_detail_edges'],[]);self.assertIn('plan_local_topology_not_verified',r['records'][0]['reasons']);self.assertEqual(before,(self.p,self.i,self.d,self.g))
 def test_intersection_is_localized(self):
  self.d['comparisons'][0]['plan_routes'][0]['paths']=[['P2']];r=evaluate('pg','ig',self.p,self.i,self.d,self.g);self.assertEqual(r['records'][0]['unresolved_detail_edges'],['P2']);self.assertIn('route_intersects_unresolved_main_detail_candidates',r['records'][0]['reasons'])
 def test_stale_and_missing_edges_fail(self):
  for ph,ih in [('bad','ig'),('pg','bad')]:
   with self.assertRaises(ValueError):evaluate(ph,ih,self.p,self.i,self.d,self.g)
  self.g['records'][0]['upper_edge']='missing'
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g)
 def test_wrong_system_and_unexpected_acceptance_fail(self):
  self.i['edges'][0]['system']='return'
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g)
  self.i['edges'][0]['system']='supply';self.g['mapping_ready']=True
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g)
 def test_source_geometry_evidence_does_not_accept_mapping(self):
  self.p['edges'][0].update(start_node_id='A',end_node_id='T');self.p['edges'][1].update(start_node_id='T',end_node_id='B');self.d['comparisons'][0]['plan_routes'][0]['paths']=[['P1','P2']]
  c={'source_sha256':'s','graph_sha256':'pg','hil_ready':False,'status':'partial_source_coverage_not_physical_length','edges':[{'edge_id':x,'system':'supply','segments':[{'status':'single_source_line_covers'}]} for x in ('P1','P2')]};j={'source_sha256':'s','graph_sha256':'pg','hil_ready':False,'status':'native_ray_evidence_unreviewed','junctions':[{'node_id':'T','system':'supply','status':'native_line_ray_evidence_not_accepted','source_rays':[{'edge_id':'P1'},{'edge_id':'P2'}]}]}
  r=evaluate('pg','ig',self.p,self.i,self.d,self.g,c,j);self.assertTrue(r['records'][0]['plan_source_path_evidence']['all_drawing_segments_covered']);self.assertTrue(r['records'][0]['plan_source_path_evidence']['junctions'][0]['source_ray_evidence']);self.assertFalse(r['mapping_ready'])
  c['graph_sha256']='old'
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g,c,j)
 def test_iso_partial_coverage_and_anchor_remain_unverified(self):
  self.d['iso_source_sha256']='is';self.i['edges'][0].update(start_node_id='T',end_node_id='D');self.i['edges'].append({'edge_id':'I2','system':'supply','start_node_id':'T','end_node_id':'R'});self.d['comparisons'][0]['isometric_routes'][0].update(anchor_edge='I2',anchor_endpoint='T')
  c={'source_sha256':'is','graph_sha256':'ig','hil_ready':False,'status':'partial_source_coverage_not_physical_length','edges':[{'edge_id':'I1','system':'supply','segments':[{'status':'no_witness_in_scoped_search'}]}]};j={'source_sha256':'is','graph_sha256':'ig','hil_ready':False,'status':'native_ray_evidence_unreviewed','junctions':[{'node_id':'T','system':'supply','status':'native_line_ray_evidence_not_accepted','source_rays':[{'edge_id':'I1'},{'edge_id':'I2'}]}]}
  r=evaluate('pg','ig',self.p,self.i,self.d,self.g,None,None,c,j);e=r['records'][1]['isometric_source_path_evidence'];self.assertFalse(e['all_drawing_segments_covered']);self.assertTrue(e['anchor']['source_ray_evidence']);self.assertFalse(r['mapping_ready'])
  dj={'source_sha256':'is','graph_sha256':'ig','hil_ready':False,'status':'native_exploded_device_joint_geometry_unreviewed','records':[{'edge_id':'I1','equipment_id':'D','system':'supply','joint_handle':'J','inner_line_handle':'L1','outer_line_handle':'L2','circle_handle':'C','status':'native_chain_geometry_unreviewed','physical_port_verified':False,'physical_length':'unknown'}]}
  r=evaluate('pg','ig',self.p,self.i,self.d,self.g,None,None,c,j,dj);self.assertEqual(r['records'][1]['isometric_device_joint_evidence'][0]['joint_handle'],'J');self.assertFalse(r['mapping_ready'])
  spans={'source_sha256':'is','graph_sha256':'ig','status':'source_witnessed_chain_and_unwitnessed_anchor_connector','hil_ready':False,'human_accepted':False,'graph_mutated':False,'records':[{'edge_id':'I1','equipment_id':'D','system':'supply','joint_handle':'J','status':'equipment_anchor_to_joint_is_unwitnessed_logical_connector','physical_port_verified':False,'connectivity_accepted':False,'physical_length':'unknown'}]}
  r=evaluate('pg','ig',self.p,self.i,self.d,self.g,None,None,c,j,dj,None,spans);self.assertEqual(r['records'][1]['isometric_anchor_span_evidence'][0]['edge_id'],'I1');self.assertFalse(r['mapping_ready']);self.assertFalse(r['records'][1]['isometric_source_path_evidence']['all_drawing_segments_covered'])
  spans['records'][0]['physical_length']=0
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g,None,None,c,j,dj,None,spans)
  dj['records'][0]['system']='return'
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g,None,None,c,j,dj)
  j['source_sha256']='old'
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g,None,None,c,j)
 def test_dn_difference_is_candidate_clue_on_both_routes(self):
  self.d['iso_source_sha256']='is';e={'plan_graph_sha256':'pg','iso_graph_sha256':'ig','plan_source_sha256':'s','iso_source_sha256':'is','status':'crossview_candidate_screen_not_mapping','hil_ready':False,'graph_mutated':False,'records':[{'plan_edge':'P1','iso_edge':'I1','system':'supply','plan_dn_candidate_mm':300,'iso_dn_candidate_mm':65,'iso_text_handle':'DN1','status':'different_values_potential_conflict','crossview_path_mapping':'not_confirmed','annotation_binding':'candidate_not_accepted','physical_diameter_selected':False}]}
  r=evaluate('pg','ig',self.p,self.i,self.d,self.g,dn_evidence=e);self.assertEqual(r['unmatched_dn_candidate_count'],0)
  for row in r['records']:self.assertIn('crossview_dn_candidate_conflict_unresolved',row['reasons']);self.assertFalse(row['mapping_ready']);self.assertEqual(row['crossview_dn_candidates'][0]['iso_dn_candidate_mm'],65)
  e['iso_graph_sha256']='stale'
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g,dn_evidence=e)
 def test_unrelated_dn_pair_is_not_attached_to_route(self):
  self.d['iso_source_sha256']='is';e={'plan_graph_sha256':'pg','iso_graph_sha256':'ig','plan_source_sha256':'s','iso_source_sha256':'is','status':'crossview_candidate_screen_not_mapping','hil_ready':False,'graph_mutated':False,'records':[{'plan_edge':'P2','iso_edge':'I1','system':'supply','plan_dn_candidate_mm':300,'iso_dn_candidate_mm':65,'iso_text_handle':'DN1','status':'different_values_potential_conflict','crossview_path_mapping':'not_confirmed','annotation_binding':'candidate_not_accepted','physical_diameter_selected':False}]}
  r=evaluate('pg','ig',self.p,self.i,self.d,self.g,dn_evidence=e);self.assertEqual(r['unmatched_dn_candidate_count'],1);self.assertTrue(all('crossview_dn_candidates' not in x for x in r['records']))
  e['records'][0]['plan_edge']='missing'
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g,dn_evidence=e)
 def test_datum_disagreement_is_pending_without_relabeling(self):
  self.d['iso_source_sha256']='is';self.i['nodes']=[{'node_id':'D','floor':2}]
  screen={'source_sha256':'is','graph_sha256':'ig','status':'drawing_anchor_datum_comparison_not_floor_assignment','hil_ready':False,'human_accepted':False,'graph_mutated':False,'records':[{'equipment_id':'D','graph_floor_label':2,'drawing_anchor_band_floor':1,'status':'anchor_band_differs_from_graph_label','physical_floor_verified':False}]}
  r=evaluate('pg','ig',self.p,self.i,self.d,self.g,iso_equipment_datum_screen=screen);self.assertIn('equipment_drawing_anchor_datum_interpretation_unresolved',r['records'][1]['reasons']);self.assertFalse(r['mapping_ready']);self.assertEqual(self.i['nodes'][0]['floor'],2)
  screen['records'][0]['physical_floor_verified']=True
  with self.assertRaises(ValueError):evaluate('pg','ig',self.p,self.i,self.d,self.g,iso_equipment_datum_screen=screen)
if __name__=='__main__':unittest.main()
