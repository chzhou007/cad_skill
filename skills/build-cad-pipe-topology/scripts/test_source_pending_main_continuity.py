import copy
import unittest
import ezdxf
from source_pending_main_continuity import attach


class PendingMainContinuityTest(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new(); m = self.doc.modelspace(); layer = '空调冷冻水回水'
        main = m.add_line((-10, 0), (10, 0), dxfattribs={'layer': layer})
        branch = m.add_line((0, 0), (0, 10), dxfattribs={'layer': layer})
        circle = m.add_circle((0, 1.3), 80, dxfattribs={'layer': layer})
        self.main, self.branch = main, branch
        self.pending = [{'x': 0, 'y': 0, 'system': 'return', 'degree': 3,
                         'reason': 'riser_or_circle_symbol_contact', 'circle_handles': [circle.dxf.handle]}]
        n = {'node_id': 'U', 'node_type': 'virtual_equipment', 'subtype': 'pending_source_junction',
             'system': 'return', 'x': 0, 'y': 0, 'source_handles': [main.dxf.handle, branch.dxf.handle], 'review_required': True}
        def e(name, dest, h, points):
            return {'edge_id': name, 'start_node_id': 'U', 'end_node_id': dest, 'system': 'return',
                    'source_handles': [h], 'attribute_paths': [points]}
        self.graph = {'metadata': {'source_sha256': 'S'}, 'nodes': [n], 'edges': [
            e('L', 'A', main.dxf.handle, [[0, 0], [-10, 0]]), e('R', 'B', main.dxf.handle, [[0, 0], [10, 0]]),
            e('X', 'C', branch.dxf.handle, [[0, 0], [0, 10]])]}

    def test_records_main_but_not_branch_connectivity(self):
        before = copy.deepcopy(self.graph); result, records = attach(self.graph, self.doc, self.pending, 'S')
        self.assertEqual(self.graph, before)
        self.assertEqual(result['edges'], before['edges'])
        self.assertEqual(result['nodes'][0]['node_type'], 'virtual_equipment')
        self.assertEqual(records[0]['main_edge_ids'], ['L', 'R'])
        self.assertEqual(records[0]['branch_connectivity'], 'pending')
        self.assertFalse(result['metadata']['hil_ready'])

    def test_branch_path_must_follow_native_endpoint_line(self):
        altered = copy.deepcopy(self.graph)
        altered['edges'][2]['attribute_paths'] = [[[0, 0], [5, 5]]]
        with self.assertRaisesRegex(ValueError, 'branch edge leaves native source line'):
            attach(altered, self.doc, self.pending, 'S')
        altered['edges'][2]['attribute_paths'] = [[[0, 0], [0, 20]]]
        with self.assertRaisesRegex(ValueError, 'branch edge leaves native source line'):
            attach(altered, self.doc, self.pending, 'S')

    def test_nearby_circle_must_cover_contact(self):
        circle = self.doc.entitydb[self.pending[0]['circle_handles'][0]]
        circle.dxf.center = (0, 200, 0)
        with self.assertRaisesRegex(ValueError, 'outside source circle'):
            attach(self.graph, self.doc, self.pending, 'S')

    def test_inconsistent_source_is_rejected(self):
        with self.assertRaises(ValueError): attach(self.graph, self.doc, self.pending, 'bad')
        altered = copy.deepcopy(self.graph); altered['edges'][2]['source_handles'].append(self.main.dxf.handle)
        with self.assertRaises(ValueError): attach(altered, self.doc, self.pending, 'S')
        altered = copy.deepcopy(self.graph); altered['edges'][1]['attribute_paths'] = [[[0, 0], [-5, 0]]]
        with self.assertRaises(ValueError): attach(altered, self.doc, self.pending, 'S')
        self.branch.dxf.start = (1, 0, 0)
        with self.assertRaises(ValueError): attach(self.graph, self.doc, self.pending, 'S')


if __name__ == '__main__': unittest.main()
