import copy,unittest
import ezdxf
from source_dn_bulk_screen import screen

class BulkDnScreenTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.line=m.add_line((0,0),(0,100),dxfattribs={'layer':'供水'});self.text=m.add_text('DN65',dxfattribs={'layer':'标注','insert':(1,50),'height':10,'rotation':90})
  self.graph={'edges':[{'edge_id':'E1','system':'supply','attribute_paths':[[[0,0],[0,100]]]}]};self.policy={'source_layer_systems':{'供水':'supply','回水':'return'},'text_layers':['标注'],'geometry_tolerance':.05}
 def test_unique_match_is_not_accepted_or_assigned(self):
  before=copy.deepcopy(self.graph);r=screen(self.doc,self.graph,self.policy);row=r['records'][0];self.assertEqual(row['status'],'unique_source_line_and_graph_segment_candidate');self.assertEqual(row['edge_candidates'][0]['edge_id'],'E1');self.assertFalse(row['human_accepted']);self.assertEqual(self.graph,before)
 def test_ambiguous_native_lines_are_not_bound(self):
  self.doc.modelspace().add_line((2,0),(2,100),dxfattribs={'layer':'回水'});self.assertEqual(screen(self.doc,self.graph,self.policy)['records'][0]['status'],'ambiguous_source_lines')
 def test_graph_duplicate_geometry_is_ambiguous(self):
  self.graph['edges'].append({'edge_id':'E2','system':'supply','attribute_paths':[[[0,0],[0,100]]]});self.assertEqual(screen(self.doc,self.graph,self.policy)['records'][0]['status'],'ambiguous_graph_segments')
 def test_no_graph_match_and_missing_source_line_are_not_assigned(self):
  self.graph['edges'][0]['system']='return';self.assertEqual(screen(self.doc,self.graph,self.policy)['records'][0]['status'],'no_matching_graph_segment')
  self.policy['source_layer_systems']={'other':'supply'};self.assertEqual(screen(self.doc,self.graph,self.policy)['records'][0]['status'],'no_source_line_in_local_scope')
 def test_unsupported_transform_and_non_dn_are_not_fabricated(self):
  self.text.dxf.text_generation_flag=2;r=screen(self.doc,self.graph,self.policy);self.assertEqual(r['records'][0]['status'],'unsupported_text_transform');self.text.dxf.text='NOT_A_DN';self.assertEqual(screen(self.doc,self.graph,self.policy)['records'],[])
 def test_justified_oblique_and_invisible_text_are_not_located_by_insert(self):
  for field,value in [('halign',2),('valign',2),('oblique',15),('invisible',1)]:
   with self.subTest(field=field):
    self.setUp();setattr(self.text.dxf,field,value);self.assertEqual(screen(self.doc,self.graph,self.policy)['records'][0]['status'],'unsupported_text_transform')
 def test_nested_rotated_and_mirrored_source_line(self):
  self.doc.modelspace().delete_entity(self.line);blk=self.doc.blocks.new('B');blk.add_line((0,0),(100,0),dxfattribs={'layer':'供水'});root=self.doc.modelspace().add_blockref('B',(0,100),dxfattribs={'rotation':90,'xscale':-1});self.graph['edges'][0]['source_insert_handle']=root.dxf.handle;self.policy['include_graph_insert_lines']=True
  before=copy.deepcopy(self.graph);r=screen(self.doc,self.graph,self.policy);row=r['records'][0];self.assertEqual(row['status'],'unique_source_line_and_graph_segment_candidate');self.assertEqual(row['source_line_provenance']['root_handle'],root.dxf.handle);self.assertIsNone(row['source_line_handle']);self.assertEqual(self.graph,before)
 def test_nested_and_modelspace_competition_is_ambiguous(self):
  blk=self.doc.blocks.new('B');blk.add_line((2,0),(2,100),dxfattribs={'layer':'回水'});root=self.doc.modelspace().add_blockref('B',(0,0));self.graph['edges'][0]['source_insert_handle']=root.dxf.handle;self.policy['include_graph_insert_lines']=True
  self.assertEqual(screen(self.doc,self.graph,self.policy)['records'][0]['status'],'ambiguous_source_lines')
 def test_non_insert_reference_is_reported_not_decomposed(self):
  self.graph['edges'][0]['source_insert_handle']=self.line.dxf.handle;self.policy['include_graph_insert_lines']=True;r=screen(self.doc,self.graph,self.policy);self.assertEqual(r['nested_scope']['non_insert_references'][0]['type'],'LINE');self.assertEqual(r['records'][0]['status'],'unique_source_line_and_graph_segment_candidate')
 def test_nested_is_opt_in(self):
  self.doc.modelspace().delete_entity(self.line);blk=self.doc.blocks.new('B');blk.add_line((0,0),(0,100),dxfattribs={'layer':'供水'});root=self.doc.modelspace().add_blockref('B',(0,0));self.graph['edges'][0]['source_insert_handle']=root.dxf.handle
  self.assertEqual(screen(self.doc,self.graph,self.policy)['records'][0]['status'],'no_source_line_in_local_scope')
 def test_two_level_insert_transform_is_preserved(self):
  self.doc.modelspace().delete_entity(self.line);child=self.doc.blocks.new('CHILD');child.add_line((0,0),(100,0),dxfattribs={'layer':'供水'});parent=self.doc.blocks.new('PARENT');parent.add_blockref('CHILD',(0,0),dxfattribs={'rotation':90});root=self.doc.modelspace().add_blockref('PARENT',(0,0));self.graph['edges'][0]['source_insert_handle']=root.dxf.handle;self.policy['include_graph_insert_lines']=True
  r=screen(self.doc,self.graph,self.policy);self.assertEqual(r['records'][0]['status'],'unique_source_line_and_graph_segment_candidate');self.assertEqual(r['records'][0]['source_line_provenance']['root_handle'],root.dxf.handle)
 def test_endpoint_context_is_opt_in_and_does_not_assign(self):
  self.text.dxf.insert=(1,105);before=copy.deepcopy(self.graph);row=screen(self.doc,self.graph,self.policy)['records'][0];self.assertNotIn('endpoint_context_candidates',row);self.policy['endpoint_context_max_text_heights']=2
  row=screen(self.doc,self.graph,self.policy)['records'][0];self.assertEqual(row['status'],'no_source_line_in_local_scope');self.assertEqual(row['endpoint_context_candidates'][0]['graph_segment_candidates'][0]['edge_id'],'E1');self.assertEqual(row['edge_candidates'],[]);self.assertFalse(row['human_accepted']);self.assertEqual(self.graph,before)
 def test_endpoint_context_keeps_competitors_and_no_wrong_system_match(self):
  self.text.dxf.insert=(1,105);self.doc.modelspace().add_line((2,0),(2,100),dxfattribs={'layer':'回水'});self.policy['endpoint_context_max_text_heights']=2;row=screen(self.doc,self.graph,self.policy)['records'][0]
  self.assertEqual(len(row['endpoint_context_candidates']),2);self.assertEqual(row['endpoint_context_candidates'][1]['graph_segment_candidates'],[]);self.assertEqual(row['status'],'no_source_line_in_local_scope')
 def test_endpoint_policy_bounds(self):
  for value in [-1,6,True,float('nan')]:
   self.policy['endpoint_context_max_text_heights']=value
   with self.assertRaises(ValueError):screen(self.doc,self.graph,self.policy)
if __name__=='__main__':unittest.main()
