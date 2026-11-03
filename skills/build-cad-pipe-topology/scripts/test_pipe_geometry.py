"""Regression cases for source crossover semantics, including real SH16 sheet03."""
import unittest,math,json,sys
from pathlib import Path
import pipe_geometry as g
class CrossoverContract(unittest.TestCase):
 def setUp(self):g.set_tolerance(.5)
 def seg(self,a,b,sy='supply',h='X'):return {'a':a,'b':b,'system':sy,'handle':h}
 def fixture(self):
  a={'a':(-100.,0.),'b':(100.,0.),'radius':100.,'span':180.,'system':'supply','handle':'ARC'}
  return a,[self.seg((-300.,0.),(-100.,0.),h='LEFT'),self.seg((100.,0.),(300.,0.),h='RIGHT')]
 def test_standard_jump_continues_owner_without_elevation(self):
  a,t=self.fixture();cross=self.seg((0,-300),(0,300),'return','CROSS');n,status=g.normalize_arc(a,t+[cross],t);self.assertEqual(status,'normalized');self.assertEqual(n['relative_elevation'],'unknown');self.assertEqual(n['crossing_connectivity'],'independent_pipes_no_junction')
  vs,ps,adj=g.build_network(t+[cross,n]);self.assertFalse(any(g.dist(p,(0,0))<.5 for p in vs));self.assertEqual(sum(g.dist(vs[p['vertices'][0]],vs[p['vertices'][1]])for p in ps if p['system']=='supply'),600)
 def test_same_system_crossing_with_real_branch_keeps_independent_channels(self):
  a,t=self.fixture();cross=self.seg((0,-300),(0,300),h='CROSS');branch=self.seg((0,0),(150,150),h='BRANCH');n,status=g.normalize_arc(a,t+[cross,branch],t);self.assertEqual(status,'normalized');vs,ps,ad=g.build_network(t+[cross,branch,n]);idx=next(i for i,p in enumerate(vs)if g.dist(p,(0,0))<.5);self.assertEqual(len(ad[('supply',idx)]),3)
  cp=next(p for p in ps if p['normalization']=='semicircular_crossover_chord');self.assertNotIn(idx,cp['vertices'])
 def test_split_crossed_native_pipe_is_still_continuous(self):
  a,t=self.fixture();c=[self.seg((0,-300),(0,0),'return','C1'),self.seg((0,0),(0,300),'return','C2')];n,st=g.normalize_arc(a,t+c,t);self.assertEqual(st,'normalized');self.assertEqual(n['crossings'][0]['crossing_evidence'],'opposite_collinear_native_pipe_rays')
 def test_one_unconnected_terminal_is_not_crossing_witness(self):
  a,t=self.fixture();n,st=g.normalize_arc(a,t+[self.seg((0,0),(0,300),'return','C')],t);self.assertIsNone(n)
 def test_no_crossing_does_not_straighten_arbitrary_arc(self):
  a,t=self.fixture();self.assertIsNone(g.normalize_arc(a,t,t)[0])
 def test_true_quarter_bend_not_straightened(self):
  a,t=self.fixture();a['span']=90;self.assertIsNone(g.normalize_arc(a,t+[self.seg((0,-300),(0,300))],t)[0])
 def test_inward_tail_rejected(self):
  a,t=self.fixture();t[0]=self.seg((-100,0),(0,0));self.assertIsNone(g.normalize_arc(a,t+[self.seg((0,-300),(0,300))],t)[0])
 def test_wrong_system_tail_rejected(self):
  a,t=self.fixture();t[0]['system']='return';self.assertIsNone(g.normalize_arc(a,t+[self.seg((0,-300),(0,300))],t)[0])
 def test_rotation_translation_and_reflection_do_not_change_connectivity(self):
  a,t=self.fixture();c=self.seg((0,-300),(0,300),'return','C');ang=.37
  def rot(p):return (2000000+p[0]*math.cos(ang)-p[1]*math.sin(ang),300000-p[0]*math.sin(ang)-p[1]*math.cos(ang))
  a.update(a=rot(a['a']),b=rot(a['b']));t=[dict(s,a=rot(s['a']),b=rot(s['b']))for s in t];c=dict(c,a=rot(c['a']),b=rot(c['b']));n,st=g.normalize_arc(a,t+[c],t);self.assertEqual(st,'normalized');self.assertEqual(n['relative_elevation'],'unknown')
 def test_bulge_retains_parent_entity_provenance(self):
  import ezdxf
  d=ezdxf.new();e=d.modelspace().add_lwpolyline([(-100,0,1),(100,0,0)],format='xyb');c=g.curve_candidates(e,'supply');self.assertEqual(len(c),1);self.assertEqual(c[0]['source_entity_handle'],e.dxf.handle);self.assertAlmostEqual(c[0]['span'],180);a,t=self.fixture();n,st=g.normalize_arc(c[0],t+[self.seg((0,-300),(0,300),'return','C')],t);self.assertEqual(st,'normalized');self.assertEqual(n['source_handles'],[e.dxf.handle])
 def test_original_same_system_T_is_preserved(self):
  vs,ps,ad=g.build_network([self.seg((-300,0),(300,0)),self.seg((0,0),(0,300),h='B')]);self.assertTrue(any(len(v)==3 for v in ad.values()))
 def test_all_seven_actual_chws_arcs_with_qualified_bs_witness(self):
  import ezdxf
  # Actual sheet03 is an optional local integration fixture; synthetic cases above are portable.
  p=Path('E:/codex/CAD/output/SH16-11tasks-v1/sources/DXF/03-冷冻水系统原理图.dxf')
  if not p.exists():self.skipTest('Local sheet03 fixture not installed; run source-profile integration separately')
  d=ezdxf.readfile(p);layers={'HVAC-D-CHWS':'supply','HVAC-D-CHWR':'return','HVAC-D-CWS':'cooling_water','HVAC-D-BS':'qualified_auxiliary_witness'};segs=[self.seg(g.xy(e.dxf.start),g.xy(e.dxf.end),layers[e.dxf.layer],e.dxf.handle)for e in d.modelspace().query('LINE')if e.dxf.layer in layers];arcs=[a for e in d.modelspace().query('ARC')if e.dxf.layer=='HVAC-D-CHWS'for a in g.curve_candidates(e,'supply')];self.assertEqual(len(arcs),7)
  for a in arcs:
   n,st=g.normalize_arc(a,segs,segs);self.assertEqual(st,'normalized',a['handle']);self.assertEqual(n['relative_elevation'],'unknown')
if __name__=='__main__':unittest.main(verbosity=2)
