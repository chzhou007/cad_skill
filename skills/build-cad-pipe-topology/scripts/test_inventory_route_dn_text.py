import unittest,ezdxf
from inventory_route_dn_text import inventory

class RouteDnInventoryTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new('R2010');m=self.doc.modelspace();m.add_text('DN300',dxfattribs={'insert':(5,2),'layer':'空调平面'});m.add_text('DN65',dxfattribs={'insert':(100,100)});m.add_text('风机房',dxfattribs={'insert':(5,3)})
  self.graph={'metadata':{'source_sha256':'s'},'edges':[{'edge_id':'E','path':[[0,0],[10,0]]}]};self.policy={'source_sha256':'s','graph_sha256':'g','edge_ids':['E'],'margin_native_units':3}
 def test_scoped_inventory_does_not_bind_or_select_value(self):
  r=inventory(self.doc,self.graph,self.policy,'s','g');self.assertEqual([x['text'] for x in r['texts']],['DN300']);self.assertEqual(r['texts'][0]['layer'],'空调平面');self.assertFalse(r['mapping_ready']);self.assertFalse(r['hil_ready'])
 def test_proxy_summary_distinguishes_model_blocks_and_objects(self):
  from inventory_route_dn_text import proxy_inventory
  class Entity:
   def __init__(self,kind):self.kind=kind
   def dxftype(self):return self.kind
  class Block(list):name='B'
  class Doc:
   blocks=[Block([Entity('ACAD_PROXY_ENTITY'),Entity('LINE')])]
   objects=[Entity('ACAD_PROXY_OBJECT')]
   def modelspace(self):return [Entity('LINE'),Entity('ACAD_PROXY_ENTITY')]
  result=proxy_inventory(Doc());self.assertEqual(result['modelspace_direct_types'],{'ACAD_PROXY_ENTITY':1});self.assertEqual(result['objects_section_types'],{'ACAD_PROXY_OBJECT':1});self.assertEqual(result['block_definitions_with_direct_proxy_entities'][0]['direct_proxy_types'],{'ACAD_PROXY_ENTITY':1});self.assertIn('opaque',result['scope'])
 def test_reject_stale_scope_or_missing_edge(self):
  self.policy['graph_sha256']='old'
  with self.assertRaisesRegex(ValueError,'stale'):inventory(self.doc,self.graph,self.policy,'s','g')
  self.policy.update(graph_sha256='g',edge_ids=['missing'])
  with self.assertRaisesRegex(ValueError,'missing'):inventory(self.doc,self.graph,self.policy,'s','g')
 def test_numbered_dn_is_reported_without_edge_binding(self):
  self.doc.modelspace().add_text('CHWS1 DN450',dxfattribs={'insert':(6,2),'layer':'空调平面'})
  r=inventory(self.doc,self.graph,self.policy,'s','g');row=next(x for x in r['texts'] if x['text']=='CHWS1 DN450')
  self.assertEqual(row['named_dn_candidate']['route_number'],'1');self.assertEqual(row['named_dn_candidate']['nominal_mm'],450);self.assertEqual(row['named_dn_candidate']['binding_status'],'unbound_source_text_candidate');self.assertNotIn('edge_id',row);self.assertFalse(r['mapping_ready'])
 def test_axis_graph_requires_matching_receipt_and_uses_path_points(self):
  self.graph['metadata']={};self.graph['edges'][0]['path_points']=self.graph['edges'][0].pop('path')
  with self.assertRaisesRegex(ValueError,'receipt'):inventory(self.doc,self.graph,self.policy,'s','g')
  receipt={'inputs':{'dxf':'s'},'final_graph_sha256':'g'}
  self.assertFalse(inventory(self.doc,self.graph,self.policy,'s','g',receipt)['mapping_ready'])
  receipt['final_graph_sha256']='other'
  with self.assertRaisesRegex(ValueError,'receipt'):inventory(self.doc,self.graph,self.policy,'s','g',receipt)
  self.graph['metadata']={'source_sha256':'other'};receipt['final_graph_sha256']='g'
  with self.assertRaisesRegex(ValueError,'stale'):inventory(self.doc,self.graph,self.policy,'s','g',receipt)
 def test_nested_visible_text_is_reported(self):
  block=self.doc.blocks.new('S');block.add_text('DN65',dxfattribs={'insert':(0,0),'height':1});self.doc.modelspace().add_blockref('S',(5,1))
  r=inventory(self.doc,self.graph,self.policy,'s','g');self.assertIn('DN65',[x['text'] for x in r['texts']]);self.assertTrue(any(x['scope']=='decomposed_insert' for x in r['texts']))
 def test_representation_screen_never_claims_no_f_marker(self):
  self.doc.modelspace().add_lwpolyline([(0,0),(1,0),(1,1)],dxfattribs={'layer':'空调平面'});self.doc.modelspace().add_line((4,1),(6,1),dxfattribs={'layer':'空调平面'})
  x=inventory(self.doc,self.graph,self.policy,'s','g')['f_leader_representation'];self.assertEqual(x['open_straight_two_or_three_vertex_count'],1);self.assertEqual(x['status'],'representation_inventory_not_absence_proof');self.assertTrue(x['near_text_line_clues'][0]['same_layer_modelspace_lines'])
if __name__=='__main__':unittest.main()
