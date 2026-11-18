import copy,unittest
import ezdxf
from qualified_member_caption_scope import departure_guard

def fixture(position=(200,5,0)):
    d=ezdxf.new('R2018');m=d.modelspace();line=m.add_line((0,0,0),(1000,0,0),dxfattribs={'layer':'空调冷冻水回水'});text=m.add_text('DN300(3.200)',dxfattribs={'insert':position,'height':10})
    common=dict(system='return',source_handles=[line.dxf.handle]);a=dict(common,edge_id='prefix',attribute_paths=[[[0,0],[500,0]]],member=dict(nominal_mm=300,plan_declarations=[]));b=dict(common,edge_id='departure',attribute_paths=[[[500,0],[1000,0]]],member=dict(nominal_mm=200,plan_declarations=[]))
    return d,a,b,dict(pairs=[],F_owned_texts={}),dict(reserved_leader_texts=[],corridors=[]),text

class PrefixCaptionScopeTests(unittest.TestCase):
    def test_owned_disjoint_prefix_caption_does_not_block_departure(self):
        d,a,b,c,o,t=fixture();before=copy.deepcopy((a,b,c,o));r=departure_guard(d,a,b,c,o)
        self.assertEqual([x['text_handle']for x in r['independently_owned_outside_prefix_captions']],[t.dxf.handle]);self.assertEqual(r['departure_DN_guard']['other_native_DN_checks'],[]);self.assertIs(d.entitydb[t.dxf.handle],t);self.assertEqual((a,b,c,o),before)
    def test_caption_inside_target_at_boundary_or_other_Z_still_blocks(self):
        for p in [(600,5,0),(500,5,0),(200,5,1)]:
            with self.subTest(position=p):
                d,a,b,c,o,_=fixture(p)
                with self.assertRaises(ValueError):departure_guard(d,a,b,c,o)
    def test_target_new_caption_and_F_owned_prefix_are_not_hidden(self):
        d,a,b,c,o,t=fixture();d.modelspace().add_text('DN250',dxfattribs={'insert':(800,5),'height':10})
        with self.assertRaises(ValueError):departure_guard(d,a,b,c,o)
        d,a,b,c,o,t=fixture();c['F_owned_texts'][t.dxf.handle]=[{}]
        with self.assertRaises(ValueError):departure_guard(d,a,b,c,o)
    def test_repeated_overlap_and_unproved_member_boundary_do_not_get_exclusion(self):
        d,a,b,c,o,_=fixture();b['attribute_paths']=[[[500,0],[1000,0]],[[1000,0],[100,0]]]
        with self.assertRaises(ValueError):departure_guard(d,a,b,c,o)
        d,a,b,c,o,_=fixture();b['attribute_paths'][0][0]=[501,0]
        with self.assertRaises(ValueError):departure_guard(d,a,b,c,o)

if __name__=='__main__':unittest.main()
