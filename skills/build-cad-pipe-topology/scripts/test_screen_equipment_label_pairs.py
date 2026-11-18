import copy,unittest,ezdxf
from screen_equipment_label_pairs import screen

class EquipmentLabelPairsTest(unittest.TestCase):
 def setUp(self):
  self.p=ezdxf.new();b=self.p.blocks.new('40kW');b.add_lwpolyline([(0,0),(100,0),(100,100),(0,100)],close=True);m=self.p.modelspace();a=m.add_blockref('40kW',(0,0));b=m.add_blockref('40kW',(0,300));t1=m.add_text('CRAH-1',dxfattribs={'insert':(150,0),'height':10,'rotation':90,'layer':'空调编号'});t2=m.add_text('CRAH-2',dxfattribs={'insert':(150,300),'height':10,'rotation':90,'layer':'空调编号'});self.a=ezdxf.new();self.a.modelspace().add_text('CRAH-1');self.a.modelspace().add_text('CRAH-2')
  self.pg={'metadata':{'source_sha256':'PS'},'nodes':[{'node_id':'A','node_type':'equipment','identity_status':'unresolved','source_handle':a.dxf.handle,'source_block':'40kW','x':50,'y':50},{'node_id':'B','node_type':'equipment','identity_status':'unresolved','source_handle':b.dxf.handle,'source_block':'40kW','x':50,'y':350}]};self.ag={'nodes':[{'node_id':'CRAH-1','node_type':'equipment'},{'node_id':'CRAH-2','node_type':'equipment'}]};self.h={'plan_source_sha256':'PS','axis_source_sha256':'AS','plan_graph_sha256':'PG','axis_graph_sha256':'AG','axis_receipt_sha256':'AR'};self.receipt={'inputs':{'dxf':'AS'},'final_graph_sha256':'AG','hil_ready':False};self.policy={**self.h,'groups':[{'id':'pair','node_ids':['A','B'],'label_handles':[t1.dxf.handle,t2.dxf.handle],'maximum_distance':1000}]}
 def test_retains_both_permutations_without_assignment(self):
  before=copy.deepcopy(self.pg);r=screen(self.p,self.a,self.pg,self.ag,self.receipt,self.policy,self.h);self.assertEqual(before,self.pg);self.assertEqual(len(r['groups'][0]['candidates']),2);self.assertIsNone(r['groups'][0]['selected_candidate']);self.assertFalse(r['mapping_ready'])
 def test_duplicate_axis_label_or_changed_source_fails(self):
  self.a.modelspace().add_text('CRAH-1')
  with self.assertRaisesRegex(ValueError,'uniquely'):screen(self.p,self.a,self.pg,self.ag,self.receipt,self.policy,self.h)
  self.setUp();self.pg['nodes'][0]['x']=500
  with self.assertRaisesRegex(ValueError,'position'):screen(self.p,self.a,self.pg,self.ag,self.receipt,self.policy,self.h)
 def test_stale_graph_and_duplicate_group_fail(self):
  self.policy['axis_graph_sha256']='stale'
  with self.assertRaisesRegex(ValueError,'stale'):screen(self.p,self.a,self.pg,self.ag,self.receipt,self.policy,self.h)
  self.policy['axis_graph_sha256']='AG';self.policy['groups'].append(self.policy['groups'][0])
  with self.assertRaisesRegex(ValueError,'scope'):screen(self.p,self.a,self.pg,self.ag,self.receipt,self.policy,self.h)
if __name__=='__main__':unittest.main()
