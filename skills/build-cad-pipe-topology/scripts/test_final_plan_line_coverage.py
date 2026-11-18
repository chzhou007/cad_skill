import copy,unittest,ezdxf
from final_plan_line_coverage import inventory

class FinalPlanLineCoverageTest(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.a=m.add_line((0,0,0),(10,0,0),dxfattribs={'layer':'供'});self.b=m.add_line((10,0,0),(0,0,0),dxfattribs={'layer':'供'});self.t=m.add_line((3,0,0),(3.002,0,0),dxfattribs={'layer':'供'});self.z=m.add_line((0,0,3),(10,0,3),dxfattribs={'layer':'供'});self.g={'metadata':{'source_sha256':'S'},'edges':[{'edge_id':'E','system':'supply','source_handles':[self.a.dxf.handle]}]};self.p={'source_sha256':'S','graph_sha256':'G','system_layers':{'供':'supply'},'normalization_tolerance':.05}
 def test_duplicate_micro_and_3d_distinguished(self):
  before=copy.deepcopy(self.g);r=inventory(self.doc,self.g,self.p,'S','G');self.assertEqual(self.g,before);by={x['source_handle']:x for x in r['records']};self.assertEqual(by[self.a.dxf.handle]['status'],'source_handle_referenced');self.assertEqual(by[self.b.dxf.handle]['status'],'coincident_referenced_source_candidate');self.assertEqual(by[self.t.dxf.handle]['status'],'shorter_than_normalization_tolerance_unclassified');self.assertEqual(by[self.z.dxf.handle]['status'],'unreferenced_source_line_unclassified');self.assertFalse(by[self.b.dxf.handle]['physical_identity_resolved'])
 def test_wrong_system_and_stale_are_not_accepted(self):
  self.g['edges'][0]['system']='return';r=inventory(self.doc,self.g,self.p,'S','G');self.assertEqual(r['records'][0]['status'],'source_handle_system_conflict')
  with self.assertRaises(ValueError):inventory(self.doc,self.g,self.p,'S','old')
if __name__=='__main__':unittest.main()
