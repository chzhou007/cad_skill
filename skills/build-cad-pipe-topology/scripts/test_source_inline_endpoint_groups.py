import unittest,ezdxf
from source_inline_endpoint_groups import attach
class InlineGroupingTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();b=self.doc.blocks.new('$VALVE$000005460');b.add_point((0,0));b.add_point((100,0));ins=self.doc.modelspace().add_blockref('$VALVE$000005460',(0,0));self.dev={'source_block_name':'$VALVE$000005460','source_top_handle':ins.dxf.handle,'device_name':'D','edge_id':'E','source_axis_coverage_status':'axis_projection_partial'};self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'U','boundary_type':'unresolved_source_terminal'},{'node_id':'T','node_type':'tee'}],'edges':[{'edge_id':'E','start_node_id':'U','end_node_id':'T','system':'return','attribute_paths':[[[-100,0],[50,0]]],'source_inline_axis_candidates':[{'source_device_name':'D','source_handle':ins.dxf.handle,'status':'axis_projection_partial'}]}]}
 def test_group_preserves_edge_route_and_input(self):
  o,a=attach(self.g,self.doc,[self.dev],'S');self.assertEqual(a['endpoint_nodes'],1);self.assertEqual(o['edges'][0]['attribute_paths'],self.g['edges'][0]['attribute_paths']);self.assertNotIn('source_inline_endpoint_group',self.g['edges'][0]);self.assertFalse(o['sourceInlineEndpointGroups'][0]['hydraulic_connection_confirmed'])
 def test_rejects_projection_status_mismatch(self):
  self.dev['source_axis_coverage_status']='axis_projection_spans_both_points'
  with self.assertRaises(ValueError):attach(self.g,self.doc,[self.dev],'S')
 def test_rejects_competing_component(self):
  with self.assertRaises(ValueError):attach(self.g,self.doc,[self.dev,self.dev],'S')
if __name__=='__main__':unittest.main()
