import unittest,ezdxf
from source_glyphs import exploded_flange_spans,source_cup_terminals
from equipment_assemblies import material_contour_candidates,collapse_package_source_geometry
from pipe_geometry import build_network
class SourceGlyphContracts(unittest.TestCase):
 def flanges(self,both=True,ink=True,offset=0):
  d=ezdxf.new();m=d.modelspace()
  if ink:
   m.add_line((0,-50),(0,50),dxfattribs={'layer':'VALVE'});m.add_line((30,-50),(30,50),dxfattribs={'layer':'VALVE'})
  ss=[dict(a=(-100,0),b=(0,0),system='physical',handle='L')]
  if both:ss.append(dict(a=(30,offset),b=(130,offset),system='physical',handle='R'))
  return exploded_flange_spans(ss,list(m),['VALVE'])
 def test_exploded_flanges_require_both_opposed_midpoint_contacts(self):self.assertEqual(len(self.flanges()[0]),1)
 def test_flange_one_tail_rejected(self):self.assertEqual(self.flanges(both=False)[0],[])
 def test_plain_gap_rejected(self):self.assertEqual(self.flanges(ink=False)[0],[])
 def test_nearby_parallel_unaligned_pipes_rejected(self):self.assertEqual(self.flanges(offset=5)[0],[])
 def terminal(self,short=True,pipe=True,near=50):
  d=ezdxf.new();m=d.modelspace()
  for a,b in [((0,0),(100,0)),((0,0),(0,50)),((100,0),(100,50))]+([((15,-25),(85,-25))]if short else []):m.add_line(a,b,dxfattribs={'layer':'SYMBOL'})
  ss=[]
  if pipe:
   e=m.add_line((near,20),(near,200),dxfattribs={'layer':'PIPE'});ss=[dict(a=(near,20),b=(near,200),system='physical',handle=e.dxf.handle)]
  vs,ps,ad=build_network(ss)
  return source_cup_terminals(list(m),vs,ps,ad,[dict(symbol_layers=['SYMBOL'],pipe_layers=['PIPE'],system='water')])
 def test_full_source_terminal_has_explicit_provenance(self):
  f,a=self.terminal();self.assertEqual(len(f),1);self.assertEqual(len(a[0]['source_symbol_handles']),4);self.assertIn('pending',a[0]['status'])
 def test_no_short_bar_no_source_terminal(self):self.assertEqual(self.terminal(short=False)[0],[])
 def test_no_pipe_no_source_terminal(self):self.assertEqual(self.terminal(pipe=False)[0],[])
 def test_off_axis_pipe_no_source_terminal(self):self.assertEqual(self.terminal(near=30)[0],[])
 def material(self,profile=True,note=True,package=False):
  d=ezdxf.new();m=d.modelspace();attrs={'linetype':'DASHED'}if package else {};m.add_lwpolyline([(0,0),(100,0),(100,120),(0,120)],close=True,dxfattribs=attrs);m.add_text('UNIT-1',dxfattribs={'insert':(10,100),'height':10})
  if package:
   m.add_text('DOSING',dxfattribs={'insert':(10,70),'height':10})
   if note:m.add_text('VENDOR PACKAGE',dxfattribs={'insert':(10,40),'height':10})
  ss=[dict(a=(-50,60),b=(150,60),system='physical',handle='P')]if package else [dict(a=(-50,60),b=(0,60),system='physical',handle='L'),dict(a=(100,60),b=(150,60),system='physical',handle='R')]
  rule=dict(tag_regex='UNIT-[0-9]+',material_name_regex='TANK',minimum_source_ports=2,label='Tank')
  if package:rule.update(geometry_family='vendor_package_enclosure',vendor_note_regex='VENDOR PACKAGE',caption_regex='DOSING')
  f,a=material_contour_candidates(d,[dict(profile_id='MATERIAL-1',source_name='TANK')]if profile else [],ss,[rule]);return f,a,ss
 def test_material_scheduled_vessel_recognized(self):self.assertEqual(len(self.material()[0]),1)
 def test_geometry_without_material_reference_remains_pending(self):self.assertEqual(self.material(profile=False)[0],[])
 def test_vendor_package_uses_outer_boundary_and_retains_internal_audit(self):
  f,a,ss=self.material(package=True);self.assertEqual(len(f),1);parts,audit=collapse_package_source_geometry(ss,f);self.assertEqual(len(parts),2);self.assertEqual(len(audit),1)
 def test_frame_without_vendor_note_is_not_whole_equipment(self):self.assertEqual(self.material(package=True,note=False)[0],[])
if __name__=='__main__':unittest.main(verbosity=2)
