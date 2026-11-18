import copy
import unittest
import ezdxf

from native_detail_corner_context import collect
from native_line_path_evidence import LAYERS


class CornerContextTests(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        handles = []
        for x, y in ((0, 0), (10, 0), (0, 5), (10, 5)):
            line = self.doc.modelspace().add_line((x, y), (x + 20, y + 30),
                dxfattribs=dict(layer='ANNO', linetype='DASH'))
            handles.append(line.dxf.handle)
        self.graph = dict(metadata=dict(source_sha256='source'), nodes=[], edges=[])
        self.policy = dict(source_sha256='source', graph_sha256='graph', annotation_layer='ANNO',
            allowed_linetypes=['DASH'], frames=[dict(frame_id='A', line_handles=handles)])

    def run_case(self, policy=None):
        return collect(self.doc, self.graph, policy or self.policy, 'source', 'graph')

    def test_translation_is_annotation_only_and_inputs_unchanged(self):
        original = copy.deepcopy(self.graph)
        result = self.run_case()
        self.assertTrue(result['frames'][0]['exact_vertical_translation'])
        self.assertFalse(result['mapping_ready'])
        self.assertEqual(result['pipe_values_assigned'], 0)
        self.assertEqual(self.graph, original)

    def test_distinct_corner_clearance_is_preserved_without_scale_inference(self):
        # Both lower bottom corners move; individual source lines stay intact.
        for h in self.policy['frames'][0]['line_handles'][:2]:
            line = self.doc.entitydb[h]
            line.dxf.start = (line.dxf.start.x, -100, 0)
        result = self.run_case()
        frame = result['frames'][0]
        self.assertFalse(frame['exact_vertical_translation'])
        self.assertEqual(frame['annotation_clearance_difference'], 100)
        self.assertFalse(result['coordinate_offsets_are_physical_lengths'])
        self.assertEqual(result['connections_added'], 0)

    def test_wrong_source_binding_rejected(self):
        policy = copy.deepcopy(self.policy)
        policy['source_sha256'] = 'other'
        with self.assertRaises(ValueError):
            self.run_case(policy)

    def test_pipe_layer_is_not_annotation(self):
        policy = copy.deepcopy(self.policy)
        policy['annotation_layer'] = LAYERS['supply']
        with self.assertRaises(ValueError):
            self.run_case(policy)

    def test_duplicate_scope_and_reused_line_are_rejected(self):
        policy = copy.deepcopy(self.policy)
        policy['frames'].append(copy.deepcopy(policy['frames'][0]))
        with self.assertRaises(ValueError):
            self.run_case(policy)
        policy['frames'][1]['frame_id'] = 'B'
        with self.assertRaises(ValueError):
            self.run_case(policy)

    def test_wrong_linetype_rejected(self):
        self.doc.entitydb[self.policy['frames'][0]['line_handles'][0]].dxf.linetype = 'CONTINUOUS'
        with self.assertRaises(ValueError):
            self.run_case()

    def test_nonplanar_corner_rejected(self):
        line = self.doc.entitydb[self.policy['frames'][0]['line_handles'][0]]
        line.dxf.start = (0, 0, 1)
        with self.assertRaises(ValueError):
            self.run_case()

    def test_crossed_corner_correspondence_rejected(self):
        handles = self.policy['frames'][0]['line_handles']
        first, second = (self.doc.entitydb[h] for h in handles[:2])
        a, b = first.dxf.start, second.dxf.start
        first.dxf.start, second.dxf.start = b, a
        with self.assertRaises(ValueError):
            self.run_case()

    def test_incomplete_rectangle_rejected(self):
        line = self.doc.entitydb[self.policy['frames'][0]['line_handles'][0]]
        line.dxf.start = (2, 2, 0)
        with self.assertRaises(ValueError):
            self.run_case()

    def test_legacy_translation_reader_still_rejects_unequal_clearance(self):
        from source_detail_frame_links import screen
        for h in self.policy['frames'][0]['line_handles'][:2]:
            line = self.doc.entitydb[h]
            line.dxf.start = (line.dxf.start.x, -100, 0)
        hashes = dict(source_sha256='source', graph_sha256='graph', glyphs_sha256='glyphs')
        policy = dict(self.policy, glyphs_sha256='glyphs')
        glyphs = dict(source_sha256='source', graph_sha256='graph', graph_mutated=False, rows=[])
        with self.assertRaises(ValueError):
            screen(self.doc, glyphs, policy, hashes)




class PortableNativeCornerFixtureTests(unittest.TestCase):
    def test_source_derived_eight_LINE_fixture_is_readable_and_nonmetric(self):
        from pathlib import Path
        from confirm_crossview_paths import load,sha
        from source_readability import read_source
        case=Path(__file__).resolve().parents[1]/'assets/regression/native-detail-corner-context'
        source=case/'sh16-10-native-corners.dxf'
        doc,preflight=read_source(source)
        self.assertEqual(preflight['status'],'PASS_STRICT_NATIVE_TEXT')
        actual=collect(doc,load(case/'graph.json'),load(case/'policy.json'),sha(source),sha(case/'graph.json'))
        self.assertEqual(len(actual['frames']),2)
        self.assertTrue(all(abs(f['annotation_clearance_difference']-100)<.05 for f in actual['frames']))
        self.assertFalse(actual['mapping_ready'])
        self.assertEqual(actual['connections_added'],0)

if __name__ == '__main__':
    unittest.main()
