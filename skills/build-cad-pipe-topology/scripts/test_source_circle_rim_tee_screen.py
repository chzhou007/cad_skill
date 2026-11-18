import copy,unittest,ezdxf
from source_circle_rim_tee_screen import scan
class SourceCircleScreen(unittest.TestCase):
 def fixture(self,circle_layer='空调冷冻水供水',branch_z=0):
  d=ezdxf.new('R2018');m=d.modelspace();circle=m.add_circle((0,0),80,dxfattribs={'layer':circle_layer});main=m.add_line((-500,0,0),(500,0,0),dxfattribs={'layer':'空调冷冻水供水'});branch=m.add_line((0,80,branch_z),(0,500,branch_z),dxfattribs={'layer':'空调冷冻水供水'});g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'U','node_type':'virtual_equipment','system':'supply','x':0,'y':80}],'edges':[{'edge_id':'M','system':'supply','start_node_id':'X','end_node_id':'Y','source_handles':[main.dxf.handle],'attribute_paths':[[[-500,0],[500,0]]]},{'edge_id':'B','system':'supply','start_node_id':'U','end_node_id':'V','source_handles':[branch.dxf.handle],'attribute_paths':[[[0,80],[0,500]]]}]};p={'source_sha256':'S','graph_sha256':'G','circle_radius':80,'z_tolerance':.05};return d,g,p,circle,main,branch
 def test_unique_source_shape_is_not_a_connection(self):
  d,g,p,c,m,b=self.fixture();old=copy.deepcopy(g);r=scan(d,g,p,'S','G');self.assertEqual(g,old);self.assertEqual(len(r['candidates']),1);x=r['candidates'][0];self.assertEqual(x['branch_graph_edges'],['B']);self.assertEqual(x['rim_virtual_nodes'],['U']);self.assertEqual(x['status'],'source_shape_graph_connection_not_established');self.assertFalse(r['hil_ready'])
 def test_layer_and_z_conflicts_are_preserved(self):
  d,g,p,c,m,b=self.fixture('空调冷冻水回水',3);x=scan(d,g,p,'S','G')['candidates'][0];self.assertFalse(x['circle_layer_matches_lines']);self.assertFalse(x['z_consistent_within_tolerance']);self.assertEqual(x['line_system'],'supply')
 def test_branch_at_interior_of_graph_path_is_reported_without_connection(self):
  d,g,p,c,m,b=self.fixture();g['edges'][1]['attribute_paths']=[[[0,0],[0,80],[0,500],[0,600]]];g['edges'][1]['start_node_id']='A';g['edges'][1]['end_node_id']='B'
  x=scan(d,g,p,'S','G')['candidates'][0];self.assertEqual(x['branch_graph_edges'],[]);self.assertEqual(x['branch_containing_rim_edges'],['B']);self.assertEqual(x['status'],'source_shape_graph_connection_not_established')
 def test_interior_crossing_is_not_rim_branch(self):
  d,g,p,c,m,b=self.fixture();b.dxf.start=(0,-500,0);b.dxf.end=(0,500,0);self.assertEqual(scan(d,g,p,'S','G')['candidates'],[])
 def test_out_of_plane_v_glyph_is_excluded(self):
  d,g,p,c,m,b=self.fixture();shape=[((0,0),(52.09458,114.14687)),((0,0),(114.14687,52.09458)),((34.72067,131.52078),(131.52078,34.72067)),((51.73687,148.53698),(148.53698,51.73687))]
  for a,z in shape:d.modelspace().add_line(a,z,dxfattribs={'layer':'空调立管、水平支管'})
  r=scan(d,g,p,'S','G');self.assertEqual(r['candidates'],[]);self.assertIn(c.dxf.handle,r['out_of_plane_glyph_suppressed'])
 def test_existing_tee_requires_both_main_halves_and_branch(self):
  d,g,p,c,m,b=self.fixture();g['nodes'].append({'node_id':'T','node_type':'tee','system':'supply','x':0,'y':0});g['edges'][1]['start_node_id']='T'
  self.assertEqual(scan(d,g,p,'S','G')['candidates'][0]['status'],'source_shape_graph_connection_not_established')
  g['edges'][0].update(end_node_id='T',attribute_paths=[[[-500,0],[0,0]]]);g['edges'].append({'edge_id':'M2','system':'supply','start_node_id':'T','end_node_id':'Y','source_handles':[m.dxf.handle],'attribute_paths':[[[0,0],[500,0]]]})
  self.assertEqual(scan(d,g,p,'S','G')['candidates'][0]['status'],'existing_graph_connection_unreviewed')
  g['edges'].append({'edge_id':'OTHER','system':'return','start_node_id':'T','end_node_id':'Z','source_handles':[],'attribute_paths':[[[0,0],[0,-5]]]});self.assertEqual(scan(d,g,p,'S','G')['candidates'][0]['status'],'source_shape_graph_connection_not_established')
 def test_existing_boundary_branch_with_rim_inside_path_is_recognized(self):
  d,g,p,c,m,b=self.fixture();g['nodes'].append({'node_id':'T','node_type':'tee','system':'supply','x':0,'y':0})
  g['edges'][0].update(end_node_id='T',attribute_paths=[[[-500,0],[0,0]]]);g['edges'].append({'edge_id':'M2','system':'supply','start_node_id':'T','end_node_id':'Y','source_handles':[m.dxf.handle],'attribute_paths':[[[0,0],[500,0]]]})
  g['edges'][1].update(start_node_id='T',end_node_id=None,attribute_paths=[[[0,0],[0,500]]]);x=scan(d,g,p,'S','G')['candidates'][0]
  self.assertEqual(x['branch_graph_edges'],[]);self.assertEqual(x['branch_containing_rim_edges'],['B']);self.assertEqual(x['status'],'existing_graph_connection_unreviewed')
  g['edges'][1]['start_node_id']='U';self.assertEqual(scan(d,g,p,'S','G')['candidates'][0]['status'],'source_shape_graph_connection_not_established')
 def test_duplicate_mains_report_ambiguity_and_stale_graph_fails(self):
  d,g,p,c,m,b=self.fixture();d.modelspace().add_line((-500,0),(500,0),dxfattribs={'layer':'空调冷冻水供水'});r=scan(d,g,p,'S','G');self.assertEqual(r['candidates'],[]);self.assertEqual(len(r['ambiguous_native_geometry']),1)
  with self.assertRaises(ValueError):scan(d,g,p,'S','other')
if __name__=='__main__':unittest.main()
