import copy,json,sys,tempfile,unittest,subprocess
from pathlib import Path
from build_visualization import building_semantic_hash
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/viewer'))
from hil_server import identity
from test_builder import create_fixture
from architecture_context import export

class PipelineIdentityTest(unittest.TestCase):
    def test_external_building_stage_and_effective_parameters(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);src=create_fixture(root/'inputs');script=Path(__file__).with_name('build_visualization.py')
            args=[sys.executable,str(script),'--graph',str(src/'graph.json'),'--devices',str(src/'devices.csv'),'--dxf',str(src/'demo.dxf'),'--config',str(src/'config.json')]
            first=root/'first';r=subprocess.run(args+['--output',str(first)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            sidecar=root/'building';export(src/'demo.dxf',first/'public/data/graph.json',sidecar)
            raw=export(src/'demo.dxf',src/'graph.json',root/'from-raw-graph')
            self.assertEqual(raw['transform'],json.loads((first/'public/data/graph.json').read_text())['transform'])
            m=json.loads((first/'public/data/manifest.json').read_text());params=root/'params.json'
            params.write_text(json.dumps({'source_sha256':m['sourceHashes']['main_dxf'],'task_id':'DEMO-X','effective':{'diameter':{'value':50,'unit':'mm','source_handle':'fixture'}}}),encoding='utf8')
            extra=['--building-context',str(sidecar/'architecture.json'),'--parameters',str(params)]
            second=root/'second';r=subprocess.run(args+extra+['--output',str(second)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
            m2=json.loads((second/'public/data/manifest.json').read_text());self.assertEqual(m2['buildingPreparationMode'],'external_stage');self.assertIn('parameters',m2['reviewContentHashes']);self.assertEqual(m2['viewerVersion'],m2['visualizationSkill'])
            self.assertTrue((second/'public/data/effective-parameters.json').is_file())
            bad=json.loads((sidecar/'architecture.json').read_text());bad['source_sha256']='wrong';(sidecar/'architecture.json').write_text(json.dumps(bad),encoding='utf8')
            r=subprocess.run(args+extra+['--output',str(root/'bad')],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertFalse((root/'bad').exists())
    def test_semantic_change_invalidates_but_projection_style_does_not(self):
        data={'source_sha256':'CAD','records':[{'id':'A','label':'Plant','source_text':'机房','position':[1,2],'display_position':[3,4],'font_height':2,'paths':[{'points':[[1,2],[2,3]],'display_points':[[3,4],[4,5]],'fill':False}]}]}
        original=building_semantic_hash(data);other=copy.deepcopy(data)
        other['transform']={'scale':999};other['records'][0]['display_position']=[99,99];other['records'][0]['font_height']=999
        other['records'][0]['paths'][0]['display_points']=[[99,99],[100,100]]
        self.assertEqual(original,building_semantic_hash(other))
        other['records'][0]['label']='Pump Room';self.assertNotEqual(original,building_semantic_hash(other))
    def test_review_identity_and_legacy_compatibility(self):
        m={'projectId':'A','sourceHashes':{'graph':'g','main_dxf':'s'}};legacy=identity(m)
        m['reviewContentHashes']={'architecture':'a','parameters':'p'};new=identity(m);self.assertNotEqual(legacy,new)
        m['bundleId']='new UI';m['viewerVersion']='new';self.assertEqual(new,identity(m))
        m['reviewContentHashes']['parameters']='p2';self.assertNotEqual(new,identity(m))
if __name__=='__main__':unittest.main()
