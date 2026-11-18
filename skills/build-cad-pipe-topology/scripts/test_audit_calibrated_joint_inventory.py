import unittest,ezdxf
from repair_native_flexible_joints import fingerprint
from audit_calibrated_joint_inventory import audit

class JointInventory(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();b=self.doc.blocks.new('J');b.add_line((0,0),(1,0));a=self.doc.modelspace().add_blockref('J',(0,0));c=self.doc.modelspace().add_blockref('J',(2,0));self.a=a.dxf.handle;self.c=c.dxf.handle
  self.hashes={'source_sha256':'S','inventory_sha256':'I'};self.policy={**self.hashes,'block_name':'J','block_fingerprint_sha256':fingerprint(b)};self.row={'source_top_handle':self.a,'equipment_type':'金属软接','assignment_status':'assigned','edge_id':'E','device_name':'D'}
 def test_all_direct_instances_are_counted_without_acceptance(self):
  r=audit(self.doc,[self.row],self.policy,self.hashes);self.assertEqual(r['total_source_instances'],2);self.assertEqual(r['counts']['unassigned_source_instance'],1);self.assertFalse(r['human_accepted'])
 def test_duplicate_and_type_conflicts_are_retained(self):
  other={**self.row,'source_top_handle':self.c,'equipment_type':'球阀'};r=audit(self.doc,[self.row,self.row,other],self.policy,self.hashes);self.assertEqual(r['counts']['duplicate_inventory_claims'],1);self.assertEqual(r['counts']['inventory_type_conflict'],1)
 def test_stale_source_fails(self):
  with self.assertRaises(ValueError):audit(self.doc,[],self.policy,{**self.hashes,'source_sha256':'other'})
 def test_same_fingerprint_alias_and_nested_reference_are_reported(self):
  alias=self.doc.blocks.new('J2');alias.add_line((0,0),(1,0));parent=self.doc.blocks.new('PARENT');ins=parent.add_blockref('J2',(5,5))
  r=audit(self.doc,[self.row],self.policy,self.hashes);self.assertEqual(r['same_fingerprint_block_definitions'],['J','J2']);self.assertEqual(r['nested_definition_references'],[{'parent_block':'PARENT','insert_handle':ins.dxf.handle,'referenced_block':'J2'}]);self.assertEqual(r['total_source_instances'],2)
if __name__=='__main__':unittest.main()
