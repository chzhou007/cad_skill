import copy,unittest,ezdxf
from duplicate_native_main_diagnostics import diagnose,same_line

class DuplicateNativeMainDiagnosticsTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.a=m.add_line((0,0,0),(10,0,0),dxfattribs={'layer':'supply'});self.b=m.add_line((10,0,0),(0,0,0),dxfattribs={'layer':'supply'});self.c=m.add_circle((5,0),1);self.branch=m.add_line((5,1),(5,5),dxfattribs={'layer':'supply'})
  self.g={'metadata':{'source_sha256':'s'},'edges':[{'edge_id':'E','source_handles':[self.a.dxf.handle]}]}
  self.screen={'source_sha256':'s','graph_sha256':'g','ambiguous_native_geometry':[{'circle_handle':self.c.dxf.handle,'system':'supply','main_handles':[self.a.dxf.handle,self.b.dxf.handle],'branch_handles':[self.branch.dxf.handle]}]}
 def test_reversed_identical_native_lines_and_ownership(self):
  before=copy.deepcopy(self.g);r=diagnose(self.doc,self.g,self.screen,'s','g');x=r['records'][0]
  self.assertEqual(x['native_same_layer_3d_groups'],[[self.a.dxf.handle,self.b.dxf.handle]])
  self.assertEqual(x['main_graph_edge_references'][self.b.dxf.handle],[]);self.assertEqual(self.g,before);self.assertFalse(r['physical_identity_resolved'])
 def test_different_z_or_layer_never_deduplicated(self):
  self.b.dxf.start=(10,0,1);self.assertFalse(same_line(self.a,self.b,.05));self.b.dxf.start=(10,0,0);self.b.dxf.layer='return';self.assertFalse(same_line(self.a,self.b,.05))
 def test_stale_and_missing_inputs_block(self):
  with self.assertRaises(ValueError):diagnose(self.doc,self.g,self.screen,'s','stale')
  incomplete=dict(self.screen);incomplete.pop('ambiguous_native_geometry')
  with self.assertRaises(ValueError):diagnose(self.doc,self.g,incomplete,'s','g')
  self.screen['ambiguous_native_geometry'][0]['main_handles'][1]='invalid'
  with self.assertRaises(ValueError):diagnose(self.doc,self.g,self.screen,'s','g')
 def test_existing_three_way_does_not_resolve_duplicate_identity(self):
  self.g['nodes']=[{'node_id':'T','node_type':'tee','system':'supply','x':5,'y':0}]
  self.g['edges']=[{'edge_id':'L','system':'supply','start_node_id':'A','end_node_id':'T','source_handles':[self.a.dxf.handle]},
   {'edge_id':'R','system':'supply','start_node_id':'T','end_node_id':'B','source_handles':[self.a.dxf.handle]},
   {'edge_id':'C','system':'supply','start_node_id':'T','end_node_id':'D','source_handles':[self.branch.dxf.handle]}]
  result=diagnose(self.doc,self.g,self.screen,'s','g');self.assertEqual(result['records'][0]['graph_junction_state'],'existing_same_system_three_way_unreviewed')
  self.assertFalse(result['physical_identity_resolved']);self.g['edges'][2]['system']='return'
  self.assertEqual(diagnose(self.doc,self.g,self.screen,'s','g')['records'][0]['graph_junction_state'],'not_proven_or_ambiguous')
if __name__=='__main__':unittest.main()
