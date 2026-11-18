import copy, unittest, ezdxf
from native_device_circle_lines import collect


def fixture():
 d=ezdxf.new(); b=d.blocks.new('EQ'); layer='空调冷冻水供水'
 b.add_circle((0,0),1); b.add_line((0,0),(10,0),dxfattribs={'layer':layer})
 b.add_line((0,0),(0,10),dxfattribs={'layer':'空调冷冻水回水'})
 i=d.modelspace().add_blockref('EQ',(20,20),dxfattribs={'rotation':90,'xscale':-1})
 g={'edges':[{'edge_id':'E','system':'supply','source_insert_handle':i.dxf.handle,'attribute_paths':[[[20,20],[30,20]]]}]}
 p={'source_sha256':'S','graph_sha256':'G','edges':['E']}
 return d,g,p


class DeviceCircleLinesTest(unittest.TestCase):
 def test_rotated_mirrored_same_system_and_unchanged_graph(self):
  d,g,p=fixture(); before=copy.deepcopy(g); r=collect(d,g,p,'S','G'); c=r['edges'][0]['candidates']
  self.assertEqual(g,before); self.assertEqual(len(c),1); self.assertFalse(c[0]['fully_covered_by_single_graph_segment'])
  self.assertEqual(c[0]['source_chain'][0],g['edges'][0]['source_insert_handle']); self.assertEqual(len(c[0]['circles']),1)
 def test_multiple_circles_are_not_silently_selected(self):
  d,g,p=fixture(); d.blocks['EQ'].add_circle((0,0),2); c=collect(d,g,p,'S','G')['edges'][0]['candidates']
  self.assertEqual(len(c[0]['circles']),2)
 def test_z_conflict_is_reported_without_suppressing_candidate(self):
  d,g,p=fixture(); line=next(e for e in d.blocks['EQ'] if e.dxftype()=='LINE' and e.dxf.layer=='空调冷冻水供水')
  line.dxf.start=(0,0,3);line.dxf.end=(10,0,3)
  c=collect(d,g,p,'S','G')['edges'][0]['candidates'][0]
  self.assertFalse(c['circles'][0]['z_coincident'])
 def test_covered_source_line(self):
  d,g,p=fixture();g['edges'][0]['attribute_paths']=[[[20,20],[20,0]]]
  c=collect(d,g,p,'S','G')['edges'][0]['candidates'][0]
  self.assertTrue(c['fully_covered_by_single_graph_segment'])
 def test_multiple_paths_checked_separately_without_bridging_gaps(self):
  d,g,p=fixture();g['edges'][0]['attribute_paths']=[[[20,30],[20,25]],[[20,20],[20,10]]]
  c=collect(d,g,p,'S','G')['edges'][0]['candidates'][0];self.assertTrue(c['fully_covered_by_single_graph_segment'])
  g['edges'][0]['attribute_paths']=[[[20,30],[20,25]],[[20,15],[20,10]]]
  c=collect(d,g,p,'S','G')['edges'][0]['candidates'][0];self.assertFalse(c['fully_covered_by_single_graph_segment'])
  g['edges'][0]['attribute_paths'][1]=[[20,15]]
  with self.assertRaisesRegex(ValueError,'invalid path'):collect(d,g,p,'S','G')
 def test_hash_and_duplicate_fail_closed(self):
  d,g,p=fixture()
  with self.assertRaisesRegex(ValueError,'hash'): collect(d,g,p,'wrong','G')
  p['edges'].append('E')
  with self.assertRaisesRegex(ValueError,'selections'): collect(d,g,p,'S','G')
 def test_definition_handle_is_not_shared_instance_identity(self):
  d,g,p=fixture(); i=d.modelspace().add_blockref('EQ',(90,90)); g['edges'].append(dict(g['edges'][0],edge_id='F',source_insert_handle=i.dxf.handle));p['edges'].append('F')
  r=collect(d,g,p,'S','G'); a,b=[x['candidates'][0]['source_chain'] for x in r['edges']]
  self.assertNotEqual(a[0],b[0]);self.assertEqual(a[1],b[1])


if __name__=='__main__': unittest.main()
