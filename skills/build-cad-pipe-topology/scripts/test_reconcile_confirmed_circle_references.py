import copy
import unittest
from confirmed_circle_junctions import apply
from reconcile_confirmed_circle_references import reconcile
from test_confirmed_circle_junctions import ConfirmedCircleTests


class ReconciliationTests(unittest.TestCase):
 def setUp(self):
  fixture=ConfirmedCircleTests();fixture.setUp();h=fixture.handle
  fixture.graph['sourceThreeRimCandidates']=[{'circle_handle':h,'contacts':[{'node_id':'U'+str(i)} for i in range(3)]}]
  fixture.graph['technicalPending']=[{'id':'THREE-RIM-SOURCE-SEMANTICS'},{'id':'OTHER'}]
  self.graph,self.audit=fixture.run_apply()
  self.inventory={'source_sha256':'source','graph_sha256':'graph','records':[{'node_id':'U'+str(i),'edge_id':'E'+str(i),'family':'circle_rim'} for i in range(3)]+[{'node_id':'N0','edge_id':'E0','family':'other'}]}
 def run_reconcile(self):return reconcile(self.graph,self.inventory,graph_sha256='new',inventory_sha256='inv')
 def test_reconcile_preserves_topology_and_other_pending(self):
  before=copy.deepcopy(self.graph);g,inv,a=self.run_reconcile()
  self.assertEqual(self.graph,before);self.assertEqual(g['nodes'],before['nodes']);self.assertEqual(g['edges'],before['edges'])
  self.assertEqual(a['archived_terminal_records'],3);self.assertEqual(a['remaining_terminal_records'],1)
  self.assertEqual(len(g['sourceThreeRimCandidateHistory']['records']),1);self.assertNotIn('sourceThreeRimCandidates',g)
  self.assertTrue(any(p['id']=='OTHER' for p in g['technicalPending']));self.assertFalse(g['metadata']['hil_ready'])
  self.assertEqual(inv['retired_record_archive']['source_inventory_sha256'],'inv')
 def test_stale_or_duplicate_inventory_rejected(self):
  self.inventory['graph_sha256']='wrong'
  with self.assertRaises(ValueError):self.run_reconcile()
  self.inventory['graph_sha256']='graph';self.inventory['records'].append(copy.deepcopy(self.inventory['records'][0]))
  with self.assertRaises(ValueError):self.run_reconcile()
 def test_wrong_candidate_or_edge_rejected(self):
  self.graph['sourceThreeRimCandidates'][0]['contacts'][0]['node_id']='unknown'
  with self.assertRaises(ValueError):self.run_reconcile()
  self.graph['sourceThreeRimCandidates'][0]['contacts'][0]['node_id']='U0';self.graph['edges'][0]['start_node_id']='N0'
  with self.assertRaises(ValueError):self.run_reconcile()
 def test_unconfirmed_candidates_remain_pending(self):
  self.graph['sourceThreeRimCandidates'].append({'circle_handle':'OTHER','contacts':[]})
  g,inv,a=self.run_reconcile();self.assertEqual(a['unresolved_circle_candidates'],1)
  self.assertEqual(g['sourceThreeRimCandidates'][0]['circle_handle'],'OTHER')
  self.assertTrue(any(p['id']=='THREE-RIM-SOURCE-SEMANTICS' for p in g['technicalPending']))
 def test_unrelated_family_handles_remain_pending(self):
  self.graph['preHilComparison']['families'].append({'id':'three-rim-source-semantics','status':'algorithm_pending','source_handles':['OTHER']})
  g,_,_=self.run_reconcile()
  self.assertTrue(any(p['id']=='THREE-RIM-SOURCE-SEMANTICS' for p in g['technicalPending']))
  self.assertEqual(g['preHilComparison']['families'][-1]['status'],'algorithm_pending')
 def test_nonincident_inventory_edge_rejected(self):
  self.inventory['records'][-1]['edge_id']='E1'
  with self.assertRaises(ValueError):self.run_reconcile()
 def test_removed_inventory_edge_mismatch_rejected(self):
  self.inventory['records'][0]['edge_id']='E1'
  with self.assertRaises(ValueError):self.run_reconcile()

if __name__=='__main__':unittest.main()
