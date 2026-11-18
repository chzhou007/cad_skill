import copy,unittest,ezdxf
from source_floor_group_diameter_evidence import attach

class GroupDiameterTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();t=self.doc.modelspace().add_text('CHWS-DN200');self.t=t
  members=[{'floor':'F1','node_id':'U1'},{'floor':'F2','node_id':'U2'}];self.g={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'U1','floor':'F1','source_floor_alignment_candidate':{'group_id':'G','members':members}},{'node_id':'U2','floor':'F2','source_floor_alignment_candidate':{'group_id':'G','members':members}}], 'edges':[{'edge_id':'E1','start_node_id':'U1','end_node_id':'T1','diameter_nominal_mm':200,'diameter_status':'verified_source_annotation','pipe_diameter':{'status':'verified_source_annotation','nominal_mm':200,'observations':[{'text':{'handle':t.dxf.handle,'text':'DN200','original_text':'CHWS-DN200'},'status':'assigned','edge_id':'E1','nominal_mm':200}]}},{'edge_id':'E2','start_node_id':'U2','end_node_id':'T2','diameter_nominal_mm':None,'diameter_status':'unannotated'}],'sourceFloorAlignmentCandidates':[{'group_id':'G','members':members}]}
  self.e={'source_sha256':'s','graph_sha256':'g','groups':1,'records':[{'group_id':'G','members':[{'floor':'F1','node_id':'U1','edge_id':'E1','diameter_nominal_mm':200,'diameter_status':'verified_source_annotation'},{'floor':'F2','node_id':'U2','edge_id':'E2','diameter_nominal_mm':None,'diameter_status':'unannotated'}]}]}
 def call(self):return attach(self.g,self.e,'s','g',self.doc)
 def test_direct_diameter_does_not_propagate(self):
  original=copy.deepcopy(self.g);out,v=self.call();self.assertEqual(self.g,original);self.assertEqual(out['edges'],original['edges']);members=out['sourceFloorAlignmentCandidates'][0]['members'];self.assertEqual(members[0]['direct_diameter_mm'],200);self.assertIsNone(members[1]['direct_diameter_mm']);self.assertEqual(v['direct_annotated_members'],1)
 def test_reject_wrong_native_text_or_wrong_edge(self):
  self.t.dxf.text='CHWS-DN250'
  with self.assertRaisesRegex(ValueError,'Native diameter'):self.call()
  self.t.dxf.text='CHWS-DN200';self.e['records'][0]['members'][0]['edge_id']='OTHER'
  with self.assertRaisesRegex(ValueError,'Changed floor edge'):self.call()

if __name__=='__main__':unittest.main()
