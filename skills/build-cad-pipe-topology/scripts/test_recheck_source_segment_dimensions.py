import copy,unittest
from unittest.mock import patch
from recheck_source_segment_dimensions import recheck

class DimensionRecheckTests(unittest.TestCase):
 def setUp(self):
  self.record={'edge_id':'E1','dimension_handle':'D1','dimension_value_mm':2400,'segment_index':1}
  self.graph={'metadata':{'source_sha256':'s'},'edges':[{'edge_id':'E1','source_dimensioned_segments':[self.record]}]}
  self.policy={'source_sha256':'s','graph_sha256':'old','dimensions':[{'dimension_handle':'D1'}]}
 def test_current_evidence_preserves_historical_provenance_and_graph(self):
  before=copy.deepcopy(self.graph)
  with patch('recheck_source_segment_dimensions.collect',return_value=[self.record]):out=recheck(None,self.graph,self.policy,'s','new')
  self.assertEqual(self.graph,before);self.assertEqual(out['graph_sha256'],'new');self.assertEqual(out['prior_policy_graph_sha256'],'old');self.assertFalse(out['whole_edge_physical_length_assigned']);self.assertFalse(out['differences'])
 def test_difference_is_reported_without_promoting_length(self):
  changed=copy.deepcopy(self.record);changed['dimension_value_mm']=2500
  with patch('recheck_source_segment_dimensions.collect',return_value=[changed]):out=recheck(None,self.graph,self.policy,'s','new')
  self.assertEqual(out['status'],'dimension_difference_requires_invalidation');self.assertEqual(out['differences'][0]['dimension_handle'],'D1');self.assertFalse(out['human_acceptance'])
 def test_missing_or_misowned_existing_evidence_fails_closed(self):
  self.graph['edges'][0]['source_dimensioned_segments']=[]
  with self.assertRaises(ValueError):recheck(None,self.graph,self.policy,'s','new')
  self.graph['edges'][0]['source_dimensioned_segments']=[dict(self.record,edge_id='E2')]
  with self.assertRaises(ValueError):recheck(None,self.graph,self.policy,'s','new')
 def test_source_mismatch_fails_closed(self):
  with self.assertRaises(ValueError):recheck(None,self.graph,self.policy,'other','new')
if __name__=='__main__':unittest.main()
