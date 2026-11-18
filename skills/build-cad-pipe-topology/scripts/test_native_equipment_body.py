import unittest
import ezdxf
from native_equipment_body import body_straight_segments, segments_intersect, point_segment_distance
from source_readability import bind_graph_source


class NativeEquipmentBodyTest(unittest.TestCase):
    def test_nested_rotated_mirrored_closed_polyline(self):
        d = ezdxf.new(); inner = d.blocks.new('inner')
        inner.add_lwpolyline([(0,0),(4,0),(4,2),(0,2)], close=True)
        outer = d.blocks.new('outer')
        outer.add_blockref('inner', (2, 3), dxfattribs={'rotation':90, 'xscale':-1})
        insert = d.modelspace().add_blockref('outer', (100, 200))
        segs, omitted = body_straight_segments(insert)
        self.assertEqual(len(segs),4)
        self.assertEqual(omitted,{})
        points={(round(x,5),round(y,5)) for seg in segs for x,y in seg}
        self.assertEqual(points,{(102.,203.),(102.,199.),(100.,199.),(100.,203.)})

    def test_outline_contact_distinguishes_endpoint_and_crossing(self):
        d=ezdxf.new(); block=d.blocks.new('body')
        block.add_lwpolyline([(0,0),(10,0),(10,10),(0,10)],close=True)
        segs,_=body_straight_segments(d.modelspace().add_blockref('body',(0,0)))
        self.assertLessEqual(min(point_segment_distance((5,0),a,b) for a,b in segs),.05)
        self.assertTrue(any(segments_intersect((-1,5),(11,5),a,b) for a,b in segs))
        self.assertFalse(any(segments_intersect((-1,-1),(11,-1),a,b) for a,b in segs))

    def test_graph_source_binding_never_replaces_a_different_source(self):
        source='a'*64; graph={'nodes':[], 'edges':[]}
        self.assertIs(bind_graph_source(graph, source),graph)
        self.assertEqual(graph['metadata']['source_sha256'],source)
        self.assertFalse(graph['metadata']['hil_ready'])
        with self.assertRaisesRegex(ValueError,'different native source'):
            bind_graph_source(graph,'b'*64)
        with self.assertRaisesRegex(ValueError,'invalid native source'):
            bind_graph_source({},'not-a-sha')

    def test_bulge_and_circle_reported_not_falsely_straight(self):
        d=ezdxf.new(); block=d.blocks.new('body')
        block.add_lwpolyline([(0,0,1),(10,0,0),(10,10,0)],format='xyb')
        block.add_circle((0,0),5)
        segs,omitted=body_straight_segments(d.modelspace().add_blockref('body',(0,0)))
        self.assertEqual(len(segs),1)
        self.assertEqual(omitted,{'LWPOLYLINE_bulge_segment':1,'CIRCLE':1})

if __name__=='__main__': unittest.main()
