import copy,unittest
import ezdxf
from repair_native_flexible_joints import fingerprint
from screen_missing_gap_joints import screen,bind_final


class MissingGapJoints(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();b=self.doc.blocks.new('JOINT');b.add_line((-150,-20),(-150,20));b.add_line((150,-20),(150,20));b.add_point((-150,0));b.add_point((150,0));b.add_spline([(0,0),(1,1),(2,0),(3,1)]);ins=self.doc.modelspace().add_blockref('JOINT',(250,0))
  self.graph={'edges':[{'edge_id':'E','system':'supply'}]};self.coverage={'source_sha256':'s','graph_sha256':'g','edges':[{'edge_id':'E','system':'supply','segments':[{'index':0,'status':'single_source_line_covers','start':[-100,0],'end':[0,0],'witnesses':[{'source_handle':'A'}]},{'index':1,'status':'no_witness_in_scoped_search','start':[0,0],'end':[500,0]},{'index':2,'status':'single_source_line_covers','start':[500,0],'end':[600,0],'witnesses':[{'source_handle':'B'}]}]}]};self.hashes={'source_sha256':'s','graph_sha256':'g','coverage_sha256':'c','inventory_sha256':'i'}
  self.policy={**self.hashes,'block_name':'JOINT','block_fingerprint_sha256':fingerprint(b),'selections':[{'edge_id':'E','segment_index':1,'insert_handle':ins.dxf.handle}]};self.handle=ins.dxf.handle
 def test_gap_joint_stays_unassigned_and_length_unknown(self):
  result=screen(self.doc,self.coverage,self.graph,[],self.policy,self.hashes);r=result['records'][0]
  self.assertEqual(r['unwitnessed_end_clearances'],[100,100]);self.assertEqual(r['joint_marker_drawing_span'],300);self.assertEqual(r['physical_length'],'unknown');self.assertFalse(result['graph_mutated'])
 def test_existing_instance_and_stale_input_rejected(self):
  with self.assertRaises(ValueError):screen(self.doc,self.coverage,self.graph,[{'source_top_handle':self.handle}],self.policy,self.hashes)
  bad=copy.deepcopy(self.coverage);bad['source_sha256']='other'
  with self.assertRaises(ValueError):screen(self.doc,bad,self.graph,[],self.policy,self.hashes)
 def test_neighbour_without_source_witness_rejected(self):
  bad=copy.deepcopy(self.coverage);bad['edges'][0]['segments'][0]['status']='no_witness_in_scoped_search'
  with self.assertRaises(ValueError):screen(self.doc,bad,self.graph,[],self.policy,self.hashes)
 def test_final_graph_rebinding_rejects_edge_changes(self):
  result=screen(self.doc,self.coverage,self.graph,[],self.policy,self.hashes)
  self.assertEqual(bind_final(result,self.graph,self.graph,'final')['candidate_count'],1)
  changed=copy.deepcopy(self.graph);changed['edges'][0]['system']='return'
  with self.assertRaises(ValueError):bind_final(result,self.graph,changed,'final')
if __name__=='__main__':unittest.main()
