from __future__ import annotations

import sys
import math
import unittest
from pathlib import Path

import ezdxf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import analyze_graph as graph
import build_edges as edges


def test_layout() -> graph.DrawingLayout:
    return graph.DrawingLayout(
        offset_x=0.0,
        offset_y=0.0,
        floor_boundary_1_2=20.0,
        floor_boundary_2_3=40.0,
        left_detail_x_max=-100.0,
        left_detail_y_min=100.0,
        right_detail_x_min=100.0,
        right_detail_y_max=-100.0,
        plot_x_min=-100.0,
        plot_x_max=100.0,
        plot_y_min=-100.0,
        plot_y_max=100.0,
    )


class EdgeBuilderTest(unittest.TestCase):
    def test_recovers_exploded_ball_valve_geometry(self) -> None:
        doc = ezdxf.new()
        modelspace = doc.modelspace()
        hatch = modelspace.add_hatch(
            color=2,
            dxfattribs={"layer": "0"},
        )
        hatch.paths.add_polyline_path(
            [(-20.0, -20.0), (20.0, -20.0), (20.0, 20.0), (-20.0, 20.0)],
            is_closed=True,
        )
        for start, end in ((0.0, math.pi), (math.pi, math.tau)):
            modelspace.add_ellipse(
                center=(0.0, 0.0),
                major_axis=(20.0, 0.0),
                ratio=1.0,
                start_param=start,
                end_param=end,
                dxfattribs={"color": 2, "layer": "0"},
            )
        for start, end in (
            ((-80.0, -100.0), (-80.0, 100.0)),
            ((80.0, -100.0), (80.0, 100.0)),
            ((-70.0, -70.0), (70.0, 70.0)),
        ):
            modelspace.add_line(
                start,
                end,
                dxfattribs={"color": 2, "layer": "0"},
            )

        result = edges.collect_exploded_ball_valve_instances(doc, test_layout())

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].equipment_type, "球阀")
        self.assertEqual(result[0].source_kind, "exploded_geometry")
        self.assertEqual(result[0].source_block_name, "EXPLODED:H-PICPNT-91")

    def test_does_not_promote_unconfirmed_yellow_hatch_to_ball_valve(self) -> None:
        doc = ezdxf.new()
        hatch = doc.modelspace().add_hatch(color=2)
        hatch.paths.add_polyline_path(
            [(-20.0, -20.0), (20.0, -20.0), (20.0, 20.0), (-20.0, 20.0)],
            is_closed=True,
        )

        result = edges.collect_exploded_ball_valve_instances(doc, test_layout())

        self.assertEqual(result, [])

    def test_compresses_pipe_between_adjacent_tees(self) -> None:
        segments = [
            graph.Segment("supply", (0.0, 0.0), (5.0, 0.0)),
            graph.Segment("supply", (5.0, 0.0), (10.0, 0.0)),
        ]
        tees = [
            graph.TeeNode("supply", 0.0, 0.0),
            graph.TeeNode("supply", 10.0, 0.0),
        ]

        result = edges.build_tee_edges(segments, tees, test_layout())

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].start_node_id, "T001")
        self.assertEqual(result[0].end_node_id, "T002")
        self.assertEqual(result[0].path_length, 10.0)
        self.assertEqual(result[0].attribute_paths, (result[0].path_points,))

    def test_inventory_groups_names_by_edge_and_type(self) -> None:
        edge = edges.LogicalEdge(
            edge_id="E0001",
            start_node_id="T001",
            end_node_id="T002",
            edge_type="tee_to_tee",
            system="supply",
            floor_start=1,
            floor_end=1,
            start_x=0.0,
            start_y=0.0,
            end_x=10.0,
            end_y=0.0,
            path_length=10.0,
            path_points=((0.0, 0.0), (10.0, 0.0)),
            attribute_paths=(((0.0, 0.0), (10.0, 0.0)),),
            device_label=None,
            source_insert_handle=None,
            connection_mode="continuous_original_cad_pipe",
        )
        components = [
            edges.ComponentInstance(
                device_name=f"球阀-BV{index:04d}",
                equipment_type="球阀",
                type_code="BV",
                x=float(index),
                y=0.0,
                assignment_x=float(index),
                assignment_y=0.0,
                source_kind="block_insert",
                source_block_name="H-PICPNT-91",
                source_top_handle=str(index),
                owner_equipment=None,
                system_hint="supply",
                edge_id="E0001",
                edge_distance=0.0,
                assignment_status="assigned",
            )
            for index in (1, 2)
        ]

        inventory = edges.build_inventory([edge], components)

        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory[0].equipment_type, "球阀")
        self.assertEqual(inventory[0].device_count, 2)
        self.assertIn("球阀-BV0001", inventory[0].device_names)
        self.assertIn("球阀-BV0002", inventory[0].device_names)

    def test_unowned_omission_marker_becomes_two_port_virtual_equipment(self) -> None:
        doc = ezdxf.new()
        doc.layers.add("DIM_SYMB")
        doc.modelspace().add_lwpolyline(
            [(0.0, 0.0), (4.0, 0.0), (5.0, 1.0), (6.0, -1.0), (7.0, 0.0), (10.0, 0.0)],
            dxfattribs={"layer": "DIM_SYMB"},
        )
        segments = [
            graph.Segment("supply", (-50.0, 0.0), (0.0, 0.0)),
            graph.Segment("return", (10.0, 0.0), (60.0, 0.0)),
        ]

        virtual, audit = edges.collect_virtual_equipment_nodes(
            doc, segments, test_layout()
        )
        logical, bindings = edges.build_virtual_equipment_edges(
            segments,
            [
                graph.TeeNode("supply", -50.0, 0.0),
                graph.TeeNode("return", 60.0, 0.0),
            ],
            virtual,
            test_layout(),
        )

        self.assertEqual(len(virtual), 1)
        self.assertEqual(len(virtual[0].ports), 2)
        self.assertEqual(audit[0].status, "virtual_equipment_created")
        self.assertEqual(len(logical), 2)
        supply = next(item for item in logical if item.system == "supply")
        return_ = next(item for item in logical if item.system == "return")
        self.assertEqual(supply.start_node_id, "T001")
        self.assertEqual(supply.end_node_id, "VDEV001")
        self.assertEqual(return_.start_node_id, "VDEV001")
        self.assertEqual(return_.end_node_id, "T002")
        self.assertEqual(len(bindings), 2)

    def test_metal_hose_gap_is_healed_without_creating_a_node(self) -> None:
        segments = [
            graph.Segment("supply", (0.0, 0.0), (5.0, 0.0)),
            graph.Segment("supply", (8.0, 0.0), (15.0, 0.0)),
        ]
        component = edges.ComponentInstance(
            device_name="",
            equipment_type="金属软接",
            type_code="MFJ",
            x=6.5,
            y=0.0,
            assignment_x=6.5,
            assignment_y=0.0,
            source_kind="block_insert",
            source_block_name="$VALVE$TEST",
            source_top_handle="1",
            owner_equipment=None,
            system_hint=None,
        )

        healed, bridges = edges.bridge_inline_metal_hose_gaps(
            segments,
            [
                graph.TeeNode("supply", 0.0, 0.0),
                graph.TeeNode("supply", 15.0, 0.0),
            ],
            [component],
        )

        self.assertEqual(len(bridges), 1)
        self.assertEqual(len(healed), 3)
        self.assertAlmostEqual(bridges[0].length, 3.0)


if __name__ == "__main__":
    unittest.main()
