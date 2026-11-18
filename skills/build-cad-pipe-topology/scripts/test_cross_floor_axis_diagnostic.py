import unittest,subprocess,sys
from pathlib import Path
from cross_floor_axis_diagnostic import diagnose
class CrossFloorDiagnosticTest(unittest.TestCase):
 def setUp(self):
  self.g={'edges':[{'edge_id':'E','system':'supply','floor_start':1,'floor_end':2,'attribute_paths':[[[0,10],[0,110],[20,110]]]}]};self.l={'edges':[{'edge_id':'E','system':'supply','segments':[{'source_handle':'A','graph_start':[0,10],'graph_end':[0,110]},{'source_handle':'B','graph_start':[0,110],'graph_end':[20,110]}]}]};self.d={'source_level_unit':'m candidate','levels':[{'floor_number':1,'datum_y_drawing_units':0,'elevation_numeric_decimal':'0.000'},{'floor_number':2,'datum_y_drawing_units':100,'elevation_numeric_decimal':'4.800'}]}
 def test_matching_datum_delta_is_candidate_only(self):
  x=diagnose(self.g,self.l,self.d);self.assertEqual(x['edges'][0]['status'],'datum_aligned_vertical_candidate');self.assertEqual(x['edges'][0]['source_datum_difference'],'4.800');self.assertFalse(x['graph_mutated']);self.assertFalse(x['hil_ready'])
 def test_nonvertical_and_unwitnessed_stay_unknown(self):
  self.g['edges'][0]['attribute_paths'][0][1]=[1,110];self.l['edges'][0]['segments'][0]['graph_end']=[1,110];self.l['edges'][0]['segments'][1]['graph_start']=[1,110];self.assertEqual(diagnose(self.g,self.l,self.d)['edges'][0]['status'],'no_datum_aligned_vertical_segment');self.l['edges']=[];self.assertEqual(diagnose(self.g,self.l,self.d)['edges'][0]['status'],'source_path_not_witnessed')
 def test_entry_requires_datum_policy(self):
  script=Path(__file__).with_name('build_isometric_v17.py');r=subprocess.run([sys.executable,str(script),'--cross-floor-line-policy','unused'],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('require datum policy',r.stderr)
 def test_stale_segment_and_duplicate_datum_rejected(self):
  self.l['edges'][0]['segments'][0]['graph_end']=[0,111]
  with self.assertRaises(ValueError):diagnose(self.g,self.l,self.d)
  self.d['levels'].append(self.d['levels'][0])
  with self.assertRaises(ValueError):diagnose(self.g,self.l,self.d)
if __name__=='__main__':unittest.main()
