import copy,math,unittest
from test_qualified_inline_DN_evidence import fixture
from component_DN_underline_end import collect
from discover_native_component_DN import discover


class Tests(unittest.TestCase):
    def test_inherited_and_opposite_underline_ends_are_discovered_in_rotated_mirrored_native_sources(self):
        for angle in [0,90,180,270]:
            for mirrored in [False,True]:
                for side in ['old','right-hub']:
                    doc,g,p,q,dn,lines,joints=fixture(angle,mirrored)
                    if side=='right-hub':
                        r=math.radians(angle);offset=(-1200*math.cos(r),-1200*math.sin(r),0)
                        q.dxf.insert=tuple(q.dxf.insert[i]+offset[i]for i in range(3));dn.dxf.insert=tuple(dn.dxf.insert[i]+offset[i]for i in range(3))
                        hub=lines[0].dxf.start;lines[0].dxf.end=(hub.x-2200*math.cos(r),hub.y-2200*math.sin(r),0)
                    before=copy.deepcopy(g)
                    with self.subTest(angle=angle,mirrored=mirrored,side=side):
                        out=discover(doc,g,'S','G');self.assertEqual(len(out['records']),1)
                        self.assertEqual(len(out['records'][0]['evidence']['records'][0]['bindings']),4)
                        self.assertFalse(out['pipe_DN_inferred']);self.assertEqual(g,before)
    def test_unpointed_same_symbols_are_not_broadcast_and_unknown_parameters_stay_unknown(self):
        doc,g,p,q,dn,lines,joints=fixture();q.dxf.text='金属软管/余同';doc.modelspace().add_blockref('FLEX',(9000,9000))
        out=collect(doc,g,p,'S','G');r=out['records'][0]
        self.assertEqual(len(r['bindings']),4);self.assertFalse(r['unpointed_same_symbols_inferred']);self.assertIsNone(r['resistance_parameter'])
    def test_arrow_to_native_component_axis_interior_attributes_component_without_creating_port(self):
        doc,g,p,q,dn,lines,joints=fixture();pts=[list(e.dxf.location)for e in joints[0].virtual_entities()if e.dxftype()=='POINT']
        lines[1].dxf.end=tuple(.25*pts[0][i]+.75*pts[1][i]for i in range(3))
        r=collect(doc,g,p,'S','G')['records'][0]['bindings'][0]
        self.assertEqual(r['annotation_target_kind'],'native_component_axis_interior');self.assertAlmostEqual(r['native_axis_fraction'],.75)
        self.assertFalse(r['physical_port_verified'])
    def test_ambiguous_native_ports_or_changed_owner_and_extra_arrow_are_rejected(self):
        for mode in ['duplicate','owner','free-arrow','source-z','pipe-qualifier']:
            doc,g,p,q,dn,lines,joints=fixture()
            if mode=='duplicate':doc.modelspace().add_blockref('FLEX',joints[0].dxf.insert)
            elif mode=='owner':g['edges'][0]['equipment_names']=[]
            elif mode=='free-arrow':
                e=doc.modelspace().add_line(lines[0].dxf.start,(9000,9000),dxfattribs={'layer':'NOTE'});p['labels'][0]['leader_handles'].append(e.dxf.handle)
            elif mode=='source-z':lines[1].dxf.end=(lines[1].dxf.end.x,lines[1].dxf.end.y,5)
            else:q.dxf.text='管道'
            with self.subTest(mode=mode),self.assertRaises(ValueError):collect(doc,g,p,'S','G')

if __name__=='__main__':unittest.main()
