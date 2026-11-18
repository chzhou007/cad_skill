import copy,unittest
from source_internal_junction_candidates import attach

class InternalJunctionTest(unittest.TestCase):
 def setUp(self):
  self.g={'metadata':{'original_dxf_sha256':'s'},'nodes':[{'node_id':'CT','node_type':'equipment','source_tag_handle':'TAG','ports':[{'port_id':'P'}]},{'node_id':'T','node_type':'tee'}],
          'edges':[{'edge_id':f'E{i}','start_node_id':'T','end_node_id':f'X{i}','system':'cooling_return','source_handles':['H' if i==0 else str(i)]}for i in range(3)]}
  self.e={'source_02_sha256':'s','graph_02_sha256':'g','tower_count':1,'return_entry_count':1,'records':[{'tower_id':'CT','internal_junction_id':'T','current_edge_id':'E0','incident_edges':['E0','E1','E2'],'native_source_line':'H','original_02_tag_handle':'TAG','original_02_cell_handles':['A','B']}]}
 def apply(self):return attach(self.g,self.e,'s','g')
 def test_candidate_preserves_paths_and_ports(self):
  before=copy.deepcopy(self.g);out,v=self.apply();self.assertEqual(self.g,before);self.assertEqual(out['edges'],before['edges']);self.assertEqual(out['nodes'][0]['ports'],before['nodes'][0]['ports']);self.assertFalse(out['metadata']['hil_ready']);self.assertEqual(v['physical_ports_inferred'],0)
 def test_wrong_hash_or_changed_incidence_fails(self):
  with self.assertRaises(ValueError):attach(self.g,self.e,'s','wrong')
  self.g['edges'][2]['system']='supply'
  with self.assertRaises(ValueError):self.apply()
 def test_existing_owner_is_never_overwritten(self):
  self.g['nodes'][1]['source_equipment_owner_candidate']={'old':True}
  with self.assertRaises(ValueError):self.apply()
 def test_wrong_equipment_tag_or_incomplete_cell_witness_rejected(self):
  self.e['records'][0]['original_02_tag_handle']='OTHER'
  with self.assertRaises(ValueError):self.apply()
  self.e['records'][0]['original_02_tag_handle']='TAG'
  self.e['records'][0]['original_02_cell_handles']=['A','A']
  with self.assertRaises(ValueError):self.apply()

if __name__=='__main__':unittest.main()
