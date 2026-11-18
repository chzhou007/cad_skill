import unittest
import ezdxf
from native_scope_leader_isolation import collect,CatalogDocument


class Tests(unittest.TestCase):
    def test_disjoint_native_components_are_preserved_in_original_document_and_queries(self):
        doc=ezdxf.new();m=doc.modelspace();l=m.add_leader([(10,10),(20,10)],dxfattribs=dict(layer='AN'))
        proof=collect(doc,[[[0,0],[0,5]]],'S');wrapped=CatalogDocument(doc,proof)
        self.assertNotIn(l,list(wrapped.modelspace()));self.assertIn(l,list(doc.modelspace()));self.assertIn(l,list(wrapped.modelspace().query('LEADER')))
        self.assertFalse(proof['source_mutated']);self.assertFalse(proof['leader_meaning_interpreted'])
    def test_crossing_annotation_chain_reaching_scope_blocks_in_rotated_and_mirrored_cases(self):
        for sign in [-1,1]:
            doc=ezdxf.new();m=doc.modelspace();m.add_leader([(10*sign,10),(20*sign,10)],dxfattribs=dict(layer='AN'))
            m.add_lwpolyline([(15*sign,15),(15*sign,0),(0,0)],dxfattribs=dict(layer='AN'))
            with self.subTest(sign=sign),self.assertRaisesRegex(ValueError,'reaches'):collect(doc,[[[0,-1],[0,1]]],'S')
    def test_unknown_referenced_annotation_curve_or_block_is_not_silently_excluded(self):
        for case in ['reference','arc','polyline_curve','insert']:
            doc=ezdxf.new();m=doc.modelspace();l=m.add_leader([(10,10),(20,10)],dxfattribs=dict(layer='AN'))
            if case=='reference':l.dxf.annotation_handle=m.add_text('DN450').dxf.handle
            elif case=='arc':m.add_arc((20,20),2,0,90,dxfattribs=dict(layer='AN'))
            elif case=='polyline_curve':m.add_lwpolyline([(10,10,1),(20,20,0)],format='xyb',dxfattribs=dict(layer='AN'))
            else:doc.blocks.new('opaque');m.add_blockref('opaque',(30,30),dxfattribs=dict(layer='AN'))
            with self.subTest(case=case),self.assertRaises(ValueError):collect(doc,[[[0,0],[0,5]]],'S')
    def test_DN_near_both_leader_and_scope_is_unresolved(self):
        doc=ezdxf.new();m=doc.modelspace();m.add_leader([(1,2),(2,2)],dxfattribs=dict(layer='AN'))
        m.add_text('DN450',dxfattribs=dict(layer='AN',height=1,insert=(.5,2)))
        with self.assertRaisesRegex(ValueError,'nearby DN'):collect(doc,[[[0,0],[0,5]]],'S')


if __name__=='__main__':unittest.main()
