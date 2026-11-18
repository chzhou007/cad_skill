import copy,unittest,ezdxf
from compound_carrier_atom_origins import refine
from native_line_path_evidence import LAYERS

def fixture():
    d=ezdxf.new();m=d.modelspace();a=m.add_line((0,0),(100,0),dxfattribs={'layer':LAYERS['supply']});b=m.add_line((100,0),(100,100),dxfattribs={'layer':LAYERS['supply']})
    text=m.add_text('DN300(3.2)/DN200(2.6)',dxfattribs=dict(layer='NOTE',height=5,insert=(30,3)))
    e=dict(edge_id='E',system='supply',source_handles=[a.dxf.handle,b.dxf.handle],attribute_paths=[[[0,0],[100,0],[100,100]]]);return d,dict(edges=[e]),a,b,text
class Tests(unittest.TestCase):
    def test_no_compound_declarations_is_valid_empty_population(self):
        d,g,a,b,t=fixture();d.modelspace().delete_entity(t);r=refine(d,g,'SRC');self.assertEqual(r['corridors'],[]);self.assertEqual(r['excluded_other_arm_origins'],[])
    def test_other_arm_does_not_seed_every_native_LINE_on_composite_edge(self):
        d,g,a,b,t=fixture();before=copy.deepcopy(g);r=refine(d,g,'SRC');self.assertEqual({c['source_LINE']for c in r['original_risks']['corridors']},{a.dxf.handle,b.dxf.handle});self.assertEqual({c['source_LINE']for c in r['corridors']},{a.dxf.handle});self.assertEqual(len(r['excluded_other_arm_origins']),1);self.assertEqual(g,before);self.assertEqual(r['physical_members_assigned'],0)
    def test_parallel_real_compound_candidate_is_retained(self):
        d,g,a,b,t=fixture();t.dxf.insert=(97,20);t.dxf.rotation=90;r=refine(d,g,'SRC');self.assertEqual({c['source_LINE']for c in r['corridors']},{b.dxf.handle})
    def test_unmodeled_duplicate_LINE_and_unsupported_transform_keep_old_barriers(self):
        for kind in('duplicate','OCS','aligned'):
            d,g,a,b,t=fixture()
            if kind=='duplicate':d.modelspace().add_line((0,0),(100,0),dxfattribs={'layer':LAYERS['supply']})
            elif kind=='OCS':t.dxf.extrusion=(0,0,-1)
            else:t.dxf.halign=2
            r=refine(d,g,'SRC')
            with self.subTest(kind=kind):self.assertFalse(r['excluded_other_arm_origins'])
    def test_exploded_F_bars_have_priority_over_axial_exclusion(self):
        d,g,a,b,t=fixture();m=d.modelspace();m.add_line((20,0),(20,20),dxfattribs={'layer':'NOTE'});m.add_line((20,0),(60,0),dxfattribs={'layer':'NOTE'});m.add_line((20,10),(60,10),dxfattribs={'layer':'NOTE'});m.add_text('DN300(3.2)/DN200(2.6)',dxfattribs=dict(layer='NOTE',height=5,insert=(30,13)))
        r=refine(d,g,'SRC');self.assertTrue(r['reserved_leader_texts']);self.assertFalse(r['excluded_other_arm_origins'])
if __name__=='__main__':unittest.main()
