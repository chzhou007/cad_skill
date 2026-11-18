import json,subprocess,sys,tempfile,unittest
from pathlib import Path
class NamedLeaderEntryTest(unittest.TestCase):
 def test_requires_explicit_final_graph_selection(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);config=root/'config.json';config.write_text('{}',encoding='utf8');policy=root/'map.json';policy.write_text(json.dumps({'TASK':'policy.json'}),encoding='utf8')
   cmd=[sys.executable,str(Path(__file__).with_name('build_ceiling_family.py')),'--input-root',str(root),'--output-root',str(root/'out'),'--normalization-config',str(config),'--final-named-leader-policy-map',str(policy)]
   result=subprocess.run(cmd,capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertIn('named leader screen requires explicit final graph selection',result.stderr)
if __name__=='__main__':unittest.main()
