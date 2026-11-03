import unittest,ezdxf
from equipment_assemblies import profile_native_assemblies
class NativeEquipment(unittest.TestCase):
 def fixture(self):
  d=ezdxf.new();b=d.blocks.new('ASSEMBLY')
  for a,z in [((0,0),(10,0)),((10,0),(10,10)),((10,10),(0,10)),((0,10),(0,0)),((0,5),(10,5))]:b.add_line(a,z)
  b.add_circle((5,5),2);d.modelspace().add_blockref('ASSEMBLY',(0,0));t=d.modelspace().add_text('CWE-1',dxfattribs={'height':1,'insert':(5,5)});bindings=[dict(equipment_tag='CWE-1',source_handle=t.dxf.handle,x=5,y=5,profile_candidates=[])]
  return d,bindings
 def test_known_native_equipment_survives_missing_parameters(self):
  d,b=self.fixture();r,a=profile_native_assemblies(d,b,[],[],native_rules=[dict(tag_regex='CWE-[0-9]+',source_block='ASSEMBLY')]);self.assertEqual(len(r),1);self.assertEqual(r[0]['binding']['profile_candidates'],[])
 def test_unverified_block_not_equipment(self):
  d,b=self.fixture();r,a=profile_native_assemblies(d,b,[],[],native_rules=[dict(tag_regex='CWE-[0-9]+',source_block='OTHER')]);self.assertFalse(r)
 def test_tag_without_verified_geometry_stays_pending(self):
  d,b=self.fixture();r,a=profile_native_assemblies(d,b,[],[]);self.assertFalse(r)
class Enclosure(NativeEquipment):
 def test_explicit_package_needs_complete_frame(self):
  d,b=self.fixture();r,a=profile_native_assemblies(d,b,[],[],native_rules=[dict(tag_regex='CWE-[0-9]+',source_block='ASSEMBLY',port_policy='verified_closed_enclosure')]);self.assertFalse(r[0]['package_boundary_verified'])
 def test_complete_frame_with_explicit_rule_qualifies(self):
  d,b=self.fixture();d.blocks['ASSEMBLY'].add_lwpolyline([(0,0),(10,0),(10,10),(0,10)],close=True);r,a=profile_native_assemblies(d,b,[],[],native_rules=[dict(tag_regex='CWE-[0-9]+',source_block='ASSEMBLY',port_policy='verified_closed_enclosure')]);self.assertTrue(r[0]['package_boundary_verified'])
 def test_frame_without_package_policy_not_qualified(self):
  d,b=self.fixture();d.blocks['ASSEMBLY'].add_lwpolyline([(0,0),(10,0),(10,10),(0,10)],close=True);r,a=profile_native_assemblies(d,b,[],[],native_rules=[dict(tag_regex='CWE-[0-9]+',source_block='ASSEMBLY')]);self.assertFalse(r[0]['package_boundary_verified'])
if __name__=='__main__':unittest.main()
