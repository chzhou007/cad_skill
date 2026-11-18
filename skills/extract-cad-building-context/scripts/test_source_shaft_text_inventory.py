import copy,unittest,ezdxf
from architecture_context import extract
from source_shaft_text_inventory import inventory

class SourceShaftTextInventoryTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();self.doc.layers.new('建筑底图');inner=self.doc.blocks.new('INNER');inner.add_text('空调管井',dxfattribs={'insert':(2,3),'height':1,'layer':'0'});outer=self.doc.blocks.new('OUTER');outer.add_blockref('INNER',(10,20),dxfattribs={'layer':'0'});self.doc.modelspace().add_blockref('OUTER',(100,200),dxfattribs={'layer':'建筑底图'});self.ctx=extract(self.doc,{'originX':0,'originY':0,'scale':1},'S');self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'R','subtype':'out_of_plane_riser','system':'supply','x':112,'y':223}]}
 def test_nested_source_text_and_position_are_retained_without_connection(self):
  before=copy.deepcopy(self.g);r=inventory(self.doc,'S',self.ctx,self.g,5);self.assertEqual(self.g,before);self.assertEqual(r['records'][0]['source_text'],'空调管井');self.assertEqual(len(r['records'][0]['source_chain']),3);self.assertEqual(r['records'][0]['nearby_riser_candidates'][0]['status'],'nearby_not_ownership');self.assertFalse(r['human_accepted'])
 def test_changed_context_or_source_fails_closed(self):
  self.ctx['records'][0]['position'][0]+=10
  with self.assertRaisesRegex(ValueError,'position changed'):inventory(self.doc,'S',self.ctx,self.g,5)
  with self.assertRaisesRegex(ValueError,'source or radius'):inventory(self.doc,'other',self.ctx,self.g,5)
if __name__=='__main__':unittest.main()
