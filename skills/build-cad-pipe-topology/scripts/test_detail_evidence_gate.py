import copy,unittest
from detail_evidence_gate import evaluate

class DetailEvidenceGateTests(unittest.TestCase):
 def setUp(self):
  self.a={'source_sha256':'s','graph_sha256':'g','hil_ready':False,'rows':[{'service':'supply','rank':1,'upper_edge':'E1','detail_edge':'E2','status':'candidate_not_confirmed','exception':''}]}
  self.b={'source_sha256':'s','graph_sha256':'g','hil_ready':False,'candidate_count':1,'rows':[{'system':'supply','rank':1,'upper_edge':'E1','detail_edge':'E2','status':'individual_mapping_ambiguous','same_signature_detail_ranks':[1,2]}]}
 def test_consistent_candidate_remains_unresolved(self):
  old=copy.deepcopy((self.a,self.b));r=evaluate('g','s',self.a,self.b);self.assertFalse(r['mapping_ready']);self.assertFalse(r['hil_ready']);self.assertEqual((self.a,self.b),old)
 def test_stale_source_or_graph_rejected(self):
  for graph,source in [('bad','s'),('g','bad')]:
   with self.assertRaises(ValueError):evaluate(graph,source,self.a,self.b)
 def test_missing_duplicate_or_changed_edge_rejected(self):
  for change in ('missing','duplicate','edge'):
   b=copy.deepcopy(self.b)
   if change=='missing':b['rows']=[]
   if change=='duplicate':b['rows'].append(copy.deepcopy(b['rows'][0]))
   if change=='edge':b['rows'][0]['detail_edge']='OTHER'
   with self.assertRaises(ValueError):evaluate('g','s',self.a,b)
 def test_cannot_promote_unreviewed_candidate(self):
  self.b['rows'][0]['status']='confirmed'
  with self.assertRaises(ValueError):evaluate('g','s',self.a,self.b)
if __name__=='__main__':unittest.main()
