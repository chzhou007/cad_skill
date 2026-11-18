import copy,unittest,ezdxf
from crossview_route_diagnostics import compare,shortest

def fixture():
 p=ezdxf.new();q=ezdxf.new();b=p.blocks.new('EQ');b.add_line((0,0),(1,1));ins=p.modelspace().add_blockref('EQ',(0,0));pt=p.modelspace().add_text('CRAH-2');it=q.modelspace().add_text('CRAH-2')
 pg={'nodes':[{'node_id':'CRAH-2','node_type':'equipment','floor':2,'source_handle':ins.dxf.handle,'connection_status':'ports_unresolved'}],'edges':[]};ig={'nodes':[{'node_id':'CRAH-2','node_type':'equipment','floor':2},{'node_id':'T','node_type':'physical_junction'},{'node_id':'V','node_type':'physical_junction'}],'edges':[{'edge_id':'A','start_node_id':'V','end_node_id':'T','system':'supply'},{'edge_id':'B','start_node_id':'T','end_node_id':'CRAH-2','system':'supply','connection_mode':'unverified'}]};policy={'comparisons':[{'equipment_id':'CRAH-2','plan_text_handle':pt.dxf.handle,'iso_text_handle':it.dxf.handle,'isometric_routes':[{'anchor_edge':'A','anchor_endpoint':'T','system':'supply'}]}]};return p,q,pg,ig,policy
class CrossViewDiagnosticTest(unittest.TestCase):
 def test_paths_and_no_mapping(self):
  p,q,pg,ig,policy=fixture();before=copy.deepcopy((pg,ig));r=compare(p,q,pg,ig,policy);self.assertEqual((pg,ig),before);self.assertEqual(r['comparisons'][0]['isometric_routes'][0]['paths'],[['B']]);self.assertEqual(r['comparisons'][0]['plan_node_degree'],0);self.assertFalse(r['hil_ready'])
 def test_system_and_floor_mismatch_rejected(self):
  p,q,pg,ig,policy=fixture();policy['comparisons'][0]['isometric_routes'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'invalid anchor'):compare(p,q,pg,ig,policy)
  p,q,pg,ig,policy=fixture();ig['nodes'][0]['floor']=3
  with self.assertRaisesRegex(ValueError,'floor mismatch'):compare(p,q,pg,ig,policy)
 def test_duplicate_caption_rejected(self):
  p,q,pg,ig,policy=fixture();p.modelspace().add_text('CRAH-2')
  with self.assertRaisesRegex(ValueError,'not unique'):compare(p,q,pg,ig,policy)
 def test_equal_shortest_paths_report_ambiguity(self):
  p,q,pg,ig,policy=fixture();ig['edges'].append({'edge_id':'C','start_node_id':'T','end_node_id':'CRAH-2','system':'supply'});r=compare(p,q,pg,ig,policy);self.assertEqual(r['comparisons'][0]['isometric_routes'][0]['status'],'no_or_ambiguous_graph_path')
 def test_plan_route_uses_matching_system_and_preserves_boundary(self):
  p,q,pg,ig,policy=fixture();pg['nodes'] += [{'node_id':'R','node_type':'virtual_equipment','subtype':'out_of_plane_riser','system':'supply','floor':2},{'node_id':'T','node_type':'tee'}];pg['edges'] += [{'edge_id':'P1','start_node_id':'R','end_node_id':'T','system':'supply'},{'edge_id':'P2','start_node_id':'T','end_node_id':'CRAH-2','system':'supply','path_length_complete':False,'confirmed_equipment_interface':{'user':'yes'}}]
  policy['comparisons'][0]['plan_routes']=[{'start_node':'R','system':'supply'}];row=compare(p,q,pg,ig,policy)['comparisons'][0]['plan_routes'][0]
  self.assertEqual(row['paths'],[['P1','P2']]);self.assertTrue(row['edge_statuses'][0][1]['confirmed_interface']);self.assertFalse(row['edge_statuses'][0][1]['path_length_complete'])
  policy['comparisons'][0]['plan_routes'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'invalid plan riser'):compare(p,q,pg,ig,policy)
 def test_plan_route_stops_at_intermediate_equipment(self):
  p,q,pg,ig,policy=fixture();pg['nodes'] += [{'node_id':'R','node_type':'virtual_equipment','subtype':'out_of_plane_riser','system':'supply','floor':2},{'node_id':'OTHER','node_type':'equipment'}];pg['edges'] += [{'edge_id':'P1','start_node_id':'R','end_node_id':'OTHER','system':'supply'},{'edge_id':'P2','start_node_id':'OTHER','end_node_id':'CRAH-2','system':'supply'}];policy['comparisons'][0]['plan_routes']=[{'start_node':'R','system':'supply'}]
  self.assertEqual(compare(p,q,pg,ig,policy)['comparisons'][0]['plan_routes'][0]['paths'],[])
if __name__=='__main__':unittest.main()
