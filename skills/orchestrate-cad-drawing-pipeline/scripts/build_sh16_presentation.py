"""Build the SH16-11 derived presentation and a viewer graph.

Annotations stay on the drawing that contains them. Unique equipment labels
map across plan and isometric. Ports and paths stay unmapped until a port is
proven. Unknown diameter and physical length stay null.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[3]
BUILD_SCRIPTS = ROOT / "skills" / "build-cad-pipe-topology" / "scripts"
ORCH_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_SCRIPTS))
sys.path.insert(0, str(ORCH_SCRIPTS))

from isometric_presentation import (  # noqa: E402
    apply_presentation,
    attach_diameter_annotations,
    attach_length_annotations,
    build_presentation,
)
from pipe_annotation_attributes import source_texts  # noqa: E402
from sh16_dual_view_loop import lf20_backtest_record  # noqa: E402

ISO_GRAPH = ROOT / "fixtures" / "isometric-sh16-11" / "graph_with_edges.json"
ISO_DXF = ROOT / "output" / "SH16-topology-build-v33" / "sources" / "DXF" / "11-空调水系统图.dxf"
PLAN_TASKS = ROOT / "work" / "sh16-ceiling-rebuild-s1b" / "output" / "tasks"
PLAN_DXF_ROOT = ROOT / "releases" / "SH16-all-tasks-v3.7.1-crossover-completion" / "sources" / "DXF"
PLAN_DRAWINGS = {
    "SH16-08-208d1e5a": ("08-一层顶部水管平面图.dxf", 1),
    "SH16-09-ffeda2df": ("09-二层顶部水管平面图.dxf", 2),
    "SH16-10-072841a6": ("10-三层顶部水管平面图.dxf", 3),
}
OUT = ROOT / "work" / "sh16-11-presentation"
ASSETS = ROOT / "skills" / "orchestrate-cad-drawing-pipeline" / "assets"
VIEWER_INPUTS = ROOT / "work" / "sh16-11-viewer" / "inputs"


def _sha256(path):
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def _load_plan():
    nodes = []
    bindings = []
    graphs = []
    annotations = []
    for task_id, (dxf_name, floor) in PLAN_DRAWINGS.items():
        graph_path = PLAN_TASKS / task_id / "topology" / "graph_with_edges.json"
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graphs.append(graph_path)
        for node in graph["nodes"]:
            if node.get("node_type") != "equipment":
                continue
            nodes.append({
                "task_id": task_id,
                "node_id": node["node_id"],
                "label": node.get("label") or node["node_id"],
                "floor": node.get("floor", floor),
                "source_handle": node.get("source_handle"),
                "connection_status": node.get("connection_status"),
            })
        binding_path = PLAN_TASKS / task_id / "topology" / "equipment-source-bindings.json"
        for row in json.loads(binding_path.read_text(encoding="utf-8")):
            if row.get("association_status") == "unique_bounded_source_label":
                continue
            bindings.append({
                "task_id": task_id,
                "floor": floor,
                "source_handle": row.get("source_handle"),
                "label_candidates": row.get("label_candidates") or [],
                "association_status": row.get("association_status"),
            })
        dxf_path = PLAN_DXF_ROOT / dxf_name
        record = {"task_id": task_id, "source_dxf": dxf_name, "floor": floor}
        if not dxf_path.is_file():
            record["wall"] = "missing_source_file"
            annotations.append(record)
            continue
        doc = ezdxf.readfile(dxf_path)
        texts = source_texts(doc, task_id, _sha256(dxf_path))
        assigned, pending = attach_diameter_annotations(doc, texts, graph["edges"])
        lengths, length_pending = attach_length_annotations(texts, graph["edges"], "plan")
        record.update({
            "assigned_diameter_count": len(assigned),
            "pending_diameter_count": len(pending),
            "assigned_length_count": len(lengths),
            "pending_length_count": len(length_pending),
            "edges": _plan_edge_annotations(graph["edges"], assigned, lengths),
        })
        annotations.append(record)
    plan_hash = hashlib.sha256()
    for path in graphs:
        plan_hash.update(path.read_bytes())
    return nodes, bindings, annotations, plan_hash.hexdigest()


def _plan_edge_annotations(edges, assigned, lengths):
    by_edge = {}
    for row in assigned:
        if row.get("status") != "assigned":
            continue
        item = by_edge.setdefault(row["edge_id"], {"edge_id": row["edge_id"], "diameters": [], "lengths": []})
        text = row.get("text") or {}
        item["diameters"].append({
            "nominal_mm": row.get("nominal_mm"),
            "handle": text.get("handle"),
            "text": text.get("text"),
            "source_view": "plan",
        })
    for row in lengths:
        item = by_edge.setdefault(row["edge_id"], {"edge_id": row["edge_id"], "diameters": [], "lengths": []})
        item["lengths"].append({
            "value": row["value"],
            "handle": row.get("handle"),
            "text": row.get("text"),
            "source_view": "plan",
            "method": row.get("method"),
        })
    return list(by_edge.values())


def _annotation_stops(edges, pending):
    stops = []
    for row in pending:
        if row.get("status") == "pending" and row.get("candidate_edge_ids"):
            stops.append({
                "edge_id": None,
                "wall": "annotation_ambiguous",
                "handles": [row.get("text", {}).get("handle")] if isinstance(row.get("text"), dict) else [],
                "candidate_edge_ids": row.get("candidate_edge_ids"),
            })
    unknown = [edge["edge_id"] for edge in edges if edge["diameter"]["status"] == "unknown"]
    return stops, unknown


def build():
    iso = json.loads(ISO_GRAPH.read_text(encoding="utf-8"))
    if not ISO_DXF.is_file():
        raise SystemExit(f"missing isometric source: {ISO_DXF}")
    doc = ezdxf.readfile(ISO_DXF)
    texts = source_texts(doc, "SH16-11", _sha256(ISO_DXF))
    assigned, pending = attach_diameter_annotations(doc, texts, iso["edges"])
    lengths, length_pending = attach_length_annotations(texts, iso["edges"], "isometric")
    plan_nodes, bindings, plan_annotations, plan_hash = _load_plan()
    iso_hash = _sha256(ISO_GRAPH)
    presentation = build_presentation(
        iso["edges"], iso["nodes"], plan_nodes, bindings, assigned, plan_hash, iso_hash, lengths
    )
    annotation_stops, unknown_edges = _annotation_stops(presentation["edges"], pending)
    presentation["annotation_stops"] = annotation_stops
    presentation["unknown_diameter_edge_ids"] = unknown_edges
    presentation["isometric_annotations"] = {
        "assigned_diameter_count": len(assigned),
        "pending_diameter_count": len(pending),
        "assigned_length_count": len(lengths),
        "pending_length_count": len(length_pending),
        "elevation_note": "A parenthetical number on a DN label is an elevation annotation, not a pipe length.",
    }
    presentation["plan_annotations"] = plan_annotations
    presentation["lf20"] = lf20_backtest_record()
    shown = apply_presentation(iso, presentation)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "presentation.json").write_text(json.dumps(presentation, ensure_ascii=False), encoding="utf-8")
    (OUT / "graph_with_edges.json").write_text(json.dumps(shown, ensure_ascii=False), encoding="utf-8")
    summary = _summary(presentation, plan_nodes, bindings)
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "sh16-11-presentation-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ASSETS / "sh16-local-topology-ledger.json").write_text(
        json.dumps(_local_ledger(bindings), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _viewer_config()
    print(json.dumps({
        "equipment_mapped": summary["equipment_mapped"],
        "equipment_unmapped": summary["equipment_unmapped"],
        "direct_diameter_edges": summary["direct_diameter_edges"],
        "unknown_diameter_edges": summary["unknown_diameter_edges"],
        "conflict_diameter_edges": summary["conflict_diameter_edges"],
        "physical_length_known": summary["physical_length_known"],
        "stops": summary["stop_counts"],
        "drawing_correct": False,
    }, ensure_ascii=False, indent=2))
    return presentation


def _summary(presentation, plan_nodes, bindings):
    edges = presentation["edges"]
    equipment = presentation["equipment"]
    walls = {}
    for stop in presentation["stops"]:
        walls[stop["wall"]] = walls.get(stop["wall"], 0) + 1
    return {
        "drawing_correct": False,
        "human_confirmation": "none",
        "hil_ready": False,
        "plan_sha256": presentation["plan_sha256"],
        "isometric_sha256": presentation["isometric_sha256"],
        "equipment_mapped": sum(row["status"] == "mapped" for row in equipment),
        "equipment_unmapped": sum(row["status"] != "mapped" for row in equipment),
        "plan_equipment_nodes": len(plan_nodes),
        "unresolved_plan_bindings": len(bindings),
        "direct_diameter_edges": sum(edge["diameter"]["status"] == "direct" for edge in edges),
        "conflict_diameter_edges": sum(edge["diameter"]["status"] == "conflict" for edge in edges),
        "unknown_diameter_edges": sum(edge["diameter"]["status"] == "unknown" for edge in edges),
        "physical_length_known": sum(edge["length"]["value"] is not None for edge in edges),
        "path_mapped": sum(edge["path"]["status"] == "mapped" for edge in edges),
        "stop_counts": walls,
        "stops": presentation["stops"],
        "isometric_annotations": presentation["isometric_annotations"],
        "plan_annotations": [
            {key: value for key, value in row.items() if key != "edges"}
            | {"annotated_edges": len(row.get("edges") or [])}
            for row in presentation["plan_annotations"]
        ],
        "annotation_ambiguous": len(presentation["annotation_stops"]),
        "lf20": {
            "backtest_ran": presentation["lf20"]["backtest_ran"],
            "gain": presentation["lf20"]["gain"],
            "regression": presentation["lf20"]["regression"],
            "missing_skill_inputs": presentation["lf20"]["missing_skill_inputs"],
        },
        "viewer_graph": "work/sh16-11-presentation/graph_with_edges.json",
    }


def _local_ledger(bindings):
    return {
        "drawing_correct": False,
        "rule": "A repair invalidates only presentation rows whose depends_on cites the changed connection.",
        "fixed_pending_regression": [{
            "id": "sheet09-real-tee-beside-unmatched-circle",
            "evidence": "Three-ray endpoint incidence remains a tee when the nearby circle is not an omission symbol or a calibrated riser.",
            "dependent_presentation_edges": [],
        }],
        "isolated": [
            {
                "id": "equipment-ports-08-10",
                "wall": "equipment_ports_unproven",
                "note": "No port is created from proximity. Mapped equipment keeps its identity and leaves ports unmapped.",
            },
            {
                "id": "shared-equipment-labels",
                "wall": "label_not_unique",
                "bindings": [
                    {"task_id": row["task_id"], "source_handle": row["source_handle"], "label_candidates": row["label_candidates"]}
                    for row in bindings
                ],
            },
            {
                "id": "double-line-ports-06-07",
                "wall": "ports_unproven",
                "note": "Outdoor double-line ports stay isolated. They do not block another unique SH16-11 loop.",
            },
            {
                "id": "shaft-multiple-pipes",
                "wall": "shaft_name_is_not_a_connection",
                "note": "A shaft name or a distance does not prove a cross-view connection.",
            },
        ],
    }


def _viewer_config():
    source = VIEWER_INPUTS / "visualization-config.json"
    if not source.is_file():
        return
    config = json.loads(source.read_text(encoding="utf-8"))
    config["preferred_port"] = 8772
    config.setdefault("display", {})["edge_attribute_language"] = "zh-CN"
    config["project"]["description"] = "Derived SH16-11 presentation. Unknown diameter and physical length stay empty. HIL is not ready."
    (OUT / "visualization-config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    build()
