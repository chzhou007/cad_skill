import json
import unittest

from isometric_presentation import (
    apply_presentation,
    build_presentation,
    display_diameter,
    fuse_walked_paths,
    invalidate_touched,
    parse_diameter_text,
    vertical_lengths_from_elevations,
    walk_system_path,
)


def iso_graph():
    return {
        "nodes": [
            {"node_id": "CRAH-4#-2-7", "node_type": "equipment", "label": "CRAH-4#-2-7", "floor": 2},
            {"node_id": "CRAH-4#-1-1", "node_type": "equipment", "label": "CRAH-4#-1-1", "floor": 1},
            {"node_id": "CRAH-4#-2-2", "node_type": "equipment", "label": "CRAH-4#-2-2", "floor": 2},
            {"node_id": "T1", "node_type": "physical_junction", "floor": 2},
        ],
        "edges": [
            {
                "edge_id": "E1",
                "start_node_id": "CRAH-4#-2-7",
                "end_node_id": "T1",
                "system": "supply",
                "floor_start": 2,
                "floor_end": 2,
                "path_length": 1200.0,
            },
            {
                "edge_id": "E2",
                "start_node_id": "T1",
                "end_node_id": "CRAH-4#-2-2",
                "system": "return",
                "floor_start": 2,
                "floor_end": 3,
                "path_length": 800.0,
            },
        ],
    }


def plan_nodes():
    return [{
        "task_id": "SH16-09",
        "node_id": "CRAH-4#-2-7",
        "label": "CRAH-4#-2-7",
        "floor": 2,
        "source_handle": "B391",
        "connection_status": "ports_unresolved",
    }]


def bindings():
    return [{
        "task_id": "SH16-09",
        "floor": 2,
        "source_handle": "B3B1",
        "label_candidates": ["CRAH-4#-2-2"],
        "association_status": "label_unresolved",
    }]


def diameters():
    return [{
        "status": "assigned",
        "edge_id": "E1",
        "nominal_mm": 450.0,
        "rule": "single_text_axial_projection_unique_parallel_source_edge_within_two_text_heights",
        "text": {"text": "DN450(2.900)", "source_id": "SH16-11", "handle": "AB"},
    }]


class PresentationContractTest(unittest.TestCase):
    def test_parenthetical_elevation_is_not_a_diameter_or_a_length(self):
        parsed = parse_diameter_text("DN450(2.900)")
        self.assertEqual(parsed["nominal_mm"], 450.0)
        self.assertEqual(parsed["elevation_annotation"], 2.9)

    def test_unique_equipment_maps_while_duplicate_and_absent_labels_stay_open(self):
        graph = iso_graph()
        record = build_presentation(
            graph["edges"], graph["nodes"], plan_nodes(), bindings(), diameters(), "plan-hash", "iso-hash"
        )
        by_label = {row["label"]: row for row in record["equipment"]}
        self.assertEqual(by_label["CRAH-4#-2-7"]["status"], "mapped")
        self.assertEqual(by_label["CRAH-4#-2-7"]["plan_source_handle"], "B391")
        self.assertEqual(by_label["CRAH-4#-2-7"]["ports"], "unmapped")
        self.assertEqual(by_label["CRAH-4#-2-2"]["reason"], "label_not_unique")
        self.assertEqual(by_label["CRAH-4#-1-1"]["reason"], "plan_equipment_absent")
        walls = {row["label"]: row["wall"] for row in record["stops"]}
        self.assertEqual(walls["CRAH-4#-2-7"], "equipment_ports_unproven")
        self.assertEqual(walls["CRAH-4#-1-1"], "plan_equipment_absent")
        self.assertFalse(record["drawing_correct"])

    def test_direct_isometric_diameter_stays_uncrosschecked_and_length_stays_null(self):
        graph = iso_graph()
        record = build_presentation(
            graph["edges"], graph["nodes"], plan_nodes(), bindings(), diameters(), "plan-hash", "iso-hash"
        )
        first = record["edges"][0]
        self.assertEqual(first["connection"]["start_node_id"], "CRAH-4#-2-7")
        self.assertEqual(first["diameter"]["status"], "direct")
        self.assertEqual(first["diameter"]["value"], 450.0)
        self.assertEqual(first["diameter"]["crosscheck"], "not_run")
        self.assertEqual(first["diameter"]["observations"][0]["elevation_annotation"], 2.9)
        self.assertIsNone(first["length"]["value"])
        self.assertEqual(first["length"]["completeness"], "incomplete")
        self.assertEqual(first["path"]["status"], "unmapped")
        vertical = record["edges"][1]
        self.assertEqual(vertical["orientation"], "vertical")
        self.assertEqual(vertical["diameter"]["status"], "unknown")
        self.assertIsNone(vertical["diameter"]["value"])
        self.assertIn("尚未与平面图互证", display_diameter(first["diameter"]))
        self.assertEqual(display_diameter(vertical["diameter"]), "未知")

    def test_conflicting_direct_values_keep_both_handles_and_no_winner(self):
        rows = diameters() + [{
            "status": "assigned",
            "edge_id": "E1",
            "nominal_mm": 200.0,
            "text": {"text": "DN200", "source_id": "SH16-11", "handle": "CD"},
        }]
        record = build_presentation(
            iso_graph()["edges"], iso_graph()["nodes"], plan_nodes(), [], rows, "plan-hash", "iso-hash"
        )
        diameter = record["edges"][0]["diameter"]
        self.assertEqual(diameter["status"], "conflict")
        self.assertIsNone(diameter["value"])
        self.assertEqual(diameter["handles"], ["AB", "CD"])

    def test_a_local_change_stales_only_the_edge_that_uses_it(self):
        record = build_presentation(
            iso_graph()["edges"], iso_graph()["nodes"], plan_nodes(), bindings(), diameters(), "plan-hash", "iso-hash"
        )
        updated = invalidate_touched(record, changed_plan_node_ids=["CRAH-4#-2-7"])
        states = {edge["edge_id"]: edge["state"] for edge in updated["edges"]}
        self.assertEqual(states["E1"], "stale")
        self.assertEqual(states["E2"], "current")
        self.assertEqual(record["edges"][0]["state"], "current")
        equipment = {row["label"]: row["state"] for row in updated["equipment"]}
        self.assertEqual(equipment["CRAH-4#-2-7"], "stale")
        self.assertEqual(equipment["CRAH-4#-1-1"], "current")

    def test_viewer_overlay_does_not_rewrite_path_length_or_fill_zero(self):
        graph = iso_graph()
        record = build_presentation(
            graph["edges"], graph["nodes"], plan_nodes(), bindings(), diameters(), "plan-hash", "iso-hash"
        )
        shown = apply_presentation(graph, record)
        edge = shown["edges"][0]
        self.assertEqual(edge["path_length"], 1200.0)
        self.assertEqual(edge["start_node_id"], "CRAH-4#-2-7")
        self.assertEqual(edge["presentation"]["physical_length_display"], "未知")
        self.assertIsNone(edge["presentation"]["physical_length_value"])
        self.assertEqual(edge["physical_length_value"], "")
        self.assertIn("B391", edge["plan_equipment_id"])
        self.assertEqual(shown["nodes"][0]["plan_correspondence"]["plan_source_handle"], "B391")
        self.assertFalse(shown["metadata"]["drawing_correct"])
        self.assertEqual(graph["edges"][0].get("pipe_diameter"), None)
        self.assertEqual(json.loads(json.dumps(edge["pipe_diameter"]))["nominal_mm"], 450.0)


class PathFusionTest(unittest.TestCase):
    def test_a_header_fork_stops_without_choosing_a_direction(self):
        nodes = [
            {"node_id": "EQ", "node_type": "equipment"},
            {"node_id": "T", "node_type": "physical_junction"},
            {"node_id": "A", "node_type": "physical_junction"},
            {"node_id": "B", "node_type": "physical_junction"},
        ]
        edges = [
            {"edge_id": "stub", "start_node_id": "EQ", "end_node_id": "T", "system": "supply", "floor_start": 2, "floor_end": 2},
            {"edge_id": "left", "start_node_id": "T", "end_node_id": "A", "system": "supply", "floor_start": 2, "floor_end": 2},
            {"edge_id": "right", "start_node_id": "T", "end_node_id": "B", "system": "supply", "floor_start": 2, "floor_end": 2},
        ]
        walked = walk_system_path("EQ", "supply", edges, nodes)
        self.assertEqual(walked["edges"], ["stub"])
        self.assertEqual(walked["stop"]["kind"], "branch_fork")
        self.assertEqual(sorted(walked["stop"]["continuations"]), ["left", "right"])

    def test_plan_without_an_incident_edge_does_not_receive_the_isometric_diameter(self):
        graph = iso_graph()
        record = build_presentation(
            graph["edges"], graph["nodes"], plan_nodes(), bindings(), diameters(), "plan-hash", "iso-hash"
        )
        fused = fuse_walked_paths(record, graph["edges"], graph["nodes"], [], plan_nodes(), {})
        supply = next(row for row in fused["stops"] if row["label"] == "CRAH-4#-2-7" and row["system"] == "supply")
        self.assertEqual(supply["path"], "unmapped")
        self.assertEqual(supply["plan_stop"], "no_incident_edge")
        self.assertEqual(fused["edges"][0]["diameter"]["source_view"], "isometric")
        self.assertEqual(fused["path_mapped"], 0)

    def test_a_connected_plan_path_supplies_the_horizontal_diameter(self):
        graph = iso_graph()
        record = build_presentation(
            graph["edges"], graph["nodes"], plan_nodes(), bindings(), diameters(), "plan-hash", "iso-hash"
        )
        plan = [
            {"node_id": "CRAH-4#-2-7", "node_type": "equipment", "floor": 2},
            {"node_id": "TP", "node_type": "tee", "floor": 2},
        ]
        plan_edges = [{
            "edge_id": "P1",
            "start_node_id": "CRAH-4#-2-7",
            "end_node_id": "TP",
            "system": "supply",
            "floor_start": 2,
            "floor_end": 2,
        }]
        fused = fuse_walked_paths(
            record, graph["edges"], graph["nodes"], plan_edges, plan, {"P1": [{"nominal_mm": 200.0, "handle": "PLAN"}]}
        )
        supply = next(row for row in fused["stops"] if row["label"] == "CRAH-4#-2-7" and row["system"] == "supply")
        self.assertEqual(supply["path"], "mapped")
        edge = next(item for item in fused["edges"] if item["edge_id"] == "E1")
        self.assertEqual(edge["diameter"]["status"], "conflict")
        self.assertIsNone(edge["diameter"]["value"])
        self.assertIn("PLAN", edge["diameter"]["handles"])
        self.assertIn("AB", edge["diameter"]["handles"])

    def test_riser_length_uses_one_elevation_at_each_end(self):
        edges = [
            {"edge_id": "riser", "start_node_id": "A", "end_node_id": "B", "system": "return", "floor_start": 1, "floor_end": 2, "path_length": 27000.0},
            {"edge_id": "low", "start_node_id": "A", "end_node_id": "C", "system": "return", "floor_start": 1, "floor_end": 1},
            {"edge_id": "high", "start_node_id": "B", "end_node_id": "D", "system": "return", "floor_start": 2, "floor_end": 2},
        ]
        rows = [
            {"edge_id": "riser", "diameter": {"observations": []}},
            {"edge_id": "low", "diameter": {"observations": [{"elevation_annotation": 2.9}]}},
            {"edge_id": "high", "diameter": {"observations": [{"elevation_annotation": 3.2}]}},
        ]
        measured = vertical_lengths_from_elevations(edges, rows)
        self.assertEqual(measured["riser"]["value"], 0.3)
        self.assertEqual(measured["riser"]["method"], "elevation_difference")
        self.assertNotEqual(measured["riser"]["value"], 27000.0)
        rows[2]["diameter"]["observations"].append({"elevation_annotation": 4.0})
        self.assertIsNone(vertical_lengths_from_elevations(edges, rows).get("riser"))


if __name__ == "__main__":
    unittest.main()
