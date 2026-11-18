import unittest
import ezdxf
from instance_geometry import recover_exploded_ball_valve_chains,source_paths


def fixture():
 doc=ezdxf.new();b=doc.blocks.new('SIX')
 for y in (-10,0,10):b.add_line((-100,y),(100,y),dxfattribs={'color':2})
 h=b.add_hatch(color=2);h.paths.add_polyline_path([(-20,-20),(20,-20),(20,20),(-20,20)],is_closed=True)
 for y in (-5,5):b.add_ellipse((0,y),major_axis=(30,0),ratio=.5,dxfattribs={'color':2})
 root=doc.modelspace().add_blockref('SIX',(1000,1000));item={'source_kind':'exploded_geometry','source_block_name':'EXPLODED:H-PICPNT-91','source_top_handle':root.dxf.handle,'x':1000.,'y':1000.,'edge_id':'E1'}
 return doc,item,root


class ExplodedValveRecoveryTest(unittest.TestCase):
 def test_exact_parent_recovered_without_edge_change(self):
  doc,item,root=fixture();self.assertEqual(recover_exploded_ball_valve_chains(doc,[item]),1);self.assertEqual(item['display_source_chain'],[root.dxf.handle]);self.assertEqual(item['edge_id'],'E1');self.assertEqual(len(source_paths(doc,chain=item['display_source_chain'])),6)
 def test_incomplete_or_unrelated_parent_is_not_recovered(self):
  doc,item,root=fixture();doc.blocks['SIX'].add_line((0,0),(1,0),dxfattribs={'color':2});self.assertEqual(recover_exploded_ball_valve_chains(doc,[item]),0)
  doc,item,root=fixture();item['x']+=1;self.assertEqual(recover_exploded_ball_valve_chains(doc,[item]),0)
 def test_duplicate_claim_and_other_kind_are_not_recovered(self):
  doc,item,root=fixture();self.assertEqual(recover_exploded_ball_valve_chains(doc,[item,dict(item)]),0)
  doc,item,root=fixture();item['source_kind']='other';self.assertEqual(recover_exploded_ball_valve_chains(doc,[item]),0)
 def test_rotated_mirrored_parent(self):
  doc,item,root=fixture();root.dxf.rotation=90;root.dxf.xscale=-1;self.assertEqual(recover_exploded_ball_valve_chains(doc,[item]),1);self.assertEqual(len(source_paths(doc,chain=item['display_source_chain'])),6)
 def test_json_encoded_existing_chain_blocks_reuse(self):
  doc,item,root=fixture();existing={'display_source_chain':'[\"'+root.dxf.handle+'\",\"CHILD\"]'};self.assertEqual(recover_exploded_ball_valve_chains(doc,[item,existing]),0)
 def test_shared_parent_or_wrong_color_is_not_recovered(self):
  doc,item,root=fixture();existing={'display_source_chain':[root.dxf.handle,'CHILD']};self.assertEqual(recover_exploded_ball_valve_chains(doc,[item,existing]),0)
  doc,item,root=fixture();next(iter(doc.blocks['SIX'])).dxf.color=3;self.assertEqual(recover_exploded_ball_valve_chains(doc,[item]),0)

if __name__=='__main__':unittest.main()
