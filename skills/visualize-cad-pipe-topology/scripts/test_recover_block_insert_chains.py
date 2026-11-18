import copy,unittest,ezdxf
from instance_geometry import recover_block_insert_chains,source_paths

def fixture():
 d=ezdxf.new();leaf=d.blocks.new('VALVE');leaf.add_line((0,0),(2,0));parent=d.blocks.new('DEVICE');child=parent.add_blockref('VALVE',(2,3));root=d.modelspace().add_blockref('DEVICE',(10,20),dxfattribs={'rotation':90,'xscale':-1});point=root.matrix44().transform(child.ocs().to_wcs(child.dxf.insert));r={'source_kind':'block_insert','source_top_handle':root.dxf.handle,'source_block_name':'VALVE','x':point.x,'y':point.y,'edge_id':'E','system':'supply'};return d,root,child,r

class BlockChainTest(unittest.TestCase):
 def test_nested_mirror_rotation_and_no_ownership_change(self):
  d,root,child,r=fixture();before=copy.deepcopy(r);self.assertEqual(recover_block_insert_chains(d,[r]),1);self.assertEqual(r['display_source_chain'],[root.dxf.handle,child.dxf.handle]);self.assertEqual(r['edge_id'],before['edge_id']);self.assertEqual(r['system'],before['system']);self.assertTrue(source_paths(d,chain=r['display_source_chain']))
 def test_competing_records_or_instances_stay_unbound(self):
  d,root,child,r=fixture();other=copy.deepcopy(r);self.assertEqual(recover_block_insert_chains(d,[r,other]),0);self.assertNotIn('display_source_chain',r)
  d,root,child,r=fixture();d.blocks['DEVICE'].add_blockref('VALVE',(2,3));self.assertEqual(recover_block_insert_chains(d,[r]),0)
 def test_existing_parent_chain_or_array_prevents_binding(self):
  d,root,child,r=fixture();other={'display_source_chain':[root.dxf.handle]};self.assertEqual(recover_block_insert_chains(d,[r,other]),0)
  d,root,child,r=fixture();child.dxf.row_count=2;self.assertEqual(recover_block_insert_chains(d,[r]),0)
 def test_unrenderable_and_missing_locations_stay_pending(self):
  d,root,child,r=fixture();d.blocks['VALVE'].add_attdef('X',(0,0));self.assertEqual(recover_block_insert_chains(d,[r]),0)
  d,root,child,r=fixture();r['x']+=1;self.assertEqual(recover_block_insert_chains(d,[r]),0)
 def test_opaque_sibling_in_parent_does_not_imply_complete_search(self):
  d,root,child,r=fixture();d.blocks['DEVICE'].new_entity('3DSOLID',dxfattribs={'layer':'0'});self.assertEqual(recover_block_insert_chains(d,[r]),0)
 def test_direct_insert_negative_ocs_is_in_world_coordinates(self):
  d=ezdxf.new();d.blocks.new('V').add_line((0,0),(1,0));root=d.modelspace().add_blockref('V',(10,20),dxfattribs={'extrusion':(0,0,-1)});p=root.ocs().to_wcs(root.dxf.insert);r={'source_kind':'block_insert','source_top_handle':root.dxf.handle,'source_block_name':'V','x':p.x,'y':p.y}
  self.assertEqual(recover_block_insert_chains(d,[r]),1);self.assertEqual(r['display_source_chain'],[root.dxf.handle])
if __name__=='__main__':unittest.main()
