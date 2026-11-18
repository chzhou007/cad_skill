import copy,unittest
from terminal_inventory_reconciliation import rebind

class TerminalRebinding(unittest.TestCase):
 def fixture(self):
  return [{'node_id':'UT1','edge_id':'OLD','source':[{'handle':'SOURCE'}]}],{'nodes':[{'node_id':'UT1','node_type':'virtual_equipment'},{'node_id':'T1','node_type':'tee'}],'edges':[{'edge_id':'NEW','start_node_id':'UT1','end_node_id':'T1','path_length':7,'source_handles':['SOURCE']}]}
 def test_rebind_requires_native_evidence_and_preserves_old_id(self):
  rows,g=self.fixture();original=copy.deepcopy(rows);out,changes=rebind(rows,g);self.assertEqual(out[0]['edge_id'],'NEW');self.assertEqual(out[0]['previous_edge_id'],'OLD');self.assertEqual(changes[0]['source_handles_matched'],['SOURCE']);self.assertEqual(rows,original)
 def test_unmatched_source_or_competing_incidence_rejected(self):
  rows,g=self.fixture();g['edges'][0]['source_handles']=['OTHER']
  with self.assertRaises(ValueError):rebind(rows,g)
  rows,g=self.fixture();g['edges'].append(dict(g['edges'][0],edge_id='E2'))
  with self.assertRaises(ValueError):rebind(rows,g)
 def test_retired_or_promoted_node_is_not_a_terminal(self):
  rows,g=self.fixture();g['nodes'][0]['node_type']='equipment'
  with self.assertRaises(ValueError):rebind(rows,g)
 def test_unchanged_edge_has_no_change_record(self):
  rows,g=self.fixture();rows[0]['edge_id']='NEW';self.assertEqual(rebind(rows,g)[1],[])
