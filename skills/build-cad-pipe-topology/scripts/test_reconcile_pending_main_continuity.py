import unittest,copy
from test_source_pending_main_continuity import PendingMainContinuityTest
from source_pending_main_continuity import attach
from reconcile_pending_main_continuity import reconcile,validate_references
class ReconcilePendingMainTest(unittest.TestCase):
 def setUp(self):
  f=PendingMainContinuityTest();f.setUp();self.f=f;g,_=attach(f.graph,f.doc,f.pending,'S');g['edges'][1]['edge_id']='R-new';self.g=g;self.h={'source_sha256':'S','graph_sha256':'G','pending_sha256':'P','devices_sha256':'D'};self.p=dict(self.h,node_ids=['U'])
 def test_rebinds_native_main_only_and_preserves_branch_pending(self):
  old=copy.deepcopy(self.g);g,changes=reconcile(self.g,self.f.doc,self.f.pending,self.p,self.h);self.assertEqual(self.g,old);self.assertEqual(g['nodes'][0]['source_main_continuation']['main_edge_ids'],['L','R-new']);self.assertEqual(g['nodes'][0]['source_main_continuation']['branch_connectivity'],'pending');self.assertEqual(g['nodes'][0]['source_main_continuation_history'][0]['evidence']['main_edge_ids'],['L','R']);self.assertEqual(g['edges'],self.g['edges'])
 def test_reference_gate_fails_old_ids_then_accepts_rebind(self):
  with self.assertRaisesRegex(ValueError,'stale pending main'):validate_references(self.g)
  out,_=reconcile(self.g,self.f.doc,self.f.pending,self.p,self.h);self.assertEqual(validate_references(out),['U'])
 def test_changed_source_or_ambiguous_graph_rejected(self):
  self.g['nodes'][0]['source_main_continuation']['branch_source_handle']='wrong'
  with self.assertRaises(ValueError):reconcile(self.g,self.f.doc,self.f.pending,self.p,self.h)
  self.g['nodes'][0]['source_main_continuation']['branch_source_handle']=self.f.branch.dxf.handle;self.g['edges'][2]['source_handles'].append(self.f.main.dxf.handle)
  with self.assertRaises(ValueError):reconcile(self.g,self.f.doc,self.f.pending,self.p,self.h)
 def test_missing_old_evidence_and_hash_rejected(self):
  self.g['nodes'][0].pop('source_main_continuation')
  with self.assertRaises(ValueError):reconcile(self.g,self.f.doc,self.f.pending,self.p,self.h)
  self.p['graph_sha256']='bad'
  with self.assertRaises(ValueError):reconcile(self.g,self.f.doc,self.f.pending,self.p,self.h)
if __name__=='__main__':unittest.main()
