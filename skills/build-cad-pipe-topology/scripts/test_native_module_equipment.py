import copy
import unittest

import ezdxf
from native_module_equipment import native_union, recognize
from native_proxy_evidence import block_fingerprint
from nested_equipment_ports import bind
from test_nested_equipment_ports import graph


def square(x=0, y=0, width=10, height=5):
    return [[x, y], [x + width, y], [x + width, y + height], [x, y + height]]


def fixture(polygons=None, captions=None, transform=None):
    doc = ezdxf.new()
    body = doc.blocks.new('NATIVE_MODULES')
    for points in polygons or [square(), square(10)]:
        body.add_lwpolyline(points, close=True)
    for caption, xy in captions or [('SWJ-01', (2, 1))]:
        body.add_text(caption, dxfattribs={'height': .3, 'insert': xy})
    parent = doc.modelspace().add_blockref('NATIVE_MODULES', (0, 0), dxfattribs=transform or {})
    rule = {'source_chain': [parent.dxf.handle], 'floor': 'F1',
            'fingerprint': block_fingerprint(body), 'module_dimensions': [10, 5],
            'module_contact_tolerance': .01, 'tag_regex': r'SWJ-\d+',
            'label': 'Water-source unit', 'label_zh': '水源机组', 'symbol_key': 'EQ_SWJ',
            'enclosed_terminal_ownership': True}
    return doc, rule


class NativeModuleEquipment(unittest.TestCase):
    def test_calibrated_true_overlap_retains_its_union_without_bridging_gaps(self):
        groups = native_union([square(), square(9.997)], .0001, .004)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]['members']), 2)
        self.assertAlmostEqual(groups[0]['native_overlap_area'], .015)
        self.assertAlmostEqual(max(p[0] for p in groups[0]['polygon']), 19.997)
        self.assertEqual(len(native_union([square(), square(10.003)], .0001, .004)), 2)

    def test_calibrated_overlap_does_not_accept_partial_side_or_multiple_captions(self):
        self.assertEqual(len(native_union([square(), square(9.997, 2)], .0001, .004)), 2)
        doc, rule = fixture([square(), square(9.997)], [('SWJ-01', (1, 1)), ('SWJ-02', (11, 1))])
        rule.update(maximum_native_module_overlap=.004, native_overlap_evidence=['native side overlap .003'])
        self.assertEqual(recognize(doc, [rule])[0], [])

    def test_external_caption_requires_unique_close_parallel_source_face(self):
        from ezdxf import bbox
        doc, rule = fixture(captions=[('SWJ-01', (2, -1))])
        text = next(iter(doc.blocks['NATIVE_MODULES'].query('TEXT')))
        extent = bbox.extents([text])
        text.dxf.insert = (2, text.dxf.insert.y - extent.extmax.y - .01, 0)
        rule.update(fingerprint=block_fingerprint(doc.blocks['NATIVE_MODULES']),
                    maximum_external_caption_gap_text_heights=.05,
                    external_caption_evidence=['native caption top .01 below original face'])
        instances, audit = recognize(doc, [rule])
        self.assertEqual(len(instances), 1)
        self.assertEqual(audit[0]['caption_placement'], 'source_calibrated_external_face')
        text.dxf.insert = (2, text.dxf.insert.y - .1, 0)
        rule['fingerprint'] = block_fingerprint(doc.blocks['NATIVE_MODULES'])
        self.assertEqual(recognize(doc, [rule])[0], [])

    def test_rotated_mirrored_actual_overlap_preserves_true_module_union(self):
        doc, rule = fixture([square(), square(9.997)], transform={'rotation': 37, 'xscale': -1})
        rule.update(maximum_native_module_overlap=.004, native_overlap_evidence=['actual parallel native overlap .003'])
        instances, _ = recognize(doc, [rule])
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['native_module_count'], 2)
    def test_bounded_outline_precision_keeps_native_endpoint_and_global_tolerance(self):
        doc, rule = fixture()
        rule.update(outline_contact_tolerance=.004, outline_precision_evidence=['paired native tips offset .003'])
        instances, _ = recognize(doc, [rule])
        original = graph([[3, -.003]])
        out, audit = bind(original, instances, {'contact_tolerance': .001})
        self.assertEqual(audit['physical_port_count'], 1)
        self.assertAlmostEqual(audit['contacts'][0]['native_outline_distance'], .003)
        self.assertEqual(out['edges'][0]['path_points'], original['edges'][0]['path_points'])
        _, audit = bind(graph([[3, -.006]]), instances, {'contact_tolerance': .001})
        self.assertEqual(audit['physical_port_count'], 0)

    def test_unbounded_or_unsubstantiated_outline_precision_is_rejected(self):
        doc, rule = fixture()
        rule.update(outline_contact_tolerance=.1, outline_precision_evidence=['some source'])
        with self.assertRaisesRegex(ValueError, 'bounded source calibration'):
            recognize(doc, [rule])
        rule.update(outline_contact_tolerance=.004, outline_precision_evidence=[])
        with self.assertRaises(ValueError):
            recognize(doc, [rule])
    def test_adjacent_modules_make_one_body_with_two_real_ports(self):
        doc, rule = fixture()
        instances, audit = recognize(doc, [rule])
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]['native_module_count'], 2)
        self.assertEqual(instances[0]['bounds'], [0, 0, 20, 5])
        self.assertEqual(len(instances[0]['source_members']), 3)
        out, ports = bind(graph([[3, 0], [17, 0]]), instances, {'contact_tolerance': .01})
        self.assertEqual(ports['physical_port_count'], 2)
        self.assertEqual(out['edges'][0]['start_node_id'], out['edges'][1]['start_node_id'])
        self.assertEqual(audit[0]['shared_side_count'], 1)

    def test_point_touch_never_joins_units(self):
        doc, rule = fixture([square(), square(10, 5)], [('SWJ-01', (1, 1)), ('SWJ-02', (11, 6))])
        instances, _ = recognize(doc, [rule])
        self.assertEqual(len(instances), 2)

    def test_visible_gap_never_joins_modules(self):
        doc, rule = fixture([square(), square(10.02)], [('SWJ-01', (1, 1)), ('SWJ-02', (11, 1))])
        self.assertEqual(len(recognize(doc, [rule])[0]), 2)

    def test_two_equipment_captions_on_touching_group_remain_pending(self):
        doc, rule = fixture(captions=[('SWJ-01', (1, 1)), ('SWJ-02', (11, 1))])
        instances, audit = recognize(doc, [rule])
        self.assertEqual(instances, [])
        self.assertEqual(audit[0]['status'], 'pending_missing_or_competing_native_caption')

    def test_outside_caption_is_not_bound_to_nearest_body(self):
        doc, rule = fixture(captions=[('SWJ-01', (2, -1))])
        instances, audit = recognize(doc, [rule])
        self.assertEqual(instances, [])
        self.assertIn('pending_caption_outside_native_bodies', [r['status'] for r in audit])

    def test_same_caption_in_separate_native_groups_keeps_distinct_instances(self):
        doc, rule = fixture([square(), square(30)], [('SWJ-01', (1, 1)), ('SWJ-01', (31, 1))])
        instances, _ = recognize(doc, [rule])
        self.assertEqual(len({r['node_id'] for r in instances}), 2)

    def test_rotated_mirrored_modules_keep_original_union(self):
        doc, rule = fixture(transform={'rotation': 90, 'xscale': -1})
        instances, _ = recognize(doc, [rule])
        expected = [-5, -20, 0, 0]
        for a, b in zip(instances[0]['bounds'], expected):
            self.assertAlmostEqual(a, b)

    def test_concave_union_not_its_bounding_box_owns_contacts(self):
        polys = [square(), square(10), square(0, 5)]
        groups = native_union(polys, .01)
        self.assertEqual(len(groups), 1)
        doc, rule = fixture(polys)
        instances, _ = recognize(doc, [rule])
        _, audit = bind(graph([[18, 8]]), instances, {'contact_tolerance': .01})
        self.assertEqual(audit['physical_port_count'], 0)

    def test_module_ring_hole_rejected(self):
        with self.assertRaisesRegex(ValueError, 'hole|disconnected'):
            native_union([square(x * 10, y * 5) for x in range(3) for y in range(3)
                          if (x, y) != (1, 1)], .01)

    def test_duplicate_source_contours_rejected(self):
        with self.assertRaises(ValueError):
            native_union([square(), square()], .01)

    def test_partial_shared_side_does_not_make_whole_equipment(self):
        groups = native_union([square(), square(10, 2)], .01)
        self.assertEqual(len(groups), 2)

    def test_changed_prototype_is_not_silently_accepted(self):
        doc, rule = fixture()
        doc.blocks['NATIVE_MODULES'].add_line((0, 0), (1, 1))
        with self.assertRaisesRegex(ValueError, 'prototype'):
            recognize(doc, [rule])

    def test_unknown_geometry_retained_in_family_ledger(self):
        doc, rule = fixture()
        doc.blocks['NATIVE_MODULES'].add_lwpolyline(square(50, width=8), close=True)
        rule['fingerprint'] = block_fingerprint(doc.blocks['NATIVE_MODULES'])
        instances, audit = recognize(doc, [rule])
        self.assertEqual(len(instances), 1)
        self.assertTrue(any(r['status'] == 'pending_unsupported_module_geometry' for r in audit))


if __name__ == '__main__':
    unittest.main()
