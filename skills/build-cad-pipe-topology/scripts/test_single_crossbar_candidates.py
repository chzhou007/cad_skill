import copy,unittest
import ezdxf
from single_crossbar_candidates import identify,attach

class SingleCrossbarCandidates(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.bar=m.add_line((0,-125),(0,125),dxfattribs={'layer':'pipe'});self.branch=m.add_line((0,0),(500,0),dxfattribs={'layer':'pipe'})
  self.graph={'metadata':{'source_sha256':'a'*64},'nodes':[{'node_id':'T','node_type':'tee','x':0,'y':0},{'node_id':'A','node_type':'virtual_equipment','x':0,'y':-125},{'node_id':'B','node_type':'virtual_equipment','x':0,'y':125},{'node_id':'C','node_type':'equipment','x':500,'y':0}],
   'edges':[{'edge_id':'E1','start_node_id':'T','end_node_id':'A','system':'supply','source_handles':[self.bar.dxf.handle]},{'edge_id':'E2','start_node_id':'T','end_node_id':'B','system':'supply','source_handles':[self.bar.dxf.handle]},{'edge_id':'E3','start_node_id':'T','end_node_id':'C','system':'supply','source_handles':[self.branch.dxf.handle]}]}
  self.profile={'source_sha256':'a'*64,'source_layers':['pipe'],'native_length':250,'tolerance':.1,'calibration_evidence':['native same-drawing reference']}
 def test_exact_single_bar_is_pending_without_graph_change(self):
  before=copy.deepcopy(self.graph);r=identify(self.graph,self.doc,self.profile);self.assertEqual(len(r),1);self.assertEqual(r[0]['status'],'source_shape_role_pending');self.assertFalse(r[0]['hydraulic_change']);self.assertEqual(self.graph,before)
 def test_negative_conflicting_system_and_protected_glyph(self):
  self.graph['edges'][2]['system']='return';self.assertFalse(identify(self.graph,self.doc,self.profile));self.graph['edges'][2]['system']='supply';self.graph['nodes'][1]['source_terminal_glyph_ids']=['known'];self.assertFalse(identify(self.graph,self.doc,self.profile))
 def test_negative_different_geometry_and_source(self):
  self.profile['native_length']=200;self.assertFalse(identify(self.graph,self.doc,self.profile));self.profile['native_length']=250;self.profile['source_sha256']='b'*64
  with self.assertRaises(ValueError):identify(self.graph,self.doc,self.profile)
 def test_negative_incomplete_end_or_nonperpendicular_branch(self):
  self.graph['nodes'][1]['y']=-100;self.assertFalse(identify(self.graph,self.doc,self.profile));self.graph['nodes'][1]['y']=-125;self.branch.dxf.end=(500,500,0);self.assertFalse(identify(self.graph,self.doc,self.profile))
 def test_mixed_source_requires_explicit_layers_and_review_flags(self):
  self.graph['edges'][2]['system']='return';self.branch.dxf.layer='return-pipe';self.profile.update(include_mixed_source_candidates=True,mixed_source_layers=['return-pipe'])
  self.assertFalse(identify(self.graph,self.doc,self.profile));self.graph['nodes'][0].update(mixed_source_contact=True,system_review_required=True)
  records=identify(self.graph,self.doc,self.profile);self.assertEqual(len(records),1);self.assertTrue(records[0]['mixed_source_contact']);self.assertEqual(records[0]['systems'],['return','supply'])
  self.profile['mixed_source_layers']=['other'];self.assertFalse(identify(self.graph,self.doc,self.profile))
 def test_attach_groups_three_nodes_without_changing_graph(self):
  before=copy.deepcopy(self.graph);out,audit=attach(self.graph,self.doc,self.profile);self.assertEqual(audit['groups'],1);self.assertEqual(audit['nodes'],3);self.assertEqual(out['edges'],before['edges']);self.assertEqual(self.graph,before)
  self.assertEqual({n['node_id'] for n in out['nodes'] if n.get('source_crossbar_candidate')},{'T','A','B'})
if __name__=='__main__':unittest.main()
