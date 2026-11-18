import subprocess,sys,tempfile,unittest
from pathlib import Path
class JunctionEntryTest(unittest.TestCase):
 def test_refuses_existing_evidence_before_rebuild(self):
  script=Path(__file__).with_name('build_isometric_v17.py')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'native_junction_ray_evidence.json';p.write_text('keep',encoding='utf8');r=subprocess.run([sys.executable,str(script),'--output-dir',d,'--junction-ray-policy','unused'],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('refusing to overwrite junction ray evidence',r.stderr);self.assertEqual(p.read_text(encoding='utf8'),'keep')
if __name__=='__main__':unittest.main()
