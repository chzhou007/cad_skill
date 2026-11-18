import copy,unittest
from unittest.mock import patch
from recheck_dn_inheritance import compare,recheck

class RecheckTests(unittest.TestCase):
 def test_lineage_and_values_must_remain_equal(self):
  original={'nominal_mm_candidate':300,'candidate_type':'inherited_candidate','lineage':[{'edge_path':['E1','E2']}],'status':'candidate'}
  self.assertEqual(compare({'E2':original},{'E2':copy.deepcopy(original)}),[])
  changed=copy.deepcopy(original);changed['lineage'][0]['edge_path']=['E1','E3']
  self.assertEqual(compare({'E2':original},{'E2':changed})[0]['edge_id'],'E2')
  self.assertEqual(compare({'E2':original},{})[0]['edge_id'],'E2')
 def test_source_mismatch_rejected(self):
  with self.assertRaises(ValueError):recheck(None,{}, {'source_sha256':'wrong'},{'source_sha256':'s'},'s','g','drawing')
 def test_evidence_rechecks_on_current_graph_without_mutation(self):
  inf={'source_graph_sha256':'old','nominal_mm_candidate':300,'candidate_type':'inherited_candidate','lineage':[],'status':'candidate'}
  graph={'edges':[{'edge_id':'E1','diameter_inference':inf,'diameter_candidate_mm':300,'pipe_diameter':{'nominal_mm':None}}]};before=copy.deepcopy(graph)
  policy={'source_sha256':'s','edges':['E1'],'junctions':['T1'],'seeds':[{'edge_id':'E1','text_handle':'X','nominal_mm':300}]};direct={'source_sha256':'s'}
  observation={'observations':[{'edge_id':'E1','source_text':{'handle':'X'},'nominal_mm':300}]}
  with patch('recheck_dn_inheritance.collect_direct',return_value=observation),patch('recheck_dn_inheritance.collect_evidence',return_value=({}, {}, {}, {})),patch('recheck_dn_inheritance.calculate',return_value=({'edges':[{'edge_id':'E1','diameter_inference':inf}]},{})):
   out=recheck(None,graph,policy,direct,'s','current','drawing')
  self.assertEqual(graph,before);self.assertEqual(out['graph_sha256'],'current');self.assertEqual(out['prior_inference_graph_sha256s'],['old']);self.assertFalse(out['human_acceptance']);self.assertFalse(out['differences'])
if __name__=='__main__':unittest.main()
