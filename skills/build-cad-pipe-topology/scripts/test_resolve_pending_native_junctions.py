import copy
import unittest

import ezdxf
from resolve_pending_native_junctions import collect, normalize
from source_circle_rim_tee_screen import LAYERS


class PendingJunctionTests(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        self.layer = next(k for k, v in LAYERS.items() if v == 'supply')
        self.other_layer = next(k for k, v in LAYERS.items() if v == 'return')
        for layer, colour in [(self.layer, 6), (self.other_layer, 4)]:
            self.doc.layers.new(layer, dxfattribs=dict(color=colour))
        ms = self.doc.modelspace()
        self.main = ms.add_line((-20, 0), (20, 0), dxfattribs=dict(layer=self.layer))
        self.branch = ms.add_line((0, 0), (0, 15), dxfattribs=dict(layer=self.layer))
        self.circle = ms.add_circle((0, 1.3), 3, dxfattribs=dict(layer=self.layer))
        self.node = dict(node_id='UT1', node_type='virtual_equipment', subtype='pending_source_junction',
            floor=2, system='supply', x=0, y=0, review_required=True,
            boundary_type='unresolved_source_terminal', source_main_continuation=dict(source_sha256='SOURCE',
                branch_connectivity='pending', source_point=[0, 0], main_edge_ids=['E1', 'E2'], branch_edge_id='E3',
                main_source_handle=self.main.dxf.handle, branch_source_handle=self.branch.dxf.handle,
                circle_handles=[self.circle.dxf.handle]))
        edges = []
        nodes = [self.node]
        for i, point in enumerate([[-10, 0], [10, 0], [0, 10]], 1):
            nodes.append(dict(node_id='T'+str(i), node_type='tee', subtype='physical_tee', floor=2, system='supply', x=point[0], y=point[1]))
            edges.append(dict(edge_id='E'+str(i), start_node_id='UT1', end_node_id='T'+str(i),
                system='supply', edge_type='tee_to_virtual_equipment', attribute_paths=[[[0, 0], point]],
                path=[[0, 0], point], path_length=10, source_handles=[self.main.dxf.handle if i < 3 else self.branch.dxf.handle],
                physical_length_mm=None, equipment_names=['VALVE1'] if i == 1 else []))
        self.graph = dict(nodes=nodes, edges=edges, metadata=dict(hil_ready=True))
        self.scope = [dict(node_id='UT1', circle_handle=self.circle.dxf.handle)]

    def read(self):
        return collect(self.doc, self.graph, self.scope, 'SOURCE', 'GRAPH')

    def test_exact_intersection_not_marker_centre_rebuilds_incident_edges(self):
        before = copy.deepcopy(self.graph)
        rows = self.read()
        out = normalize(self.graph, rows)
        self.assertEqual(self.graph, before)
        self.assertAlmostEqual(rows[0]['circle_offset'], 1.3)
        self.assertEqual(out['nodes'][0]['node_type'], 'tee')
        self.assertEqual([out['nodes'][0]['x'], out['nodes'][0]['y']], [0, 0])
        self.assertEqual(len(out['edges']), 3)
        for original, edge in zip(before['edges'], out['edges']):
            self.assertEqual(edge['edge_type'], 'tee_to_tee')
            for key in ('source_handles', 'path', 'attribute_paths', 'path_length', 'equipment_names', 'physical_length_mm'):
                self.assertEqual(edge[key], original[key])
        self.assertFalse(out['metadata']['hil_ready'])
        self.assertFalse(out['sourcePendingNativeJunctionResolution']['human_accepted'])

    def test_source_Z_and_colour_disagreement_block(self):
        self.branch.dxf.start = (0, 0, 2)
        with self.assertRaises(ValueError): self.read()
        self.branch.dxf.start = (0, 0, 0)
        self.branch.dxf.color = 4
        with self.assertRaisesRegex(ValueError, 'colours disagree'): self.read()

    def test_opposite_service_cannot_be_inferred_connected(self):
        self.branch.dxf.layer = self.other_layer
        with self.assertRaises(ValueError): self.read()

    def test_fourth_native_arm_blocks(self):
        self.doc.modelspace().add_line((0, 0), (0, -10), dxfattribs=dict(layer=self.layer))
        with self.assertRaises(ValueError): self.read()

    def test_missing_marker_and_nonendpoint_contact_block(self):
        self.circle.dxf.center = (0, 8)
        with self.assertRaisesRegex(ValueError, 'outside its marker'): self.read()
        self.circle.dxf.center = (0, 1.3)
        self.branch.dxf.start = (0, -5)
        with self.assertRaisesRegex(ValueError, 'exact native endpoint'): self.read()

    def test_unreviewed_arbitrary_interface_or_changed_owner_block(self):
        self.node['subtype'] = 'equipment_port'
        with self.assertRaises(ValueError): self.read()
        self.node['subtype'] = 'pending_source_junction'
        self.node['source_main_continuation']['branch_edge_id'] = 'OTHER'
        with self.assertRaisesRegex(ValueError, 'edge ownership'): self.read()

    def test_boundary_and_nearby_unsupported_geometry_block(self):
        self.graph['boundary_anchors'] = [dict(source_marker_handles=[self.circle.dxf.handle])]
        with self.assertRaisesRegex(ValueError, 'boundary'): self.read()
        self.graph.pop('boundary_anchors')
        self.doc.modelspace().add_lwpolyline([(-1, -1), (1, 1)], dxfattribs=dict(layer=self.layer))
        with self.assertRaisesRegex(ValueError, 'Unsupported nearby'): self.read()


if __name__ == '__main__':
    unittest.main()
