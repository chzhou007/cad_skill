import copy,unittest,ezdxf
from source_inline_axis_coverage import attach

class AxisCoverageTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();block=self.doc.blocks.new('PROXY');block.add_point((0,0));block.add_point((10,0));block.add_line((0,0),(10,0));ins=self.doc.modelspace().add_blockref('PROXY',(0,0));self.h=ins.dxf.handle
  self.g={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'A'}],'edges':[{'edge_id':'E','start_node_id':'A','end_node_id':'B','attribute_paths':[[[-5,0],[9,0]]]}]}
  self.d=[{'device_name':'D','edge_id':'E','source_top_handle':self.h,'source_block_name':'PROXY'}]
  self.ev={'source_sha256':'s','graph_sha256':'g','instances':1,'records':[{'instance_id':'D','handle':self.h,'edge_id':'E','path_projection_range':[-.5,.9],'covers_point_axis_span':False}]}
 def call(self):return attach(self.g,self.d,self.ev,'s','g',self.doc)
 def test_partial_preserves_topology_and_blocks_hil(self):
  old=copy.deepcopy(self.g);out,dev,v=self.call();self.assertEqual(self.g,old);self.assertEqual(out['nodes'],old['nodes']);self.assertEqual(out['edges'][0]['start_node_id'],'A');self.assertEqual(dev[0]['source_axis_coverage_status'],'axis_projection_partial');self.assertEqual(v['partial_axis_projections'],1);self.assertFalse(out['metadata']['hil_ready'])
 def test_source_change_stale_and_forgery_rejected(self):
  with self.assertRaises(ValueError):attach(self.g,self.d,self.ev,'s','bad',self.doc)
  self.ev['records'][0]['path_projection_range']=[-.5,1.1]
  with self.assertRaises(ValueError):self.call()
  self.ev['records'][0]['path_projection_range']=[-.5,.9];self.d[0]['edge_id']='OTHER'
  with self.assertRaises(ValueError):self.call()
 def test_spans_projection_does_not_assert_continuity(self):
  self.g['edges'][0]['attribute_paths']=[[[-5,0],[15,0]]];self.ev['records'][0]['path_projection_range']=[-.5,1.5];self.ev['records'][0]['covers_point_axis_span']=True
  out,dev,v=self.call();self.assertEqual(v['spans_axis_projections'],1);self.assertIn('does not prove',dev[0]['source_axis_coverage_scope'])

if __name__=='__main__':unittest.main()
