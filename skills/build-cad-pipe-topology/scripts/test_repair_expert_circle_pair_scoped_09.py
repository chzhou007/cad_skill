import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
class CirclePairCLI(unittest.TestCase):
 def test_incorrect_graph_hash_fails_before_output(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);files={k:root/k for k in ('source','graph','devices','issue','policy')};ev=root/'evidence';ev.mkdir()
   for k in ('source','graph','devices','issue'):files[k].write_text(k,encoding='utf8')
   for k in ('source_gap_coverage.json','source-fragments.json'):(ev/k).write_text(k,encoding='utf8')
   sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();p={'source_sha256':sha(files['source']),'input_graph_sha256':'wrong','devices_sha256':sha(files['devices']),'issue_sha256':sha(files['issue']),'gap_coverage_sha256':sha(ev/'source_gap_coverage.json'),'fragments_sha256':sha(ev/'source-fragments.json')};files['policy'].write_text(json.dumps(p),encoding='utf8');out=root/'out';cmd=[sys.executable,str(Path(__file__).with_name('repair_expert_circle_pair_scoped_09.py'))]
   for k,v in files.items():cmd+=['--'+k,str(v)]
   r=subprocess.run(cmd+['--output',str(out),'--evidence-dir',str(ev)],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('input_graph_sha256 mismatch',r.stderr);self.assertFalse(out.exists())
 def test_optimized_execution_is_rejected(self):
  r=subprocess.run([sys.executable,'-O',str(Path(__file__).with_name('repair_expert_circle_pair_scoped_09.py'))],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('assertions enabled',r.stderr)
 def test_missing_inferred_marker_fails_before_output(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);files={k:root/k for k in ('source','graph','devices','issue','policy')};ev=root/'evidence';ev.mkdir()
   for k in ('source','graph','devices','issue'):files[k].write_text(k,encoding='utf8')
   for k in ('source_gap_coverage.json','source-fragments.json'):(ev/k).write_text(k,encoding='utf8')
   sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();p={'source_sha256':sha(files['source']),'input_graph_sha256':sha(files['graph']),'devices_sha256':sha(files['devices']),'issue_sha256':sha(files['issue']),'gap_coverage_sha256':sha(ev/'source_gap_coverage.json'),'fragments_sha256':sha(ev/'source-fragments.json'),'source_circle_scope':['12F6C','12F6D'],'lower_circle_inferred':False};files['policy'].write_text(json.dumps(p),encoding='utf8');out=root/'out';cmd=[sys.executable,str(Path(__file__).with_name('repair_expert_circle_pair_scoped_09.py'))]
   for k,v in files.items():cmd+=['--'+k,str(v)]
   r=subprocess.run(cmd+['--output',str(out),'--evidence-dir',str(ev)],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('invalid explicit circle scope',r.stderr);self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
