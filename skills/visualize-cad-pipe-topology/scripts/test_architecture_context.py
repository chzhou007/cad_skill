import unittest,ezdxf
from architecture_context import extract,svg_markup,english_label
T=dict(originX=0,originY=100,scale=2)
class ArchitectureContext(unittest.TestCase):
 def test_nested_wall_coordinates_and_source_identity(self):
  d=ezdxf.new();d.layers.new('A-WALL');b=d.blocks.new('B');line=b.add_line((0,0),(10,0));i=d.modelspace().add_blockref('B',(20,30),dxfattribs={'layer':'A-WALL','rotation':90})
  r=extract(d,T)['records'][0];self.assertEqual(r['source_chain'],[i.dxf.handle,line.dxf.handle]);self.assertEqual(r['category'],'wall');self.assertAlmostEqual(r['paths'][0]['points'][-1][1],40);self.assertAlmostEqual(r['paths'][0]['display_points'][-1][1],30)
 def test_room_source_preserved_and_ui_english(self):
  d=ezdxf.new();d.layers.new('建筑底图');d.modelspace().add_text('走廊',dxfattribs={'layer':'建筑底图','height':200})
  a=extract(d,T);r=a['records'][0];self.assertEqual(r['source_text'],'走廊');self.assertEqual(r['label'],'Corridor');self.assertNotIn('走廊',svg_markup(a));self.assertNotIn('room_polygon',r)
 def test_unknown_text_explicit_not_discarded(self):
  label,status=english_label('未知房间','B1');self.assertEqual(status,'translation_pending');self.assertEqual(label,'Source label B1')
 def test_numeric_dimensions_retained(self):
  d=ezdxf.new();dim=d.modelspace().add_linear_dim(base=(0,20),p1=(0,0),p2=(100,0));dim.render()
  a=extract(d,T);self.assertTrue(any(r.get('label')=='100'for r in a['records']));self.assertTrue(any(r['category']=='dimension'for r in a['records']))
 def test_hatch_holes_compound_evenodd(self):
  d=ezdxf.new();d.layers.new('A-WALL');h=d.modelspace().add_hatch(dxfattribs={'layer':'A-WALL'});h.paths.add_polyline_path([(0,0),(10,0),(10,10),(0,10)],is_closed=True);h.paths.add_polyline_path([(2,2),(8,2),(8,8),(2,8)],is_closed=True)
  s=svg_markup(extract(d,T));self.assertIn('fill-rule="evenodd"',s);self.assertEqual(s.count('<path'),1)
 def test_pipe_layer_is_not_architecture(self):
  d=ezdxf.new();d.layers.new('CHWS');d.modelspace().add_line((0,0),(1,0),dxfattribs={'layer':'CHWS'});self.assertEqual(extract(d,T)['records'],[])
 def test_xref_is_explicit_pending(self):
  d=ezdxf.new();b=d.blocks.new('EXTERNAL');b.block.dxf.flags=4;d.modelspace().add_blockref('EXTERNAL',(0,0));a=extract(d,T);self.assertEqual(a['issues'][0]['reason'],'xref_not_embedded')
 def test_attributes_keep_block_grid_identity(self):
  d=ezdxf.new();d.layers.new('AXIS_TEXT');b=d.blocks.new('AXIS');b.add_attdef('AXIS',(0,0));i=d.modelspace().add_blockref('AXIS',(10,20),dxfattribs={'layer':'AXIS_TEXT'});i.add_auto_attribs({'AXIS':'G'})
  a=extract(d,T);self.assertTrue(any(r.get('label')=='G'and r['category']=='grid'for r in a['records']))
 def test_mirrored_ocs_text_uses_world_coordinates(self):
  d=ezdxf.new();d.layers.new('A-ANNO-TEXT');d.modelspace().add_text('M',dxfattribs={'layer':'A-ANNO-TEXT','insert':(-10,20,0),'extrusion':(0,0,-1),'height':2})
  r=extract(d,T)['records'][0];self.assertEqual(r['position'],[10,20]);self.assertEqual(r['display_position'],[5,40])
 def test_wipeout_mask_is_preserved_without_becoming_a_wall(self):
  d=ezdxf.new();d.layers.new('建筑底图');w=d.modelspace().add_wipeout([(0,0),(10,0),(10,10),(0,10)]);w.dxf.layer='建筑底图'
  a=extract(d,T);self.assertEqual(a['records'][0]['render_role'],'occlusion_mask');self.assertIn('fill="white"',svg_markup(a))
if __name__=='__main__':unittest.main()

