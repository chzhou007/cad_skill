import json,subprocess,sys,tempfile,unittest
from pathlib import Path
SCRIPT=Path(__file__).with_name('build_ceiling_family.py')
class DirectDNEntryTests(unittest.TestCase):
 def test_missing_endpoint_stage_fails_before_read(self):
  r=subprocess.run([sys.executable,str(SCRIPT),'--input-root','missing','--output-root','missing','--normalization-config','missing','--direct-dn-policy-map','missing'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('source evidence requires endpoint semantics',r.stderr)
 def test_unknown_task_policy_fails_before_rebuild(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);lib=p/'reference-library/parameters-v1';lib.mkdir(parents=True);(p/'batch.json').write_text(json.dumps({'tasks':[{'task_id':'valid','sheet':'09'}]}));(lib/'catalog-manifest.json').write_text('{}');(lib/'cad-pattern-prototypes.json').write_text('[]');(p/'config.json').write_text('{}');(p/'map.json').write_text(json.dumps({'typo':'policy.json'}));r=subprocess.run([sys.executable,str(SCRIPT),'--input-root',str(p),'--output-root',str(p/'out'),'--normalization-config',str(p/'config.json'),'--direct-dn-policy-map',str(p/'map.json'),'--endpoint-semantics'],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('direct DN policy map contains unrecognized ceiling task IDs',r.stderr);self.assertFalse((p/'out').exists())
if __name__=='__main__':unittest.main()
