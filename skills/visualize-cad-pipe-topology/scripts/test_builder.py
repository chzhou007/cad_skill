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
from unittest.mock import patch

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
    def test_bundle_validation_reuses_native_source_context_and_rejects_wrong_hash(self):
        from validate_visualization import validate_bundle
        from coverage_display_paths import partition
        result=self.run_builder();self.assertEqual(result.returncode,0,result.stderr)
        doc=ezdxf.readfile(self.root/'demo.dxf');source_hash=hashlib.sha256((self.root/'demo.dxf').read_bytes()).hexdigest()
        with patch('validate_visualization.partition_source_coverage',wraps=partition) as replay:
            self.assertEqual(validate_bundle(self.out,native_doc=doc,native_source_sha256=source_hash)['status'],'passed')
        self.assertTrue(replay.call_args_list);self.assertTrue(all(call.args[1] is doc and call.args[2]==source_hash for call in replay.call_args_list))
        with self.assertRaisesRegex(ValueError,'source hash mismatch'):validate_bundle(self.out,native_doc=doc,native_source_sha256='wrong')
    def test_unpaired_wave_rejects_stale_source_or_wrong_endpoint(self):
        g=self.read('graph.json');e=g['edges'][1];e['source_handles']=['line'];e['source_wave_terminal']={'source_sha256':'wrong','endpoint_node_id':e['start_node_id'],'source_pipe_handle':'line','source_wave_handle':'wave','destination':'unknown','paired_continuation':'not_established','physical_length':'unknown'};self.write('graph.json',g)
        self.assertNotEqual(self.run_builder().returncode,0)
        e['source_wave_terminal']['source_sha256']=hashlib.sha256((self.root/'demo.dxf').read_bytes()).hexdigest();e['source_wave_terminal']['endpoint_node_id']='wrong';self.write('graph.json',g)
        self.assertNotEqual(self.run_builder().returncode,0)
    def test_source_conflict_cannot_be_marked_hil_ready(self):
        g=self.read('graph.json');g['metadata']={'hil_ready':True};g['junctionValidation']={'new_unexplained_degree_exceptions':[],'existing_pending':[{'node_id':'J-A'},{'node_id':'J-B'}]};g['sourceInlineSystemConflicts']=[{'joint_handle':'J'}];self.write('graph.json',g)
        result=self.run_builder();self.assertEqual(result.returncode,0,result.stderr)
        graph=json.loads((self.out/'public/data/graph.json').read_text(encoding='utf8'));self.assertIs(graph['metadata']['hil_ready'],False);self.assertIn('sourceInlineSystemConflicts',graph['metadata']['hil_block_reason'])
    def test_missing_junction_audit_keeps_preview_but_blocks_hil(self):
        result=self.run_builder();self.assertEqual(result.returncode,0,result.stderr)
        graph=json.loads((self.out/'public/data/graph.json').read_text(encoding='utf8'))
        self.assertIs(graph['metadata']['hil_ready'],False)
        self.assertIn('Junction validation',graph['metadata']['hil_block_reason'])
        gate=json.loads((self.out/'quality-gate.json').read_text(encoding='utf8'))
        self.assertTrue(any(item['id']=='junction-validation' for item in gate['pending']))
    def test_reference_equipment_coverage_detects_omitted_nested_body(self):
        from build_visualization import validate_reference_equipment_coverage
        nodes=[{'node_id':'CT1','node_type':'equipment','display_source_chain':['R','F','C'],'display_source_handles':['C']}]
        refs=[{'handle':'R','mode':'architectural_context','retained_mep_chains':[]}]
        with self.assertRaisesRegex(ValueError,'omits nested graph equipment'):validate_reference_equipment_coverage(nodes,refs)
        refs[0]['retained_mep_chains']=[{'source_chain':['R','F','C']}]
        self.assertEqual(validate_reference_equipment_coverage(nodes,refs)['status'],'PASS')
        nodes[0]['display_source_chain']=['R','F'];nodes[0]['display_source_handles']=['C','D']
        with self.assertRaisesRegex(ValueError,'omits nested graph equipment'):validate_reference_equipment_coverage(nodes,refs)
        refs[0]['retained_mep_chains'].append({'source_chain':['R','F','D']})
        self.assertEqual(validate_reference_equipment_coverage(nodes,refs)['status'],'PASS')
    def test_source_building_labels_fail_closed_on_unreadable_text(self):
        from build_visualization import validate_native_building_text
        validate_native_building_text({'records':[{'id':'B1','source_text':'不上人屋面'}]})
        with self.assertRaisesRegex(ValueError,'Unreadable native building text'):validate_native_building_text({'records':[{'id':'B2','source_text':'乱码\ufffd'}]})
        with self.assertRaisesRegex(ValueError,'Unreadable native building text'):validate_native_building_text({'records':[{'id':'B3','source_text':'\ud800'}]})
    def test_reference_scope_retains_audited_nested_mep_without_changing_walls(self):
        from build_visualization import cad_reference_chunks
        from architecture_context import extract
        d=ezdxf.new();body=d.blocks.new('FanWall');body.add_lwpolyline([(0,0),(4,0),(4,2),(0,2)],close=True)
        b=d.blocks.new('Building');b.add_line((0,0),(10,0),dxfattribs={'layer':'A-WALL'});child=b.add_blockref('FanWall',(5,5))
        top=d.modelspace().add_blockref('Building',(20,30));building=extract(d,dict(originX=0,originY=0,scale=1))
        chain=[top.dxf.handle,child.dxf.handle];spec=[dict(handle=top.dxf.handle,block='Building',mode='architectural_context',reason='native scope',retained_mep_chains=[dict(source_chain=chain,reason='verified whole equipment body')])]
        chunks,count=cad_reference_chunks(d,building,spec,lambda x,y:(x,-y),1)
        self.assertEqual(count,2);self.assertIn('data-mep-source-chain=', ''.join(chunks));self.assertIn('25.000,-35.000',''.join(chunks));self.assertIn('data-source-handle="'+'/'.join(chain)+'"',''.join(chunks))
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
    def test_upstream_colour_resolution_requires_reproducible_source_audit(self):
        g=self.read('graph.json');g['sourceInlineSystemResolutions']=[{'joint_handle':'J'}]
        self.write('graph.json',g);r=self.run_builder()
        self.assertNotEqual(r.returncode,0)
        self.assertIn('upstream-system-repair-audit.json',r.stderr)
        self.assertFalse(self.out.exists())
    def test_floor_label_correction_requires_reproducible_source_audit(self):
        g=self.read('graph.json');g['sourceFloorLabelRepair']={'changes':[{'node_id':'J-A'}]}
        self.write('graph.json',g);r=self.run_builder()
        self.assertNotEqual(r.returncode,0)
        self.assertIn('floor-label-repair-audit.json',r.stderr)
        self.assertFalse(self.out.exists())
    def test_manifest_binds_actual_built_viewer_graph(self):
        import hashlib
        result=self.run_builder();self.assertEqual(result.returncode,0,result.stderr)
        data=self.out/'public/data'
        manifest=json.loads((data/'manifest.json').read_text(encoding='utf8'))
        self.assertEqual(manifest['reviewContentHashes']['viewer_graph'],hashlib.sha256((data/'graph.json').read_bytes()).hexdigest())
    def test_explicit_unicode_labels_are_readable_and_reject_markup(self):
        cfg=self.read('config.json');cfg['project']['title']='供回水管网';self.write('config.json',cfg)
        self.assertNotEqual(self.run_builder().returncode,0)
        cfg['display']={'human_label_language':'unicode'};cfg['systems']['supply']['name']='供水';cfg['project']['description']='候选连接待核';self.write('config.json',cfg)
        result=self.run_builder();self.assertEqual(result.returncode,0,result.stderr)
        graph=json.loads((self.out/'public/data/graph.json').read_text(encoding='utf8'));self.assertEqual(graph['project']['title'],'供回水管网');self.assertEqual(graph['systems']['supply']['name'],'供水')
    def test_unicode_labels_reject_unreadable_and_html(self):
        cfg=self.read('config.json');cfg['display']={'human_label_language':'unicode'}
        for value in ('供水<script>', '供水\ufffd', '供水\ud800', '供水\u202e'):
            cfg['project']['title']=value;self.write('config.json',cfg);self.assertNotEqual(self.run_builder().returncode,0)
    def test_folded_valve_recovers_native_chain_in_full_builder(self):
        doc=ezdxf.readfile(self.root/'demo.dxf');valve=next(e for e in doc.modelspace().query('INSERT') if e.dxf.name=='CUSTOM_VALVE')
        path=self.root/'devices.csv'
        with path.open(encoding='utf8',newline='') as f:
            reader=csv.DictReader(f);rows=list(reader);fields=reader.fieldnames
        rows[0]['source_kind']='turn_display_valve_folded_to_elbow';rows[0]['source_top_handle']=valve.dxf.handle
        with path.open('w',encoding='utf8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
        result=self.run_builder();self.assertEqual(result.returncode,0,result.stderr)
        graph=json.loads((self.out/'public/data/graph.json').read_text(encoding='utf8'));instance=graph['instances'][0]
        self.assertEqual(instance['display_source_chain'],[valve.dxf.handle]);self.assertEqual(instance['edge_id'],'P-A')
        self.assertTrue(instance['sourceGeometry']);self.assertEqual(instance['display_source_status'],'verified_nested_folded_valve_insert_chain')
    def test_suppressed_node_label_requires_scoped_source_evidence(self):
        g=self.read('graph.json');g['nodes'][0]['node_label_visible']=False;self.write('graph.json',g)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('hidden node label requires expert issue',r.stderr)
    def test_node_label_visibility_rejects_string(self):
        g=self.read('graph.json');g['nodes'][0]['node_label_visible']='false';self.write('graph.json',g)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('must be boolean',r.stderr)
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
    def test_explicit_user_confirmed_overlay_has_no_source_path_or_length(self):
        g=self.read('graph.json');e=g['edges'][0];e.update(attribute_paths=[],source_handles=[],source_path_status='user_confirmed_overlay_no_native_supply_path',connection_mode='user_confirmed_overlaid_supply',path_length_complete=False,physical_length='unknown',path_length=0);self.write('graph.json',g)
        r=self.run_builder();self.assertEqual(r.returncode,0,r.stderr)
        rendered=json.loads((self.out/'public/data/graph.json').read_text(encoding='utf8'));edge=next(x for x in rendered['edges'] if x['edge_id']==e['edge_id']);self.assertEqual(edge['sourcePaths'],[]);self.assertFalse(edge['path_length_complete'])
    def test_partial_source_paths_exclude_unwitnessed_segment(self):
        import math
        g=self.read('graph.json');e=g['edges'][0];a,z=e['attribute_paths'][0][0],e['attribute_paths'][0][-1];mid=[(a[i]+z[i])/2 for i in (0,1)]
        e['attribute_paths']=[[a,mid,z]];e['path_length_complete']=False;e['source_path_coverage']={'source_sha256':hashlib.sha256((self.root/'demo.dxf').read_bytes()).hexdigest(),'coverage_sha256':'c','input_graph_sha256':'g','unverified_segment_indices':[1],'unverified_drawing_length':math.dist(mid,z)};self.write('graph.json',g)
        r=self.run_builder();self.assertEqual(r.returncode,0,r.stderr)
        rendered=json.loads((self.out/'public/data/graph.json').read_text(encoding='utf8'));edge=next(x for x in rendered['edges'] if x['edge_id']==e['edge_id'])
        self.assertEqual(len(edge['sourcePaths']),1);self.assertEqual(len(edge['unverifiedPaths']),1);self.assertEqual(edge['sourcePaths'][0][-1],edge['unverifiedPaths'][0][0])
        from validate_visualization import validate_bundle
        edge['unverifiedPaths'][0][0][0]+=1;(self.out/'public/data/graph.json').write_text(json.dumps(rendered),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'coordinates changed'):validate_bundle(self.out)
    def test_partial_source_paths_reject_stale_drawing(self):
        import math
        g=self.read('graph.json');e=g['edges'][0];a,z=e['attribute_paths'][0][0],e['attribute_paths'][0][-1];mid=[(a[i]+z[i])/2 for i in (0,1)]
        e['attribute_paths']=[[a,mid,z]];e['path_length_complete']=False;e['source_path_coverage']={'source_sha256':'wrong','coverage_sha256':'c','input_graph_sha256':'g','unverified_segment_indices':[1],'unverified_drawing_length':math.dist(mid,z)};self.write('graph.json',g)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('partial coverage source hash mismatch',r.stderr)
    def test_crossover_paths_reject_stale_source(self):
        g=self.read('graph.json');e=g['edges'][0]
        e.update(path_length_scope='drawing_paths_excluding_source_crossover_gaps_physical_length_unknown',source_normalized_crossovers=[{'source_sha256':'wrong','source_gap_coverage_sha256':'a','source_fragments_sha256':'b'}])
        self.write('graph.json',g);r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('crossover evidence source mismatch',r.stderr)
    def test_unverified_overlay_cannot_bypass_source_path_requirement(self):
        g=self.read('graph.json');e=g['edges'][0];e.update(attribute_paths=[],source_handles=[],source_path_status='user_confirmed_overlay_no_native_supply_path',connection_mode='user_confirmed_overlaid_supply',path_length_complete=True,physical_length='unknown',path_length=0);self.write('graph.json',g)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('attribute_paths',r.stderr)
    def test_calculation_unknown_length_stays_null_with_evidence(self):
        g=self.read('graph.json');e=g['edges'][0];e.update(path_length=None,path_length_complete=False,path_length_scope='sum_of_source_edge_lengths_no_display_connector',calculation_source_length_evidence=[{'edge_id':'X','recorded_source_length':1},{'edge_id':'Y','recorded_source_length':None}]);self.write('graph.json',g)
        r=self.run_builder();self.assertEqual(r.returncode,0,r.stderr)
        rendered=json.loads((self.out/'public/data/graph.json').read_text(encoding='utf8'));edge=next(x for x in rendered['edges'] if x['edge_id']==e['edge_id'])
        self.assertIsNone(edge['path_length']);self.assertFalse(edge['path_length_complete'])
        self.assertIn('e.path_length===null', (self.out/'public/app.js').read_text(encoding='utf8'))
    def test_unknown_length_without_evidence_is_rejected(self):
        g=self.read('graph.json');g['edges'][0].update(path_length=None,path_length_complete=False);self.write('graph.json',g)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('unknown length requires',r.stderr);self.assertFalse(self.out.exists())
    def test_bad_endpoint_fails_before_publication(self):
        g=self.read('graph.json');g['edges'][0]['end_node_id']='MISSING';self.write('graph.json',g)
        r=self.run_builder();self.assertNotEqual(r.returncode,0);self.assertIn('missing endpoint',r.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
