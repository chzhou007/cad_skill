import unittest
import ezdxf
from instance_geometry import recover_folded_valve_chains, source_paths


class FoldedValveRecoveryTest(unittest.TestCase):
 def fixture(self,duplicate=False):
  doc=ezdxf.new();v=doc.blocks.new('VALVE');v.add_line((0,0),(5,0));b=doc.blocks.new('ASSEMBLY');child=b.add_blockref('VALVE',(20,0))
  if duplicate:b.add_blockref('VALVE',(20,0))
  root=doc.modelspace().add_blockref('ASSEMBLY',(100,100));item={'source_kind':'turn_display_valve_folded_to_elbow','source_block_name':'VALVE','source_top_handle':root.dxf.handle,'x':120.,'y':100.,'edge_id':'E1','assignment_x':130.}
  return doc,item,[root.dxf.handle,child.dxf.handle]
 def test_unique_nested_valve_is_recovered_without_reassigning_edge(self):
  doc,item,expected=self.fixture();self.assertEqual(recover_folded_valve_chains(doc,[item]),1);self.assertEqual(item['display_source_chain'],expected);self.assertEqual(item['edge_id'],'E1');self.assertEqual(item['assignment_x'],130.);self.assertTrue(source_paths(doc,chain=expected))
 def test_ambiguous_and_wrong_position_remain_pending(self):
  doc,item,_=self.fixture(duplicate=True);self.assertEqual(recover_folded_valve_chains(doc,[item]),0);self.assertNotIn('display_source_chain',item)
  doc,item,_=self.fixture();item['x']+=2;self.assertEqual(recover_folded_valve_chains(doc,[item]),0)
 def test_wrong_kind_and_unowned_root_are_not_inferred(self):
  doc,item,_=self.fixture();item['source_kind']='block_insert';self.assertEqual(recover_folded_valve_chains(doc,[item]),0)
  doc,item,_=self.fixture();item['source_top_handle']='NOPE';self.assertEqual(recover_folded_valve_chains(doc,[item]),0)
 def test_duplicate_claims_do_not_recover(self):
  doc,item,_=self.fixture();other=dict(item);self.assertEqual(recover_folded_valve_chains(doc,[item,other]),0);self.assertNotIn('display_source_chain',item)
 def test_existing_evidence_is_preserved(self):
  doc,item,expected=self.fixture();item['display_source_chain']=expected;self.assertEqual(recover_folded_valve_chains(doc,[item]),0);self.assertEqual(item['display_source_chain'],expected)

if __name__=='__main__':unittest.main()
