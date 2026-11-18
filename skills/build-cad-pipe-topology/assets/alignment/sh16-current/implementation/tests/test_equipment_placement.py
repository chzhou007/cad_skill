from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import analyze_graph as graph
import connect_equipment as placement_utils
import place_equipment_nodes as placement


class EquipmentPlacementTest(unittest.TestCase):
    def test_equipment_node_is_relocated_to_main_marker(self) -> None:
        node = graph.EquipmentNode(
            "CRAH-test", 2, 7, 100.0, 200.0, "block:7"
        )
        marker = placement_utils.OmissionMarker(
            device_label=node.label,
            main_x=10.0,
            main_y=20.0,
            equipment_side_x=90.0,
            equipment_side_y=190.0,
            main_vertices=((0.0, 20.0), (20.0, 20.0)),
        )

        relocated = placement_utils.relocate_equipment_nodes(
            [node], {node.label: marker}
        )[0]

        self.assertEqual((relocated.x, relocated.y), (10.0, 20.0))
        self.assertEqual(relocated.source, "main-omission-marker:block:7")

    def test_updated_drawing_has_62_relocated_equipment_nodes(self) -> None:
        doc = graph.ezdxf.readfile(placement.DEFAULT_DXF)
        original = graph.detect_equipment_nodes(doc)
        owned, exploded_direct = placement_utils.collect_owned_equipment(
            doc, original
        )
        markers = placement_utils.collect_omission_markers(doc, owned)
        placed = placement_utils.relocate_equipment_nodes(original, markers)

        self.assertEqual(len(original), 92)
        self.assertEqual(len(placed), 92)
        self.assertEqual(len(markers), 62)
        self.assertEqual(len(exploded_direct), 6)
        self.assertEqual(
            sum(node.source.startswith("main-omission-marker:") for node in placed),
            62,
        )
        self.assertEqual(len({node.label for node in placed}), 92)

    def test_node_payload_contains_no_edges(self) -> None:
        equipment = [
            graph.EquipmentNode("CRAH-test", 1, 1, 1.0, 2.0, "block:7")
        ]
        tees = [graph.TeeNode("supply", 3.0, 4.0)]
        layout = graph.DrawingLayout(
            0.0,
            0.0,
            10.0,
            20.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            100.0,
            0.0,
            100.0,
        )

        payload = placement.node_payload(equipment, tees, {}, layout)

        self.assertEqual(payload["edges"], [])
        self.assertEqual(
            payload["metadata"]["edge_processing"],
            "intentionally_not_started",
        )


if __name__ == "__main__":
    unittest.main()
