import unittest,tempfile,hashlib
from pathlib import Path
from source_comparison_gate import check
class GateTests(unittest.TestCase):
 def test_missing_and_stale_comparison_cannot_pass(self):
  r=check({},'G',Path('.'));self.assertFalse(r['hil_ready']);self.assertEqual(r['status'],'failed')
 def test_family_blockers_and_exact_evidence_hash(self):
  with tempfile.TemporaryDirectory()as t:
   p=Path(t)/'native.png';p.write_bytes(b'native evidence fixture')
   r={'graph_sha256':'G','rounds_completed':1,'families':[{'id':'circle','status':'algorithm_pending','source_handles':['C'],'disposition':'calibration pending'}],'native_comparisons':[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
   self.assertEqual(check(r,'G',t)['status'],'pending')
   r['families'][0]['status']='resolved';self.assertTrue(check(r,'G',t)['hil_ready'])
   p.write_bytes(b'changed');self.assertEqual(check(r,'G',t)['status'],'failed')
if __name__=='__main__':unittest.main()
