import unittest,ezdxf
from native_offset_circle_candidates import collect
class OffsetCircleTest(unittest.TestCase):
 def fixture(self,offset=1):
  d=ezdxf.new();b=d.blocks.new('EQ');b.add_circle((0,0),10);b.add_line((offset,0),(20,0),dxfattribs={'layer':'空调冷冻水供水'});i=d.modelspace().add_blockref('EQ',(100,200),dxfattribs={'rotation':90,'xscale':-1});g={'edges':[{'edge_id':'E','system':'supply','source_insert_handle':i.dxf.handle}]};p={'source_sha256':'S','graph_sha256':'G','edges':['E'],'max_radius_ratio':.2};return d,g,p
 def test_offset_is_preserved_not_promoted(self):
  d,g,p=self.fixture();r=collect(d,g,p,'S','G');self.assertEqual(r['edges'][0]['status'],'unique_offset_candidate');self.assertAlmostEqual(r['edges'][0]['candidates'][0]['offset'],1);self.assertFalse(r['graph_mutated']);self.assertFalse(r['hil_ready'])
 def test_exact_center_and_large_offset_excluded(self):
  for x in (0,3):
   d,g,p=self.fixture(x);self.assertEqual(collect(d,g,p,'S','G')['edges'][0]['candidates'],[])
 def test_ambiguous_and_invalid_hash(self):
  d,g,p=self.fixture();d.blocks['EQ'].add_circle((0,0),9);self.assertEqual(collect(d,g,p,'S','G')['edges'][0]['status'],'ambiguous_or_no_candidate')
  with self.assertRaises(ValueError):collect(d,g,p,'bad','G')
if __name__=='__main__':unittest.main()
