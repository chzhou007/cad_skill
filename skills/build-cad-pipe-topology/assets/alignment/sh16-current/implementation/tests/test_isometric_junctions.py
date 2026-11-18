from pathlib import Path
import sys
import unittest
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import analyze_graph as graph
import build_edges as builder
import connect_equipment as network


class IsometricJunctionTest(unittest.TestCase):
    def test_three_connected_rays_need_no_opposite_pair(self):
        segments = [graph.Segment('return', (0, 0), p)
                    for p in [(10, 0), (10, 10), (0, -10)]]
        self.assertEqual(len(graph.detect_tee_nodes(segments)), 1)

    def test_two_ray_corner_and_mixed_system_are_not_tees(self):
        segments = [graph.Segment('return', (0, 0), (10, 0)),
                    graph.Segment('return', (0, 0), (10, 10)),
                    graph.Segment('supply', (0, 0), (0, -10))]
        self.assertEqual(graph.detect_tee_nodes(segments), [])

    def test_healing_preserves_crossing_but_recognizes_remote_three_way(self):
        segments = [graph.Segment('supply', (0, 0), (10, 0)),
                    graph.Segment('supply', (0, 0), (-10, -10)),
                    graph.Segment('supply', (0, 0), (0, -2)),
                    graph.Segment('supply', (0, -2), (1, -1)),
                    graph.Segment('supply', (3, 1), (5, 3))]
        cleaned, bridges = graph.bridge_pipe_crossover_gaps(segments)
        self.assertEqual(len(bridges), 1)
        tees = graph.detect_tee_nodes(cleaned)
        self.assertEqual([(t.x, t.y) for t in tees], [(0, 0)])
        self.assertAlmostEqual(bridges[0].crossing_x, 2)

    def test_sh16_four_missing_junctions_and_boundary_interface(self):
        case = ROOT.parents[0]
        doc = graph.ezdxf.readfile(case / 'inputs/dxf/sh16-native-isometric_updated.fixed.dxf')
        layout = graph.infer_drawing_layout(graph.equipment_labels(doc))
        segments, _ = graph.trim_short_dangling_overshoots(graph.collect_pipe_segments(doc))
        segments, _ = graph.remove_turn_display_valve_stubs(segments, graph.collect_turn_display_valve_regions(doc))
        segments, _ = graph.remove_auto_air_vent_display_legs(segments, graph.collect_auto_air_vent_ports(doc), layout)
        segments, bridges = graph.bridge_pipe_crossover_gaps(segments)
        tees = graph.detect_tee_nodes(segments, layout)
        self.assertEqual(len(tees), 305)
        expected = [(2474516.38334222, 185664.9576115417),
                    (2475240.647410932, 185964.9576115417),
                    (2478533.843944361, 189258.1541449713),
                    (2478409.57987565, 189558.1541449713)]
        self.assertEqual([(t.x, t.y) for t in tees[-4:]], expected)
        for bridge in bridges:
            self.assertTrue(all(math.dist((t.x,t.y), (bridge.crossing_x,bridge.crossing_y)) > graph.POINT_TOLERANCE for t in tees))
        virtual, audit = builder.collect_virtual_equipment_nodes(doc, segments, layout)
        self.assertEqual(len(virtual), 30)
        recovered = next(v for v in virtual if v.source_marker_handle == 'C19')
        self.assertEqual(recovered.node_id, 'VDEV030')
        self.assertEqual({p.system for p in recovered.ports}, {'supply','return'})
        self.assertTrue(all(a.node_id is None for a in audit if a.source_marker_handle in {'C11','C12'}))
        edges = builder.build_tee_edges(segments, tees, layout)
        ports, _ = builder.build_virtual_equipment_edges(segments, tees, virtual, layout)
        for tid in ['T302','T303','T304','T305']:
            incident = [e for e in edges + ports if tid in (e.start_node_id,e.end_node_id)]
            self.assertEqual(len(incident), 3, tid)


if __name__ == '__main__':
    unittest.main()
