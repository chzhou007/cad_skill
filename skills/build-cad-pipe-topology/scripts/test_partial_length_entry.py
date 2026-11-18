import subprocess,sys,unittest
from pathlib import Path
class PartialLengthEntryTest(unittest.TestCase):
 def test_partial_stage_requires_both_policies_before_rebuild(self):
  script=Path(__file__).with_name('build_isometric_v17.py')
  for option in ('--path-coverage-policy','--partial-length-policy'):
   r=subprocess.run([sys.executable,str(script),option,'unused.json'],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('requires both coverage and partial policies',r.stderr)
if __name__=='__main__':unittest.main()
