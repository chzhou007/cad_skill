"""Derived isometric presentation.

This record cites plan and isometric topology. It does not add edges, ports,
or rewrite either local graph. Unknown diameter and physical length stay null.
A local connection change marks only the presentation rows that use it.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict

import pipe_geometry as pg
from dual_view_attributes import physical_length
from pipe_annotation_attributes import direct_diameters, recognize_f_leaders

DN_TEXT = re.compile(r"DN\s*(\d+(?:\.\d+)?)(?:\(([-+]?\d+(?:\.\d+)?)\))?$", re.I)
LENGTH_TEXT = re.compile(r"^(\d+(?:\.\d+)?)\s*(?:m|米)$", re.I)


class PresentationError(ValueError):
    pass


def parse_diameter_text(text):
    match = DN_TEXT.fullmatch(" ".join(str(text).split()))
    if not match:
        return None
    nominal = float(match.group(1))
    if nominal == 0:
        raise PresentationError("unknown diameter must not be stored as zero")
    elevation = float(match.group(2)) if match.group(2) else None
    return {"nominal_mm": nominal, "elevation_annotation": elevation, "text": match.group(0)}


def parse_length_text(text):
    match = LENGTH_TEXT.fullmatch(" ".join(str(text).split()))
    if not match:
        return None
    value = float(match.group(1))
    if value == 0:
        raise PresentationError("unknown length must not be stored as zero")
    return value


def orientation_of(edge):
    if edge.get("floor_start") != edge.get("floor_end"):
        return "vertical"
    return "horizontal"


def _observation(row):
    text = row["text"]
    parsed = parse_diameter_text(text["text"]) or {}
    return {
        "text": text["text"],
        "source_id": text.get("source_id"),
        "handle": text.get("handle"),
        "nominal_mm": row.get("nominal_mm"),
        "elevation_annotation": parsed.get("elevation_annotation"),
        "rule": row.get("rule"),
    }


def diameter_from_assignments(rows, source_view):
    observations = [_observation(row) for row in rows]
    values = []
    for row in rows:
        value = row.get("nominal_mm")
        if value == 0:
            raise PresentationError("unknown diameter must not be stored as zero")
        if value is not None and value not in values:
            values.append(value)
    handles = [item["handle"] for item in observations if item.get("handle")]
    if len(values) > 1:
        return {
            "status": "conflict",
            "value": None,
            "source_view": source_view,
            "crosscheck": "not_run",
            "handles": handles,
            "observations": observations,
            "chain": [],
        }
    if len(values) == 1:
        return {
            "status": "direct",
            "value": values[0],
            "source_view": source_view,
            "crosscheck": "not_run",
            "handles": handles,
            "observations": observations,
            "chain": [],
        }
    return {
        "status": "unknown",
        "value": None,
        "source_view": None,
        "crosscheck": "not_run",
        "handles": [],
        "observations": [],
        "chain": [],
    }


def index_plan_equipment(nodes, unresolved_bindings):
    grouped = defaultdict(list)
    for node in nodes:
        grouped[(node["label"], node["floor"])].append({
            "kind": "node",
            "task_id": node["task_id"],
            "node_id": node["node_id"],
            "source_handle": node.get("source_handle"),
            "connection_status": node.get("connection_status"),
            "label": node["label"],
            "floor": node["floor"],
        })
    for binding in unresolved_bindings:
        floor = binding["floor"]
        task_id = binding["task_id"]
        for label in binding.get("label_candidates") or []:
            grouped[(label, floor)].append({
                "kind": "unresolved_binding",
                "task_id": task_id,
                "source_handle": binding.get("source_handle"),
                "label": label,
                "floor": floor,
            })
    return grouped


def map_equipment(isometric_nodes, plan_index):
    mapped = []
    for node in isometric_nodes:
        if node.get("node_type") != "equipment":
            continue
        label = node.get("label") or node["node_id"]
        floor = node.get("floor")
        hits = plan_index.get((label, floor), [])
        nodes = [hit for hit in hits if hit["kind"] == "node"]
        record = {
            "kind": "equipment",
            "label": label,
            "floor": floor,
            "isometric_node_id": node["node_id"],
            "ports": "unmapped",
            "state": "current",
        }
        if len(hits) == 1 and len(nodes) == 1:
            plan = nodes[0]
            record.update({
                "status": "mapped",
                "plan_task": plan["task_id"],
                "plan_node_id": plan["node_id"],
                "plan_source_handle": plan["source_handle"],
                "port_reason": "ports_unresolved" if plan.get("connection_status") == "ports_unresolved" else "ports_unproven",
            })
        elif hits:
            record.update({
                "status": "unmapped",
                "reason": "label_not_unique",
                "candidate_handles": [hit.get("source_handle") for hit in hits],
            })
        else:
            record.update({"status": "unmapped", "reason": "plan_equipment_absent"})
        mapped.append(record)
    return mapped


def _equipment_on_edge(edge, equipment_by_node):
    rows = []
    for node_id in (edge["start_node_id"], edge["end_node_id"]):
        record = equipment_by_node.get(node_id)
        if record:
            rows.append(dict(record))
    return rows


def _length_record(edge, length_annotation=None):
    orientation = orientation_of(edge)
    expected = "plan" if orientation == "horizontal" else "isometric"
    if length_annotation is None:
        return physical_length(orientation, expected, None, None)
    return physical_length(orientation, length_annotation["source_view"], length_annotation["value"], length_annotation["method"])


def build_edge_presentation(edges, diameter_rows, equipment_rows, length_rows=()):
    by_edge = defaultdict(list)
    for row in diameter_rows:
        if row.get("status") != "assigned" or not row.get("edge_id"):
            continue
        by_edge[row["edge_id"]].append(row)
    equipment_by_node = {row["isometric_node_id"]: row for row in equipment_rows}
    lengths = {row["edge_id"]: row for row in length_rows}
    presented = []
    for edge in edges:
        orientation = orientation_of(edge)
        equipment = _equipment_on_edge(edge, equipment_by_node)
        plan_node_ids = [row["plan_node_id"] for row in equipment if row.get("status") == "mapped"]
        presented.append({
            "edge_id": edge["edge_id"],
            "connection": {
                "start_node_id": edge["start_node_id"],
                "end_node_id": edge["end_node_id"],
                "system": edge.get("system"),
                "status": "existing_endpoints",
            },
            "orientation": orientation,
            "equipment": equipment,
            "path": {
                "status": "unmapped",
                "reason": _path_reason(equipment),
            },
            "diameter": diameter_from_assignments(by_edge.get(edge["edge_id"], []), "isometric"),
            "length": _length_record(edge, lengths.get(edge["edge_id"])),
            "differences": [],
            "depends_on": {
                "isometric_edge_id": edge["edge_id"],
                "isometric_node_ids": [edge["start_node_id"], edge["end_node_id"]],
                "plan_edge_ids": [],
                "plan_node_ids": plan_node_ids,
            },
            "state": "current",
        })
    return presented


def _path_reason(equipment):
    if not equipment:
        return "no_equipment_endpoint"
    reasons = []
    for row in equipment:
        if row.get("status") != "mapped":
            reasons.append(row.get("reason") or "unmapped")
        else:
            reasons.append(row.get("port_reason") or "ports_unproven")
    return reasons[0]


def loop_stops(equipment_rows):
    stops = []
    for row in equipment_rows:
        if row.get("status") != "mapped":
            stops.append({
                "label": row["label"],
                "floor": row["floor"],
                "isometric_node_id": row["isometric_node_id"],
                "systems": ["supply", "return"],
                "wall": row.get("reason") or "unmapped",
                "path": "unmapped",
            })
            continue
        stops.append({
            "label": row["label"],
            "floor": row["floor"],
            "isometric_node_id": row["isometric_node_id"],
            "plan_task": row.get("plan_task"),
            "plan_source_handle": row.get("plan_source_handle"),
            "systems": ["supply", "return"],
            "wall": "equipment_ports_unproven",
            "equipment": "mapped",
            "ports": "unmapped",
            "path": "unmapped",
        })
    return stops


def build_presentation(isometric_edges, isometric_nodes, plan_nodes, unresolved_bindings, diameter_rows, plan_hash, isometric_hash, length_rows=()):
    if not plan_hash or not isometric_hash:
        raise PresentationError("presentation must cite both topology hashes")
    equipment_rows = map_equipment(isometric_nodes, index_plan_equipment(plan_nodes, unresolved_bindings))
    edges = build_edge_presentation(isometric_edges, diameter_rows, equipment_rows, length_rows)
    return {
        "layer": "cross_view_fusion",
        "drawing_correct": False,
        "human_confirmation": "none",
        "hil_ready": False,
        "plan_sha256": plan_hash,
        "isometric_sha256": isometric_hash,
        "equipment": equipment_rows,
        "edges": edges,
        "stops": loop_stops(equipment_rows),
        "state": "current",
    }


def invalidate_touched(presentation, changed_edge_ids=(), changed_node_ids=(), changed_plan_edge_ids=(), changed_plan_node_ids=()):
    updated = json.loads(json.dumps(presentation))
    changed_edges = set(changed_edge_ids)
    changed_nodes = set(changed_node_ids)
    changed_plan_edges = set(changed_plan_edge_ids)
    changed_plan_nodes = set(changed_plan_node_ids)
    for edge in updated.get("edges", []):
        depends = edge.get("depends_on") or {}
        hit = (
            edge["edge_id"] in changed_edges
            or bool(set(depends.get("isometric_node_ids") or []) & changed_nodes)
            or bool(set(depends.get("plan_edge_ids") or []) & changed_plan_edges)
            or bool(set(depends.get("plan_node_ids") or []) & changed_plan_nodes)
        )
        if not hit:
            continue
        edge["state"] = "stale"
        edge["reason"] = "local topology changed; recompute before use"
        for key in ("diameter", "length", "path"):
            if key in edge:
                edge[key]["state"] = "stale"
    for row in updated.get("equipment", []):
        if row.get("isometric_node_id") in changed_nodes or row.get("plan_node_id") in changed_plan_nodes:
            row["state"] = "stale"
            row["reason_invalidation"] = "local topology changed; recompute before use"
    return updated


def display_diameter(diameter):
    status = diameter.get("status")
    value = diameter.get("value")
    if status == "conflict":
        return "冲突"
    if status in {"direct", "inherited"} and value is not None:
        nominal = int(value) if float(value).is_integer() else value
        if status == "direct" and diameter.get("source_view") == "plan":
            note = "与轴测一致" if diameter.get("crosscheck") == "matches_isometric" else "来自已对应平面路径"
            return f"DN{nominal}（{note}）"
        if status == "direct" and diameter.get("source_view") == "isometric" and diameter.get("crosscheck") == "not_run":
            return f"DN{nominal}（轴测直接值，尚未与平面图互证）"
        if status == "inherited":
            return f"DN{nominal}（继承）"
        return f"DN{nominal}"
    return "未知"


def display_equipment(equipment):
    if not equipment:
        return "未知"
    parts = []
    for row in equipment:
        if row.get("status") == "mapped":
            parts.append(f"{row['label']} · {row['plan_task']}:{row['plan_source_handle']} · 端口未对应")
        else:
            parts.append("未知")
    return "; ".join(parts)


def _segments(edges):
    segments = []
    for edge in edges:
        handles = list(edge.get("source_handles") or [])
        for path in edge.get("attribute_paths") or []:
            for start, end in zip(path, path[1:]):
                segments.append({
                    "a": (start[0], start[1]),
                    "b": (end[0], end[1]),
                    "handle": handles[0] if handles else edge["edge_id"],
                    "source_handles": handles or [edge["edge_id"]],
                    "system": edge.get("system"),
                    "source_system": edge.get("system"),
                })
    return segments


def attach_diameter_annotations(doc, texts, edges):
    """Bind DN and F-shape text to edges of the drawing that contains them."""

    normalized = []
    for text in texts:
        compact = " ".join(str(text["text"]).split())
        if parse_diameter_text(compact):
            normalized.append(dict(text, text=compact))
    layers = sorted({text["layer"] for text in normalized})
    if not layers:
        return [], []
    assigned, pending = direct_diameters(normalized, edges, set(), layers)
    for row in recognize_f_leaders(doc, normalized, _segments(edges), edges, layers):
        if row.get("status") != "assigned":
            pending.append(row)
            continue
        for binding in row.get("bindings") or []:
            edge_ids = binding.get("edge_ids") or []
            if len(edge_ids) != 1:
                continue
            assigned.append({
                "status": "assigned",
                "edge_id": edge_ids[0],
                "nominal_mm": binding["nominal_mm"],
                "rule": binding.get("rule"),
                "text": binding["text"],
            })
    return assigned, pending


def attach_length_annotations(texts, edges, source_view):
    """Bind an explicit length unit to the one parallel edge that can own it."""

    assigned = []
    pending = []
    by_id = {edge["edge_id"]: edge for edge in edges}
    for text in texts:
        compact = " ".join(str(text["text"]).split())
        value = parse_length_text(compact)
        if value is None:
            continue
        angle = math.radians(float(text.get("rotation") or 0))
        axis = (math.cos(angle), math.sin(angle))
        point = text["position"]
        height = float(text.get("height") or 0)
        candidates = []
        for edge in edges:
            if orientation_of(edge) == "horizontal" and source_view != "plan":
                continue
            if orientation_of(edge) == "vertical" and source_view != "isometric":
                continue
            for path in edge.get("attribute_paths") or []:
                for start, end in zip(path, path[1:]):
                    vector = pg.sub((end[0], end[1]), (start[0], start[1]))
                    length = pg.dist((start[0], start[1]), (end[0], end[1]))
                    if not length or abs(pg.cross(axis, vector)) / length > math.sin(math.radians(2)):
                        continue
                    along = pg.dot(pg.sub(point, (start[0], start[1])), vector) / (length * length)
                    if not 0 < along < 1:
                        continue
                    foot = (start[0] + along * vector[0], start[1] + along * vector[1])
                    distance = pg.dist(point, foot)
                    if distance <= 2 * height:
                        candidates.append((distance, edge["edge_id"]))
        best = {}
        for distance, edge_id in candidates:
            if edge_id not in best or distance < best[edge_id]:
                best[edge_id] = distance
        values = sorted((distance, edge_id) for edge_id, distance in best.items())
        if values and (len(values) == 1 or values[1][0] - values[0][0] > 0.5 * height):
            edge = by_id[values[0][1]]
            measured = physical_length(orientation_of(edge), source_view, value, "dimension_text")
            if measured["value"] is None:
                pending.append({"text": compact, "handle": text.get("handle"), "reason": "wrong_source_view"})
                continue
            assigned.append({
                "edge_id": edge["edge_id"],
                "value": measured["value"],
                "source_view": source_view,
                "method": "dimension_text",
                "handle": text.get("handle"),
                "text": compact,
            })
        else:
            pending.append({"text": compact, "handle": text.get("handle"), "reason": "ambiguous_or_unaligned"})
    return assigned, pending


JUNCTION_TYPES = {"physical_junction", "tee"}


def _adjacency(edges):
    adjacent = defaultdict(list)
    for edge in edges:
        adjacent[edge["start_node_id"]].append(edge)
        adjacent[edge["end_node_id"]].append(edge)
    return adjacent


def _other_node(edge, node_id):
    if edge["start_node_id"] == node_id:
        return edge["end_node_id"]
    return edge["start_node_id"]


def walk_system_path(start_id, system, edges, nodes):
    """Follow one existing same-system path. A fork is a stop, not a guess."""

    nodes_by_id = {node["node_id"]: node for node in nodes}
    adjacent = _adjacency(edges)
    incident = [edge for edge in adjacent.get(start_id, []) if edge.get("system") == system]
    if not incident:
        return {"edges": [], "stop": {"kind": "no_incident_edge", "node_id": start_id, "system": system}}
    if len(incident) != 1:
        return {
            "edges": [],
            "stop": {
                "kind": "ambiguous_incident_edges",
                "node_id": start_id,
                "system": system,
                "edge_ids": [edge["edge_id"] for edge in incident],
            },
        }
    walked = []
    seen = set()
    previous = start_id
    current = incident[0]
    while current is not None:
        walked.append(current["edge_id"])
        seen.add(current["edge_id"])
        arrived = _other_node(current, previous)
        node = nodes_by_id.get(arrived)
        if node is None:
            return {"edges": walked, "stop": {"kind": "missing_node", "node_id": arrived, "system": system}}
        if current.get("floor_start") != current.get("floor_end"):
            return {"edges": walked, "stop": {"kind": "riser", "node_id": arrived, "system": system, "edge_id": current["edge_id"]}}
        if node.get("node_type") not in JUNCTION_TYPES:
            return {"edges": walked, "stop": {"kind": node.get("node_type") or "endpoint", "node_id": arrived, "system": system}}
        continuations = [
            edge for edge in adjacent.get(arrived, [])
            if edge["edge_id"] not in seen and edge.get("system") == system
        ]
        headers = []
        for edge in continuations:
            other = nodes_by_id.get(_other_node(edge, arrived))
            if other and other.get("node_type") in JUNCTION_TYPES and edge.get("floor_start") == edge.get("floor_end"):
                headers.append(edge)
        chosen = headers if headers else continuations
        if len(chosen) != 1:
            return {
                "edges": walked,
                "stop": {
                    "kind": "branch_fork" if len(chosen) > 1 else "dead_end",
                    "node_id": arrived,
                    "system": system,
                    "continuations": [edge["edge_id"] for edge in chosen],
                },
            }
        previous = arrived
        current = chosen[0]
    return {"edges": walked, "stop": {"kind": "dead_end", "node_id": previous, "system": system}}


def _elevations(edge_row):
    values = []
    for observation in (edge_row.get("diameter") or {}).get("observations") or []:
        elevation = observation.get("elevation_annotation")
        if elevation is not None and elevation not in values:
            values.append(elevation)
    return values


def vertical_lengths_from_elevations(iso_edges, presentation_edges):
    """Riser length is the difference of one elevation at each end.

    Equal elevations and mixed elevations at one end stay empty. The drawing-unit
    path length is not used.
    """

    rows = {edge["edge_id"]: edge for edge in presentation_edges}
    adjacent = _adjacency(iso_edges)
    measured = {}
    for edge in iso_edges:
        if edge.get("floor_start") == edge.get("floor_end"):
            continue
        row = rows.get(edge["edge_id"])
        if row is None:
            continue
        end_values = []
        usable = True
        for node_id in (edge["start_node_id"], edge["end_node_id"]):
            found = []
            for other in adjacent.get(node_id, []):
                if other.get("system") != edge.get("system"):
                    continue
                for elevation in _elevations(rows.get(other["edge_id"], {})):
                    if elevation not in found:
                        found.append(elevation)
            if len(found) != 1:
                usable = False
                break
            end_values.append(found[0])
        if not usable or len(end_values) != 2 or end_values[0] == end_values[1]:
            continue
        value = round(abs(end_values[0] - end_values[1]), 3)
        if value == 0:
            continue
        measured[edge["edge_id"]] = physical_length("vertical", "isometric", value, "elevation_difference")
        measured[edge["edge_id"]]["elevations"] = end_values
    return measured


def fuse_walked_paths(presentation, iso_edges, iso_nodes, plan_edges, plan_nodes, plan_diameter_by_edge):
    """Attach a walked path to each mapped equipment. Fuse only when both views have edges."""

    updated = json.loads(json.dumps(presentation))
    edge_rows = {edge["edge_id"]: edge for edge in updated["edges"]}
    stops = []
    for row in updated["equipment"]:
        systems = {}
        for system in ("supply", "return"):
            isometric_walk = walk_system_path(row["isometric_node_id"], system, iso_edges, iso_nodes)
            plan_walk = {"edges": [], "stop": {"kind": "equipment_unmapped", "system": system}}
            if row.get("status") == "mapped":
                plan_walk = walk_system_path(row["plan_node_id"], system, plan_edges, plan_nodes)
            fused = bool(isometric_walk["edges"] and plan_walk["edges"])
            systems[system] = {
                "isometric_edges": isometric_walk["edges"],
                "plan_edges": plan_walk["edges"],
                "isometric_stop": isometric_walk["stop"],
                "plan_stop": plan_walk["stop"],
                "fused": fused,
            }
            if fused:
                _fuse_horizontal(edge_rows, isometric_walk["edges"], plan_walk["edges"], plan_diameter_by_edge)
            wall = row.get("reason") if row.get("status") != "mapped" else plan_walk["stop"]["kind"]
            stops.append({
                "label": row["label"],
                "floor": row["floor"],
                "isometric_node_id": row["isometric_node_id"],
                "plan_task": row.get("plan_task"),
                "plan_source_handle": row.get("plan_source_handle"),
                "system": system,
                "wall": wall,
                "equipment": row.get("status"),
                "ports": row.get("ports"),
                "path": "mapped" if fused else "unmapped",
                "isometric_stop": isometric_walk["stop"]["kind"],
                "plan_stop": plan_walk["stop"]["kind"],
                "isometric_edges": isometric_walk["edges"],
                "plan_edges": plan_walk["edges"],
            })
        row["paths"] = systems
    for edge in updated["edges"]:
        owners = []
        for row in updated["equipment"]:
            for system, path in row.get("paths", {}).items():
                if edge["edge_id"] in path["isometric_edges"]:
                    owners.append({
                        "label": row["label"],
                        "system": system,
                        "fused": path["fused"],
                        "plan_stop": path["plan_stop"]["kind"],
                        "isometric_stop": path["isometric_stop"]["kind"],
                    })
        if not owners:
            continue
        fused_owners = [owner for owner in owners if owner["fused"]]
        edge["path"] = {
            "status": "mapped" if fused_owners else "unmapped",
            "reason": "both_views_have_edges" if fused_owners else owners[0]["plan_stop"],
            "isometric_stop": owners[0]["isometric_stop"],
            "owners": owners,
        }
        if fused_owners:
            edge["depends_on"]["plan_edge_ids"] = sorted({
                edge_id
                for row in updated["equipment"]
                for path in row.get("paths", {}).values()
                for edge_id in path["plan_edges"]
                if edge["edge_id"] in path["isometric_edges"] and path["fused"]
            })
    for edge_id, measured in vertical_lengths_from_elevations(iso_edges, updated["edges"]).items():
        edge_rows[edge_id]["length"] = measured
    updated["stops"] = stops
    updated["path_mapped"] = sum(edge["path"]["status"] == "mapped" for edge in updated["edges"])
    return updated


def _fuse_horizontal(edge_rows, isometric_ids, plan_ids, plan_diameter_by_edge):
    plan_values = []
    plan_handles = []
    for plan_id in plan_ids:
        for item in plan_diameter_by_edge.get(plan_id, []):
            value = item.get("nominal_mm")
            if value is None or value in plan_values:
                if value is not None and item.get("handle") not in plan_handles:
                    plan_handles.append(item.get("handle"))
                continue
            plan_values.append(value)
            plan_handles.append(item.get("handle"))
    for edge_id in isometric_ids:
        edge = edge_rows.get(edge_id)
        if edge is None or edge.get("orientation") != "horizontal":
            continue
        own = edge["diameter"]["value"] if edge["diameter"]["status"] == "direct" else None
        if len(plan_values) > 1 or (len(plan_values) == 1 and own is not None and own != plan_values[0]):
            edge["diameter"] = {
                "status": "conflict",
                "value": None,
                "source_view": "plan",
                "crosscheck": "conflict",
                "handles": [handle for handle in edge["diameter"].get("handles", []) + plan_handles if handle],
                "observations": edge["diameter"].get("observations") or [],
                "chain": plan_ids,
            }
            continue
        if len(plan_values) == 1:
            edge["diameter"] = {
                "status": "direct",
                "value": plan_values[0],
                "source_view": "plan",
                "crosscheck": "matches_isometric" if own == plan_values[0] else "plan_only",
                "handles": [handle for handle in plan_handles if handle],
                "observations": edge["diameter"].get("observations") or [],
                "chain": list(plan_ids),
            }


def _length_display(length):
    if length.get("value") is None:
        return "未知"
    if length.get("method") == "elevation_difference":
        elevations = length.get("elevations") or []
        shown = "/".join(str(item) for item in elevations)
        return f"{length['value']}（轴测标高差 {shown}）"
    return str(length["value"])


def _path_display(path):
    if path.get("status") == "mapped":
        return "两侧路径已对应"
    labels = {
        "no_incident_edge": "平面图设备没有入射边",
        "branch_fork": "轴测干管在三通处分叉",
        "ambiguous_incident_edges": "设备上有多条同系统边",
        "plan_equipment_absent": "平面图没有这台设备",
        "label_not_unique": "平面标签不唯一",
        "no_equipment_endpoint": "边端不是设备",
        "equipment_unmapped": "设备未对应",
    }
    plan_text = labels.get(path.get("reason"), path.get("reason") or "未对应")
    isometric_stop = path.get("isometric_stop")
    if not isometric_stop:
        return plan_text
    isometric_text = labels.get(isometric_stop, isometric_stop)
    if isometric_text == plan_text:
        return plan_text
    return plan_text + "；" + isometric_text


def apply_presentation(graph, presentation):
    """Copy viewer fields onto a graph. Connectivity and path_length stay unchanged."""

    updated = json.loads(json.dumps(graph))
    by_id = {edge["edge_id"]: edge for edge in presentation["edges"]}
    equipment = {row["isometric_node_id"]: row for row in presentation["equipment"]}
    for edge in updated.get("edges", []):
        row = by_id.get(edge["edge_id"])
        if not row:
            continue
        if edge.get("path_length") == 0 and row["length"]["value"] is None:
            raise PresentationError("drawing-unit path length must not be replaced with a physical zero")
        length_value = row["length"]["value"]
        edge["pipe_diameter"] = {
            "display": display_diameter(row["diameter"]),
            "status": row["diameter"]["status"],
            "nominal_mm": row["diameter"]["value"],
            "observations": [
                {"text": {"text": item["text"], "source_id": item.get("source_id"), "handle": item.get("handle")}}
                for item in row["diameter"].get("observations") or []
            ],
        }
        edge["presentation"] = {
            "orientation": row["orientation"],
            "diameter_status": row["diameter"]["status"],
            "crosscheck": row["diameter"]["crosscheck"],
            "physical_length_display": _length_display(row["length"]),
            "path_display": _path_display(row.get("path") or {}),
            "physical_length_value": length_value,
            "physical_length_source": row["length"].get("source_view"),
            "physical_length_completeness": row["length"].get("completeness"),
            "plan_equipment_display": display_equipment(row["equipment"]),
            "path_status": row["path"]["status"],
            "state": row["state"],
        }
        edge["diameter_nominal_mm"] = "" if row["diameter"]["value"] is None else row["diameter"]["value"]
        edge["diameter_text"] = edge["pipe_diameter"]["display"]
        edge["diameter_status"] = row["diameter"]["status"]
        edge["physical_length_value"] = "" if length_value is None else length_value
        edge["plan_equipment_id"] = edge["presentation"]["plan_equipment_display"]
    for node in updated.get("nodes", []):
        row = equipment.get(node["node_id"])
        if row:
            node["plan_correspondence"] = {
                "status": row["status"],
                "label": row["label"],
                "floor": row["floor"],
                "plan_task": row.get("plan_task"),
                "plan_node_id": row.get("plan_node_id"),
                "plan_source_handle": row.get("plan_source_handle"),
                "ports": row.get("ports"),
                "reason": row.get("reason") or row.get("port_reason"),
            }
    metadata = updated.setdefault("metadata", {})
    metadata["drawing_correct"] = False
    metadata["hil_ready"] = False
    metadata["presentation_layer"] = "cross_view_fusion"
    metadata["plan_sha256"] = presentation["plan_sha256"]
    metadata["isometric_sha256"] = presentation["isometric_sha256"]
    return updated
