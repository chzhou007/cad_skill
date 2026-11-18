import copy,unittest
from compare_named_boundary_routes import compare
class NamedBoundaryRouteTest(unittest.TestCase):
 def setUp(self):
  self.p={'metadata':{'source_sha256':'PS'},'nodes':[{'node_id':'A','system':'supply','boundary_type':'unresolved_source_terminal'},{'node_id':'B','system':'supply','boundary_type':'unresolved_source_terminal'},{'node_id':'T','node_type':'tee'}],'edges':[{'edge_id':'P1','system':'supply','start_node_id':'A','end_node_id':'T'},{'edge_id':'P2','system':'supply','start_node_id':'T','end_node_id':'B'}]}
  self.a={'nodes':[{'node_id':'V','node_type':'virtual_equipment','ports':[{'port_id':'V1','system':'supply'},{'port_id':'V2','system':'supply'}]},{'node_id':'X','node_type':'tee'},{'node_id':'Y','node_type':'tee'}],'edges':[{'edge_id':'A1','system':'supply','start_node_id':'V','end_node_id':'X','start_port_id':'V1'},{'edge_id':'A2','system':'supply','start_node_id':'V','end_node_id':'Y','start_port_id':'V2'},{'edge_id':'A3','system':'supply','start_node_id':'X','end_node_id':'Y'}]}
  self.s={'status':'scoped_leader_candidates_not_binding','graph_sha256':'PG','source_sha256':'PS','mapping_ready':False,'selections':[{'node_id':'A','system':'supply','label':{'original_text':'CHWS1 DN450'}},{'node_id':'B','system':'supply','label':{'original_text':'CHWS2 DN450'}}]};self.e={'status':'source_geometry_witnesses_crossview_not_accepted','axis_graph_sha256':'AG','axis_source_sha256':'AS','mapping_ready':False,'pairs':[{'source_label':{'original_text':'CHWS1 DN450'},'axis':{'port_id':'V1','edge_id':'A1'}},{'source_label':{'original_text':'CHWS2 DN450'},'axis':{'port_id':'V2','edge_id':'A2'}}]};self.pol={'plan_graph_sha256':'PG','axis_graph_sha256':'AG','plan_source_sha256':'PS','axis_source_sha256':'AS','comparisons':[{'system':'supply','ends':[{'plan_node':'A','axis_port':'V1','axis_edge':'A1','axis_node':'V'},{'plan_node':'B','axis_port':'V2','axis_edge':'A2','axis_node':'V'}]}]}
 def run_compare(self):return compare(self.p,self.a,self.s,self.e,self.pol,'PG','AG','PS','AS')
 def test_paths_exclude_shared_virtual_node(self):
  out=self.run_compare();self.assertFalse(out['mapping_ready']);self.assertEqual(out['comparisons'][0]['plan_shortest_paths'],[['P1','P2']]);self.assertEqual(out['comparisons'][0]['axis_shortest_paths_excluding_anchor_edges'],[['A3']])
 def test_wrong_label_or_port_fails(self):
  self.e['pairs'][0]['source_label']['original_text']='CHWR1 DN450'
  with self.assertRaises(ValueError):self.run_compare()
  self.e['pairs'][0]['source_label']['original_text']='CHWS1 DN450';self.a['nodes'][0]['ports'][0]['system']='return'
  with self.assertRaises(ValueError):self.run_compare()
 def test_disconnected_axis_not_invented(self):
  self.a['edges'].pop();self.assertEqual(self.run_compare()['comparisons'][0]['axis_shortest_paths_excluding_anchor_edges'],[])
if __name__=='__main__':unittest.main()
