import copy,unittest
from unittest.mock import patch
from detail_scope_coverage import analyze

def fake_glyph(doc,n):return {'center':[n['x'],n['y'],0],'handles':[n['node_id']],'signature':{'system':n['system']}}
class DetailScopeTests(unittest.TestCase):
 def setUp(self):
  def n(i,x,y):return {'node_id':i,'node_type':'virtual_equipment','subtype':'out_of_plane_interface','system':'supply','x':x,'y':y}
  self.graph={'metadata':{'source_sha256':'S'},'nodes':[n('U1',100,100),n('U2',200,100),n('D1',10,10)]}
  sig={'signature':{'system':'supply'}};self.evidence={'source_sha256':'S','graph_sha256':'G','rows':[{'system':'supply','upper_glyph':'U1','detail_glyph':'D1','upper':sig,'detail':sig}]}
  self.policy={'source_sha256':'S','graph_sha256':'G','translation_tolerance':0.1,'regions':{'upper':{'xmin':0,'xmax':300,'ymin':90,'ymax':110},'detail':{'xmin':0,'xmax':300,'ymin':0,'ymax':20}}}
 def run_case(self):
  with patch('detail_scope_coverage.glyph',fake_glyph):return analyze(None,self.graph,self.evidence,self.policy,'S','G')
 def test_reports_unselected_interfaces_without_automatic_identity(self):
  r=self.run_case();self.assertEqual(r['counts']['upper_outside_candidates'],1);self.assertEqual(r['counts']['detail_in_candidates'],1);self.assertFalse(r['mapping_ready']);self.assertFalse(r['graph_mutated']);self.assertEqual(len(r['upper'][0]['translation_matches']),1)
 def test_stale_and_wrong_candidate_are_rejected(self):
  self.policy['graph_sha256']='old'
  with self.assertRaises(ValueError):self.run_case()
  self.policy['graph_sha256']='G';self.evidence['rows'][0]['detail_glyph']='absent'
  with self.assertRaises(ValueError):self.run_case()
 def test_duplicate_candidate_is_rejected(self):
  self.evidence['rows'].append(copy.deepcopy(self.evidence['rows'][0]))
  with self.assertRaises(ValueError):self.run_case()
if __name__=='__main__':unittest.main()
