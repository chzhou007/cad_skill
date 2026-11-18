import copy,unittest
from test_source_circle_rim_tee_screen import SourceCircleScreen
from source_circle_rim_tee_screen import scan
from circle_source_z_profile import profile

class CircleZProfileTest(unittest.TestCase):
 def test_contact_and_far_endpoint_are_separate_checks(self):
  d,g,p,c,m,b=SourceCircleScreen().fixture();b.dxf.start=(0,80,0);b.dxf.end=(0,500,3)
  s=scan(d,g,p,'S','G');r=profile(d,g,s,'S','G');x=r['records'][0]
  self.assertTrue(x['contact_z_consistent']);self.assertFalse(x['all_line_endpoints_match_circle_z']);self.assertEqual(x['status'],'line_endpoint_z_differs_uninterpreted');self.assertFalse(r['human_accepted'])
 def test_tampered_screen_or_source_system_fails(self):
  d,g,p,c,m,b=SourceCircleScreen().fixture();s=scan(d,g,p,'S','G');bad=copy.deepcopy(s);bad['candidates'][0]['branch_z_at_rim']=12
  with self.assertRaises(ValueError):profile(d,g,bad,'S','G')
  b.dxf.layer='空调冷冻水回水'
  with self.assertRaises(ValueError):profile(d,g,s,'S','G')
 def test_unchanged_z_is_not_a_connection_confirmation(self):
  d,g,p,c,m,b=SourceCircleScreen().fixture();s=scan(d,g,p,'S','G');r=profile(d,g,s,'S','G');self.assertTrue(r['records'][0]['all_line_endpoints_match_circle_z']);self.assertFalse(r['graph_mutated'])
if __name__=='__main__':unittest.main()
