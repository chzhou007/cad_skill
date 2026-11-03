import unittest,ezdxf
import pipe_geometry as pg
from topology_normalization import exclude_paired_bar_display_tails
from equipment_assemblies import collapse_package_source_geometry
class ExpertSourceRules(unittest.TestCase):
 def setUp(self):pg.set_tolerance(.05)
 def tearDown(self):pg.set_tolerance(.5)
 def test_two_bar_display_tail_does_not_create_a_tee(self):
  d=ezdxf.new();m=d.modelspace();m.add_line((-4,3),(4,3));m.add_line((-4,4),(4,4));ss=[dict(a=(0,0),b=(0,3),system='supply',handle='stub'),dict(a=(-20,0),b=(0,0),system='supply',handle='left'),dict(a=(0,0),b=(0,-20),system='supply',handle='down')];r,a=exclude_paired_bar_display_tails(ss,d,dict(bar_layers=['0'],maximum_length=10));self.assertEqual(len(r),2);self.assertEqual(a[0]['status'],'display_excluded')
 def test_pipe_continuing_beyond_marker_is_not_a_dead_display_tail(self):
  d=ezdxf.new();m=d.modelspace();m.add_line((-4,3),(4,3));m.add_line((-4,4),(4,4));ss=[dict(a=(0,0),b=(0,3),system='supply',handle='stub'),dict(a=(-20,0),b=(20,0),system='supply',handle='main'),dict(a=(0,3),b=(0,20),system='supply',handle='continuation')];self.assertFalse(exclude_paired_bar_display_tails(ss,d,dict(bar_layers=['0'],maximum_length=10))[1])
 def test_verified_main_crossing_vendor_frame_remains_continuous(self):
  ss=[dict(a=(0,-20),b=(0,20),system='physical',source_system='return',handle='main')];p=[dict(package_boundary=True,bounds=[-5,-5,5,5],label='Dosing Unit',binding=dict(equipment_tag='SC'))];r,a=collapse_package_source_geometry(ss,p,{'Dosing Unit':['return']});self.assertEqual(len(r),1);self.assertEqual(r[0]['a'],(0,-20));self.assertIn('preserved',a[0]['rule'])
 def test_unproven_equipment_internal_pipe_is_not_preserved_as_a_main(self):
  ss=[dict(a=(0,-20),b=(0,20),system='physical',source_system='return',handle='internal')];p=[dict(package_boundary=True,bounds=[-5,-5,5,5],label='Equipment',binding=dict(equipment_tag='E'))];r,a=collapse_package_source_geometry(ss,p,{});self.assertEqual(len(r),2)
if __name__=='__main__':unittest.main()
