"""Persistent diameter scopes and notes, including pre-fix invisible remarks."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/viewer'))
from test_hil import HilTest
from edge_review_store import save_edge_review
from hil_server import ReviewError

class AttributeReviewTests(HilTest):
 def edit(self,action,**kw):
  return save_edge_review(self.store,dict(datasetId=self.store.dataset,baseRevision=self.store.read()['revision'],edgeId='E1',action=action,**kw))
 def test_notes_without_length_roundtrip_clear_and_preserve(self):
  note='专家中文备注\n下一行 <不是HTML>'
  doc=self.edit('saveNote',note=note);self.assertEqual(doc['edgeEdits']['E1']['note'],note);self.assertNotIn('length',doc['edgeEdits']['E1'])
  doc=self.edit('setDiameter',diameterScope='horizontal',diameterMm=250);self.assertEqual(doc['edgeEdits']['E1']['note'],note)
  self.assertEqual(self.store.read()['edgeEdits']['E1']['note'],note)
  doc=self.edit('saveNote',note='');self.assertEqual(doc['edgeEdits']['E1']['note'],'')
 def test_directional_diameters_reset_do_not_change_other_scope_or_source(self):
  original=copy.deepcopy(self.store.graph)
  self.edit('setDiameter',diameterScope='horizontal',diameterMm=250,note='水平')
  doc=self.edit('setDiameter',diameterScope='vertical',diameterMm=450,note='垂直')
  self.assertEqual(doc['edgeEdits']['E1']['diameters']['horizontal']['nominalMm'],250)
  doc=self.edit('resetDiameter',diameterScope='horizontal')
  self.assertNotIn('horizontal',doc['edgeEdits']['E1']['diameters']);self.assertEqual(doc['edgeEdits']['E1']['diameters']['vertical']['nominalMm'],450)
  self.assertEqual(self.store.graph,original)
 def test_diameter_validation_and_stale_writer(self):
  for value in [None,True,0,-1,float('inf'),float('nan'),'DN200']:
   with self.assertRaises(ReviewError):self.edit('setDiameter',diameterScope='horizontal',diameterMm=value)
  with self.assertRaises(ReviewError):self.edit('setDiameter',diameterScope='wrong',diameterMm=200)
  self.assertEqual(self.store.read()['revision'],0)
  doc=self.edit('setDiameter',diameterScope='whole_edge',diameterMm=300)
  with self.assertRaises(ReviewError):save_edge_review(self.store,dict(datasetId=self.store.dataset,baseRevision=0,edgeId='E1',action='saveNote',note='stale'))
  self.assertEqual(self.store.read(),doc)
 def test_legacy_length_note_recovery(self):
  doc=self.edit('setLength',lengthM=12,note='旧版看不见的备注')
  for k in ['note','noteAuthor','noteUpdatedAt']:doc['edgeEdits']['E1'].pop(k,None)
  self.store.persist(doc)
  doc=self.edit('review');self.assertEqual(doc['edgeEdits']['E1']['note'],'旧版看不见的备注')

if __name__=='__main__':unittest.main()
