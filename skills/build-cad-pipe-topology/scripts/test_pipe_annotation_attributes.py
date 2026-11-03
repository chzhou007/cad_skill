import unittest,math
import ezdxf
from pipe_annotation_attributes import *

class AnnotationAttributes(unittest.TestCase):
 def setUp(self):pg.set_tolerance(.01)
 def scene(self,angle=0,mirror=False,bent=False):
  theta=math.radians(angle)
  def tf(p):
   x,y=p;x=-x if mirror else x
   return (math.cos(theta)*x-math.sin(theta)*y+500,math.sin(theta)*x+math.cos(theta)*y-700)
  d=ezdxf.new();m=d.modelspace()
  m.add_lwpolyline([tf(p)for p in [(0,30),(0,40),(20,40)]],dxfattribs={'layer':'A'})
  if bent:m.add_lwpolyline([tf(p)for p in [(-40,30),(20,30)]],dxfattribs={'layer':'A'});pipes=[[(-15,0),(-15,60)],[(-35,0),(-35,60)]]
  else:m.add_lwpolyline([tf(p)for p in [(0,0),(0,30),(20,30)]],dxfattribs={'layer':'A'});pipes=[[(-50,20),(50,20)],[(-50,0),(50,0)]]
  texts=[dict(id=str(i),handle=str(i),text=text,position=tf((2,y)),height=4,rotation=angle+(180 if mirror else 0),layer='A',source_id='fixture')for i,(text,y)in enumerate([('DN125',41),('DN250',31)])]
  segs=[dict(a=tf(a),b=tf(b),handle=str(i),system='physical',source_system='supply'if i==0 else'return')for i,(a,b)in enumerate(pipes)]
  edges=[dict(edge_id='E'+str(i),system=s['source_system'],source_handles=[s['handle']],attribute_paths=[[s['a'],s['b']]])for i,s in enumerate(segs)]
  return d,texts,segs,edges
 def test_straight_and_folded_rotation_mirror_order(self):
  for bent in [False,True]:
   for mirror in [False,True]:
    for angle in [0,37,90,180,270]:
     with self.subTest(bent=bent,mirror=mirror,angle=angle):
      r=recognize_f_leaders(*self.scene(angle,mirror,bent),['A']);self.assertEqual(len(r),1);self.assertEqual(r[0]['status'],'assigned');self.assertEqual([(v['nominal_mm'],v['edge_ids'])for v in r[0]['bindings']],[(125.,['E0']),(250.,['E1'])])
 def test_missing_text_remains_pending(self):
  d,t,s,e=self.scene();t=t[:1];self.assertEqual(recognize_f_leaders(d,t,s,e,['A'])[0]['status'],'pending')
 def test_no_second_crossing_never_filled_by_distance(self):
  d,t,s,e=self.scene();r=recognize_f_leaders(d,t,s[:1],e,['A']);self.assertEqual(r[0]['bindings'],[])
 def test_third_pipe_is_ambiguous(self):
  d,t,s,e=self.scene();s.append(dict(s[0],a=(450,-690),b=(550,-690),handle='third'));e.append(dict(e[0],edge_id='E2',source_handles=['third'],attribute_paths=[[s[-1]['a'],s[-1]['b']]]));self.assertEqual(recognize_f_leaders(d,t,s,e,['A'])[0]['status'],'pending')
 def test_ambiguous_junction_is_not_assigned(self):
  d,t,s,e=self.scene();e.append(dict(e[0],edge_id='E-extra'));self.assertEqual(recognize_f_leaders(d,t,s,e,['A'])[0]['status'],'pending')
 def test_floor_boundary_does_not_double_assign(self):
  b=dict(xmin=0,xmax=20,y=0,ymax=10);self.assertEqual(path_band_intervals([(0,10),(20,10)],b),[]);self.assertEqual(len(path_band_intervals([(5,-5),(5,15)],b)),1)
 def test_two_different_diameters_stay_ordered(self):
  r=recognize_f_leaders(*self.scene(37,True),['A']);self.assertNotEqual(r[0]['bindings'][0]['nominal_mm'],r[0]['bindings'][1]['nominal_mm'])
 def test_direct_label_below_pipe_and_no_cross_node_fill(self):
  t=dict(id='T',text='DN40',layer='A',rotation=0,position=[5,-1.8],height=1)
  edges=[dict(edge_id='E',attribute_paths=[[(0,0),(10,0)]]),dict(edge_id='OTHER',attribute_paths=[[(10,0),(20,0)]])]
  yes,no=direct_diameters([t],edges,set(),['A']);self.assertEqual(len(yes),1);self.assertEqual(yes[0]['edge_id'],'E')
 def test_parenthetical_elevation_does_not_change_the_nominal(self):
  t=dict(id='T',text='DN450(2.900)',layer='A',rotation=0,position=[5,-1.8],height=1)
  edges=[dict(edge_id='E',attribute_paths=[[(0,0),(10,0)]])]
  yes,no=direct_diameters([t],edges,set(),['A']);self.assertEqual(len(yes),1);self.assertEqual(yes[0]['nominal_mm'],450.)
 def test_ambiguous_parallel_direct_label_stays_pending(self):
  t=dict(id='T',text='DN40',layer='A',rotation=0,position=[5,1],height=1)
  edges=[dict(edge_id='E',attribute_paths=[[(0,0),(10,0)]]),dict(edge_id='OTHER',attribute_paths=[[(0,2),(10,2)]])]
  yes,no=direct_diameters([t],edges,set(),['A']);self.assertEqual(yes,[]);self.assertEqual(len(no),1)
 def test_three_F_above_is_three_below_is_two_and_stacked_panel_capped(self):
  d=ezdxf.new();m=d.modelspace()
  for y,label,left,right in [(0,'2F',0,20000),(10,'3F',0,20000),(20,'4F',0,20000),(-20,'机房层',10,19000)]:
   m.add_lwpolyline([(left,y),(right,y)],dxfattribs={'layer':'F'});m.add_text(label,dxfattribs={'layer':'F','height':1,'insert':(left+.1,y+.25)})
  bands=floor_bands(d,source_texts(d,'fixture','hash'),['F'],[[-1,-30,21000,40]])
  self.assertEqual([b['source_floor']for b in bands if b['xmin']==0 and b['y']<=11<b['ymax']],['3F'])
  self.assertEqual([b['source_floor']for b in bands if b['xmin']==0 and b['y']<=9<b['ymax']],['2F'])
  self.assertEqual(next(b for b in bands if b['source_floor']=='机房层')['ymax'],0)

if __name__=='__main__':unittest.main()
