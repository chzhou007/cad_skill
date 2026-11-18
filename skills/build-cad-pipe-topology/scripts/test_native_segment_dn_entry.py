import subprocess,sys,unittest
from pathlib import Path
class SegmentDNEntryTest(unittest.TestCase):
 def test_segment_stage_requires_line_stage_before_rebuild(self):
  script=Path(__file__).with_name('build_isometric_v17.py');r=subprocess.run([sys.executable,str(script),'--segment-dn-policy','unused.json'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('segment DN candidates require source line path evidence',r.stderr)
if __name__=='__main__':unittest.main()
