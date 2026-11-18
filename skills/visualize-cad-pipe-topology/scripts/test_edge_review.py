"""Manual length authority, history, stale writers and source conservation."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/viewer'))
from test_hil import HilTest
from edge_review_store import save_edge_review
from hil_server import ReviewError

class EdgeReviewTests(HilTest):
 def write_edge(self,action='setLength',**kw):
  return save_edge_review(self.store,{'datasetId':self.store.dataset,'baseRevision':self.store.read()['revision'],'edgeId':'E1','action':action,'lengthM':12.35,'note':'专家实测 中文','author':'expert',**kw})
 def test_length_reload_reset_history_and_original(self):
  original=copy.deepcopy(self.store.graph);d=self.write_edge();self.assertEqual(d['edgeEdits']['E1']['length']['valueM'],12.35)
  self.assertEqual(self.store.read()['edgeEdits'],d['edgeEdits']);d=self.write_edge('resetLength');self.assertNotIn('length',d['edgeEdits']['E1']);self.assertEqual(len(d['edgeEditHistory']),2);self.assertEqual(self.store.graph,original)
 def test_invalid_values_and_unknown_ids(self):
  for value in [None,False,0,-1,float('nan'),float('inf'),'12']:
   with self.assertRaises(ReviewError):self.write_edge(lengthM=value)
  with self.assertRaises(ReviewError):self.write_edge(edgeId='NOPE')
  self.assertEqual(self.store.read()['revision'],0)
 def test_stale_and_wrong_dataset_do_not_overwrite(self):
  self.write_edge()
  for kw in [{'baseRevision':0},{'datasetId':'other'}]:
   with self.assertRaises(ReviewError):self.write_edge(**kw)
  self.assertEqual(self.store.read()['revision'],1)
 def test_edits_invalidate_confirmation_preserve_issues(self):
  d=self.initial();self.save(d,confirm=True,reviewer='original');d=self.write_edge();self.assertIsNone(d['confirmation']);self.assertEqual(len(d['errors']),1);self.assertEqual(len(d['historicalConfirmations']),1)
  d=self.write_edge('review');self.assertIn('reviewed',d['edgeEdits']['E1']);d=self.write_edge();self.assertNotIn('reviewed',d['edgeEdits']['E1'])
 def test_normal_hil_save_preserves_manual_values(self):
  d=self.write_edge();d['errors']=[self.issue()];d=self.save(d);self.assertEqual(d['edgeEdits']['E1']['length']['valueM'],12.35)

if __name__=='__main__':unittest.main()
