"""Contract tests with a non-SH16 drawing, custom symbols and named floors."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import ezdxf

HERE=Path(__file__).resolve().parent

def create_fixture(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    doc=ezdxf.new();valve=doc.blocks.new('CUSTOM_VALVE')
    valve.add_lwpolyline([(0,0,.01,.01,1),(.01,0,.01,.01,1)],format='xyseb',close=True)
    valve.add_line((-.01,0),(.02,0))
    cabinet=doc.blocks.new('CUSTOM_CABINET');cabinet.add_lwpolyline([(0,0),(.02,0),(.02,.04),(0,.04)],close=True)
    doc.modelspace().add_blockref('CUSTOM_VALVE',(.0005,.0005));doc.modelspace().add_blockref('CUSTOM_CABINET',(0,0))
    doc.modelspace().add_line((0,0),(.005,.005));doc.saveas(root/'demo.dxf')
    nodes=[{'node_id':'UNIT-A','node_type':'physical_equipment','floor':'B2','x':0,'y':0},
           {'node_id':'J-A','node_type':'tee','floor':'B2','x':.001,'y':.001},
           {'node_id':'J-B','node_type':'tee','floor':'Roof','x':.004,'y':.004},
           {'node_id':'UNIT-B','node_type':'physical_equipment','floor':'Roof','x':.005,'y':.005}]
    edges=[]
    for eid,a,b,inventory in [('P-A','J-A','UNIT-A',[{'equipment_type':'TestValve','count':1,'device_names':['VALVE-X']}]),('P-B','J-A','J-B',[]),('P-C','J-B','UNIT-B',[])]:
        n1=next(n for n in nodes if n['node_id']==a);n2=next(n for n in nodes if n['node_id']==b);pts=[[n1['x'],n1['y']],[n2['x'],n2['y']]]
        edges.append({'edge_id':eid,'start_node_id':a,'end_node_id':b,'system':'supply','path_length':.002,'path_points':pts,'attribute_paths':[pts],'equipment_inventory':inventory,'connection_mode':'direct_source_path'})
    graph={'nodes':nodes,'edges':edges}
    config={'project':{'id':'DEMO-X','title':'Pipe Explorer','description':'Test water network','equipmentLabel':'Source cabinet'},'preferred_port':8768,
            'systems':{'supply':{'code':'S','name':'Supply','color':'#b525aa','dash':''},'return':{'code':'R','name':'Return','color':'#886600','dash':'4 2'}},
            'floors':[{'id':'Roof','label':'Roof Level'},{'id':'B2','label':'Basement 2'}],
            'device_types':[{'code':'TV','label':'Test Valve','source_names':['TestValve'],'symbol':{'drawing':'main','block':'CUSTOM_VALVE'}}],
            'equipment_symbol':{'drawing':'main','block':'CUSTOM_CABINET'}}
    (root/'graph.json').write_text(json.dumps(graph),encoding='utf8');(root/'config.json').write_text(json.dumps(config),encoding='utf8')
    row={'device_name':'VALVE-X','equipment_type':'TestValve','edge_id':'P-A','assignment_status':'assigned','x':.0005,'y':.0005,'assignment_x':.0005,'assignment_y':.0005,'edge_distance':0,'source_kind':'block_insert','source_block_name':'CUSTOM_VALVE','source_top_handle':'A1','owner_equipment':'UNIT-A'}
    with (root/'devices.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
    return root

class BuilderContract(unittest.TestCase):
    def test_reference_scope_retains_audited_nested_mep_without_changing_walls(self):
        from build_visualization import cad_reference_chunks
        from architecture_context import extract
        d=ezdxf.new();body=d.blocks.new('FanWall');body.add_lwpolyline([(0,0),(4,0),(4,2),(0,2)],close=True)
        b=d.blocks.new('Building');b.add_line((0,0),(10,0),dxfattribs={'layer':'A-WALL'});child=b.add_blockref('FanWall',(5,5))
        top=d.modelspace().add_blockref('Building',(20,30));building=extract(d,dict(originX=0,originY=0,scale=1))
        chain=[top.dxf.handle,child.dxf.handle];spec=[dict(handle=top.dxf.handle,block='Building',mode='architectural_context',reason='native scope',retained_mep_chains=[dict(source_chain=chain,reason='verified whole equipment body')])]
        chunks,count=cad_reference_chunks(d,building,spec,lambda x,y:(x,-y),1)
        self.assertEqual(count,2);self.assertIn('data-mep-source-chain=', ''.join(chunks));self.assertIn('25.000,-35.000',''.join(chunks))
        spec[0]['retained_mep_chains'][0]['source_chain']=[child.dxf.handle]
        with self.assertRaisesRegex(ValueError,'actual reference parent'):cad_reference_chunks(d,building,spec,lambda x,y:(x,y),1)
    def test_reference_scope_keeps_primary_geometry_and_native_architecture(self):
        from build_visualization import cad_reference_chunks
        from architecture_context import extract
        d=ezdxf.new();b=d.blocks.new('Building');b.add_line((0,0),(10,0),dxfattribs={'layer':'A-WALL'});b.add_circle((5,5),2,dxfattribs={'layer':'E-Equipment'})
        ins=d.modelspace().add_blockref('Building',(20,30));primary=d.modelspace().add_line((1,1),(2,1),dxfattribs={'layer':'CHWS'})
        data=extract(d,dict(originX=0,originY=0,scale=1));spec=[dict(handle=ins.dxf.handle,block='Building',mode='architectural_context',reason='Actual architectural reference scope')]
        chunks,count=cad_reference_chunks(d,data,spec,lambda x,y:(x,-y),1)
        text=''.join(chunks);self.assertEqual(count,2);self.assertEqual(text.count('data-source-handle='),2);self.assertIn(primary.dxf.handle,text);self.assertIn(ins.dxf.handle+'/',text);self.assertNotIn('E-Equipment',text);self.assertIn('20.000000,-30.000000',text)
        all_chunks,all_count=cad_reference_chunks(d,data,[],lambda x,y:(x,-y),1);self.assertEqual(all_count,3)
    def test_reference_scope_rejects_missing_source_or_empty_sidecar(self):
        from build_visualization import cad_reference_chunks
        d=ezdxf.new();b=d.blocks.new('Building');ins=d.modelspace().add_blockref('Building',(0,0));spec=[dict(handle=ins.dxf.handle,block='Wrong',mode='architectural_context',reason='scope')]
        with self.assertRaisesRegex(ValueError,'actual top-level'):cad_reference_chunks(d,{'records':[]},spec,lambda x,y:(x,y),1)
        spec[0]['block']='Building'
        with self.assertRaisesRegex(ValueError,'no building-owned'):cad_reference_chunks(d,{'records':[]},spec,lambda x,y:(x,y),1)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=create_fixture(Path(self.tmp.name)/'inputs');self.out=Path(self.tmp.name)/'viewer'
    def tearDown(self):self.tmp.cleanup()
    def run_builder(self):
        return subprocess.run([sys.executable,str(HERE/'build_visualization.py'),'--graph',str(self.root/'graph.json'),'--devices',str(self.root/'devices.csv'),'--dxf',str(self.root/'demo.dxf'),'--config',str(self.root/'config.json'),'--output',str(self.out)],capture_output=True,text=True)
    def read(self,name):return json.loads((self.root/name).read_text())
    def write(self,name,value):(self.root/name).write_text(json.dumps(value),encoding='utf8')
    def test_other_project_named_floors_and_tiny_geometry(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()}
        result=self.run_builder();self.assertEqual(result.returncode,0,result.stderr)
        g=json.loads((self.out/'public/data/graph.json').read_text());r=json.loads((self.out/'validation-report.json').read_text())
        self.assertEqual((r['nodes'],r['edges'],r['instances'],r['reviews']),(4,3,1,2));self.assertEqual(g['project']['id'],'DEMO-X')
        self.assertEqual([f['label'] for f in g['floors']],['Roof Level','Basement 2']);self.assertEqual([f['equipmentCount'] for f in g['floors']],[1,1])
        self.assertAlmostEqual(max(n['px'] for n in g['nodes'])-min(n['px'] for n in g['nodes']),1000)
        self.assertIn('fill="currentColor"',g['symbols']['TV']['markup']);self.assertEqual(g['symbols']['TV']['block'],'CUSTOM_VALVE')
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()})
        with zipfile.ZipFile(self.out.with_suffix('.zip')) as z:self.assertIn('viewer/public/data/graph.json',z.namelist())
    def test_count_mismatch_does_not_emit_bundle(self):
        g=self.read('graph.json');g['edges'][0]['equipment_inventory'][0]['count']=2;self.write('graph.json',g)
        self.assertNotEqual(self.run_builder().returncode,0);self.assertFalse(self.out.exists());self.assertFalse(self.out.with_suffix('.zip').exists())
    def test_isolated_pending_equipment_has_a_default_visible_filter(self):
        g=self.read('graph.json');g['nodes'].append({'node_id':'ISOLATED','node_type':'physical_equipment','floor':'B2','x':.002,'y':.002,'system':'unresolved'});self.write('graph.json',g)
        r=self.run_builder();self.assertEqual(r.returncode,0,r.stderr)
        result=json.loads((self.out/'public/data/graph.json').read_text())
        visible={n['node_id'] for n in result['nodes'] if not n.get('system')or n['system']in result['systems']}
        self.assertIn('ISOLATED',visible);self.assertEqual(len(result['edges']),3)
        self.assertEqual(result['systems']['unresolved']['code'],'PENDING')
        from validate_visualization import validate_bundle
        result['systems'].pop('unresolved');(self.out/'public/data/graph.json').write_text(json.dumps(result),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Node hidden'):validate_bundle(self.out)
    def test_missing_typed_node_filter_is_not_silently_hidden_or_reclassified(self):
        g=self.read('graph.json');g['nodes'].append({'node_id':'ISOLATED','node_type':'physical_equipment','floor':'B2','x':.002,'y':.002,'system':'custom_loop'});self.write('graph.json',g)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('node system missing',r.stderr)
    def test_unknown_symbol_is_not_replaced_by_generic_icon(self):
        c=self.read('config.json');c['device_types'][0]['symbol']['block']='MISSING';self.write('config.json',c)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('source block',r.stderr);self.assertFalse(self.out.exists())
    def test_incomplete_floor_config_cannot_hide_data(self):
        c=self.read('config.json');c['floors']=c['floors'][:1];self.write('config.json',c)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('floor',r.stderr.lower())
    def test_no_overwrite(self):
        self.assertEqual(self.run_builder().returncode,0);p=self.out/'public/data/graph.json';before=p.read_bytes()
        self.assertNotEqual(self.run_builder().returncode,0);self.assertEqual(p.read_bytes(),before)
    def test_dotted_version_keeps_its_full_archive_name(self):
        self.out=self.out.with_name('viewer-v1.2')
        self.assertEqual(self.run_builder().returncode,0)
        self.assertTrue(self.out.with_name('viewer-v1.2.zip').is_file())
        self.assertFalse(self.out.with_name('viewer-v1.zip').exists())
    def test_missing_source_paths_are_not_synthesized(self):
        g=self.read('graph.json');del g['edges'][0]['attribute_paths'];self.write('graph.json',g)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('attribute_paths',r.stderr)
    def test_bad_endpoint_fails_before_publication(self):
        g=self.read('graph.json');g['edges'][0]['end_node_id']='MISSING';self.write('graph.json',g)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('missing endpoint',r.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
