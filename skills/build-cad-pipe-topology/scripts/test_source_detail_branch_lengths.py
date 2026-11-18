import copy
import unittest
import ezdxf
from source_detail_branch_lengths import repair


class DetailLengths(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        self.circle = self.doc.modelspace().add_circle((0, 0), 1)
        self.line = self.doc.modelspace().add_line((1, 0), (5, 0))
        self.graph = {'metadata': {'source_sha256': 'abc'},
            'sourceDetailComparison': {'source_sha256': 'abc', 'pairs': [{'detail_tee': 'T', 'detail_pipe': self.line.dxf.handle, 'detail_circle': self.circle.dxf.handle, 'system': 'supply'}]},
            'nodes': [{'node_id': 'T', 'x': 0, 'y': 0}, {'node_id': 'V', 'x': 5, 'y': 0}],
            'edges': [{'edge_id': 'E', 'start_node_id': 'T', 'end_node_id': 'V', 'system': 'supply', 'source_handles': [self.line.dxf.handle], 'attribute_paths': [[[0, 0], [5, 0]]], 'path_points': [[0, 0], [5, 0]], 'path_length': 5}]}

    def test_source_length_and_logical_path_are_separate(self):
        old = copy.deepcopy(self.graph)
        g, audit = repair(self.graph, self.doc, 'abc')
        self.assertEqual(self.graph, old)
        self.assertEqual(g['nodes'], old['nodes'])
        self.assertEqual(g['edges'][0]['path_points'], old['edges'][0]['path_points'])
        self.assertEqual(g['edges'][0]['attribute_paths'], [[[1, 0], [5, 0]]])
        self.assertEqual(g['edges'][0]['path_length'], 4)
        self.assertFalse(g['edges'][0]['path_length_complete'])
        self.assertEqual(audit[0]['removed_display_radius'], 1)

    def test_wrong_source_or_nonrim_line_fails_without_mutating_graph(self):
        old = copy.deepcopy(self.graph)
        with self.assertRaisesRegex(ValueError, 'identity'): repair(self.graph, self.doc, 'other')
        self.line.dxf.start = (2, 0)
        with self.assertRaisesRegex(ValueError, 'circle rim'): repair(self.graph, self.doc, 'abc')
        self.assertEqual(self.graph, old)

    def test_reverse_orientation(self):
        e = self.graph['edges'][0]
        e['start_node_id'], e['end_node_id'] = e['end_node_id'], e['start_node_id']
        e['attribute_paths'] = [[[5, 0], [0, 0]]]
        g, _ = repair(self.graph, self.doc, 'abc')
        self.assertEqual(g['edges'][0]['attribute_paths'], [[[5, 0], [1, 0]]])


if __name__ == '__main__': unittest.main()
