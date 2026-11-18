import copy,unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from source_roof_tower_reconciliation import reconcile

class Entity:
 def __init__(self,kind,**values):self.kind=kind;self.dxf=NS(**values)
 def dxftype(self):return self.kind
 def plain_text(self):return '冷塔单模块'

class RoofTowerTest(unittest.TestCase):
 def setUp(self):
  root=Entity('INSERT',name='root',handle='486',xscale=1,yscale=1,rotation=0,insert=NS(x=0,y=0))
  parent=Entity('INSERT',name='parent',handle='39A68',owner='root-record',xscale=1,yscale=1,rotation=0,insert=NS(x=0,y=0))
  body=Entity('INSERT',name='X-建筑底图_t3$0$kt1.25',handle='A1',owner='parent-record',layer='equipment')
  self.doc=NS(entitydb={'486':root,'39A68':parent,'A1':body,'59E27':Entity('TEXT')},blocks={'root':NS(block_record_handle='root-record'),'parent':NS(block_record_handle='parent-record')})
  self.graph={'metadata':{'source_sha256':'s'},'nodes':[],'edges':[{'edge_id':'E'}]}
  self.inv={'source_sha256':'s','graph_sha256':'g','source_caption':'冷塔单模块','source_caption_handle':'59E27','candidate_insert_count':1,'candidates':[{'source_chain':['486','39A68','A1'],'block':body.dxf.name,'source_layer':'equipment','world_bbox':[0,0,10,20]}]}
  self.box=NS(has_data=True,extmin=NS(x=0,y=0),extmax=NS(x=10,y=20))
 def apply(self):
  with patch('source_roof_tower_reconciliation.bbox.extents',return_value=self.box):return reconcile(self.doc,self.graph,self.inv,'s','g')
 def test_body_added_without_pipe_or_port_inference(self):
  old=copy.deepcopy(self.graph);out,proof=self.apply();self.assertEqual(self.graph,old);self.assertEqual(out['edges'],old['edges']);self.assertEqual(out['nodes'][0]['source_ports'],[]);self.assertEqual(proof['ports_inferred'],0)
 def test_stale_evidence_and_wrong_chain_fail_closed(self):
  self.inv['graph_sha256']='stale'
  with self.assertRaises(ValueError):self.apply()
  self.inv['graph_sha256']='g';self.doc.entitydb['A1'].dxf.owner='wrong'
  with self.assertRaisesRegex(ValueError,'ancestry'):self.apply()
 def test_duplicate_or_changed_geometry_fail_closed(self):
  self.inv['candidates'].append(copy.deepcopy(self.inv['candidates'][0]));self.inv['candidate_insert_count']=2
  with self.assertRaises(ValueError):self.apply()
  self.inv['candidates'].pop();self.inv['candidate_insert_count']=1;self.box.extmax.x=11
  with self.assertRaisesRegex(ValueError,'extent'):self.apply()

if __name__=='__main__':unittest.main()
