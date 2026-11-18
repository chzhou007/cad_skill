import unittest,tempfile,subprocess,json,hashlib,sys
from pathlib import Path
from unittest.mock import patch
from pipeline import validate_anchored_plan_metrics,reconstruct_anchored_plan_metrics,validate_anchored_native_metric_viewer
from reapply_anchored_plan_metrics import MODE
class Tests(unittest.TestCase):
    def proof(self):return dict(mode=MODE,complete_original_provider_replayed=True,all_pending_horizontal_length_scopes_screened=True,original_metric_readers_reused=True,native_T_paths_components_and_joint_origins_replayed=True,source_graphs_mutated=False,component_owners_changed=False,human_accepted=False,DN_values_assigned=0,vertical_values_assigned=0,installed_lengths_assigned=0,counts={})
    def test_formal_native_batch_and_viewer_replay_entries(self):
        with patch('reapply_anchored_plan_metrics.verify_output',return_value=self.proof()):self.assertEqual(validate_anchored_plan_metrics('x')['native_anchored_metrics'],'passed')
        with patch('reapply_anchored_plan_metrics.produce')as produce,patch('pipeline.validate_anchored_plan_metrics',return_value={}):reconstruct_anchored_plan_metrics('manifest','output')
        produce.assert_called_once_with('manifest','output')
        with patch('refresh_anchored_native_plan_metrics.verify',return_value={'status':'pending'})as verify:self.assertEqual(validate_anchored_native_metric_viewer('view')['status'],'pending')
        verify.assert_called_once_with('view')
    def test_no_source_replay_or_silent_DN_vertical_installation_fill_blocks(self):
        for key,value in [('complete_original_provider_replayed',False),('native_T_paths_components_and_joint_origins_replayed',False),('source_graphs_mutated',True),('DN_values_assigned',1),('vertical_values_assigned',1),('installed_lengths_assigned',1)]:
            proof=self.proof();proof[key]=value
            with self.subTest(key=key),patch('reapply_anchored_plan_metrics.verify_output',return_value=proof),self.assertRaises(ValueError):validate_anchored_plan_metrics('x')
    def test_complete_original_owner_compares_all_canonical_outputs_and_pinned_bytes(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);skills=root/'skills';scripts=skills/'build-cad-pipe-topology/scripts';scripts.mkdir(parents=True);run=root/'run';run.mkdir()
            (scripts/'fixture_owner.py').write_text("def verify_output(path):\n    return ({'pairs':[('P','A')]},{'count':1},{'nodes':[]})\n",encoding='utf8')
            (scripts/'confirm_crossview_paths.py').write_text("import json\ndef encode(x):\n    return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\\n').encode('utf8')\n",encoding='utf8')
            values=[{'pairs':[['P','A']]},{'count':1},{'nodes':[]}];files=['proof.json','provider.json','member.json']
            for file,value in zip(files,values):(run/file).write_bytes((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8'))
            sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();snapshot=root/'snapshot.json';snapshot.write_text(json.dumps(dict(skills=['build-cad-pipe-topology'],files={p.relative_to(skills).as_posix():sha(p)for p in scripts.glob('*.py')})),encoding='utf8')
            cmd=[sys.executable,'-X','utf8','-B',str(Path(__file__).with_name('replay_fixed_complete_owner.py')),'--skills-root',str(skills),'--snapshot',str(snapshot),'--native-run',str(run),'--owner','fixture_owner','--result-files',json.dumps(files),'--output',str(root/'checked')]
            result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8');self.assertEqual(result.returncode,0,result.stderr)
            for file in files:self.assertEqual((root/'checked'/file).read_bytes(),(run/file).read_bytes())
            (scripts/'fixture_owner.py').write_text('raise RuntimeError("changed source")\n',encoding='utf8');cmd[-1]=str(root/'changed');result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8');self.assertNotEqual(result.returncode,0);self.assertFalse((root/'changed').exists())
if __name__=='__main__':unittest.main()
