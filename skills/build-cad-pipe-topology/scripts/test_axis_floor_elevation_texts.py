import unittest,ezdxf
from axis_floor_elevation_texts import collect

def scene(duplicate=False,mirror=False):
    doc=ezdxf.new();ms=doc.modelspace();sign=-1 if mirror else 1
    for n,(label,value)in enumerate([('一层','±0.000'),('二层','4.800'),('三层','9.800')]):
        y=n*10000
        for a,b in[((0,y),(-300,y+300)),((0,y),(300,y+300)),((300*sign,y+300),(-1500*sign,y+300))]:ms.add_line(a,b,dxfattribs={'layer':'LEVEL'})
        ms.add_line((-2000,y),(8000,y),dxfattribs={'layer':'BUILDING'})
        ms.add_text(label,dxfattribs={'insert':(1600,y+400),'height':500,'layer':'LEVEL'})
        ms.add_text(value,dxfattribs={'insert':(-1530*sign,y+400),'height':300,'layer':'LEVEL'})
        if duplicate and n==1:ms.add_text('5.800',dxfattribs={'insert':(-1000*sign,y+410),'height':300,'layer':'LEVEL'})
    ms.add_text('28',dxfattribs={'insert':(200,200),'height':300,'layer':'LEVEL'})
    ms.add_text('DN300(3.200)',dxfattribs={'insert':(200,400),'height':300,'layer':'LEVEL'})
    return doc

class FloorElevationTextEvidence(unittest.TestCase):
    def test_native_glyph_pairs_read_without_dimensions_or_pipe_length_assignment(self):
        for mirror in(False,True):
            r=collect(scene(mirror=mirror),'source')
            self.assertEqual([x['elevation_source_value']for x in r['records']],[0,4.8,9.8]);self.assertEqual(r['native_DIMENSION_count'],0)
            self.assertTrue(all(x['physical_pipe_length_mm']is None and x['pipe_endpoint_binding']is None for x in r['records']));self.assertEqual(r['physical_lengths_assigned'],0)
    def test_competing_numbers_are_held_and_floor_height_is_not_pipe_length(self):
        r=collect(scene(duplicate=True),'source');self.assertEqual(len(r['records']),2);self.assertEqual(len(r['pending']),1)
        self.assertTrue(r['floor_level_is_not_pipe_center_height'])

if __name__=='__main__':unittest.main()
