import copy,unittest,ezdxf
from native_line_path_evidence import collect as line_collect
from native_segment_dn_candidates import collect

def fixture():
 d=ezdxf.new();m=d.modelspace();a=m.add_line((0,0),(100,0),dxfattribs={'layer':'空调冷冻水供水'});b=m.add_line((100,0),(100,100),dxfattribs={'layer':'空调冷冻水供水'});t=m.add_text('DN200(3.000)',dxfattribs={'insert':(40,2),'height':5,'layer':'空调平面'});g={'edges':[{'edge_id':'E','system':'supply','connection_mode':'continuous_original_cad_pipe','attribute_paths':[[[0,0],[100,0],[100,100]]]}]};w=line_collect(d,g,{'source_sha256':'S','graph_sha256':'G','selections':[{'edge_id':'E','line_handles':[a.dxf.handle,b.dxf.handle]}]},'S','G');p={'source_sha256':'S','graph_sha256':'G','line_evidence_sha256':'L','text_layers':['空调平面'],'selections':[{'edge_id':'E','segment_index':0,'text_handle':t.dxf.handle,'expected_text':'DN200(3.000)'}]};return d,g,w,p
class SegmentDNCandidateTest(unittest.TestCase):
 def test_aligned_text_insert_is_not_used_as_source_position(self):
  d,g,w,p=fixture();d.entitydb[p['selections'][0]['text_handle']].dxf.halign=2
  with self.assertRaisesRegex(ValueError,'unsupported text transform'):collect(d,g,w,p,'S','G','L')
 def test_source_segment_and_no_graph_mutation(self):
  d,g,w,p=fixture();before=copy.deepcopy(g);r=collect(d,g,w,p,'S','G','L');self.assertEqual(g,before);self.assertEqual(r['observations'][0]['nominal_mm_candidate'],200);self.assertEqual(r['observations'][0]['parenthesized_source_value'],'3.000');self.assertFalse(r['hil_ready'])
 def test_hash_and_wrong_segment_rejected(self):
  d,g,w,p=fixture()
  with self.assertRaisesRegex(ValueError,'hash'):collect(d,g,w,p,'S','G','bad')
  p['selections'][0]['segment_index']=1
  with self.assertRaisesRegex(ValueError,'ambiguous'):collect(d,g,w,p,'S','G','L')
 def test_competing_source_line_and_altered_text_rejected(self):
  d,g,w,p=fixture();d.modelspace().add_line((0,3),(100,3),dxfattribs={'layer':'空调冷冻水回水'})
  with self.assertRaisesRegex(ValueError,'ambiguous'):collect(d,g,w,p,'S','G','L')
  d,g,w,p=fixture();p['selections'][0]['expected_text']='DN150'
  with self.assertRaisesRegex(ValueError,'invalid text'):collect(d,g,w,p,'S','G','L')
 def test_duplicate_text_selection_and_witness_tamper_rejected(self):
  d,g,w,p=fixture();p['selections'].append(dict(p['selections'][0]))
  with self.assertRaisesRegex(ValueError,'duplicate'):collect(d,g,w,p,'S','G','L')
  d,g,w,p=fixture();w['edges'][0]['segments'][0]['graph_end']=[99,0]
  with self.assertRaisesRegex(ValueError,'witness'):collect(d,g,w,p,'S','G','L')
 def test_referenced_nested_pipe_blocks_ambiguous_label(self):
  d,g,w,p=fixture();block=d.blocks.new('NESTED_PIPE');block.add_line((0,0),(100,0),dxfattribs={'layer':'空调冷冻水回水'});ref=d.modelspace().add_blockref('NESTED_PIPE',(0,3));g['edges'].append({'edge_id':'OTHER','system':'return','source_insert_handle':ref.dxf.handle,'attribute_paths':[]})
  with self.assertRaisesRegex(ValueError,'ambiguous'):collect(d,g,w,p,'S','G','L')
 def test_non_insert_reference_is_reported_not_decomposed(self):
  d,g,w,p=fixture();ref=d.modelspace().add_lwpolyline([(0,20),(10,20)]);g['edges'].append({'edge_id':'OTHER','source_insert_handle':ref.dxf.handle,'attribute_paths':[]})
  self.assertIn(ref.dxf.handle,collect(d,g,w,p,'S','G','L')['non_insert_source_references_not_decomposed'])
 def test_layer_zero_nested_line_blocks_without_guessing_system(self):
  d,g,w,p=fixture();block=d.blocks.new('LAYER_ZERO');block.add_line((0,0),(100,0),dxfattribs={'layer':'0'});ref=d.modelspace().add_blockref('LAYER_ZERO',(0,3),dxfattribs={'layer':'空调'});g['edges'].append({'edge_id':'OTHER','source_insert_handle':ref.dxf.handle,'attribute_paths':[]})
  with self.assertRaisesRegex(ValueError,'ambiguous'):collect(d,g,w,p,'S','G','L')
 def test_withheld_source_text_is_recorded_without_attribution(self):
  d,g,w,p=fixture();t=d.modelspace().add_text('DN450',dxfattribs={'insert':(10,20),'height':5,'layer':'空调平面'});p['withheld_candidates']=[{'text_handle':t.dxf.handle,'expected_text':'DN450','reason':'competing nested line'}]
  result=collect(d,g,w,p,'S','G','L');self.assertEqual(result['withheld_observations'][0]['status'],'withheld_not_attributed');self.assertNotIn('edge_id',result['withheld_observations'][0])
  p['withheld_candidates'][0]['text_handle']=p['selections'][0]['text_handle']
  with self.assertRaisesRegex(ValueError,'selected withheld'):collect(d,g,w,p,'S','G','L')
if __name__=='__main__':unittest.main()
