import copy
import unittest
import ezdxf
from source_glyph_system_conflicts import attach


class SourceGlyphSystemConflictsTest(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new(); m = self.doc.modelspace()
        circle = m.add_circle((0, 0), 80, dxfattribs={'layer': '空调冷冻水回水'})
        pipe = m.add_line((0, 0), (-500, 0), dxfattribs={'layer': '空调冷冻水供水'})
        coords = [((0, 0), (52.09458, 114.14687)), ((0, 0), (114.14687, 52.09458)),
                  ((34.72067, 131.52078), (131.52078, 34.72067)),
                  ((51.73687, 148.53698), (148.53698, 51.73687))]
        glyph = [m.add_line(a, b, dxfattribs={'layer': '空调立管、水平支管'}) for a, b in coords]
        self.item = {'circle_handle': circle.dxf.handle, 'center': [0, 0], 'radius': 80, 'system': 'return',
                     'glyph_handles': [e.dxf.handle for e in glyph], 'source_system_conflict': 'exact_opposite_system_endpoint',
                     'near_opposite_system_source_endpoints': [{'source_handle': pipe.dxf.handle, 'system': 'supply',
                                                                 'distance_to_circle_center': 0}]}
        self.inventory = {'source_sha256': 'S', 'glyphs': [self.item]}
        self.graph = {'metadata': {'source_sha256': 'S'},
                      'nodes': [{'node_id': 'U', 'node_type': 'virtual_equipment', 'subtype': 'unresolved_source_terminal',
                                 'system': 'supply', 'x': 0, 'y': 0, 'source_handles': [pipe.dxf.handle]},
                                {'node_id': 'T', 'node_type': 'tee', 'system': 'supply', 'x': -500, 'y': 0}],
                      'edges': [{'edge_id': 'E', 'start_node_id': 'T', 'end_node_id': 'U',
                                 'source_handles': [pipe.dxf.handle], 'system': 'supply'}]}

    def test_conflict_is_visible_and_topology_unchanged(self):
        before = copy.deepcopy(self.graph)
        graph, records = attach(self.graph, self.doc, self.inventory, 'S')
        self.assertEqual(self.graph, before)
        self.assertEqual(graph['edges'], before['edges'])
        self.assertEqual(graph['nodes'][0]['subtype'], 'unresolved_source_terminal')
        self.assertEqual(graph['nodes'][0]['resolution_state'], 'source_glyph_system_conflict_pending')
        self.assertEqual(records[0]['pipe_source_system'], 'supply')
        self.assertFalse(graph['metadata']['hil_ready'])

    def test_source_and_graph_mismatches_fail_closed(self):
        with self.assertRaises(ValueError): attach(self.graph, self.doc, self.inventory, 'wrong')
        altered = copy.deepcopy(self.graph); altered['edges'][0]['system'] = 'return'
        with self.assertRaises(ValueError): attach(altered, self.doc, self.inventory, 'S')
        altered = copy.deepcopy(self.inventory); altered['glyphs'][0]['glyph_handles'].pop()
        with self.assertRaises(ValueError): attach(self.graph, self.doc, altered, 'S')
        self.doc.entitydb[self.item['circle_handle']].dxf.layer = '空调冷冻水供水'
        with self.assertRaises(ValueError): attach(self.graph, self.doc, self.inventory, 'S')


if __name__ == '__main__': unittest.main()
