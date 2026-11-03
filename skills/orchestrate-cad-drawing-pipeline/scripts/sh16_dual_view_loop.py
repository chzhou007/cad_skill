"""SH16 plan comparison, one isometric cross-check loop, and an unreviewed package.

This module does not edit a graph, does not create an equipment port from
proximity, and does not copy an isometric connection onto the plan. Unknown
diameter and length stay null. A count match is not acceptance.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import dual_view_scope as scope

ROOT = Path(__file__).resolve().parents[3]
PIPE_SCRIPTS = ROOT / "skills" / "build-cad-pipe-topology" / "scripts"
if str(PIPE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PIPE_SCRIPTS))
import dual_view_attributes as attributes
RELEASE_DXF = ROOT / "releases" / "SH16-all-tasks-v3.7.1-crossover-completion" / "sources" / "DXF"
PLAN_GRAPH = ROOT / "work" / "sh16-ceiling-rebuild-s1b" / "output" / "tasks"
ISO_GRAPH = ROOT / "fixtures" / "isometric-sh16-11" / "graph_with_edges.json"
LF20_SHEETS = {
    "LF20-02": Path(r"E:\codex\CAD\output\02双盘管冷源-冷塔回水对照-v2\inputs\02双盘管冷源系统原理图.dxf"),
    "LF20-03": Path(r"E:\codex\CAD\output\A楼-03空调水管平面-阶段验收-v1\inputs\03空调水管平面图.dxf"),
    "LF20-06": Path(r"E:\codex\CAD\output\A楼-06末端空调-管径楼层-v3\inputs\06末端空调系统图.dxf"),
}
LF20_RUNNERS = (
    "skills/build-cad-pipe-topology/scripts/confirmed_circle_junctions.py",
    "skills/build-cad-pipe-topology/scripts/source_readability.py",
    "skills/build-cad-pipe-topology/scripts/run_confirmed_circle_pipeline.py",
)
BRANCH_LAYER = "空调立管、水平支管"
LABEL_BOUNDS = {
    "B3B1": ((2313672.1390086897, 74946.9949084227), (2314672.1390086897, 76438.94011474634)),
    "B3B2": ((2314872.1390086897, 74946.9949084227), (2315872.1390086897, 76438.94011474634)),
}
OMISSION_CIRCLES = {
    "B99D": ((2386344.779274319, 147322.0824846236), "return"),
    "B99E": ((2386344.779274317, 147122.0824846236), "supply"),
    "B9A7": ((2386344.779274319, 150202.0824846232), "return"),
    "B9A8": ((2386344.779274317, 150002.0824846232), "supply"),
}


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pipe_rules():
    if str(PIPE_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(PIPE_SCRIPTS))
    from cad_ceiling_native_rules import match_out_of_plane_symbol
    from ceiling_equipment_labels import bind_ceiling_equipment_labels
    return match_out_of_plane_symbol, bind_ceiling_equipment_labels


def _entity(doc, handle, expected_type):
    entity = doc.entitydb.get(handle)
    if entity is None or entity.dxftype() != expected_type:
        raise scope.ScopeError(f"{handle} is not a {expected_type} in this DXF")
    return entity


def _on_segment(point, start, end, tol=0.05):
    if abs(point[0] - start[0]) <= tol and abs(point[0] - end[0]) <= tol:
        low, high = sorted((start[1], end[1]))
        return low - tol <= point[1] <= high + tol
    if abs(point[1] - start[1]) <= tol and abs(point[1] - end[1]) <= tol:
        low, high = sorted((start[0], end[0]))
        return low - tol <= point[0] <= high + tol
    return False


def compare_real_tees(doc):
    """Sheet 09 T025 and T065 are endpoint-incidence tees beside unmatched circles."""
    cases = (
        ("T025", "return", "B669", "12E98", "12E9B"),
        ("T065", "supply", "B66A", "12E99", "12E9A"),
    )
    branch_lines = []
    for entity in doc.modelspace():
        if entity.dxftype() == "LINE" and entity.dxf.layer == BRANCH_LAYER:
            branch_lines.append((
                (entity.dxf.start.x, entity.dxf.start.y),
                (entity.dxf.end.x, entity.dxf.end.y),
            ))
    rows = []
    for node_id, system, main_handle, branch_handle, circle_handle in cases:
        main = _entity(doc, main_handle, "LINE")
        branch = _entity(doc, branch_handle, "LINE")
        circle = _entity(doc, circle_handle, "CIRCLE")
        main_a = (main.dxf.start.x, main.dxf.start.y)
        main_b = (main.dxf.end.x, main.dxf.end.y)
        branch_a = (branch.dxf.start.x, branch.dxf.start.y)
        center = (circle.dxf.center.x, circle.dxf.center.y)
        if main.dxf.layer != f"空调冷冻水{'回水' if system == 'return' else '供水'}":
            raise scope.ScopeError(f"{main_handle} is not the {system} main")
        if not _on_segment(branch_a, main_a, main_b):
            raise scope.ScopeError(f"{branch_handle} does not meet {main_handle}")
        offset = math.dist(center, branch_a)
        if abs(circle.dxf.radius - 80) > 0.05 or not 1.0 <= offset <= 2.0:
            raise scope.ScopeError(f"{circle_handle} is not the unmatched radius-80 circle beside the tee")
        nearby = [
            line for line in branch_lines
            if min(math.dist(center, line[0]), math.dist(center, line[1])) <= 230
        ]
        if nearby:
            raise scope.ScopeError(f"{circle_handle} has branch-layer geometry inside the omission radius")
        rows.append({
            "node_id": node_id,
            "sheet": "SH16-09",
            "system": system,
            "main_handle": main_handle,
            "branch_handle": branch_handle,
            "circle_handle": circle_handle,
            "junction": [branch_a[0], branch_a[1]],
            "circle_offset": offset,
            "branch_line_length": math.dist(branch_a, (branch.dxf.end.x, branch.dxf.end.y)),
            "status": "matches_source",
            "drawing_acceptance": False,
        })
    return rows


def compare_omission_symbols(doc):
    match_out_of_plane_symbol, _bind = _pipe_rules()
    glyphs = []
    centers = {handle: spec[0] for handle, spec in OMISSION_CIRCLES.items()}
    for entity in doc.modelspace():
        if entity.dxftype() != "LINE" or entity.dxf.layer != BRANCH_LAYER:
            continue
        start = (entity.dxf.start.x, entity.dxf.start.y)
        end = (entity.dxf.end.x, entity.dxf.end.y)
        if any(min(math.dist(start, center), math.dist(end, center)) <= 400 for center in centers.values()):
            glyphs.append({"handle": entity.dxf.handle, "a": start, "b": end})
    rows = []
    for handle, (center, system) in OMISSION_CIRCLES.items():
        circle = _entity(doc, handle, "CIRCLE")
        if abs(circle.dxf.radius - 80) > 0.05 or math.dist((circle.dxf.center.x, circle.dxf.center.y), center) > 0.05:
            raise scope.ScopeError(f"{handle} is not the expected radius-80 circle")
        matched = match_out_of_plane_symbol(
            {"handle": handle, "center": center, "radius": 80, "system": system},
            glyphs,
        )
        if matched is None:
            raise scope.ScopeError(f"{handle} did not match its own arms and forward bars")
        arms, bars = matched
        rows.append({
            "sheet": "SH16-08",
            "circle_handle": handle,
            "system": system,
            "arm_handles": [item["handle"] for item in arms],
            "bar_handles": [item["handle"] for item in bars],
            "status": "matches_source",
            "drawing_acceptance": False,
        })
    return rows


def compare_shared_label(doc):
    _match, bind_ceiling_equipment_labels = _pipe_rules()
    labels = []
    for handle in ("B3BF", "B3C0"):
        text = _entity(doc, handle, "TEXT")
        labels.append({"text": text.dxf.text, "x": text.dxf.insert.x, "y": text.dxf.insert.y, "handle": handle})
    blocks = [
        {"source_handle": handle, "bounds": bounds}
        for handle, bounds in LABEL_BOUNDS.items()
    ]
    for handle in LABEL_BOUNDS:
        _entity(doc, handle, "INSERT")
    rows = bind_ceiling_equipment_labels(blocks, labels)
    if any(row["association_status"] != "label_unresolved" or row["connection_status"] != "ports_unresolved" for row in rows):
        raise scope.ScopeError("shared CRAH-4#-2-2 label was treated as a unique port")
    if any("port_id" in row for row in rows):
        raise scope.ScopeError("shared label created a port")
    return {
        "sheet": "SH16-09",
        "insert_handles": ["B3B1", "B3B2"],
        "text_handles": {"B3BF": "CRAH-4#-2-1", "B3C0": "CRAH-4#-2-2"},
        "rows": rows,
        "status": "matches_source_identity_unresolved",
        "drawing_acceptance": False,
    }


def compare_plan_sources(dxf_dir=RELEASE_DXF):
    import ezdxf

    directory = Path(dxf_dir)
    sheet09 = next(directory.glob("09-*.dxf"))
    sheet08 = next(directory.glob("08-*.dxf"))
    return {
        "binding": "current_release_dxf",
        "count_is_not_acceptance": True,
        "tees": compare_real_tees(ezdxf.readfile(sheet09)),
        "omission_symbols": compare_omission_symbols(ezdxf.readfile(sheet08)),
        "shared_label": compare_shared_label(ezdxf.readfile(sheet09)),
        "equipment_ports": {
            "status": "ports_unresolved",
            "ports_created": 0,
            "reason": "No unresolved terminal lies on an equipment outline. The nearest distances in the s1b rebuild are 380, 300 and 300 drawing units on sheets 08, 09 and 10.",
            "drawing_acceptance": False,
        },
    }


def _region(sheet, class_name, instances, plan_status):
    return {
        "sheet": sheet,
        "class": class_name,
        "instances": instances,
        "plan_check": plan_status,
        "isometric_check": "not_run_for_this_range",
        "eligible_for_mapping": False,
    }


def classify_loop(plan_comparison, iso_graph):
    """One loop: the two checked tees. Mapping waits for an isometric pass."""
    nodes = {node["node_id"]: node for node in iso_graph["nodes"]}
    junctions = [node for node in iso_graph["nodes"] if node.get("node_type") == "physical_junction"]
    degree = {node_id: 0 for node_id in nodes}
    for edge in iso_graph["edges"]:
        degree[edge["start_node_id"]] += 1
        degree[edge["end_node_id"]] += 1
    if len(iso_graph["nodes"]) != 424 or len(iso_graph["edges"]) != 576 or len(junctions) != 302:
        raise scope.ScopeError("isometric fixture no longer matches the historical count lock")
    if any(degree[node["node_id"]] != 3 for node in junctions):
        raise scope.ScopeError("isometric junction degree is not the recorded three-way lock")
    external = nodes["VDEV001"]
    if external.get("semantic_status") != "unresolved":
        raise scope.ScopeError("VDEV001 changed resolution without an isometric source proof")
    tee_ids = [row["node_id"] for row in plan_comparison["tees"]]
    checked = [
        _region("SH16-09", "circle_adjacent_real_tee", tee_ids, "matches_source"),
        _region("SH16-08", "adjacent_omission_symbol", [row["circle_handle"] for row in plan_comparison["omission_symbols"]], "matches_source"),
    ]
    for region in checked:
        region["eligible_for_mapping"] = region["plan_check"] == "matches_source" and region["isometric_check"] == "matches_source"
    differences = [
        attributes.record_difference(
            "plan_only",
            {"sheet": "SH16-09", "nodes": tee_ids, "source": "endpoint incidence on B669/B66A"},
            {"sheet": "SH16-11", "correspondence": "none_proven", "filled_from_plan": False},
        ),
        attributes.record_difference(
            "isometric_only",
            {"sheet": "SH16-08-10", "correspondence": "none_proven", "filled_from_isometric": False},
            {"node_id": "VDEV001", "semantic_status": "unresolved", "source_marker_handle": "2BCE3"},
        ),
    ]
    horizontal = attributes.physical_length("horizontal", "plan", plan_comparison["tees"][0]["branch_line_length"], "source_line_length")
    vertical = attributes.physical_length("vertical", "plan", None, "not_present_on_plan")
    if horizontal["value"] == 0 or vertical["value"] == 0:
        raise attributes.AttributeError("unknown length must stay null")
    return {
        "isometric_inspection": {
            "fixture": "fixtures/isometric-sh16-11/graph_with_edges.json",
            "nodes": 424,
            "edges": 576,
            "tees": 302,
            "count_is_not_correctness": True,
            "proven_fix": None,
            "unresolved_external_interface": "VDEV001",
        },
        "mapping": [],
        "mapping_reason": "S4 starts only for a range that passed both the plan and isometric checks. This loop passed the plan check only.",
        "differences": differences,
        "candidate_attributes": [
            {"id": "SH16-09-12E98", "fused": False, "diameter": None, "length": horizontal, "reason": "no mapping survived S5"},
            {"id": "SH16-09-T025-vertical", "fused": False, "diameter": None, "length": vertical, "reason": "plan has no vertical length"},
        ],
        "checked_regions": checked,
        "isolated_regions": [
            "SH16-08/09/10 equipment supply and return ports",
            "SH16-09 shared labels B3B1 and B3B2",
            "unmatched radius-80 circles",
            "plan riser destinations",
            "SH16-11 VDEV001",
            "same-name equipment across sheets",
        ],
    }


def lf20_backtest_record():
    sheets = []
    for sheet, path in LF20_SHEETS.items():
        sheets.append({
            "sheet": sheet,
            "path": str(path),
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else None,
        })
    missing_runners = [path for path in LF20_RUNNERS if not (ROOT / path).is_file()]
    return {
        "backtest_ran": False,
        "gain": None,
        "regression": None,
        "project_difference": "LF20 02 is a cooling-source schematic, 03 is an A-building water plan, and 06 is a terminal system diagram. The SH16 ceiling extractor was not applied to them.",
        "sheets": sheets,
        "missing_skill_inputs": missing_runners,
        "reason": "The native DXFs exist. The family runners named by the registry are not in this checkout, so no gain or regression number was produced.",
    }


def build_record(dxf_dir=RELEASE_DXF, iso_graph_path=ISO_GRAPH):
    plan = compare_plan_sources(dxf_dir)
    iso_graph = json.loads(Path(iso_graph_path).read_text(encoding="utf-8"))
    loop = classify_loop(plan, iso_graph)
    plan_hash = None
    plan_graph = PLAN_GRAPH / "SH16-09-ffeda2df" / "topology" / "graph_with_edges.json"
    if plan_graph.is_file():
        plan_hash = _sha256(plan_graph)
    return {
        "program": "sh16-dual-view",
        "drawing_correct": False,
        "human_confirmation": "none",
        "hil_ready": False,
        "plan_comparison": plan,
        "loop": loop,
        "hashes": {
            "plan_sheet09_graph_sha256": plan_hash,
            "isometric_fixture_sha256": _sha256(iso_graph_path),
        },
        "attribute_fusion": {
            "state": "not_started",
            "reason": "no connection survived S5",
            "human_confirmation": "none",
            "values": [],
        },
        "lf20": lf20_backtest_record(),
        "progress": {
            "historical_features": "M1 copied seven registered sources from the CAD v7 snapshot and left every other absent name to_fix.",
            "plan_correctness": "Two sheet 09 tees and four sheet 08 omission symbols match the release DXF. Equipment ports stay unresolved and no drawing is accepted.",
            "isometric_cross_check": "The SH16-11 count lock was rechecked and no isometric connection was repaired or filled from the plan. Mapping did not start.",
            "shared_delivery": "The HIL package is unreviewed. LF20 drawings were found, and the missing family runners blocked a backtest.",
        },
    }
