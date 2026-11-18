import unittest,ezdxf
from near_offset_circle_candidates import scan
class NearOffsetCircleTest(unittest.TestCase):
 def fixture(self):
  d=ezdxf.new();m=d.modelspace();c=m.add_circle((0,0),100,dxfattribs={'layer':'空调冷冻水供水'});a=m.add_line((-500,-1),(500,-1),dxfattribs={'layer':'空调冷冻水回水'});b=m.add_line((0,100),(0,500),dxfattribs={'layer':'空调冷冻水回水'});g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'U','node_type':'virtual_equipment','system':'return','x':0,'y':100}],'edges':[{'edge_id':'M','system':'return','source_handles':[a.dxf.handle],'attribute_paths':[[[-500,-1],[500,-1]]]},{'edge_id':'B','system':'return','source_handles':[b.dxf.handle],'attribute_paths':[[[0,100],[0,500]]]}]};p={'source_sha256':'S','graph_sha256':'G','circle_radius':100,'max_main_offset':2};return d,g,p,c,a,b
 def test_offset_is_candidate_not_connectivity(self):
  d,g,p,c,a,b=self.fixture();r=scan(d,g,p,'S','G');self.assertEqual(len(r['candidates']),1);x=r['candidates'][0];self.assertEqual(x['main_offset_drawing_units'],1);self.assertEqual(x['branch_graph_edges'],['B']);self.assertEqual(x['rim_virtual_nodes'],['U']);self.assertFalse(r['human_accepted'])
 def test_exact_and_too_far_are_not_this_candidate(self):
  d,g,p,c,a,b=self.fixture();a.dxf.start=(-500,0);a.dxf.end=(500,0);self.assertEqual(scan(d,g,p,'S','G')['candidates'],[]);a.dxf.start=(-500,-3);a.dxf.end=(500,-3);self.assertEqual(scan(d,g,p,'S','G')['candidates'],[])
 def test_competing_main_or_other_system_stays_ambiguous(self):
  d,g,p,c,a,b=self.fixture();d.modelspace().add_line((-500,-1.5),(500,-1.5),dxfattribs={'layer':'空调冷冻水回水'});r=scan(d,g,p,'S','G');self.assertEqual(r['candidates'],[]);self.assertEqual(len(r['ambiguous_native_geometry']),1)
  with self.assertRaises(ValueError):scan(d,g,p,'S','stale')
if __name__=='__main__':unittest.main()
