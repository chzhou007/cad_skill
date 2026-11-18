import unittest,ezdxf
from circle_witness_inventory import scan
class CircleWitnessInventory(unittest.TestCase):
 def test_nested_circle_transform_and_negative(self):
  d=ezdxf.new();b=d.blocks.new('RING');b.add_circle((0,0),5);d.modelspace().add_blockref('RING',(100,200));r=scan(d,[{'id':'center','point':[100,200]},{'id':'rim','point':[105,200]},{'id':'far','point':[300,300]}],.01);self.assertEqual(r['records'][0]['hits'][0]['scope'],'nested_insert');self.assertEqual(r['records'][1]['hits'][0]['relationship'],'rim');self.assertEqual(r['records'][2]['hits'],[]);self.assertFalse(r['exceptions'])
 def test_polyline_bulge_is_arc_candidate_not_complete_ring(self):
  d=ezdxf.new();d.modelspace().add_lwpolyline([(0,0,1),(10,0,0)],format='xyb');r=scan(d,[{'id':'a','point':[5,0]}],.01);h=r['records'][0]['hits'];self.assertEqual(len(h),1);self.assertEqual(h[0]['type'],'ARC');self.assertEqual(h[0]['relationship'],'center');self.assertAlmostEqual(h[0]['arc_span_degrees'],180)
 def test_nested_nonuniform_circle_yields_ellipse_candidate(self):
  d=ezdxf.new();b=d.blocks.new('R');b.add_circle((0,0),2);d.modelspace().add_blockref('R',(20,20),dxfattribs={'xscale':2,'yscale':1});r=scan(d,[{'id':'e','point':[20,20]}],.01);self.assertEqual(r['records'][0]['hits'][0]['type'],'ELLIPSE')
 def test_invalid_tolerance(self):
  with self.assertRaises(ValueError):scan(ezdxf.new(),[],0)
if __name__=='__main__':unittest.main()
