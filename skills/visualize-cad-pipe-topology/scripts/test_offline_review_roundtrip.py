"""Real backup roundtrip, atomic rejection and extraction-directory isolation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'assets/viewer'))
from test_hil import HilTest
from hil_server import ReviewError, ReviewStore
from edge_review_store import save_edge_review
from review_backup import restore_backup

class OfflineReviewTests(HilTest):
 def edit(self, **kw):
  return save_edge_review(self.store, dict(datasetId=self.store.dataset, baseRevision=self.store.read()['revision'],edgeId='E1', **kw))
 def restore(self, backup):
  return restore_backup(self.store, dict(baseRevision=self.store.read()['revision'],document=backup))
 def test_full_backup_roundtrip_retains_values_replies_and_old_history(self):
  doc=self.initial();response=self.response(doc)
  self.store.import_expert(dict(baseRevision=doc['revision'],response=response))
  self.edit(action='setLength',lengthM=12.35,note='中文备注\n第二行')
  self.edit(action='setDiameter',diameterScope='horizontal',diameterMm=250)
  backup=self.edit(action='setDiameter',diameterScope='vertical',diameterMm=400)
  self.edit(action='resetLength'); self.edit(action='saveNote',note='restore前的文字')
  previous=self.store.read();result=self.restore(backup)
  self.assertEqual(result['edgeEdits'],backup['edgeEdits'])
  self.assertEqual(result['errors'],backup['errors'])
  self.assertIn(previous['edgeEditHistory'][-1],result['edgeEditHistory'])
  self.assertEqual(json.loads((self.store.folder/'history'/f"{previous['revision']:08d}.json").read_text('utf8')),previous)
  self.assertEqual(ReviewStore(self.root).read(),result)
  self.assertIsNone(result['confirmation'])
 def test_legacy_backup_without_manual_attributes_and_explicit_clear(self):
  backup=self.initial();self.edit(action='setLength',lengthM=2)
  self.assertEqual(self.restore(backup)['edgeEdits'],{})
  backup=self.edit(action='saveNote',note='')
  self.assertEqual(self.restore(backup)['edgeEdits']['E1']['note'],'')
 def test_invalid_backup_rejected_atomically_and_stale_writer_blocked(self):
  backup=self.edit(action='setLength',lengthM=12)
  baseline=self.store.read()
  for field,value in [('datasetId','other'),('edgeEdits',{'missing':{}}),('edgeEdits',{'E1':{'length':{'valueM':0}}}),('edgeEdits',{'E1':{'diameters':{'sideways':{}}}}),('errors',[{}])]:
   bad=copy.deepcopy(backup);bad[field]=value
   with self.assertRaises((ReviewError,ValueError)): self.restore(bad)
   self.assertEqual(self.store.read(),baseline)
  with self.assertRaises(ReviewError):restore_backup(self.store,dict(baseRevision=0,document=backup))
  self.assertEqual(self.store.read(),baseline)
 def test_restoring_confirmation_archives_but_never_accepts(self):
  backup=self.save(self.initial(),confirm=True,reviewer='expert')
  result=self.restore(backup)
  self.assertIsNone(result['confirmation']);self.assertTrue(result['historicalConfirmations'])
 def test_same_bundle_other_directory_never_reuses_annotation_store(self):
  assets=Path(__file__).resolve().parents[1]/'assets/viewer'
  for name in ('serve.py','hil_server.py','edge_review_store.py','review_backup.py'):shutil.copy2(assets/name,self.root/name)
  self.manifest['preferredPort']=19500
  (self.root/'public/data/manifest.json').write_text(json.dumps(self.manifest),encoding='utf8')
  (self.root/'public/index.html').write_text('<meta name="cad-viewer-build" content="ui-v1">',encoding='utf8')
  second=self.root/'second';shutil.copytree(self.root,second,ignore=shutil.ignore_patterns('second'))
  with socket.socket()as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  def launch(root):return subprocess.Popen([sys.executable,'-B','-u',str(root/'serve.py'),'--port',str(port)],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8')
  def ready(proc):
   lines=[]
   reader=threading.Thread(target=lambda:lines.append(proc.stdout.readline()),daemon=True);reader.start();reader.join(15)
   self.assertFalse(reader.is_alive(),'server startup did not complete');return ''.join(lines)
  a=launch(self.root);b=None
  try:
   self.assertIn(f':{port}',ready(a))
   same=launch(self.root)
   try:self.assertIn('already running',same.communicate(timeout=15)[0]);self.assertEqual(same.returncode,0)
   finally:
    if same.poll()is None:same.terminate();same.wait(10)
   b=launch(second);line=ready(b);self.assertNotIn('already running',line)
   actual=int(line.strip().rsplit(':',1)[-1]);self.assertNotEqual(actual,port)
   with urlopen(f'http://127.0.0.1:{actual}/api/instance')as r:instance=json.load(r)
   expected=hashlib.sha256(os.path.normcase(str(second.resolve())).encode('utf8')).hexdigest()
   self.assertEqual(instance['instanceId'],expected)
   payload=dict(datasetId=self.store.dataset,baseRevision=0,edgeId='E1',action='saveNote',note='第二份包的备注')
   origin=f'http://127.0.0.1:{actual}'
   with urlopen(Request(origin+'/api/edge-review',data=json.dumps(payload).encode(),method='PUT',headers={'Origin':origin,'Content-Type':'application/json'}))as r:self.assertEqual(r.status,200)
   self.assertEqual(self.store.read()['revision'],0)
   self.assertEqual(ReviewStore(second).read()['edgeEdits']['E1']['note'],'第二份包的备注')
  finally:
   for proc in (a,b):
    if proc is not None:
     proc.terminate();proc.communicate(timeout=15)

if __name__=='__main__':unittest.main()
