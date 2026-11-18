from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import ezdxf
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import analyze_graph as graph


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DXF = (
    PROJECT_ROOT
    / "data"
    / "updated"
    / "interim"
    / "sh16-native-isometric_updated.fixed.dxf"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "updated"
NUMERIC_EQUIPMENT_BLOCKS = {"1", "2", "3", "4", "5", "7"}
OWNER_POINT_TOLERANCE = 0.3
VECTOR_RESIDUAL_TOLERANCE = 1.0


@dataclass(frozen=True)
class OwnedEquipment:
    node: graph.EquipmentNode
    block_name: str
    insert_handle: str
    pipe_segments: tuple[graph.Segment, ...]


@dataclass(frozen=True)
class ProvisionalMatch:
    equipment: graph.EquipmentNode
    block_name: str
    system: str
    tee: graph.TeeNode
    tee_id: str
    candidate_count: int
    candidate_selection: str


@dataclass(frozen=True)
class ConnectionEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    system: str
    device_label: str
    floor: int
    group_id: str
    block_name: str
    tee_id: str
    tee_x: float
    tee_y: float
    device_x: float
    device_y: float
    translation_dx: float
    translation_dy: float
    group_consensus_dx: float
    group_consensus_dy: float
    residual: float
    candidate_count: int
    candidate_selection: str
    order_index: int
    order_valid: bool
    status: str


@dataclass(frozen=True)
class GroupAudit:
    group_id: str
    floor: int
    block_name: str
    device_count: int
    device_labels: str
    supply_dx: float
    supply_dy: float
    return_dx: float
    return_dy: float
    maximum_residual: float
    supply_order_valid: bool
    return_order_valid: bool
    no_duplicate_targets: bool
    status: str


@dataclass(frozen=True)
class OmissionMarker:
    device_label: str
    main_x: float
    main_y: float
    equipment_side_x: float
    equipment_side_y: float
    main_vertices: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class MaterializedEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    system: str
    device_label: str
    floor: int
    group_id: str
    block_name: str
    tee_id: str
    tee_x: float
    tee_y: float
    graph_device_x: float
    graph_device_y: float
    display_device_x: float
    display_device_y: float
    connection_mode: str
    omission_marker_x: float | None
    omission_marker_y: float | None
    branch_attachment_x: float | None
    branch_attachment_y: float | None
    source_insert_handle: str
    source_block_name: str
    source_system_layer: str
    attribute_carrier: str
    attribute_extraction_status: str
    cad_path_id: str | None
    match_translation_dx: float
    match_translation_dy: float
    group_consensus_dx: float
    group_consensus_dy: float
    match_residual: float
    candidate_count: int
    candidate_selection: str
    order_index: int
    order_valid: bool
    status: str


@dataclass(frozen=True)
class BranchPath:
    cad_path_id: str
    edge_id: str
    device_label: str
    system: str
    tee_id: str
    source_insert_handle: str
    source_block_name: str
    start_x: float
    start_y: float
    attachment_x: float
    attachment_y: float
    total_length: float
    pipe_fragment_count: int
    owner_segment_indexes: tuple[int, ...]
    ordered_points: tuple[tuple[float, float], ...]
    attribute_scope: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reconnect omitted CRAH connections using repeated-row translation "
            "consensus and order-preserving branch-slot matching."
        )
    )
    parser.add_argument("--dxf", type=Path, default=DEFAULT_DXF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def cleaned_pipe_graph(doc, layout: graph.DrawingLayout) -> list[graph.Segment]:
    segments = graph.collect_pipe_segments(doc)
    segments, _ = graph.trim_short_dangling_overshoots(segments)
    segments, _ = graph.remove_turn_display_valve_stubs(
        segments, graph.collect_turn_display_valve_regions(doc)
    )
    segments, _ = graph.remove_auto_air_vent_display_legs(
        segments, graph.collect_auto_air_vent_ports(doc), layout
    )
    segments, _ = graph.bridge_pipe_crossover_gaps(segments)
    return segments


def equipment_layer_name(doc) -> str:
    return next(
        layer.dxf.name
        for layer in doc.layers
        if layer.dxf.color == 3 and layer.dxf.name.endswith("平面")
    )


def insert_equipment_center(insert, equipment_layer: str) -> tuple[float, float]:
    points: list[tuple[float, float]] = []
    for entity in insert.virtual_entities():
        if entity.dxftype() != "LINE" or entity.dxf.layer != equipment_layer:
            continue
        points.extend(
            [
                (float(entity.dxf.start.x), float(entity.dxf.start.y)),
                (float(entity.dxf.end.x), float(entity.dxf.end.y)),
            ]
        )
    if not points:
        raise RuntimeError(
            f"Numeric equipment insert {insert.dxf.handle} has no outline geometry"
        )
    return (
        (min(point[0] for point in points) + max(point[0] for point in points))
        / 2.0,
        (min(point[1] for point in points) + max(point[1] for point in points))
        / 2.0,
    )


def insert_pipe_segments(insert, system_layers: dict[str, str]) -> tuple[graph.Segment, ...]:
    segments: dict[tuple, graph.Segment] = {}
    for entity in graph.recursive_entities(insert):
        if entity.dxftype() != "LINE" or entity.dxf.layer not in system_layers:
            continue
        start = (float(entity.dxf.start.x), float(entity.dxf.start.y))
        end = (float(entity.dxf.end.x), float(entity.dxf.end.y))
        if math.dist(start, end) < 1e-6:
            continue
        segment = graph.Segment(system_layers[entity.dxf.layer], start, end)
        endpoints = sorted(
            [graph.point_key(start, 0.01), graph.point_key(end, 0.01)]
        )
        segments.setdefault((segment.system, *endpoints), segment)
    return tuple(segments.values())


def collect_owned_equipment(
    doc, equipment: list[graph.EquipmentNode]
) -> tuple[list[OwnedEquipment], list[graph.EquipmentNode]]:
    """Attach each of the 86 omitted devices to its source block instance.

    Block provenance is used only to enumerate local branch-slot candidates.
    Pairing is subsequently accepted only by row-wide translation consensus
    and spatial order checks.
    """
    equipment_layer = equipment_layer_name(doc)
    system_layers = graph.get_system_layers(doc)
    remaining = {
        node.label: node
        for node in equipment
        if node.source.startswith("block:")
    }
    candidates = []
    for insert in doc.modelspace().query("INSERT"):
        block_name = insert.dxf.name
        if block_name not in NUMERIC_EQUIPMENT_BLOCKS:
            continue
        center = insert_equipment_center(insert, equipment_layer)
        candidates.append((insert, block_name, center))

    pairs: list[tuple[float, int, str]] = []
    for insert_index, (_, block_name, center) in enumerate(candidates):
        expected_source = f"block:{block_name}"
        for label, node in remaining.items():
            if node.source != expected_source:
                continue
            pairs.append(
                (math.dist(center, (node.x, node.y)), insert_index, label)
            )
    pairs.sort()

    assigned_inserts: set[int] = set()
    assigned_labels: set[str] = set()
    owned: list[OwnedEquipment] = []
    for distance, insert_index, label in pairs:
        if insert_index in assigned_inserts or label in assigned_labels:
            continue
        if distance > 0.5:
            continue
        insert, block_name, _ = candidates[insert_index]
        owned.append(
            OwnedEquipment(
                node=remaining[label],
                block_name=block_name,
                insert_handle=str(insert.dxf.handle),
                pipe_segments=insert_pipe_segments(insert, system_layers),
            )
        )
        assigned_inserts.add(insert_index)
        assigned_labels.add(label)

    missing = sorted(set(remaining) - assigned_labels)
    if missing:
        raise RuntimeError(f"Unmatched omitted-connection equipment: {missing}")
    if len(owned) != len(candidates):
        raise RuntimeError(
            f"Numeric insert mismatch: {len(owned)} matched for {len(candidates)} inserts"
        )

    direct = sorted(
        (node for node in equipment if node.source == "exploded-outline"),
        key=lambda node: (node.floor, node.sequence),
    )
    return sorted(owned, key=lambda item: (item.node.floor, item.node.sequence)), direct


def polyline_center(
    vertices: tuple[tuple[float, float], ...]
) -> tuple[float, float]:
    return (
        (min(point[0] for point in vertices) + max(point[0] for point in vertices))
        / 2.0,
        (min(point[1] for point in vertices) + max(point[1] for point in vertices))
        / 2.0,
    )


def collect_omission_markers(
    doc, owned_equipment: list[OwnedEquipment]
) -> dict[str, OmissionMarker]:
    """Find paired DIM_SYMB breaks and retain the main-diagram-side marker.

    Each genuinely omitted device has exactly two six-vertex break marks: one
    beside the remote equipment drawing and one terminating the attribute-rich
    branch in the main diagram. The latter is farther from the display box.
    """
    markers: dict[str, OmissionMarker] = {}
    for owned in owned_equipment:
        insert = doc.entitydb[owned.insert_handle]
        pairs: list[
            tuple[
                float,
                tuple[float, float],
                tuple[tuple[float, float], ...],
            ]
        ] = []
        for entity in graph.recursive_entities(insert):
            if not (
                entity.dxftype() == "LWPOLYLINE"
                and entity.dxf.layer == "DIM_SYMB"
            ):
                continue
            vertices = tuple(
                (float(x), float(y)) for x, y, *_ in entity.get_points()
            )
            if len(vertices) < 4:
                continue
            center = polyline_center(vertices)
            pairs.append(
                (
                    math.dist(center, (owned.node.x, owned.node.y)),
                    center,
                    vertices,
                )
            )
        if not pairs:
            continue
        if len(pairs) != 2:
            raise RuntimeError(
                f"Expected a marker pair for {owned.node.label}, got {len(pairs)}"
            )
        pairs.sort(key=lambda item: item[0])
        _, equipment_center, _ = pairs[0]
        _, main_center, main_vertices = pairs[1]
        markers[owned.node.label] = OmissionMarker(
            device_label=owned.node.label,
            main_x=main_center[0],
            main_y=main_center[1],
            equipment_side_x=equipment_center[0],
            equipment_side_y=equipment_center[1],
            main_vertices=main_vertices,
        )
    return markers


def point_to_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    vx, vy = end[0] - start[0], end[1] - start[1]
    length_squared = vx * vx + vy * vy
    if length_squared < 1e-12:
        return math.dist(point, start)
    parameter = (
        (point[0] - start[0]) * vx + (point[1] - start[1]) * vy
    ) / length_squared
    parameter = max(0.0, min(1.0, parameter))
    projected = (start[0] + parameter * vx, start[1] + parameter * vy)
    return math.dist(point, projected)


def point_to_polyline_distance(
    point: tuple[float, float],
    vertices: tuple[tuple[float, float], ...],
) -> float:
    return min(
        point_to_segment_distance(point, start, end)
        for start, end in zip(vertices, vertices[1:])
    )


def branch_attachment(
    owned: OwnedEquipment,
    marker: OmissionMarker,
    system: str,
) -> tuple[float, float]:
    candidates: dict[tuple[int, int], tuple[float, float]] = {}
    for segment in owned.pipe_segments:
        if segment.system != system:
            continue
        for endpoint in (segment.start, segment.end):
            if (
                point_to_polyline_distance(endpoint, marker.main_vertices)
                <= OWNER_POINT_TOLERANCE
            ):
                candidates[
                    graph.point_key(endpoint, graph.ENDPOINT_QUANTUM)
                ] = endpoint
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected one {system} attachment at the main omission marker for "
            f"{owned.node.label}, got {len(candidates)}"
        )
    return next(iter(candidates.values()))


def relocate_equipment_nodes(
    equipment: list[graph.EquipmentNode],
    markers: dict[str, OmissionMarker],
) -> list[graph.EquipmentNode]:
    relocated = []
    for node in equipment:
        marker = markers.get(node.label)
        if marker is None:
            relocated.append(node)
            continue
        relocated.append(
            graph.EquipmentNode(
                label=node.label,
                floor=node.floor,
                sequence=node.sequence,
                x=marker.main_x,
                y=marker.main_y,
                source=f"main-omission-marker:{node.source}",
            )
        )
    return sorted(relocated, key=lambda node: (node.floor, node.sequence))


def materialize_edges(
    doc,
    owned_equipment: list[OwnedEquipment],
    relation_edges: list[ConnectionEdge],
    markers: dict[str, OmissionMarker],
) -> list[MaterializedEdge]:
    owned_by_label = {item.node.label: item for item in owned_equipment}
    system_layer_by_name = {
        system: layer for layer, system in graph.get_system_layers(doc).items()
    }
    result = []
    for edge in relation_edges:
        owned = owned_by_label[edge.device_label]
        marker = markers.get(edge.device_label)
        if marker is None:
            graph_x, graph_y = edge.device_x, edge.device_y
            attachment_x = attachment_y = None
            marker_x = marker_y = None
            mode = "existing_direct_cad_path"
            attribute_carrier = (
                f"DXF_INSERT:{owned.insert_handle}/BLOCK:{owned.block_name}/"
                f"SYSTEM:{edge.system}/TEE:{edge.tee_id}->EQUIPMENT"
            )
        else:
            graph_x, graph_y = marker.main_x, marker.main_y
            attachment_x, attachment_y = branch_attachment(
                owned, marker, edge.system
            )
            marker_x, marker_y = marker.main_x, marker.main_y
            mode = "cad_branch_to_main_omission_marker"
            attribute_carrier = (
                f"DXF_INSERT:{owned.insert_handle}/BLOCK:{owned.block_name}/"
                f"SYSTEM:{edge.system}/TEE:{edge.tee_id}->MAIN_DIM_SYMB"
            )
        result.append(
            MaterializedEdge(
                edge_id=edge.edge_id,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                edge_type="equipment_branch",
                system=edge.system,
                device_label=edge.device_label,
                floor=edge.floor,
                group_id=edge.group_id,
                block_name=edge.block_name,
                tee_id=edge.tee_id,
                tee_x=edge.tee_x,
                tee_y=edge.tee_y,
                graph_device_x=graph_x,
                graph_device_y=graph_y,
                display_device_x=edge.device_x,
                display_device_y=edge.device_y,
                connection_mode=mode,
                omission_marker_x=marker_x,
                omission_marker_y=marker_y,
                branch_attachment_x=attachment_x,
                branch_attachment_y=attachment_y,
                source_insert_handle=owned.insert_handle,
                source_block_name=owned.block_name,
                source_system_layer=system_layer_by_name[edge.system],
                attribute_carrier=attribute_carrier,
                attribute_extraction_status=(
                    "ordered_cad_path_preserved_attributes_not_yet_normalized"
                    if marker is not None
                    else "preserved_in_source_cad_not_yet_normalized"
                ),
                cad_path_id=(
                    f"PATH-{edge.edge_id}"
                    if marker is not None
                    else None
                ),
                match_translation_dx=edge.translation_dx,
                match_translation_dy=edge.translation_dy,
                group_consensus_dx=edge.group_consensus_dx,
                group_consensus_dy=edge.group_consensus_dy,
                match_residual=edge.residual,
                candidate_count=edge.candidate_count,
                candidate_selection=edge.candidate_selection,
                order_index=edge.order_index,
                order_valid=edge.order_valid,
                status=edge.status,
            )
        )
    return result


def trace_branch_path(
    owned: OwnedEquipment, edge: MaterializedEdge
) -> BranchPath:
    if (
        edge.cad_path_id is None
        or edge.branch_attachment_x is None
        or edge.branch_attachment_y is None
    ):
        raise RuntimeError(f"Edge {edge.edge_id} has no omission-marker path target")
    segments = [
        segment for segment in owned.pipe_segments if segment.system == edge.system
    ]
    tee = graph.TeeNode(edge.system, edge.tee_x, edge.tee_y)
    adjacency, points = build_owner_network(segments, [tee])
    start = graph.point_key((edge.tee_x, edge.tee_y), graph.ENDPOINT_QUANTUM)
    goal = graph.point_key(
        (edge.branch_attachment_x, edge.branch_attachment_y),
        graph.ENDPOINT_QUANTUM,
    )
    distances = {start: 0.0}
    previous: dict[tuple[int, int], tuple[int, int]] = {}
    queue: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance > distances[node] + 1e-9:
            continue
        if node == goal:
            break
        for neighbor, weight in adjacency.get(node, []):
            proposal = distance + weight
            if proposal + 1e-9 < distances.get(neighbor, math.inf):
                distances[neighbor] = proposal
                previous[neighbor] = node
                heapq.heappush(queue, (proposal, neighbor))
    if goal not in distances:
        raise RuntimeError(
            f"No original CAD pipe path from {edge.tee_id} to the main omission "
            f"marker for {edge.device_label} {edge.system}"
        )

    keys = [goal]
    while keys[-1] != start:
        keys.append(previous[keys[-1]])
    keys.reverse()
    ordered_points = tuple(points[key] for key in keys)
    segment_indexes: list[int] = []
    for first, second in zip(ordered_points, ordered_points[1:]):
        candidates = [
            index
            for index, segment in enumerate(segments)
            if graph.projection_parameter(
                first,
                segment.start,
                segment.end,
                OWNER_POINT_TOLERANCE,
            )
            is not None
            and graph.projection_parameter(
                second,
                segment.start,
                segment.end,
                OWNER_POINT_TOLERANCE,
            )
            is not None
        ]
        if not candidates:
            raise RuntimeError(
                f"Unattributed path fragment for {edge.edge_id}: {first} -> {second}"
            )
        segment_indexes.append(candidates[0])

    return BranchPath(
        cad_path_id=edge.cad_path_id,
        edge_id=edge.edge_id,
        device_label=edge.device_label,
        system=edge.system,
        tee_id=edge.tee_id,
        source_insert_handle=edge.source_insert_handle,
        source_block_name=edge.source_block_name,
        start_x=edge.tee_x,
        start_y=edge.tee_y,
        attachment_x=edge.branch_attachment_x,
        attachment_y=edge.branch_attachment_y,
        total_length=distances[goal],
        pipe_fragment_count=len(ordered_points) - 1,
        owner_segment_indexes=tuple(segment_indexes),
        ordered_points=ordered_points,
        attribute_scope=(
            "Original same-system CAD pipe fragments from the selected first T "
            "to the unique main-side DIM_SYMB attachment; query valves, hoses, "
            "diameter text and other branch entities against this ordered path "
            "within the referenced source INSERT."
        ),
    )


def trace_omitted_branch_paths(
    owned_equipment: list[OwnedEquipment], edges: list[MaterializedEdge]
) -> list[BranchPath]:
    owned_by_label = {item.node.label: item for item in owned_equipment}
    return [
        trace_branch_path(owned_by_label[edge.device_label], edge)
        for edge in edges
        if edge.connection_mode == "cad_branch_to_main_omission_marker"
    ]


def tee_id_lookup(tees: list[graph.TeeNode]) -> dict[tuple[str, tuple[int, int]], str]:
    return {
        (tee.system, graph.point_key((tee.x, tee.y), graph.ENDPOINT_QUANTUM)): f"T{index:03d}"
        for index, tee in enumerate(tees, start=1)
    }


def owner_tee_candidates(
    owned: OwnedEquipment, tees: list[graph.TeeNode], system: str
) -> list[graph.TeeNode]:
    owner_segments = [
        segment for segment in owned.pipe_segments if segment.system == system
    ]
    candidates = [
        tee
        for tee in tees
        if tee.system == system
        and any(
            graph.projection_parameter(
                (tee.x, tee.y),
                segment.start,
                segment.end,
                OWNER_POINT_TOLERANCE,
            )
            is not None
            for segment in owner_segments
        )
    ]
    return sorted(candidates, key=lambda tee: (tee.y, tee.x))


def build_owner_network(
    segments: list[graph.Segment], candidates: list[graph.TeeNode]
) -> tuple[
    dict[tuple[int, int], list[tuple[tuple[int, int], float]]],
    dict[tuple[int, int], tuple[float, float]],
]:
    """Split owner lines at touching endpoints and candidate T coordinates."""
    point_by_key: dict[tuple[int, int], tuple[float, float]] = {}
    endpoints = [point for segment in segments for point in (segment.start, segment.end)]
    candidate_points = [(tee.x, tee.y) for tee in candidates]
    split_points = endpoints + candidate_points
    adjacency: dict[tuple[int, int], list[tuple[tuple[int, int], float]]] = defaultdict(list)

    for segment in segments:
        points_on_segment: dict[tuple[int, int], tuple[float, tuple[float, float]]] = {}
        for point in split_points:
            parameter = graph.projection_parameter(
                point,
                segment.start,
                segment.end,
                OWNER_POINT_TOLERANCE,
            )
            if parameter is None:
                continue
            key = graph.point_key(point, graph.ENDPOINT_QUANTUM)
            points_on_segment[key] = (parameter, point)
            point_by_key[key] = point
        ordered = sorted(points_on_segment.items(), key=lambda item: item[1][0])
        for (first_key, (_, first)), (second_key, (_, second)) in zip(
            ordered, ordered[1:]
        ):
            distance = math.dist(first, second)
            if distance < 1e-6:
                continue
            adjacency[first_key].append((second_key, distance))
            adjacency[second_key].append((first_key, distance))
    return adjacency, point_by_key


def shortest_distances(
    adjacency: dict[tuple[int, int], list[tuple[tuple[int, int], float]]],
    start: tuple[int, int],
) -> dict[tuple[int, int], float]:
    distances = {start: 0.0}
    queue: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance > distances[node] + 1e-9:
            continue
        for neighbor, weight in adjacency.get(node, []):
            proposal = distance + weight
            if proposal + 1e-9 < distances.get(neighbor, math.inf):
                distances[neighbor] = proposal
                heapq.heappush(queue, (proposal, neighbor))
    return distances


def first_tee_from_omission_side(
    owned: OwnedEquipment,
    candidates: list[graph.TeeNode],
    system: str,
) -> graph.TeeNode:
    """Choose the first T reached from the local omitted-side branch terminal.

    This resolves the only repeated template that contains two supply T points
    in one source block. Euclidean nearest-T is intentionally not used.
    """
    segments = [segment for segment in owned.pipe_segments if segment.system == system]
    adjacency, points = build_owner_network(segments, candidates)
    candidate_by_key = {
        graph.point_key((tee.x, tee.y), graph.ENDPOINT_QUANTUM): tee
        for tee in candidates
    }
    candidate_keys = set(candidate_by_key)

    # Candidate-containing connected components only; detached symbol fragments
    # cannot be the continuation of the omitted pipe.
    component_by_key: dict[tuple[int, int], int] = {}
    component = 0
    for start in adjacency:
        if start in component_by_key:
            continue
        stack = [start]
        component_by_key[start] = component
        while stack:
            node = stack.pop()
            for neighbor, _ in adjacency[node]:
                if neighbor not in component_by_key:
                    component_by_key[neighbor] = component
                    stack.append(neighbor)
        component += 1
    candidate_components = {
        component_by_key[key]
        for key in candidate_keys
        if key in component_by_key
    }
    terminal_keys = [
        key
        for key, neighbors in adjacency.items()
        if len(neighbors) == 1
        and key not in candidate_keys
        and component_by_key.get(key) in candidate_components
    ]
    if not terminal_keys:
        raise RuntimeError(
            f"No omission-side terminal for {owned.node.label} {system}"
        )
    start = min(
        terminal_keys,
        key=lambda key: math.dist(
            points[key], (owned.node.x, owned.node.y)
        ),
    )
    distances = shortest_distances(adjacency, start)
    reachable = [
        (distances[key], candidate_by_key[key])
        for key in candidate_keys
        if key in distances
    ]
    if not reachable:
        raise RuntimeError(
            f"No reachable T from omission side for {owned.node.label} {system}"
        )
    return min(reachable, key=lambda item: item[0])[1]


def make_provisional_matches(
    owned_equipment: list[OwnedEquipment], tees: list[graph.TeeNode]
) -> list[ProvisionalMatch]:
    ids = tee_id_lookup(tees)
    matches: list[ProvisionalMatch] = []
    for owned in owned_equipment:
        for system in ("supply", "return"):
            candidates = owner_tee_candidates(owned, tees, system)
            if not candidates:
                raise RuntimeError(
                    f"No branch-slot T candidate for {owned.node.label} {system}"
                )
            if len(candidates) == 1:
                selected = candidates[0]
                selection = "single_owner_branch_candidate"
            else:
                selected = first_tee_from_omission_side(
                    owned, candidates, system
                )
                selection = "first_tee_from_omission_side_by_path"
            tee_id = ids[
                (
                    selected.system,
                    graph.point_key(
                        (selected.x, selected.y), graph.ENDPOINT_QUANTUM
                    ),
                )
            ]
            matches.append(
                ProvisionalMatch(
                    equipment=owned.node,
                    block_name=owned.block_name,
                    system=system,
                    tee=selected,
                    tee_id=tee_id,
                    candidate_count=len(candidates),
                    candidate_selection=selection,
                )
            )
    return matches


def equipment_runs(
    owned_equipment: list[OwnedEquipment],
) -> list[list[OwnedEquipment]]:
    """Find collinear repeated banks without relying on label sequence order."""
    buckets: dict[tuple[int, str], list[OwnedEquipment]] = defaultdict(list)
    for item in owned_equipment:
        buckets[(item.node.floor, item.block_name)].append(item)

    runs: list[list[OwnedEquipment]] = []
    for _, items in sorted(buckets.items()):
        if len(items) == 1:
            runs.append(items)
            continue
        nearest_distances = []
        for first in items:
            nearest_distances.append(
                min(
                    math.dist(
                        (first.node.x, first.node.y),
                        (second.node.x, second.node.y),
                    )
                    for second in items
                    if second is not first
                )
            )
        typical_spacing = statistics.median(nearest_distances)
        link_limit = typical_spacing * 1.8
        adjacency: dict[str, set[str]] = defaultdict(set)
        by_label = {item.node.label: item for item in items}
        for index, first in enumerate(items):
            for second in items[index + 1 :]:
                distance = math.dist(
                    (first.node.x, first.node.y),
                    (second.node.x, second.node.y),
                )
                if distance <= link_limit:
                    adjacency[first.node.label].add(second.node.label)
                    adjacency[second.node.label].add(first.node.label)

        seen: set[str] = set()
        for item in items:
            if item.node.label in seen:
                continue
            component: list[OwnedEquipment] = []
            stack = [item.node.label]
            seen.add(item.node.label)
            while stack:
                label = stack.pop()
                component.append(by_label[label])
                for neighbor in adjacency[label]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            runs.append(component)

    return sorted(
        runs,
        key=lambda run: (
            run[0].node.floor,
            min(item.node.y for item in run),
            min(item.node.x for item in run),
        ),
    )


def principal_axis(items: list[OwnedEquipment]) -> tuple[float, float]:
    if len(items) == 1:
        return 1.0, 0.0
    first, second = max(
        (
            (first, second)
            for index, first in enumerate(items)
            for second in items[index + 1 :]
        ),
        key=lambda pair: math.dist(
            (pair[0].node.x, pair[0].node.y),
            (pair[1].node.x, pair[1].node.y),
        ),
    )
    dx = second.node.x - first.node.x
    dy = second.node.y - first.node.y
    length = math.hypot(dx, dy)
    axis = (dx / length, dy / length)
    if axis[0] < -1e-9 or (abs(axis[0]) <= 1e-9 and axis[1] < 0):
        axis = (-axis[0], -axis[1])
    return axis


def projection(x: float, y: float, axis: tuple[float, float]) -> float:
    return x * axis[0] + y * axis[1]


def finalize_matches(
    owned_equipment: list[OwnedEquipment],
    provisional: list[ProvisionalMatch],
) -> tuple[list[ConnectionEdge], list[GroupAudit]]:
    by_device_system = {
        (match.equipment.label, match.system): match for match in provisional
    }
    edges: list[ConnectionEdge] = []
    audits: list[GroupAudit] = []
    edge_number = 1

    for group_number, run in enumerate(equipment_runs(owned_equipment), start=1):
        floor = run[0].node.floor
        block_name = run[0].block_name
        group_id = f"G{group_number:02d}-F{floor}-B{block_name}"
        axis = principal_axis(run)
        device_order = sorted(
            run,
            key=lambda item: projection(item.node.x, item.node.y, axis),
        )
        order_by_label = {
            item.node.label: index
            for index, item in enumerate(device_order, start=1)
        }

        consensus: dict[str, tuple[float, float]] = {}
        order_valid: dict[str, bool] = {}
        residuals: list[float] = []
        group_edges: list[ConnectionEdge] = []
        for system in ("supply", "return"):
            matches = [
                by_device_system[(item.node.label, system)] for item in run
            ]
            dx_values = [
                match.equipment.x - match.tee.x for match in matches
            ]
            dy_values = [
                match.equipment.y - match.tee.y for match in matches
            ]
            median_dx = statistics.median(dx_values)
            median_dy = statistics.median(dy_values)
            consensus[system] = (median_dx, median_dy)

            target_order = sorted(
                matches,
                key=lambda match: projection(match.tee.x, match.tee.y, axis),
            )
            target_labels = [match.equipment.label for match in target_order]
            device_labels = [item.node.label for item in device_order]
            order_valid[system] = target_labels == device_labels

            for match in matches:
                dx = match.equipment.x - match.tee.x
                dy = match.equipment.y - match.tee.y
                residual = math.hypot(dx - median_dx, dy - median_dy)
                residuals.append(residual)
                if system == "supply":
                    source, target = match.tee_id, match.equipment.label
                else:
                    source, target = match.equipment.label, match.tee_id
                group_edges.append(
                    ConnectionEdge(
                        edge_id=f"EC{edge_number:03d}",
                        source_node_id=source,
                        target_node_id=target,
                        edge_type="omitted_equipment_reconnection",
                        system=system,
                        device_label=match.equipment.label,
                        floor=match.equipment.floor,
                        group_id=group_id,
                        block_name=block_name,
                        tee_id=match.tee_id,
                        tee_x=match.tee.x,
                        tee_y=match.tee.y,
                        device_x=match.equipment.x,
                        device_y=match.equipment.y,
                        translation_dx=dx,
                        translation_dy=dy,
                        group_consensus_dx=median_dx,
                        group_consensus_dy=median_dy,
                        residual=residual,
                        candidate_count=match.candidate_count,
                        candidate_selection=match.candidate_selection,
                        order_index=order_by_label[match.equipment.label],
                        order_valid=order_valid[system],
                        status="pending_group_validation",
                    )
                )
                edge_number += 1

        target_ids = [edge.tee_id for edge in group_edges]
        no_duplicate_targets = len(target_ids) == len(set(target_ids))
        maximum_residual = max(residuals, default=0.0)
        group_ok = (
            maximum_residual <= VECTOR_RESIDUAL_TOLERANCE
            and all(order_valid.values())
            and no_duplicate_targets
        )
        final_status = "accepted" if group_ok else "rejected"
        group_edges = [
            ConnectionEdge(
                **{
                    **asdict(edge),
                    "status": final_status,
                }
            )
            for edge in group_edges
        ]
        edges.extend(group_edges)
        audits.append(
            GroupAudit(
                group_id=group_id,
                floor=floor,
                block_name=block_name,
                device_count=len(run),
                device_labels=";".join(
                    item.node.label for item in device_order
                ),
                supply_dx=consensus["supply"][0],
                supply_dy=consensus["supply"][1],
                return_dx=consensus["return"][0],
                return_dy=consensus["return"][1],
                maximum_residual=maximum_residual,
                supply_order_valid=order_valid["supply"],
                return_order_valid=order_valid["return"],
                no_duplicate_targets=no_duplicate_targets,
                status=final_status,
            )
        )

    rejected = [audit.group_id for audit in audits if audit.status != "accepted"]
    if rejected:
        raise RuntimeError(f"Rejected reconnection groups: {rejected}")
    if len({(edge.system, edge.tee_id) for edge in edges}) != len(edges):
        raise RuntimeError("A T target was assigned more than once across groups")
    return sorted(edges, key=lambda edge: edge.edge_id), audits


def write_dataclass_csv(path: Path, records: Iterable[object]) -> None:
    rows = [asdict(record) for record in records]
    if not rows:
        raise RuntimeError(f"Refusing to write empty audit file: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_omission_markers(
    ax,
    markers: dict[str, OmissionMarker],
    equipment: list[graph.EquipmentNode],
    floor: int | None = None,
) -> None:
    floor_by_label = {node.label: node.floor for node in equipment}
    for label, marker in markers.items():
        if floor is not None and floor_by_label[label] != floor:
            continue
        ax.plot(
            [point[0] for point in marker.main_vertices],
            [point[1] for point in marker.main_vertices],
            color="#22c55e",
            linewidth=1.05,
            alpha=0.9,
            zorder=2,
        )


def connection_legend() -> list[Line2D]:
    return graph.legend_handles() + [
        Line2D(
            [0],
            [0],
            color="#22c55e",
            linewidth=1.5,
            label="主图侧省略标记（设备节点落点）",
        ),
    ]


def save_visualizations(
    output_dir: Path,
    segments: list[graph.Segment],
    equipment: list[graph.EquipmentNode],
    tees: list[graph.TeeNode],
    edges: list[MaterializedEdge],
    markers: dict[str, OmissionMarker],
    layout: graph.DrawingLayout,
) -> None:
    graph.configure_plotting()
    fig, ax = plt.subplots(figsize=(20, 13), dpi=220)
    graph.plot_base_segments(ax, segments, layout)
    plot_omission_markers(ax, markers, equipment)
    graph.plot_nodes(ax, equipment, tees, layout)
    ax.set_xlim(layout.plot_x_min, layout.plot_x_max)
    ax.set_ylim(layout.plot_y_min, layout.plot_y_max)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(handles=connection_legend(), loc="upper right", frameon=True, fontsize=9)
    ax.set_title(
        "SH16 设备节点主图落位（全量）\n"
        f"{len(markers)} 台设备迁移到主图侧省略标记；不绘制跨图直连线",
        fontsize=18,
        pad=18,
    )
    fig.savefig(
        output_dir / "equipment_reconnection_overview.png",
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.12,
        facecolor="white",
    )
    plt.close(fig)

    ranges = {
        1: (layout.plot_y_min, layout.floor_boundary_1_2),
        2: (layout.floor_boundary_1_2, layout.floor_boundary_2_3),
        3: (layout.floor_boundary_2_3, layout.plot_y_max + 4_000.0),
    }
    fig, axes = plt.subplots(3, 1, figsize=(22, 17), dpi=220)
    for axis_plot, floor in zip(axes, (3, 2, 1)):
        y_range = ranges[floor]
        graph.plot_base_segments(axis_plot, segments, layout, y_range)
        plot_omission_markers(axis_plot, markers, equipment, floor)
        graph.plot_nodes(
            axis_plot,
            equipment,
            tees,
            layout,
            floor=floor,
            add_equipment_labels=True,
        )
        marker_count = sum(
            node.floor == floor and node.label in markers for node in equipment
        )
        axis_plot.set_xlim(layout.plot_x_min, layout.plot_x_max)
        axis_plot.set_ylim(*y_range)
        axis_plot.set_aspect("equal")
        axis_plot.axis("off")
        axis_plot.text(
            0.01,
            0.96,
            f"{floor}F：省略设备主图落位 {marker_count} 台",
            transform=axis_plot.transAxes,
            ha="left",
            va="top",
            fontsize=12,
            bbox={
                "boxstyle": "round,pad=0.35",
                "facecolor": "white",
                "alpha": 0.9,
                "edgecolor": "#d1d5db",
            },
        )
    axes[0].legend(handles=connection_legend(), loc="upper right", frameon=True, fontsize=8)
    fig.suptitle("设备节点迁移到主图侧省略标记：按楼层核对", fontsize=18, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    fig.savefig(
        output_dir / "equipment_reconnection_by_floor.png",
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.12,
        facecolor="white",
    )
    plt.close(fig)


def graph_payload(
    equipment: list[graph.EquipmentNode],
    tees: list[graph.TeeNode],
    edges: list[MaterializedEdge],
    markers: dict[str, OmissionMarker],
    paths: list[BranchPath],
    layout: graph.DrawingLayout,
) -> dict:
    nodes = [
        {
            "node_id": node.label,
            "node_type": "equipment",
            "subtype": "CRAH",
            "floor": node.floor,
            "label": node.label,
            "x": node.x,
            "y": node.y,
            "source": node.source,
        }
        for node in equipment
    ]
    nodes.extend(
        {
            "node_id": f"T{index:03d}",
            "node_type": "physical_junction",
            "subtype": f"tee_{node.system}",
            "floor": graph.drawing_band(node.y, layout),
            "label": "",
            "x": node.x,
            "y": node.y,
            "source": "preprocessed_three_ray_tee",
        }
        for index, node in enumerate(tees, start=1)
    )
    return {
        "metadata": {
            "scope": "omission-aware equipment placement and branch association",
            "node_count": len(nodes),
            "equipment_count": len(equipment),
            "tee_count": len(tees),
            "equipment_relocated_to_main_omission_marker": len(markers),
            "equipment_branch_relation_count": len(edges),
            "omission_branch_path_count": len(paths),
            "edge_scope_note": (
                "Edges reference their original CAD insert as the attribute carrier. "
                "No synthetic straight T-to-equipment geometry is created; pipe-derived "
                "T-to-T edges and six exploded direct devices remain outside this stage."
            ),
        },
        "nodes": nodes,
        "omission_markers": [
            asdict(markers[label]) for label in sorted(markers)
        ],
        "cad_branch_paths": [asdict(path) for path in paths],
        "edges": [asdict(edge) for edge in edges],
    }


def main() -> None:
    raise SystemExit(
        "The edge stage is intentionally paused. Run place_equipment_nodes.py "
        "for the current node-placement-only deliverable."
    )
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.readfile(args.dxf)
    labels = graph.equipment_labels(doc)
    layout = graph.infer_drawing_layout(labels)
    segments = cleaned_pipe_graph(doc, layout)
    equipment = graph.detect_equipment_nodes(doc)
    tees = graph.detect_tee_nodes(segments, layout)
    owned, direct = collect_owned_equipment(doc, equipment)
    provisional = make_provisional_matches(owned, tees)
    relation_edges, audits = finalize_matches(owned, provisional)
    markers = collect_omission_markers(doc, owned)
    relocated_equipment = relocate_equipment_nodes(equipment, markers)
    edges = materialize_edges(doc, owned, relation_edges, markers)
    paths = trace_omitted_branch_paths(owned, edges)

    expected_numeric = 86
    expected_omitted = 62
    expected_exploded_direct = 6
    if (
        len(owned) != expected_numeric
        or len(markers) != expected_omitted
        or len(direct) != expected_exploded_direct
    ):
        raise RuntimeError(
            "Equipment class count changed: "
            f"numeric={len(owned)}, omitted={len(markers)}, "
            f"exploded_direct={len(direct)}"
        )
    if len(edges) != expected_numeric * 2:
        raise RuntimeError(f"Expected 172 branch relations, got {len(edges)}")
    if len(paths) != expected_omitted * 2:
        raise RuntimeError(f"Expected 124 omission branch paths, got {len(paths)}")

    write_dataclass_csv(
        args.output_dir / "equipment_reconnection_edges.csv", edges
    )
    write_dataclass_csv(
        args.output_dir / "equipment_reconnection_groups.csv", audits
    )
    graph.write_nodes_csv(
        args.output_dir / "equipment_reconnection_nodes.csv",
        relocated_equipment,
        tees,
        layout,
    )
    (args.output_dir / "equipment_branch_paths.json").write_text(
        json.dumps(
            [asdict(path) for path in paths], ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    payload = graph_payload(
        relocated_equipment, tees, edges, markers, paths, layout
    )
    (args.output_dir / "equipment_reconnection_graph.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    candidate_counts = defaultdict(int)
    for edge in edges:
        candidate_counts[str(edge.candidate_count)] += 1
    summary = {
        "source_file": str(args.dxf.resolve()),
        "algorithm": (
            "owner-derived branch slots + first-T path disambiguation + "
            "row-wide common translation vector + order-preserving one-to-one match + "
            "main-side DIM_SYMB equipment placement"
        ),
        "counts": {
            "all_equipment_nodes": len(equipment),
            "numeric_block_equipment_with_relation": len(owned),
            "omitted_connection_equipment_relocated": len(markers),
            "direct_numeric_equipment_unchanged": len(owned) - len(markers),
            "direct_exploded_equipment_unchanged": len(direct),
            "accepted_groups": len(audits),
            "equipment_branch_relations": len(edges),
            "omission_marker_branch_relations": sum(
                edge.connection_mode == "cad_branch_to_main_omission_marker"
                for edge in edges
            ),
            "direct_numeric_branch_relations": sum(
                edge.connection_mode == "existing_direct_cad_path"
                for edge in edges
            ),
            "original_cad_branch_paths_preserved": len(paths),
            "supply_edges": sum(edge.system == "supply" for edge in edges),
            "return_edges": sum(edge.system == "return" for edge in edges),
        },
        "validation": {
            "all_groups_accepted": all(
                audit.status == "accepted" for audit in audits
            ),
            "maximum_translation_residual": max(
                audit.maximum_residual for audit in audits
            ),
            "all_orders_valid": all(
                audit.supply_order_valid and audit.return_order_valid
                for audit in audits
            ),
            "all_targets_unique": len(
                {(edge.system, edge.tee_id) for edge in edges}
            )
            == len(edges),
            "candidate_counts_by_edge": dict(sorted(candidate_counts.items())),
        },
        "omitted_equipment": sorted(markers),
        "direct_numeric_equipment": sorted(
            item.node.label
            for item in owned
            if item.node.label not in markers
        ),
        "direct_exploded_equipment": [node.label for node in direct],
    }
    (args.output_dir / "equipment_reconnection_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    exploded_direct_labels = "、".join(node.label for node in direct)
    report = f"""# SH16 设备节点主图落位与支路关联结果

## 处理范围

- 输入：`{args.dxf.resolve()}`
- 全部设备节点：{len(equipment)} 台
- 带成对 `DIM_SYMB` 省略标记、迁移到主图侧的设备：{len(markers)} 台
- 无省略标记、保留原设备位置的块设备：{len(owned) - len(markers)} 台
- 无省略标记的炸开设备：{len(direct)} 台（{exploded_direct_labels}）

## 算法

1. 从设备源块中只提取供水、回水候选支路槽位；块归属不直接决定最终配对。
2. 对同层、同模板、空间连续且共线的设备形成设备排，共得到 {len(audits)} 组。
3. 每组分别拟合“供水 T → 设备”和“回水 T → 设备”的公共平移向量。
4. 要求组内一一对应、空间顺序一致、目标 T 不重复。
5. 多候选支路不使用最近邻，改为从省略端沿支路拓扑前进，选择首先到达的 T 节点。
6. 对存在成对省略标记的设备，取远离设备图形的主图侧标记，把设备节点坐标迁移到该标记中心。
7. 供、回水管段在该标记上各有唯一原生附着点；边引用原始 CAD 块实例作为属性载体，不生成跨图直线。

## 结果与校验

| 指标 | 结果 |
|---|---:|
| 迁移到主图侧省略标记的设备 | {len(markers)} |
| 省略设备属性承载支路 | {sum(edge.connection_mode == 'cad_branch_to_main_omission_marker' for edge in edges)} |
| 已保存的原始 CAD 有序支路路径 | {len(paths)} |
| 无省略标记块设备支路 | {sum(edge.connection_mode == 'existing_direct_cad_path' for edge in edges)} |
| 已建立设备—T 支路关系 | {len(edges)} |
| 设备排组 | {len(audits)} |
| 最大公共平移残差 | {max(audit.maximum_residual for audit in audits):.12g} |
| 顺序校验 | 全部通过 |
| 目标 T 唯一性 | 全部通过 |

说明：设备—T 仍是图上的边关系，但其几何和属性载体是原 CAD 支路，而不是 T 到设备图形中心的合成直线。管网内部 T—T 边及 6 台炸开设备的直接边仍不在本阶段物化范围内。
"""
    (args.output_dir / "equipment_reconnection_report.md").write_text(
        report, encoding="utf-8"
    )
    save_visualizations(
        args.output_dir,
        segments,
        relocated_equipment,
        tees,
        edges,
        markers,
        layout,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
