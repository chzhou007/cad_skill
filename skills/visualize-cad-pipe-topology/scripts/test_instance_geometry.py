import unittest,ezdxf
from instance_geometry import source_paths,find_insert_chains
class NativeChain(unittest.TestCase):
 def test_selected_native_members_keep_parent_transform_without_other_equipment(self):
  d=ezdxf.new();body=d.blocks.new('ASSEMBLY');a=body.add_line((0,0),(10,0));b=body.add_line((20,0),(30,0));parent=d.modelspace().add_blockref('ASSEMBLY',(100,20),dxfattribs={'xscale':-1});p=source_paths(d,handles=[a.dxf.handle],chain=[parent.dxf.handle]);self.assertEqual(p,[{'points':[[100,20],[90,20]],'fill':False}]);self.assertNotIn([80,20],[q for path in p for q in path['points']])
 def test_member_selection_rejects_foreign_or_duplicate_members(self):
  d=ezdxf.new();b=d.blocks.new('ASSEMBLY');a=b.add_line((0,0),(1,0));foreign=d.modelspace().add_line((0,0),(1,0));parent=d.modelspace().add_blockref('ASSEMBLY',(0,0));self.assertRaises(ValueError,source_paths,d,handles=[foreign.dxf.handle],chain=[parent.dxf.handle]);self.assertRaises(ValueError,source_paths,d,handles=[a.dxf.handle,a.dxf.handle],chain=[parent.dxf.handle])
 def test_nested_translated_mirrored_source_instance(self):
  d=ezdxf.new();body=d.blocks.new('BODY');body.add_line((0,0),(10,0));group=d.blocks.new('GROUP');child=group.add_blockref('BODY',(5,0),dxfattribs={'xscale':-1});outer=d.modelspace().add_blockref('GROUP',(100,20));p=source_paths(d,chain=[outer.dxf.handle,child.dxf.handle])[0]['points'];self.assertEqual(p,[[105,20],[95,20]])
 def test_unrelated_insert_cannot_be_used_as_parent(self):
  d=ezdxf.new();d.blocks.new('A');d.blocks.new('B');parent=d.modelspace().add_blockref('A',(0,0));other=d.blocks['B'].add_line((0,0),(1,0));self.assertRaises(ValueError,source_paths,d,chain=[parent.dxf.handle,other.dxf.handle])
 def test_child_lookup_uses_block_identity_and_transformed_insert(self):
  d=ezdxf.new();d.blocks.new('GAUGE');p=d.blocks.new('PACKAGE');child=p.add_blockref('GAUGE',(5,0));outer=d.modelspace().add_blockref('PACKAGE',(100,20));self.assertEqual(find_insert_chains(d,outer.dxf.handle,'GAUGE',(105,20)),[[outer.dxf.handle,child.dxf.handle]]);self.assertEqual(find_insert_chains(d,outer.dxf.handle,'GAUGE',(110,20)),[])
if __name__=='__main__':unittest.main(verbosity=2)
