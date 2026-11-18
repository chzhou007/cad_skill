from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import analyze_graph as graph


class DrawingLayoutTest(unittest.TestCase):
    def test_layout_and_detail_exclusion_follow_drawing_translation(self) -> None:
        anchor_x, anchor_y = graph.CANONICAL_ANCHOR
        labels = [
            ("CRAH-4#-1-1", 1, 1, anchor_x, anchor_y),
            ("CRAH-4#-2-1", 2, 1, anchor_x, anchor_y + 20_000.0),
            ("CRAH-4#-3-1", 3, 1, anchor_x, anchor_y + 40_000.0),
        ]
        translated = [
            (name, floor, sequence, x + 100.0, y + 200.0)
            for name, floor, sequence, x, y in labels
        ]

        first = graph.infer_drawing_layout(labels)
        second = graph.infer_drawing_layout(translated)

        self.assertAlmostEqual(first.floor_boundary_1_2, 144_000.0)
        self.assertAlmostEqual(first.floor_boundary_2_3, 168_000.0)
        self.assertAlmostEqual(
            second.floor_boundary_1_2 - first.floor_boundary_1_2, 200.0
        )
        self.assertAlmostEqual(
            second.left_detail_x_max - first.left_detail_x_max, 100.0
        )
        point = (first.left_detail_x_max - 1.0, first.left_detail_y_min + 1.0)
        self.assertTrue(graph.is_excluded_detail_point(*point, first))
        self.assertTrue(
            graph.is_excluded_detail_point(point[0] + 100.0, point[1] + 200.0, second)
        )


class ShortOvershootPreprocessingTest(unittest.TestCase):
    def test_short_dangling_overshoot_becomes_tee(self) -> None:
        segments = [
            graph.Segment("supply", (-10.0, 0.0), (10.0, 0.0)),
            graph.Segment("supply", (0.0, -10.0), (0.0, 0.5)),
        ]

        self.assertEqual(graph.detect_tee_nodes(segments), [])
        cleaned, trims = graph.trim_short_dangling_overshoots(segments)

        self.assertEqual(len(trims), 1)
        self.assertAlmostEqual(trims[0].length, 0.5)
        self.assertEqual(cleaned[1].end, (0.0, 0.0))
        self.assertEqual(len(graph.detect_tee_nodes(cleaned)), 1)

    def test_long_stub_is_not_trimmed(self) -> None:
        segments = [
            graph.Segment("supply", (-50.0, 0.0), (50.0, 0.0)),
            graph.Segment("supply", (0.0, -50.0), (0.0, 20.0)),
        ]

        cleaned, trims = graph.trim_short_dangling_overshoots(segments)

        self.assertEqual(trims, [])
        self.assertEqual(cleaned, segments)

    def test_connected_endpoint_is_not_trimmed(self) -> None:
        segments = [
            graph.Segment("supply", (-10.0, 0.0), (10.0, 0.0)),
            graph.Segment("supply", (0.0, -10.0), (0.0, 0.5)),
            graph.Segment("supply", (0.0, 0.5), (5.0, 0.5)),
        ]

        cleaned, trims = graph.trim_short_dangling_overshoots(segments)

        self.assertEqual(trims, [])
        self.assertEqual(cleaned, segments)


class PipeCrossoverGapPreprocessingTest(unittest.TestCase):
    def test_crossover_gap_is_healed_without_creating_tee(self) -> None:
        segments = [
            graph.Segment("supply", (-10.0, 0.0), (10.0, 0.0)),
            graph.Segment("supply", (-5.0, -5.0), (-1.0, -1.0)),
            graph.Segment("supply", (1.0, 1.0), (5.0, 5.0)),
        ]

        cleaned, bridges = graph.bridge_pipe_crossover_gaps(segments)

        self.assertEqual(len(bridges), 1)
        self.assertEqual(len(cleaned), 4)
        self.assertEqual(cleaned[-1].start, (-1.0, -1.0))
        self.assertEqual(cleaned[-1].end, (1.0, 1.0))
        self.assertEqual((bridges[0].crossing_x, bridges[0].crossing_y), (0.0, 0.0))
        self.assertEqual(graph.detect_tee_nodes(cleaned), [])

    def test_collinear_gap_without_crossing_pipe_is_not_healed(self) -> None:
        segments = [
            graph.Segment("supply", (-5.0, 0.0), (-1.0, 0.0)),
            graph.Segment("supply", (1.0, 0.0), (5.0, 0.0)),
        ]

        cleaned, bridges = graph.bridge_pipe_crossover_gaps(segments)

        self.assertEqual(bridges, [])
        self.assertEqual(cleaned, segments)

    def test_full_crossing_lines_are_not_joined_or_promoted_to_tee(self) -> None:
        segments = [
            graph.Segment("supply", (-10.0, 0.0), (10.0, 0.0)),
            graph.Segment("return", (0.0, -10.0), (0.0, 10.0)),
        ]

        cleaned, bridges = graph.bridge_pipe_crossover_gaps(segments)

        self.assertEqual(bridges, [])
        self.assertEqual(cleaned, segments)
        self.assertEqual(graph.detect_tee_nodes(cleaned), [])


class ValveDisplayStubPreprocessingTest(unittest.TestCase):
    def test_nested_valve_insert_is_collected_in_world_coordinates(self) -> None:
        doc = graph.ezdxf.new()
        valve = doc.blocks.new("H-PICPNT-87")
        valve.add_line((-1.0, -1.0), (1.0, 1.0))
        equipment = doc.blocks.new("test-equipment")
        equipment.add_blockref("H-PICPNT-87", (5.0, 0.0))
        doc.modelspace().add_blockref("test-equipment", (100.0, 200.0))

        regions = graph.collect_turn_display_valve_regions(doc)

        self.assertEqual(len(regions), 1)
        self.assertAlmostEqual(regions[0].min_x, 104.0)
        self.assertAlmostEqual(regions[0].min_y, 199.0)
        self.assertAlmostEqual(regions[0].max_x, 106.0)
        self.assertAlmostEqual(regions[0].max_y, 201.0)

    def test_valve_display_leg_is_removed_from_elbow(self) -> None:
        segments = [
            graph.Segment("supply", (0.0, 2.0), (0.0, 10.0)),
            graph.Segment("supply", (0.0, 2.0), (-5.0, -3.0)),
            graph.Segment("supply", (0.0, 1.0), (0.0, 2.0)),
        ]
        valve = graph.ValveRegion("test-valve", -1.0, -1.0, 1.0, 1.0)

        self.assertEqual(len(graph.detect_tee_nodes(segments)), 1)
        cleaned, removals = graph.remove_turn_display_valve_stubs(
            segments, [valve]
        )

        self.assertEqual(len(removals), 1)
        self.assertEqual(removals[0].junction, (0.0, 2.0))
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(graph.detect_tee_nodes(cleaned), [])

    def test_valve_branch_from_straight_main_is_preserved(self) -> None:
        segments = [
            graph.Segment("supply", (-10.0, 2.0), (0.0, 2.0)),
            graph.Segment("supply", (0.0, 2.0), (10.0, 2.0)),
            graph.Segment("supply", (0.0, 1.0), (0.0, 2.0)),
        ]
        valve = graph.ValveRegion("test-valve", -1.0, -1.0, 1.0, 1.0)

        cleaned, removals = graph.remove_turn_display_valve_stubs(
            segments, [valve]
        )

        self.assertEqual(removals, [])
        self.assertEqual(cleaned, segments)


class AutoAirVentPreprocessingTest(unittest.TestCase):
    def test_semantic_air_vent_port_is_collected(self) -> None:
        doc = graph.ezdxf.new()
        doc.modelspace().add_attdef(
            "WHAT", (10.0, 20.0), text="自动排气阀"
        )

        self.assertEqual(
            graph.collect_auto_air_vent_ports(doc), [(10.0, 20.0)]
        )

    def test_standalone_air_vent_leg_is_removed(self) -> None:
        segments = [
            graph.Segment("return", (0.0, 2.0), (0.0, 10.0)),
            graph.Segment("return", (0.0, 2.0), (-5.0, -3.0)),
            graph.Segment("return", (0.0, 1.0), (0.0, 2.0)),
        ]

        cleaned, removals = graph.remove_auto_air_vent_display_legs(
            segments, [(0.0, 1.0)]
        )

        self.assertEqual(len(removals), 1)
        self.assertEqual(removals[0].action, "remove")
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(graph.detect_tee_nodes(cleaned), [])

    def test_continuous_line_is_trimmed_back_to_air_vent_elbow(self) -> None:
        segments = [
            graph.Segment("return", (0.0, -10.0), (0.0, 3.0)),
            graph.Segment("return", (0.0, 2.0), (-5.0, -3.0)),
        ]

        cleaned, removals = graph.remove_auto_air_vent_display_legs(
            segments, [(0.0, 3.0)]
        )

        self.assertEqual(len(removals), 1)
        self.assertEqual(removals[0].action, "trim")
        self.assertEqual(cleaned[0].end, (0.0, 2.0))
        self.assertEqual(graph.detect_tee_nodes(cleaned), [])


if __name__ == "__main__":
    unittest.main()
