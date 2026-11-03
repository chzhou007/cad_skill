import unittest,tempfile,json,subprocess,sys
from pathlib import Path
from unittest.mock import patch,MagicMock
import ezdxf
import test_builder as fixture
import cad_geometry as cg
HERE=Path(__file__).resolve().parent
class NewDrawingViewerContract(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=fixture.create_fixture(Path(self.tmp.name)/'inputs');self.out=Path(self.tmp.name)/'viewer'
 def tearDown(self):self.tmp.cleanup()
 def build(self):return subprocess.run([sys.executable,str(HERE/'build_visualization.py'),'--graph',str(self.root/'graph.json'),'--devices',str(self.root/'devices.csv'),'--dxf',str(self.root/'demo.dxf'),'--config',str(self.root/'config.json'),'--output',str(self.out)],capture_output=True,text=True)
 def test_equipment_uses_its_own_native_block(self):
  d=ezdxf.readfile(self.root/'demo.dxf');b=d.blocks.new('CUSTOM_PUMP');b.add_circle((0,0),.01);b.add_line((-.01,0),(.01,0));d.saveas(self.root/'demo.dxf')
  c=json.loads((self.root/'config.json').read_text());c['equipment_symbols']={'EQ_UNIT':{'label':'Cabinet','symbol':{'drawing':'main','block':'CUSTOM_CABINET'}},'EQ_PUMP':{'label':'Pump','symbol':{'drawing':'main','block':'CUSTOM_PUMP'}}};(self.root/'config.json').write_text(json.dumps(c))
  g=json.loads((self.root/'graph.json').read_text());g['nodes'][0]['symbol_key']='EQ_UNIT';g['nodes'][3]['symbol_key']='EQ_PUMP';g['metadata']={'extraction_status':'partial'};g['pendingSourcePaths']=[{'path_points':[[0,0],[.005,.005]]}];(self.root/'graph.json').write_text(json.dumps(g))
  ret=self.build();self.assertEqual(ret.returncode,0,ret.stderr);actual=json.loads((self.out/'public/data/graph.json').read_text());self.assertNotEqual(actual['symbols']['EQ_UNIT']['markup'],actual['symbols']['EQ_PUMP']['markup']);self.assertEqual(actual['nodes'][3]['symbol_key'],'EQ_PUMP');self.assertEqual(len(actual['pendingSourcePaths'][0]['points']),2);coverage=json.loads((self.out/'public/data/extraction-report.json').read_text());self.assertEqual(coverage['pending_source_path_groups'],1);self.assertEqual(coverage['status'],'partial_unreviewed')
 def test_unknown_equipment_source_key_fails(self):
  g=json.loads((self.root/'graph.json').read_text());g['nodes'][0]['symbol_key']='EQ_MISSING';(self.root/'graph.json').write_text(json.dumps(g));ret=self.build();self.assertNotEqual(ret.returncode,0);self.assertIn('Missing equipment source symbol',ret.stderr);self.assertFalse(self.out.exists())
 def test_empty_native_width_trace_does_not_crash_or_hide_warning(self):
  d=ezdxf.new();e=d.modelspace().add_lwpolyline([(0,0),(1,0)],dxfattribs={'const_width':.1});trace=MagicMock();trace.polygons_wcs.return_value=[()];before=len(cg.RENDER_WARNINGS)
  with patch.object(cg.TraceBuilder,'from_polyline',return_value=trace):self.assertEqual(cg.strokes(e),[])
  self.assertEqual(len(cg.RENDER_WARNINGS),before+1);self.assertEqual(cg.RENDER_WARNINGS[-1]['source_handle'],e.dxf.handle)
 def test_third_system_and_explicit_source_mixed_junction_supported(self):
  cfg=json.loads((self.root/'config.json').read_text());cfg['systems']['makeup_water']={'code':'MUW','name':'Makeup Water','color':'#21866b','dash':''};(self.root/'config.json').write_text(json.dumps(cfg))
  g=json.loads((self.root/'graph.json').read_text());g['edges'][2]['system']='makeup_water';n=g['nodes'][2];n.update(system='supply',mixed_source_contact=True,system_review_required=True,source_handles=['source-1','source-2'],incident_systems=['supply','makeup_water']);(self.root/'graph.json').write_text(json.dumps(g));ret=self.build();self.assertEqual(ret.returncode,0,ret.stderr);actual=json.loads((self.out/'public/data/graph.json').read_text());self.assertIn('makeup_water',actual['systems']);self.assertEqual(actual['edges'][2]['system'],'makeup_water')
 def test_mixed_source_junction_requires_explicit_evidence(self):
  cfg=json.loads((self.root/'config.json').read_text());cfg['systems']['makeup_water']={'code':'MUW','name':'Makeup Water','color':'#21866b','dash':''};(self.root/'config.json').write_text(json.dumps(cfg));g=json.loads((self.root/'graph.json').read_text());g['edges'][2]['system']='makeup_water';(self.root/'graph.json').write_text(json.dumps(g));ret=self.build();self.assertNotEqual(ret.returncode,0);self.assertIn('mixed junction needs explicit source evidence',ret.stderr)
 def test_full_source_geometry_and_multiple_edge_context_preserved(self):
  g=json.loads((self.root/'graph.json').read_text());import csv
  with (self.root/'devices.csv').open(encoding='utf-8-sig',newline='')as f:rows=list(csv.DictReader(f))
  name=rows[0]['device_name'];rows[0]['related_edge_ids']=json.dumps([g['edges'][0]['edge_id'],g['edges'][1]['edge_id']])
  fields=list(rows[0]);
  with (self.root/'devices.csv').open('w',encoding='utf-8-sig',newline='')as f:
   w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
  g['componentSourceGeometry']=[{'device_name':name,'paths':[{'points':[[0,0],[.005,.005]],'fill':False}]}];(self.root/'graph.json').write_text(json.dumps(g));ret=self.build();self.assertEqual(ret.returncode,0,ret.stderr);actual=json.loads((self.out/'public/data/graph.json').read_text());row=actual['instances'][0];self.assertEqual(len(row['related_edge_ids']),2);self.assertEqual(len(row['sourceGeometry'][0]['points']),2);self.assertNotEqual(row['sourceGeometry'][0]['points'][0],row['sourceGeometry'][0]['points'][1])
 def test_unresolved_virtual_terminal_is_hint_not_human_error(self):
  g=json.loads((self.root/'graph.json').read_text());n=g['nodes'][-1];n.update(node_type='virtual_equipment',boundary_type='unresolved_source_terminal',review_required=True,ports=[{'port_id':'END-P1','system':'supply','x':n['x'],'y':n['y']}]);g['edges'][-1]['end_port_id']='END-P1';(self.root/'graph.json').write_text(json.dumps(g));ret=self.build();self.assertEqual(ret.returncode,0,ret.stderr);actual=json.loads((self.out/'public/data/graph.json').read_text());hint=next(r for r in actual['review']if r['id']==n['node_id']);self.assertIn('Unresolved source terminal',hint['reason']);self.assertTrue(hint['automatic_hint']);self.assertFalse((self.out/'annotations').exists())
 def test_standard_csv_source_handles_generate_native_geometry(self):
  import csv
  d=ezdxf.readfile(self.root/'demo.dxf');h=next(iter(d.modelspace().query('LINE'))).dxf.handle
  with (self.root/'devices.csv').open(encoding='utf-8-sig',newline='')as f:rows=list(csv.DictReader(f))
  rows[0]['source_handles']=json.dumps([h])
  rows[0]['source_kind']='native_primitive';rows[0]['source_top_handle']=h
  with (self.root/'devices.csv').open('w',encoding='utf-8-sig',newline='')as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  ret=self.build();self.assertEqual(ret.returncode,0,ret.stderr);actual=json.loads((self.out/'public/data/graph.json').read_text());self.assertEqual(len(actual['instances'][0]['sourceGeometry'][0]['points']),2)
 def test_incomplete_sensor_head_stays_assigned_but_creates_completeness_hint(self):
  import csv
  with (self.root/'devices.csv').open(encoding='utf-8-sig',newline='')as f:rows=list(csv.DictReader(f))
  rows[0]['source_head_status']='pending_no_proven_head'
  with (self.root/'devices.csv').open('w',encoding='utf-8-sig',newline='')as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  ret=self.build();self.assertEqual(ret.returncode,0,ret.stderr);g=json.loads((self.out/'public/data/graph.json').read_text());self.assertEqual(g['instances'][0]['assignment_status'],'assigned');self.assertEqual(len(g['componentReview']),1);self.assertEqual(g['componentReview'][0]['id'],g['instances'][0]['id']);self.assertFalse((self.out/'annotations').exists())
if __name__=='__main__':unittest.main(verbosity=2)
