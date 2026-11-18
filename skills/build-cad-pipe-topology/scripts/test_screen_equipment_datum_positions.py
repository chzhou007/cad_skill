import copy,unittest,ezdxf,json,subprocess,sys,tempfile
from pathlib import Path
from screen_equipment_datum_positions import screen

class DatumPositionTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new('R2010');m=self.doc.modelspace();self.levels=[]
  for floor,y,label in [(1,0,'一层'),(2,10,'二层')]:
   line=m.add_line((0,y),(100,y));text=m.add_text(label,dxfattribs={'insert':(0,y+1)});self.levels.append({'floor_number':floor,'floor_text':label,'datum_y_drawing_units':y,'source_handles':{'baseline':line.dxf.handle,'floor_text':text.dxf.handle}})
  m.add_text('CRAH-2',dxfattribs={'insert':(15,8)});self.graph={'nodes':[{'node_id':'CRAH-2','node_type':'equipment','x':20,'y':9,'floor':2}]};self.datum={'source_sha256':'s','hil_ready':False,'levels':self.levels};self.policy={'source_sha256':'s','graph_sha256':'g','equipment_ids':['CRAH-2']}
 def run_it(self):return screen(self.doc,self.graph,self.datum,self.policy,'s','g')
 def test_mismatch_is_a_candidate_not_floor_assignment(self):
  before=copy.deepcopy(self.graph);r=self.run_it();x=r['records'][0];self.assertEqual(x['drawing_anchor_band_floor'],1);self.assertEqual(x['status'],'anchor_band_differs_from_graph_label');self.assertTrue(x['anchor_x_within_claimed_native_baseline']);self.assertFalse(x['physical_floor_verified']);self.assertEqual(self.graph,before)
 def test_outside_extent_is_explicit(self):
  self.graph['nodes'][0]['x']=200;r=self.run_it();self.assertFalse(r['records'][0]['anchor_x_within_claimed_native_baseline']);self.assertEqual(r['interpretation_families'][0]['id'],'DATUM-EXTRAPOLATED');self.assertEqual(r['interpretation_families'][0]['unresolved_equipment_ids'],['CRAH-2'])
 def test_numeric_match_outside_extent_is_a_control_not_physical_acceptance(self):
  self.graph['nodes'][0].update(x=200,y=12);r=self.run_it();f=r['interpretation_families'][0]
  self.assertEqual(f['numeric_match_control_ids'],['CRAH-2']);self.assertFalse(f['physical_floor_verified']);self.assertFalse(r['human_accepted'])
 def test_unselected_equipment_remains_explicitly_out_of_scope(self):
  self.graph['nodes'].append({'node_id':'OTHER','node_type':'equipment','x':3,'y':12,'floor':2});r=self.run_it();self.assertFalse(r['scope_complete']);self.assertEqual(r['unscreened_equipment_ids'],['OTHER'])
 def test_rejects_stale_or_modified_datum(self):
  self.policy['graph_sha256']='old'
  with self.assertRaises(ValueError):self.run_it()
  self.policy['graph_sha256']='g';self.levels[1]['datum_y_drawing_units']=11
  with self.assertRaises(ValueError):self.run_it()
 def test_cli_rejects_stale_datum_before_source_decode(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'datum.json').write_text('{}',encoding='utf8');(root/'policy.json').write_text(json.dumps({'datum_sha256':'stale'}),encoding='utf8')
   cmd=[sys.executable,str(Path(__file__).with_name('screen_equipment_datum_positions.py')),'--source',str(root/'missing.dxf'),'--graph',str(root/'missing.json'),'--datum',str(root/'datum.json'),'--policy',str(root/'policy.json'),'--output',str(root/'out.json')]
   result=subprocess.run(cmd,capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertIn('stale datum evidence hash',result.stderr);self.assertFalse((root/'out.json').exists())
if __name__=='__main__':unittest.main()
