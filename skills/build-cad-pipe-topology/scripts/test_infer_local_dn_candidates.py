import copy,unittest
from infer_local_dn_candidates import calculate
class CandidateInheritance(unittest.TestCase):
 def setUp(self):
  self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'T','node_type':'tee'},{'node_id':'A','node_type':'virtual_equipment'},{'node_id':'B','node_type':'virtual_equipment'},{'node_id':'C','node_type':'equipment'}],'edges':[{'edge_id':'E1','system':'supply','start_node_id':'T','end_node_id':'A','pipe_diameter':{'observations':[{'text':{'handle':'TXT','text':'DN300'},'nominal_mm':300,'status':'native_source_local_observation'}]},'diameter_nominal_mm':None},{'edge_id':'E2','system':'supply','start_node_id':'T','end_node_id':'B'},{'edge_id':'E3','system':'supply','start_node_id':'T','end_node_id':'C'}]}
  self.p={'source_sha256':'S','graph_sha256':'G','edges':['E1','E2','E3'],'junctions':['T'],'junction_witnesses':[{'node_id':'T'}],'seeds':[{'edge_id':'E1','text_handle':'TXT','nominal_mm':300}]}
  self.cover={'source_sha256':'S','graph_sha256':'G','edges':[{'edge_id':e,'segments':[{'status':'single_source_line_covers'}]} for e in self.p['edges']]};self.rays={'source_sha256':'S','graph_sha256':'G','junctions':[{'node_id':'T'}]};self.risk={'source_sha256':'S','graph_sha256':'G','observations':[]};self.nested={'source_sha256':'S','graph_sha256':'G','selected_edges':['E1','E2','E3'],'nearby_nested_dn':[]}
 def call(self):return calculate(self.g,self.p,self.cover,self.rays,self.risk,self.nested,'S','G')
 def test_inherited_only_as_candidates_with_lineage(self):
  old=copy.deepcopy(self.g);out,a=self.call();self.assertEqual(old,self.g);self.assertFalse(a['edgewide_values_assigned']);e=next(e for e in out['edges'] if e['edge_id']=='E2');self.assertIsNone(e['diameter_nominal_mm']);self.assertEqual(e['diameter_inference']['nominal_mm_candidate'],300);self.assertEqual(e['diameter_inference']['lineage'][0]['edge_path'],['E1','E2']);self.assertFalse(out['metadata']['hil_ready'])
 def test_stale_missing_or_ambiguous_coverage_rejected(self):
  self.cover['graph_sha256']='old'
  with self.assertRaises(ValueError):self.call()
  self.cover['graph_sha256']='G';self.cover['edges'][0]['segments'][0]['status']='ambiguous_multiple_witnesses'
  with self.assertRaises(ValueError):self.call()
 def test_unparsed_or_different_nearby_dn_blocks_propagation(self):
  self.risk['observations']=[{'geometric_candidate_edge_ids':['E2'],'syntax':'other_dn_text','parsed_single_dn':None}]
  with self.assertRaises(ValueError):self.call()
  self.risk['observations'][0].update(syntax='single_dn',parsed_single_dn={'nominal_mm':200})
  with self.assertRaises(ValueError):self.call()
 def test_nested_dn_conflict_or_unresolved_block_ref_blocks_candidate(self):
  self.nested['nearby_nested_dn']=[{'parsed_single_dn':{'nominal_mm':200}}]
  with self.assertRaises(ValueError):self.call()
  self.nested['nearby_nested_dn']=[];self.nested['xref_blocks']=['external']
  with self.assertRaises(ValueError):self.call()
 def test_wrong_system_or_pending_t_cannot_propagate(self):
  self.g['edges'][2]['system']='return'
  with self.assertRaises(ValueError):self.call()
  self.g['edges'][2]['system']='supply';self.g['nodes'][0]['resolution_state']='source_main_continuation_branch_pending'
  with self.assertRaises(ValueError):self.call()
 def test_unselected_conflicting_seed_and_existing_dn_rejected(self):
  self.g['edges'][1]['diameter_nominal_mm']=100
  with self.assertRaises(ValueError):self.call()
if __name__=='__main__':unittest.main()
