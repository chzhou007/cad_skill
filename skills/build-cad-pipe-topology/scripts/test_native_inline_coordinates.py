import math,unittest
import ezdxf
from native_inline_coordinates import ball_valve_anchor,balancing_valve_anchor

class NativeInlineCoordinatesTest(unittest.TestCase):
    def fixture(self,extrusion=(0,0,1),rotation=0,xscale=1,yscale=1):
        d=ezdxf.new();b=d.blocks.new('VERIFIED')
        b.add_lwpolyline([(9,20,1),(11,20,1)],format='xyb',close=True)
        for a,c in [((9,18),(9,22)),((11,18),(11,22)),((8,20),(12,20))]:b.add_line(a,c)
        ins=d.modelspace().add_blockref('VERIFIED',(100,200),dxfattribs={'extrusion':extrusion,'rotation':rotation,'xscale':xscale,'yscale':yscale})
        return ins
    def test_rotated_mirrored_and_negative_ocs_match_transformed_center(self):
        for axis in [(0,0,1),(0,0,-1)]:
            for rotation in [0,45,90,180,270]:
                for mirror in [1,-1]:
                    with self.subTest(axis=axis,rotation=rotation,mirror=mirror):
                        ins=self.fixture(axis,rotation,mirror);a=ball_valve_anchor(ins);expected=ins.matrix44().transform((10,20,0))
                        self.assertAlmostEqual(a['center'][0],expected.x,places=7);self.assertAlmostEqual(a['center'][1],expected.y,places=7)
    def test_negative_extrusion_is_not_raw_ocs(self):
        ins=self.fixture((0,0,-1));a=ball_valve_anchor(ins);poly=next(e for e in ins.virtual_entities()if e.dxftype()=='LWPOLYLINE');raw=list(poly.get_points())
        self.assertNotAlmostEqual(a['center'][0],(raw[0][0]+raw[1][0])/2)
    def test_incomplete_and_plain_arc_negative_controls(self):
        ins=self.fixture();b=ins.doc.blocks['VERIFIED'];b.delete_entity(next(e for e in b if e.dxftype()=='LINE'));self.assertIsNone(ball_valve_anchor(ins))
        ins=self.fixture();poly=next(e for e in ins.doc.blocks['VERIFIED']if e.dxftype()=='LWPOLYLINE');poly.set_points([(9,20,.2),(11,20,.2)],format='xyb');self.assertIsNone(ball_valve_anchor(ins))
    def test_balancing_full_signature_and_transform(self):
        d=ezdxf.new();b=d.blocks.new('BALANCING')
        for a,c in [((-1,-2),(1,-2)),((-1,2),(1,2)),((-1,-2),(1,2)),((1,-2),(-1,2)),((.5,-1),(1.1,-1)),((.5,1),(1.1,1))]:b.add_line(a,c)
        for rotation in (0,45,90,180):
            ins=d.modelspace().add_blockref('BALANCING',(100,200),dxfattribs={'rotation':rotation,'xscale':-1})
            anchor=balancing_valve_anchor(ins);self.assertIsNotNone(anchor);self.assertAlmostEqual(anchor['center'][0],100);self.assertAlmostEqual(anchor['center'][1],200)
        b.delete_entity(list(b)[-1]);self.assertIsNone(balancing_valve_anchor(ins))
    def test_random_six_lines_are_not_balancing_valve(self):
        d=ezdxf.new();b=d.blocks.new('RANDOM')
        for k in range(6):b.add_line((k,0),(k,10))
        self.assertIsNone(balancing_valve_anchor(d.modelspace().add_blockref('RANDOM',(0,0))))
if __name__=='__main__':unittest.main()
