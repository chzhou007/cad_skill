import unittest,ezdxf
from instrumentation import box_contact,exploded_bowties,symbol_pipe_contacts,source_reference_regions,measurement_assemblies,source_gauges
from straight_crossovers import recover_straight_crossovers
from pipe_geometry import build_network,set_tolerance
class MeasurementContracts(unittest.TestCase):
 def test_boundary_aligned_pipe_intersects_symbol(self):self.assertTrue(box_contact((0,-20),(0,20),(0,-2,5,2)))
 def test_remote_pipe_does_not_contact_symbol(self):self.assertFalse(box_contact((-10,-20),(-10,20),(0,-2,5,2)))
 def bowtie(self,missing=False,rect=False):
  d=ezdxf.new();m=d.modelspace();rows=[((0,-5),(0,5)),((10,-5),(10,5)),((0,-5),(10,5)),((0,5),(10,-5))]
  if rect:rows=rows[:2]+[((0,-5),(10,-5)),((0,5),(10,5))]
  if missing:rows=rows[:-1]
  for a,b in rows:m.add_line(a,b,dxfattribs={'layer':'SYMBOL'})
  return exploded_bowties(d,['SYMBOL'])
 def test_complete_exploded_bowtie_is_source_component(self):self.assertEqual(len(self.bowtie()),1)
 def test_three_strokes_not_valve(self):self.assertEqual(self.bowtie(missing=True),[])
 def test_rectangle_not_valve(self):self.assertEqual(self.bowtie(rect=True),[])
 def test_sensor_prefers_primitive_pipe_tip_over_bbox_second_pipe(self):
  d=ezdxf.new();b=d.blocks.new('SENSOR');b.add_lwpolyline([(2,-2),(4,-2),(4,2),(2,2)],close=True);b.add_line((0,0),(2,0));ins=d.modelspace().add_blockref('SENSOR',(0,0));s=dict(entity=ins,block='SENSOR',bounds=[0,-2,4,2]);edges=[dict(edge_id='A',path_points=[(0,-10),(0,10)]),dict(edge_id='B',path_points=[(1,-10),(1,10)])];found,rule=symbol_pipe_contacts(s,edges,d,['SENSOR']);self.assertEqual([e['edge_id']for e in found],['A']);self.assertEqual(rule,'native_primitive_endpoint_on_pipe')
 def gap(self,cross=True,long=False):
  ss=[dict(a=(-100,0),b=(-10,0),system='physical',source_system='return',handle='L'),dict(a=(10,0),b=(100,0),system='physical',source_system='return',handle='R')]
  if cross:ss.append(dict(a=(0,-100),b=(0,100),system='physical',source_system='supply',handle='X'))
  syms=[dict(block='VALVE',bounds=[0,0,10,10])];return recover_straight_crossovers(ss,syms,dict(blocks=['VALVE'],maximum_gap_symbol_diagonals=.5 if long else 2)),ss
 def test_straight_crossing_gap_restores_only_owner(self):
  (spans,audit),ss=self.gap();self.assertEqual(len(spans),1);vs,ps,ad=build_network(ss+spans);self.assertFalse(any(len(v)>2 for v in ad.values()));self.assertEqual(audit[0]['relative_elevation'],'unknown')
 def test_plain_gap_without_crossed_pipe_not_healed(self):self.assertEqual(self.gap(cross=False)[0][0],[])
 def test_large_unqualified_gap_not_healed(self):self.assertEqual(self.gap(long=True)[0][0],[])
 def test_dps_label_and_circle_alone_not_hydraulic_assembly(self):
  d=ezdxf.new();d.modelspace().add_circle((0,0),10);d.modelspace().add_text('DPS',dxfattribs={'insert':(-5,-2),'height':3});ss,g,c=measurement_assemblies(d,[],[],dict(hydraulic_main_layers=['MAIN'],capillary_layers=['CAP']));self.assertEqual(g,[])
 def test_shared_layer_loop_ignores_disconnected_main_strokes(self):
  set_tolerance(.01);d=ezdxf.new();m=d.modelspace();m.add_circle((40,0),10);m.add_text('DPS',dxfattribs={'insert':(35,-2),'height':3});segments=[];symbols=[]
  for a,b in [((0,-200),(0,200)),((0,20),(0,30)),((40,10),(40,20)),((40,25),(40,40)),((40,40),(0,40)),((40,-10),(40,-20)),((40,-25),(40,-40)),((40,-40),(0,-40))]:
   e=m.add_line(a,b,dxfattribs={'layer':'SHARED'});segments.append(dict(a=a,b=b,handle=e.dxf.handle,source_layer='SHARED'))
  for low,high in [(20,25),(-25,-20)]:
   hs=[]
   for a,b in [((35,low),(45,low)),((35,high),(45,high)),((35,low),(45,high)),((45,low),(35,high))]:hs.append(m.add_line(a,b).dxf.handle)
   symbols.append(dict(handle=hs[0],source_handles=hs,bounds=[35,low,45,high]))
  _,groups,_=measurement_assemblies(d,segments,symbols,dict(hydraulic_main_layers=['SHARED'],capillary_layers=['SHARED']));self.assertEqual(len(groups),1);self.assertEqual(len(groups[0]['native_capillary_handles']),6);self.assertEqual(len(groups[0]['component_handles']),2);set_tolerance(.5)
 def test_legend_title_alone_cannot_hide_source(self):
  d=ezdxf.new();d.modelspace().add_text('图例',dxfattribs={'height':10});self.assertEqual(source_reference_regions(d,{'Valve'}),[])
 def test_source_gauge_keeps_diameter_with_native_drafting_roundoff(self):
  from instrumentation import source_gauges
  d=ezdxf.new();m=d.modelspace();m.add_circle((0,0),100);m.add_text('TIT-1',dxfattribs={'insert':(-25,-5),'height':15});bar=m.add_line((-100.8,.1),(100.8,.1));g=source_gauges(d);self.assertEqual(len(g),1);self.assertIn(bar.dxf.handle,g[0]['handles'])
if __name__=='__main__':unittest.main(verbosity=2)
