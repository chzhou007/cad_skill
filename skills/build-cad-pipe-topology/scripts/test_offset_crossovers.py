"""Opt-in drafting precision never relaxes physical crossing/branch evidence."""
import unittest
import pipe_geometry as pg
from straight_crossovers import recover_straight_crossovers

class OffsetCrossovers(unittest.TestCase):
 def setUp(self):pg.set_tolerance(.25)
 def scene(self,offset=3.55):
  return [dict(a=(-10000,offset),b=(-100,offset),system='physical',source_system='humidification',handle='L'),dict(a=(100,0),b=(10000,0),system='physical',source_system='humidification',handle='R'),dict(a=(0,-1000),b=(0,1000),system='physical',source_system='humidification',handle='X')]
 def run_case(self,ss=None,**kw):
  cfg=dict(maximum_gap_native_units=250,maximum_tail_offset_native_units=5,maximum_tail_angle_degrees=2,exclude_symbol_bounds=True);cfg.update(kw)
  return recover_straight_crossovers(self.scene()if ss is None else ss,[],cfg)
 def test_small_offset_restores_only_own_pipe(self):
  ss=self.scene();spans,audit=self.run_case(ss);self.assertEqual(len(spans),1)
  self.assertEqual(audit[0]['tail_alignment']['kind'],'profile_bounded_drafting_offset')
  vs,ps,ad=pg.build_network(ss+spans)
  self.assertFalse(any(len(ids)>2 for ids in ad.values()))
 def test_default_remains_strict(self):
  self.assertEqual(self.run_case(maximum_tail_offset_native_units=None)[0],[])
 def test_offset_limit(self):self.assertEqual(self.run_case(self.scene(5.1))[0],[])
 def test_angle_limit(self):self.assertEqual(self.run_case(maximum_tail_angle_degrees=.5)[0],[])
 def test_no_witness(self):self.assertEqual(self.run_case(self.scene()[:2])[0],[])
 def test_conflicting_service(self):
  ss=self.scene();ss[1]['source_system']='return';self.assertEqual(self.run_case(ss)[0],[])
 def test_symbol_gap(self):
  spans,_=recover_straight_crossovers(self.scene(),[dict(bounds=[-101,-10,101,10],block='V')],dict(maximum_gap_native_units=250,maximum_tail_offset_native_units=5,maximum_tail_angle_degrees=2,exclude_symbol_bounds=True));self.assertEqual(spans,[])
 def test_genuine_branch_at_gap_end_survives(self):
  ss=self.scene();ss.append(dict(a=(-100,3.55),b=(-100,1000),system='physical',source_system='humidification',handle='BRANCH'))
  spans,_=self.run_case(ss);self.assertEqual(len(spans),1);vs,ps,ad=pg.build_network(ss+spans)
  self.assertEqual(sum(len(ids)==3 for ids in ad.values()),1)
 def test_occupied_span(self):
  ss=self.scene();ss.append(dict(a=(-90,3.3725),b=(90,.1775),system='physical',source_system='humidification',handle='INK'));self.assertEqual(self.run_case(ss)[0],[])

if __name__=='__main__':unittest.main()
