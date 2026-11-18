import copy,unittest,ezdxf
from native_path_coverage_audit import audit

def fixture(nested=False):
 d=ezdxf.new();m=d.modelspace();layer='空调冷冻水供水';block=d.blocks.new('EQ');block.add_line((0,0),(10,0),dxfattribs={'layer':layer});i=m.add_blockref('EQ',(5,5),dxfattribs={'rotation':90})
 if nested:path=[[5,5],[5,15],[8,18]];handle=i.dxf.handle
 else:m.add_line((0,0),(10,0),dxfattribs={'layer':layer});path=[[0,0],[10,0],[20,0]];handle=None
 g={'edges':[{'edge_id':'E','system':'supply','attribute_paths':[path],'source_insert_handle':handle}]};p={'source_sha256':'S','graph_sha256':'G','edges':['E']};return d,g,p
class NativePathCoverageTest(unittest.TestCase):
 def test_partial_source_and_no_graph_mutation(self):
  d,g,p=fixture();before=copy.deepcopy(g);r=audit(d,g,p,'S','G');self.assertEqual(g,before);self.assertEqual([x['status'] for x in r['edges'][0]['segments']],['single_source_line_covers','no_witness_in_scoped_search']);self.assertEqual(r['edges'][0]['physical_length'],'unknown')
 def test_nested_rotated_insert(self):
  d,g,p=fixture(True);r=audit(d,g,p,'S','G');self.assertEqual(r['edges'][0]['segments'][0]['witnesses'][0]['scope'],'decomposed_selected_insert');self.assertEqual(r['edges'][0]['segments'][1]['status'],'no_witness_in_scoped_search')
 def test_multiport_polyline_is_not_pipe_coverage(self):
  d,g,p=fixture();marker=d.modelspace().add_lwpolyline([(0,0),(1,0)],dxfattribs={'layer':'DIM_SYMB'});e=g['edges'][0];e.update(start_node_id='V',end_node_id='T',start_port_id='P',source_insert_handle=marker.dxf.handle,connection_mode='standalone_multiport_omission_stitched_by_order',attribute_paths=[[[0,0],[1,0],[10,0]]]);g['nodes']=[{'node_id':'V','node_type':'virtual_equipment','source_marker_handle':marker.dxf.handle,'x':0,'y':0,'ports':[{'port_id':'P','system':'supply','x':1,'y':0}]}]
  d.modelspace().delete_entity(next(x for x in d.modelspace().query('LINE') if x.dxf.layer=='空调冷冻水供水'));d.modelspace().add_line((1,0),(10,0),dxfattribs={'layer':'空调冷冻水供水'})
  r=audit(d,g,p,'S','G');self.assertEqual([x['status'] for x in r['edges'][0]['segments']],['no_witness_in_scoped_search','single_source_line_covers'])
  g['nodes'][0]['ports'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'marker port'):audit(d,g,p,'S','G')
  g['nodes'][0]['ports'][0]['system']='supply';marker.dxf.layer='other'
  with self.assertRaisesRegex(ValueError,'source insert'):audit(d,g,p,'S','G')
 def test_single_port_omission_marker_is_not_a_pipe(self):
  d,g,p=fixture();marker=d.modelspace().add_lwpolyline([(0,0),(1,0)],dxfattribs={'layer':'DIM_SYMB'});e=g['edges'][0];e.update(start_node_id='V',end_node_id='T',start_port_id='P',source_insert_handle=marker.dxf.handle,connection_mode='standalone_omission_to_first_tee',attribute_paths=[[[0,0],[1,0],[10,0]]]);g['nodes']=[{'node_id':'V','node_type':'virtual_equipment','source_marker_handle':marker.dxf.handle,'x':0,'y':0,'ports':[{'port_id':'P','system':'supply','x':1,'y':0}]}]
  d.modelspace().delete_entity(next(x for x in d.modelspace().query('LINE') if x.dxf.layer=='空调冷冻水供水'));d.modelspace().add_line((1,0),(10,0),dxfattribs={'layer':'空调冷冻水供水'})
  self.assertEqual([x['status'] for x in audit(d,g,p,'S','G')['edges'][0]['segments']],['no_witness_in_scoped_search','single_source_line_covers'])
  g['nodes'][0]['ports'][0]['x']=2
  with self.assertRaisesRegex(ValueError,'marker port'):audit(d,g,p,'S','G')
 def test_duplicate_and_hash_rejected(self):
  d,g,p=fixture();p['edges'].append('E')
  with self.assertRaisesRegex(ValueError,'selections'):audit(d,g,p,'S','G')
  d,g,p=fixture()
  with self.assertRaisesRegex(ValueError,'hash'):audit(d,g,p,'bad','G')
if __name__=='__main__':unittest.main()
