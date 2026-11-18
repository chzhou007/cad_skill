import copy,unittest
from source_downturn_terminals import reconcile

class DownturnTest(unittest.TestCase):
 def setUp(self):
  self.graph={'nodes':[{'node_id':'U1','node_type':'virtual_equipment','floor':'Roof','review_required':True,'ports':[{'port_id':'U1-P1'}]}, {'node_id':'T1','node_type':'tee'}],
              'edges':[{'edge_id':'E1','start_node_id':'U1','end_node_id':'T1','source_handles':['L1'],'system':'return'}]}
  self.ev={'source_sha256':'s','graph_sha256':'g','legend_sha256':'l','legend':{'text':'向下转弯','text_handle':'T','circle_handle':'C','line_handle':'L'},
           'total':1,'local_signature_pass':1,'records':[{'node_id':'U1','edge_id':'E1','circle_handle':'C1','source_layer':'water',
              'pipe_hits':[{'handle':'L1','endpoint_distances':[0,100]}],'other_same_layer_overlapping_entities':[],'matches_complete_local_legend_signature':True}]}
 def apply(self):return reconcile(self.graph,self.ev,'s','g','l')
 def test_role_only_and_nonmutation(self):
  old=copy.deepcopy(self.graph);out,report=self.apply();self.assertEqual(self.graph,old);self.assertEqual(out['edges'],old['edges']);self.assertEqual(out['nodes'][0]['ports'],old['nodes'][0]['ports']);self.assertFalse(out['nodes'][0]['remote_continuation_confirmed']);self.assertEqual(report['applied_count'],1)
 def test_stale_legend_or_existing_owner_rejected(self):
  with self.assertRaises(ValueError):reconcile(self.graph,self.ev,'s','g','different')
  self.graph['nodes'][0]['interface_destination']={'text':'existing'}
  with self.assertRaises(ValueError):self.apply()
 def test_competing_geometry_and_nonunique_adjacency_rejected(self):
  self.ev['records'][0]['other_same_layer_overlapping_entities']=['X']
  with self.assertRaises(ValueError):self.apply()
  self.ev['records'][0]['other_same_layer_overlapping_entities']=[];self.graph['edges'].append({'edge_id':'E2','start_node_id':'U1','end_node_id':'T1'})
  with self.assertRaises(ValueError):self.apply()
 def test_duplicate_and_wrong_source_line_rejected(self):
  self.ev['records'][0]['pipe_hits'][0]['handle']='wrong'
  with self.assertRaises(ValueError):self.apply()
  self.ev['records'][0]['pipe_hits'][0]['handle']='L1';self.ev['records'].append(copy.deepcopy(self.ev['records'][0]));self.ev['total']=2;self.ev['local_signature_pass']=2
  with self.assertRaises(ValueError):self.apply()
 def test_native_radius_not_a_global_25_unit_cutoff(self):
  self.ev['records'][0]['radius_native']=120
  with self.assertRaisesRegex(ValueError,'extend outside'):self.apply()
  self.ev['records'][0]['pipe_hits'][0]['endpoint_distances']=[0,150]
  out,_=self.apply();self.assertEqual(out['nodes'][0]['source_downturn_evidence']['radius_native'],120)

if __name__=='__main__':unittest.main()
