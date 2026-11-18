import copy,unittest
from test_screen_applied_near_tees import AppliedNearTeesTest
from screen_applied_near_tees import screen
from attach_applied_near_tee_state import attach

class AttachAppliedNearTeeStateTest(unittest.TestCase):
 def setUp(self):
  f=AppliedNearTeesTest();f.setUp();self.g=f.g;self.e=screen(f.d,f.g,f.a,f.p,f.h)
 def test_preserves_topology_and_marks_pending(self):
  before=copy.deepcopy(self.g);out=attach(self.g,self.e,'S','G');self.assertEqual(self.g,before);self.assertEqual(out['edges'],before['edges']);self.assertEqual(out['nodes'][0]['resolution_state'],'source_contact_reconstructed_pending_comparison');self.assertFalse(out['metadata']['hil_ready'])
 def test_stale_and_conflicting_review_fail(self):
  with self.assertRaisesRegex(ValueError,'stale'):attach(self.g,self.e,'S','old')
  self.g['nodes'][0]['resolution_state']='confirmed'
  with self.assertRaisesRegex(ValueError,'mismatch'):attach(self.g,self.e,'S','G')
if __name__=='__main__':unittest.main()
