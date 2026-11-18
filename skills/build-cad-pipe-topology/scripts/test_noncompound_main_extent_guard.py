import copy,unittest
import ezdxf
from noncompound_main_extent_guard import barriers,check
from native_main_endpoint_extent import qualify
from test_native_main_endpoint_extent import fixture

class Tests(unittest.TestCase):
    def test_no_compound_labels_is_explicitly_not_applicable(self):
        r=barriers(ezdxf.new('R2013'),dict(edges=[]),'s'*64)
        self.assertEqual(r['corridors'],[]);check(dict(plan_edges=['E']),r)

    def test_compound_LINE_children_block_both_directions_other_LINE_keeps_extent(self):
        doc=ezdxf.new('R2013');m=doc.modelspace();a=m.add_line((0,0),(2000,0),dxfattribs={'layer':'空调冷冻水供水'});b=m.add_line((0,500),(2000,500),dxfattribs={'layer':'空调冷冻水供水'})
        m.add_text('DN300(3.600)/DN200(3.000)',dxfattribs={'insert':(200,50),'height':40,'layer':'空调平面'})
        g=dict(edges=[dict(edge_id='A',system='supply',source_handles=[a.dxf.handle],attribute_paths=[[[0,0],[1000,0]]]),dict(edge_id='B',system='supply',source_handles=[a.dxf.handle],attribute_paths=[[[2000,0],[1000,0]]]),dict(edge_id='C',system='supply',source_handles=[b.dxf.handle],attribute_paths=[[[2000,500],[0,500]]])])
        before=copy.deepcopy(g);proof=barriers(doc,g,'s'*64)
        for eid in ('A','B'):
            with self.assertRaisesRegex(ValueError,'member_identity'):check(dict(plan_edges=[eid]),proof)
        check(dict(plan_edges=['C']),proof);self.assertEqual(g,before)

    def test_orientation_composes_with_compound_guard_without_changing_DN_or_paths(self):
        for p in (False,True):
            for a in (False,True):
                plan,axis,row,projection=fixture(p,a);old=copy.deepcopy((plan,axis))
                check(row,dict(corridors=[]));r=qualify(plan,axis,row,250.,projection,[0,45,135])
                self.assertEqual((r['nominal_mm'],r['complete_horizontal_centerline_route_mm']),(250.,10.))
                self.assertEqual((plan,axis),old);self.assertIsNone(r['whole_installed_length_mm'])

if __name__=='__main__':unittest.main()
