import unittest
from unittest.mock import patch
import ezdxf
import pipe_geometry as pg
from ezdxf import bbox
from source_symbol_bounds import visible_symbol_bounds
from instrumentation import symbol_pipe_contacts


def fixture():
    doc = ezdxf.new()
    block = doc.blocks.new('VALVE')
    block.add_line((-.5, -.35), (-.5, .35))
    block.add_line((.5, -.35), (.5, .35))
    block.add_line((-.4, -.35), (.4, .35))
    block.add_circle((0, 0), .09)
    block.add_attdef('TYPE', (2, 0), text='', dxfattribs={'flags': 1})
    insert = doc.modelspace().add_blockref('VALVE', (0, 0))
    attr = insert.add_attrib('TYPE', '无值', (2, 0), dxfattribs={'flags': 1, 'height': .2})
    return doc, insert, attr


class VisibleSymbolBounds(unittest.TestCase):
    def test_unreadable_native_attribute_stops_geometry_trial(self):
        _, insert, attr = fixture()
        attr.dxf.text = '管径\ufffd'
        with self.assertRaisesRegex(ValueError, 'verify Chinese'):
            visible_symbol_bounds(insert)

    def setUp(self):
        self.tolerance = patch.object(pg, 'TOL', .01)
        self.tolerance.start()

    def tearDown(self):
        self.tolerance.stop()

    def test_invisible_native_attribute_is_metadata_not_symbol_extent(self):
        doc, insert, attr = fixture()
        old = bbox.extents([insert])
        bounds, audit = visible_symbol_bounds(insert)
        self.assertGreater(old.extmax.x, 2)
        self.assertEqual(bounds, [-.5, -.35, .5, .35])
        self.assertEqual(audit['nonrendering_metadata'][0]['text'], '无值')
        self.assertEqual(audit['nonrendering_metadata'][0]['source_handle'], attr.dxf.handle)
        self.assertEqual(attr.dxf.text, '无值')
        self.assertTrue(audit['bounds_changed'])

    def test_geometry_bbox_removes_false_foreign_pipe_candidate(self):
        doc, insert, _ = fixture()
        edges = [dict(edge_id='OWN', path_points=[[-2, 0], [2, 0]]),
                 dict(edge_id='FOREIGN', path_points=[[2, -1], [2, 1]])]
        old = bbox.extents([insert])
        symbol = {'entity': insert, 'block': 'VALVE', 'bounds': [old.extmin.x, old.extmin.y, old.extmax.x, old.extmax.y]}
        before, _ = symbol_pipe_contacts(symbol, edges, doc)
        self.assertEqual({r['edge_id'] for r in before}, {'OWN', 'FOREIGN'})
        symbol['bounds'], _ = visible_symbol_bounds(insert)
        after, _ = symbol_pipe_contacts(symbol, edges, doc)
        self.assertEqual([r['edge_id'] for r in after], ['OWN'])

    def test_true_two_pipe_contacts_stay_ambiguous(self):
        doc, insert, _ = fixture()
        edges = [dict(edge_id='A', path_points=[[-2, 0], [2, 0]]),
                 dict(edge_id='B', path_points=[[0, -1], [0, 1]])]
        bounds, _ = visible_symbol_bounds(insert)
        found, _ = symbol_pipe_contacts({'entity': insert, 'block': 'VALVE', 'bounds': bounds}, edges, doc)
        self.assertEqual(len(found), 2)

    def test_visible_attribute_is_preserved_in_visible_extent(self):
        _, insert, attr = fixture()
        attr.dxf.flags = 0
        bounds, audit = visible_symbol_bounds(insert)
        self.assertGreater(bounds[2], 2)
        self.assertEqual(audit['nonrendering_metadata'], [])

    def test_empty_visible_attribute_does_not_make_false_extent(self):
        _, insert, attr = fixture()
        attr.dxf.flags = 0
        attr.dxf.text = ''
        bounds, audit = visible_symbol_bounds(insert)
        self.assertEqual(bounds, [-.5, -.35, .5, .35])
        self.assertEqual(audit['nonrendering_metadata'][0]['reason'], 'empty_text')

    def test_nested_mirror_rotation_preserves_actual_source_bounds(self):
        doc, _, _ = fixture()
        group = doc.blocks.new('GROUP')
        group.add_blockref('VALVE', (10, 20), dxfattribs={'rotation': 90, 'xscale': -1})
        root = doc.modelspace().add_blockref('GROUP', (100, 200))
        bounds, _ = visible_symbol_bounds(root)
        for actual, expected in zip(bounds, [109.65, 219.5, 110.35, 220.5]):
            self.assertAlmostEqual(actual, expected)

    def test_metadata_only_declared_symbol_is_not_fabricated_hardware(self):
        doc = ezdxf.new();block = doc.blocks.new('ONLY_METADATA')
        block.add_attdef('TYPE', (0, 0), text='', dxfattribs={'flags': 1})
        insert = doc.modelspace().add_blockref('ONLY_METADATA', (0, 0))
        insert.add_attrib('TYPE', 'DN250', (10, 10), dxfattribs={'flags': 1})
        with self.assertRaisesRegex(ValueError, 'no visible native geometry'):
            visible_symbol_bounds(insert)


if __name__ == '__main__':
    unittest.main()
