import subprocess,sys,unittest
from pathlib import Path
class FinalIsometricAttributeEntry(unittest.TestCase):
 def test_final_dn_requires_device_chain(self):
  p=subprocess.run([sys.executable,str(Path(__file__).with_name('build_isometric_v17.py')),'--final-bulk-source-dn-policy','x'],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('final bulk DN requires final device chain stage',p.stderr)
 def test_final_floor_requires_chain_and_datum(self):
  p=subprocess.run([sys.executable,str(Path(__file__).with_name('build_isometric_v17.py')),'--final-cross-floor-line-policy','x'],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('final cross-floor evidence requires final device chain and datum stages',p.stderr)
 def test_equipment_datum_requires_final_graph_and_datum(self):
  p=subprocess.run([sys.executable,str(Path(__file__).with_name('build_isometric_v17.py')),'--final-equipment-datum-policy','x'],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('final equipment datum screen requires final device chain and datum stages',p.stderr)
 def test_final_length_requires_pair_and_chain(self):
  script=str(Path(__file__).with_name('build_isometric_v17.py'))
  p=subprocess.run([sys.executable,script,'--final-path-coverage-policy','x'],capture_output=True,text=True);self.assertNotEqual(p.returncode,0);self.assertIn('requires both coverage and partial policies',p.stderr)
  p=subprocess.run([sys.executable,script,'--final-path-coverage-policy','x','--final-partial-length-policy','y'],capture_output=True,text=True);self.assertNotEqual(p.returncode,0);self.assertIn('requires final device chain stage',p.stderr)
 def test_partial_line_evidence_requires_final_coverage(self):
  p=subprocess.run([sys.executable,str(Path(__file__).with_name('build_isometric_v17.py')),'--final-partial-line-policy','x'],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('requires final coverage and partial length',p.stderr)
 def test_partial_line_attachment_requires_evidence(self):
  p=subprocess.run([sys.executable,str(Path(__file__).with_name('build_isometric_v17.py')),'--final-attach-partial-line'],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('partial line attachment requires final partial line evidence',p.stderr)
if __name__=='__main__':unittest.main()
