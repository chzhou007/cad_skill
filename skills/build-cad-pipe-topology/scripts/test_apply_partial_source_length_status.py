import copy,unittest,ezdxf
from native_path_coverage_audit import audit
from apply_partial_source_length_status import apply

def fixture():
 d=ezdxf.new();d.modelspace().add_line((0,0),(10,0),dxfattribs={'layer':'空调冷冻水供水'});g={'metadata':{'hil_ready':True},'nodes':[],'edges':[{'edge_id':'E','system':'supply','attribute_paths':[[[0,0],[10,0],[20,0]]],'path_length':20}]};c=audit(d,g,{'source_sha256':'S','graph_sha256':'G','edges':['E']},'S','G');p={'source_sha256':'S','graph_sha256':'G','coverage_sha256':'C','edge_ids':['E']};return g,c,p
class PartialLengthTest(unittest.TestCase):
 def test_source_and_display_separate_without_mutation(self):
  g,c,p=fixture();before=copy.deepcopy(g);out,r=apply(g,c,'S','G','C',p);e=out['edges'][0];self.assertEqual(g,before);self.assertEqual(e['drawing_path_length'],20);self.assertEqual(e['path_length'],10);self.assertFalse(e['path_length_complete']);self.assertEqual(e['physical_length'],'unknown');self.assertFalse(out['metadata']['hil_ready'])
 def test_tamper_and_wrong_hash_rejected(self):
  g,c,p=fixture()
  with self.assertRaisesRegex(ValueError,'hash'):apply(g,c,'S','G','wrong',p)
  c['edges'][0]['segments'][0]['end']=[11,0]
  with self.assertRaisesRegex(ValueError,'geometry'):apply(g,c,'S','G','C',p)
 def test_fully_uncovered_does_not_become_zero(self):
  g,c,p=fixture();c['edges'][0]['segments'][0]['status']='no_witness_in_scoped_search';c['edges'][0]['segments'][0]['witnesses']=[]
  with self.assertRaisesRegex(ValueError,'both witnessed'):apply(g,c,'S','G','C',p)
 def test_omission_edge_has_unknown_physical_length_and_retains_paths(self):
  g,c,p=fixture();g['nodes']=[{'node_id':'EQ','node_type':'equipment'},{'node_id':'T','node_type':'tee'}]
  e={'edge_id':'O','start_node_id':'EQ','end_node_id':'T','system':'supply','connection_mode':'omission_pair_stitched_at_main_marker','path_length':20,'attribute_paths':[[[0,0],[10,0]],[[20,0],[30,0]]]};g['edges'].append(e);p['unverified_omission_edge_ids']=['O']
  out,a=apply(g,c,'S','G','C',p);o=next(x for x in out['edges'] if x['edge_id']=='O');self.assertEqual(o['attribute_paths'],e['attribute_paths']);self.assertEqual(o['path_length'],20);self.assertFalse(o['path_length_complete']);self.assertEqual(o['physical_length'],'unknown');self.assertEqual(len(a['omission_edges']),1)
 def test_omission_not_generalized_to_joined_paths(self):
  g,c,p=fixture();g['nodes']=[{'node_id':'EQ','node_type':'equipment'},{'node_id':'T','node_type':'tee'}];g['edges'].append({'edge_id':'O','start_node_id':'EQ','end_node_id':'T','connection_mode':'omission_pair_stitched_at_main_marker','path_length':20,'attribute_paths':[[[0,0],[10,0]],[[10,0],[20,0]]]});p['unverified_omission_edge_ids']=['O']
  with self.assertRaisesRegex(ValueError,'separately expressed'):apply(g,c,'S','G','C',p)
if __name__=='__main__':unittest.main()
