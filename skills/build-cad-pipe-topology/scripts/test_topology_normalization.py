import unittest
import pipe_geometry as pg
from straight_crossovers import recover_straight_crossovers
from topology_normalization import trim_elbow_overshoots

class Crossovers(unittest.TestCase):
 def setUp(self):pg.set_tolerance(.01)
 def tearDown(self):pg.set_tolerance(.5)
 def base(self):return [dict(a=(-100,0),b=(-10,0),system='physical',source_system='return',handle='L'),dict(a=(10,0),b=(100,0),system='physical',source_system='return',handle='R')]
 def run_case(self,segments):return recover_straight_crossovers(segments,[],{'maximum_gap_native_units':25})
 def test_split_crossed_pipe(self):
  ss=self.base()+[dict(a=(0,-100),b=(0,0),system='physical',source_system='supply',handle='X1'),dict(a=(0,0),b=(0,100),system='physical',source_system='supply',handle='X2')]
  spans,a=self.run_case(ss);self.assertEqual(len(spans),1);vs,ps,ad=pg.build_network(ss+spans);self.assertFalse(any(len(x)>2 for x in ad.values()))
 def test_true_tee_at_gap_endpoint_retained(self):
  ss=self.base()+[dict(a=(0,-100),b=(0,100),system='physical',source_system='supply',handle='X'),dict(a=(-10,0),b=(-10,50),system='physical',source_system='return',handle='B')]
  spans,a=self.run_case(ss);self.assertEqual(len(spans),1);vs,ps,ad=pg.build_network(ss+spans);self.assertEqual(len(ad['physical',next(i for i,p in enumerate(vs)if pg.dist(p,(-10,0))<.01)]),3)
 def test_plain_gap(self):self.assertEqual(self.run_case(self.base())[0],[])
 def test_crossed_terminal_alone(self):self.assertEqual(self.run_case(self.base()+[dict(a=(0,0),b=(0,100),system='physical',source_system='supply',handle='X')])[0],[])
 def test_conflicting_owner_classes(self):
  ss=self.base();ss[1]['source_system']='supply';ss.append(dict(a=(0,-100),b=(0,100),system='physical',source_system='supply',handle='X'));self.assertEqual(self.run_case(ss)[0],[])
 def test_valve_or_equipment_symbol_gap_excluded(self):
  ss=self.base()+[dict(a=(0,-100),b=(0,100),system='physical',source_system='supply',handle='X')]
  self.assertEqual(recover_straight_crossovers(ss,[dict(block='VALVE',bounds=[-12,-5,12,5])],dict(maximum_gap_native_units=25,exclude_symbol_bounds=True))[0],[])
 def test_multiple_crossing_witnesses_not_accepted(self):
  ss=self.base()+[dict(a=(x,-100),b=(x,100),system='physical',source_system='supply',handle='X'+str(x))for x in [-3,3]]
  self.assertEqual(self.run_case(ss)[0],[])
 def elbow(self):return [dict(a=(0,-100),b=(0,2.1),system='supply',handle='A'),dict(a=(-50,-50),b=(0,0),system='supply',handle='B')]
 def test_micro_elbow_overshoot(self):
  rows,a=trim_elbow_overshoots(self.elbow(),dict(maximum_length=10,maximum_ratio=.1,minimum_angle_degrees=20));self.assertEqual(len(a),1);self.assertEqual(rows[0]['b'],(0,0))
 def test_real_third_branch_not_removed(self):
  ss=self.elbow()+[dict(a=(0,2.1),b=(50,2.1),system='supply',handle='PORT')];self.assertEqual(trim_elbow_overshoots(ss,dict(maximum_length=10,maximum_ratio=.1,minimum_angle_degrees=20))[1],[])
 def test_protected_equipment_port_not_trimmed(self):
  self.assertEqual(trim_elbow_overshoots(self.elbow(),dict(maximum_length=10,maximum_ratio=.1,minimum_angle_degrees=20,protected_points=[(0,2.1)]))[1],[])

if __name__=='__main__':unittest.main()
