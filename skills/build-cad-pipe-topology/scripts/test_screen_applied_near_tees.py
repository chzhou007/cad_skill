import copy,unittest,ezdxf
from screen_applied_near_tees import screen

class AppliedNearTeesTest(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();m=self.d.modelspace();layer='空调冷冻水供水';self.main=m.add_line((0,0),(0,10),dxfattribs={'layer':layer});self.branch=m.add_line((-5,5),(.5,5),dxfattribs={'layer':layer});mh=self.main.dxf.handle;bh=self.branch.dxf.handle
  self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'T','node_type':'tee','x':0,'y':5}],'edges':[{'edge_id':str(i),'start_node_id':'T','system':'supply','source_handles':[h]} for i,h in enumerate((mh,mh,bh))]}
  self.a={'near_junction':[{'source_handles':[bh],'main_source_handles':[mh],'original_endpoint':[.5,5],'semantic_endpoint':[0,5],'removed_length':.5,'physical_length':'unknown','action':'trim','status':'applied'}]};self.h={'source_sha256':'S','graph_sha256':'G','normalization_sha256':'N'};self.p={**self.h,'selections':[{'branch_handle':bh,'main_handle':mh,'system':'supply','node_id':'T'}]}
 def test_reports_pending_without_mutation(self):
  old=copy.deepcopy(self.g);r=screen(self.d,self.g,self.a,self.p,self.h);self.assertEqual(old,self.g);self.assertFalse(r['human_accepted']);self.assertEqual(len(r['records'][0]['incident_edge_ids']),3)
 def test_wrong_source_and_mixed_system_fail(self):
  self.g['edges'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'incidence'):screen(self.d,self.g,self.a,self.p,self.h)
  self.setUp();self.a['near_junction'][0]['original_endpoint']=[2,5]
  with self.assertRaises(ValueError):screen(self.d,self.g,self.a,self.p,self.h)
 def test_stale_and_duplicate_fail(self):
  self.p['graph_sha256']='stale'
  with self.assertRaisesRegex(ValueError,'stale'):screen(self.d,self.g,self.a,self.p,self.h)
  self.p['graph_sha256']='G';self.p['selections']*=2
  with self.assertRaisesRegex(ValueError,'duplicate'):screen(self.d,self.g,self.a,self.p,self.h)
if __name__=='__main__':unittest.main()
