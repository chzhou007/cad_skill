import subprocess,sys,unittest
from pathlib import Path
class EquipmentIdentityEntryTest(unittest.TestCase):
 def test_rotated_caption_identity_requires_endpoint_stage(self):
  script=Path(__file__).with_name('build_ceiling_family.py');r=subprocess.run([sys.executable,str(script),'--input-root','x','--output-root','x','--normalization-config','x','--rotated-equipment-identity-policy-map','x'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('rotated equipment identity requires endpoint semantics',r.stderr)
 def test_requires_endpoint_stage(self):
  script=Path(__file__).with_name('build_ceiling_family.py');r=subprocess.run([sys.executable,str(script),'--input-root','x','--output-root','x','--normalization-config','x','--equipment-identity-policy-map','x'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('source evidence requires endpoint semantics',r.stderr)
 def test_local_dn_requires_endpoint_stage(self):
  script=Path(__file__).with_name('build_ceiling_family.py');r=subprocess.run([sys.executable,str(script),'--input-root','x','--output-root','x','--normalization-config','x','--local-dn-policy-map','x'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('source evidence requires endpoint semantics',r.stderr)
 def test_dn_inheritance_requires_endpoint_stage(self):
  script=Path(__file__).with_name('build_ceiling_family.py');r=subprocess.run([sys.executable,str(script),'--input-root','x','--output-root','x','--normalization-config','x','--dn-inheritance-policy-map','x'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('source evidence requires endpoint semantics',r.stderr)
 def test_segment_dimensions_require_endpoint_stage(self):
  script=Path(__file__).with_name('build_ceiling_family.py');r=subprocess.run([sys.executable,str(script),'--input-root','x','--output-root','x','--normalization-config','x','--segment-dimension-policy-map','x'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('source evidence requires endpoint semantics',r.stderr)
if __name__=='__main__':unittest.main()
