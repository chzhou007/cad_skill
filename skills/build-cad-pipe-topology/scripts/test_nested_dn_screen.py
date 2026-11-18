import unittest,ezdxf
from nested_dn_screen import screen
class NestedDN(unittest.TestCase):
 def fixture(self):
  d=ezdxf.new('R2018');block=d.blocks.new('A');leaf=block.add_text('DN200',dxfattribs={'height':5,'insert':(0,0)});top=d.modelspace().add_blockref('A',(50,4),dxfattribs={'rotation':90,'xscale':-1,'yscale':1});g={'metadata':{'source_sha256':'S'},'edges':[{'edge_id':'E','attribute_paths':[[[0,0],[100,0]]]}]};p={'source_sha256':'S','graph_sha256':'G','edges':['E'],'nested_search_radius':10};return d,g,p,leaf,top
 def test_rotated_mirrored_nested_native_text_has_source_identity(self):
  d,g,p,leaf,top=self.fixture();r=screen(d,g,p,'S','G');self.assertEqual(len(r['nearby_nested_dn']),1);x=r['nearby_nested_dn'][0];self.assertEqual(x['top_insert_handle'],top.dxf.handle);self.assertEqual(x['leaf_handle'],leaf.dxf.handle);self.assertEqual(x['parsed_single_dn']['nominal_mm'],200);self.assertEqual(x['distances'][0]['edge_id'],'E');self.assertFalse(r['hil_ready'])
 def test_nearby_attrib_and_composite_are_not_assigned(self):
  d,g,p,leaf,top=self.fixture();top.add_attrib('S','DN300/DN200',(50,3),dxfattribs={'height':5});r=screen(d,g,p,'S','G');self.assertTrue(any(x['parsed_single_dn'] is None and x['text']=='DN300/DN200' for x in r['nearby_nested_dn']))
 def test_far_and_wrong_hash(self):
  d,g,p,leaf,top=self.fixture();top.dxf.insert=(50,100);self.assertEqual(screen(d,g,p,'S','G')['nearby_nested_dn'],[])
  with self.assertRaises(ValueError):screen(d,g,p,'S','old')
 def test_duplicate_edges_and_invalid_scope_rejected(self):
  d,g,p,leaf,top=self.fixture();p['edges'].append('E')
  with self.assertRaises(ValueError):screen(d,g,p,'S','G')
  p['edges']=['E'];p['nested_search_radius']=float('nan')
  with self.assertRaises(ValueError):screen(d,g,p,'S','G')
if __name__=='__main__':unittest.main()
