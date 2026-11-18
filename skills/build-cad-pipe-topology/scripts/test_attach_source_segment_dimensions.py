import copy,unittest,ezdxf
from attach_source_segment_dimensions import collect,attach,validate_dn_dependencies
class SegmentDimensions(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new('R2018');self.d.header['$INSUNITS']=4;m=self.d.modelspace();self.line=m.add_line((0,0),(2400,0),dxfattribs={'layer':'空调冷冻水回水'});z=m.add_linear_dim(base=(0,1000),p1=(0,0),p2=(2400,0),angle=0,dxfattribs={'layer':'空调平面'});z.render();self.dim=z.dimension;texts=[x for x in self.d.blocks[self.dim.dxf.geometry] if x.dxftype() in ('TEXT','MTEXT')];self.assertEqual(texts[0].plain_text(),'2400')
  self.g={'metadata':{'source_sha256':'S'},'nodes':[],'edges':[{'edge_id':'E','system':'return','attribute_paths':[[[-100,0],[0,0],[2400,0],[2500,0]]],'source_handles':[self.line.dxf.handle],'path_length':2600}]}
  self.p={'source_sha256':'S','graph_sha256':'G','dimensions':[{'edge_id':'E','dimension_handle':self.dim.dxf.handle,'text_handle':texts[0].dxf.handle,'expected_text':'2400','expected_value_mm':2400,'source_line_handle':self.line.dxf.handle,'segment_index':1,'dimension_layer':'空调平面'}]}
 def call(self):return collect(self.d,self.g,self.p,'S','G')
 def test_selected_segment_does_not_become_total_length(self):
  before=copy.deepcopy(self.g);rows=self.call();out=attach(self.g,rows,'S','G');self.assertEqual(self.g,before);self.assertEqual(rows[0]['dimension_value_mm'],2400);self.assertFalse(rows[0]['edge_total_length_known']);self.assertEqual(out['edges'][0]['path_length'],2600);self.assertFalse(out['metadata']['hil_ready'])
 def test_wrong_units_points_or_display_rejected(self):
  self.d.header['$INSUNITS']=6
  with self.assertRaises(ValueError):self.call()
  self.d.header['$INSUNITS']=4;self.dim.dxf.defpoint2=(1,0,0)
  with self.assertRaises(ValueError):self.call()
  self.dim.dxf.defpoint2=(0,0,0);self.p['dimensions'][0]['expected_text']='999'
  with self.assertRaises(ValueError):self.call()
 def test_duplicate_edge_geometry_and_scaled_dimension_rejected(self):
  self.g['edges'].append(copy.deepcopy(self.g['edges'][0]));self.g['edges'][1]['edge_id']='E2'
  with self.assertRaises(ValueError):self.call()
  self.g['edges'].pop();self.d.dimstyles.get(self.dim.dxf.dimstyle).dxf.dimlfac=2
  with self.assertRaises(ValueError):self.call()
 def test_duplicate_native_line_is_ambiguous(self):
  self.d.modelspace().add_line((0,0),(2400,0),dxfattribs={'layer':'空调冷冻水回水'})
  with self.assertRaisesRegex(ValueError,'not unique'):self.call()
 def test_longer_overlapping_native_line_is_ambiguous(self):
  self.d.modelspace().add_line((-50,0),(2450,0),dxfattribs={'layer':'空调冷冻水回水'})
  with self.assertRaisesRegex(ValueError,'not unique'):self.call()
 def test_stale_hash_and_nonpipe_line_rejected(self):
  self.p['graph_sha256']='old'
  with self.assertRaises(ValueError):self.call()
  self.p['graph_sha256']='G';self.line.dxf.layer='other'
  with self.assertRaises(ValueError):self.call()
class DependencyBinding(unittest.TestCase):
 def test_stale_or_partial_dn_lineage_rejected(self):
  graph={'diameterInheritanceCandidates':{'source_sha256':'S','input_graph_sha256':'PRE','status':'candidate_not_accepted','edgewide_values_assigned':False,'changes':[{'edge_id':'E'}]}};direct={'source_sha256':'S','graph_sha256':'G'};policy={'source_sha256':'S','graph_sha256':'PRE','edges':['E']}
  validate_dn_dependencies(graph,direct,policy,'S','G');policy['graph_sha256']='stale'
  with self.assertRaises(ValueError):validate_dn_dependencies(graph,direct,policy,'S','G')
  policy['graph_sha256']='PRE';policy['edges']=['E','OTHER']
  with self.assertRaises(ValueError):validate_dn_dependencies(graph,direct,policy,'S','G')
if __name__=='__main__':unittest.main()
