import copy,math,unittest
import ezdxf
from native_paired_end_labels import collect,observe,pair,level_key

def fixture(rotation=0):
    d=ezdxf.new('R2013');m=d.modelspace();a=math.radians(rotation)
    def p(x,y):return(x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a))
    supply=m.add_line(p(0,0),p(4000,0),dxfattribs={'layer':'空调冷冻水供水'})
    ret=m.add_line(p(0,400),p(4400,400),dxfattribs={'layer':'空调冷冻水回水'})
    t1=m.add_text('DN200(3.000)',dxfattribs={'insert':p(4500,-380),'height':350,'rotation':rotation,'layer':'空调平面'})
    t2=m.add_text('DN200(3.000)',dxfattribs={'insert':p(4500,290),'height':350,'rotation':rotation,'layer':'空调平面'})
    return d,supply,ret,t1,t2

class Tests(unittest.TestCase):
    def test_joint_ordered_pair_and_rotation_without_DN_matching(self):
        for angle in(0,90,180,270):
            d,s,r,t1,t2=fixture(angle);result=collect(d);self.assertEqual(len(result['pairs']),1)
            rows=result['pairs'][0]['observations'];self.assertEqual([x['native_pipe']['source_LINE']for x in rows],[s.dxf.handle,r.dxf.handle])
            self.assertFalse(result['pairs'][0]['DN_or_level_used_to_choose_pipe'])
            t1.dxf.text='DN150(8.100)';t2.dxf.text='DN250(9.200)'
            self.assertEqual([x['native_pipe']['source_LINE']for x in collect(d)['pairs'][0]['observations']],[s.dxf.handle,r.dxf.handle])

    def test_competing_native_LINE_unknown_transform_and_different_profiles_fail(self):
        d,s,r,t1,t2=fixture();duplicate=r.copy();d.modelspace().add_entity(duplicate)
        self.assertEqual(collect(d)['pairs'],[])
        d,s,r,t1,t2=fixture();t1.dxf.extrusion=(0,0,-1);self.assertEqual(collect(d)['pairs'],[])
        d,s,r,t1,t2=fixture();t1.dxf.height=300;self.assertEqual(collect(d)['pairs'],[])

    def test_interior_caption_is_not_reinterpreted_as_end_label(self):
        d,s,r,t1,t2=fixture();t1.dxf.insert=(2000,-380);t2.dxf.insert=(2000,290)
        self.assertEqual(collect(d)['pairs'],[])

    def test_literal_levels_do_not_create_elevation_units(self):
        self.assertEqual(level_key('3.000'),level_key('3.0'));self.assertNotEqual(level_key('3.6'),level_key('3.0'))
        self.assertIsNone(level_key(None))
        with self.assertRaises(ValueError):level_key('NaN')
if __name__=='__main__':unittest.main()
