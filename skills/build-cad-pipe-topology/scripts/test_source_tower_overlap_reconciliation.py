import copy,unittest
from source_tower_overlap_reconciliation import reconcile

class TowerOverlapTest(unittest.TestCase):
 def setUp(self):
  self.g={'nodes':[{'node_id':'T','node_type':'equipment','source_ports':[],'ports':[]},{'node_id':'D','node_type':'virtual_equipment','boundary_type':'source_native_downturn_terminal','source_downturn_evidence':{'circle_handle':'C'}},{'node_id':'A','node_type':'virtual_equipment'},{'node_id':'B','node_type':'virtual_equipment'}],
          'edges':[{'edge_id':'E0','start_node_id':'D','end_node_id':'X','system':'cooling_supply'},{'edge_id':'E1','start_node_id':'A','end_node_id':'B','system':'cooling_return'}]}
  self.o={'source_sha256':'s','graph_sha256':'g','records':[{'system':'cooling_supply','node_id':'D','tower_id':'T','edge_id':'E0','source_circle':'C','nearby_equipment_circle_candidates':[{'handle':'H','distance':3.7}],'native_equipment_circle_matches':[],'nearest_equipment_circle_center_distance':3.7}]}
  self.p={'source_sha256':'s','graph_sha256':'g','records':[{'tower_id':'T','node_id':n,'edge_id':'E1','native_circle_matches':[{'handle':h,'distance':.03}]}for n,h in [('A','P1'),('B','P2')]]}
 def apply(self):return reconcile(self.g,self.o,self.p,'s','g')
 def test_candidates_do_not_create_links_or_ports(self):
  original=copy.deepcopy(self.g);out,report=self.apply();self.assertEqual(self.g,original);self.assertEqual(out['edges'],original['edges']);self.assertEqual(out['nodes'][0]['ports'],[]);self.assertEqual(len(out['nodes'][0]['source_port_candidates']),2);self.assertTrue(out['nodes'][1]['review_required']);self.assertEqual(report['physical_ports_inferred'],0)
 def test_stale_or_competing_evidence_fails(self):
  self.p['graph_sha256']='stale'
  with self.assertRaises(ValueError):self.apply()
  self.p['graph_sha256']='g';self.p['records'][1]['node_id']='A'
  with self.assertRaises(ValueError):self.apply()
 def test_nearby_is_not_a_connection_tolerance(self):
  self.o['records'][0]['nearby_equipment_circle_candidates'][0]['distance']=4.1
  with self.assertRaises(ValueError):self.apply()

if __name__=='__main__':unittest.main()
