import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
class ScopedWaveCLI(unittest.TestCase):
 def test_graph_hash_mismatch_fails_before_output(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);files={k:p/k for k in ('source','graph','devices','issue','policy')}
   for k in ('source','graph','devices','issue'):files[k].write_text(k,encoding='utf8')
   sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();files['policy'].write_text(json.dumps({'source_sha256':sha(files['source']),'input_graph_sha256':'bad','devices_sha256':sha(files['devices']),'issue_sha256':sha(files['issue'])}),encoding='utf8');out=p/'out';cmd=[sys.executable,str(Path(__file__).with_name('repair_expert_wave_scoped_09.py'))]
   for k,v in files.items():cmd+=['--'+k,str(v)]
   r=subprocess.run(cmd+['--output',str(out)],text=True,capture_output=True);self.assertNotEqual(r.returncode,0);self.assertIn('input_graph_sha256 mismatch',r.stderr);self.assertFalse(out.exists())
 def test_optimized_execution_is_rejected(self):
  r=subprocess.run([sys.executable,'-O',str(Path(__file__).with_name('repair_expert_wave_scoped_09.py'))],text=True,capture_output=True);self.assertNotEqual(r.returncode,0);self.assertIn('assertions enabled',r.stderr)
if __name__=='__main__':unittest.main()
