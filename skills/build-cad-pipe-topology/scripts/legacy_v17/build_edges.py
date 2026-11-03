from __future__ import annotations

import argparse
import csv
import heapq
import itertools
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import ezdxf
import matplotlib.pyplot as plt
from ezdxf import bbox
from matplotlib.lines import Line2D

import analyze_graph as graph
import connect_equipment as equipment_graph
PREVIOUS_GRAPH = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DXF = (
    PROJECT_ROOT
    / "data"
    / "updated"
    / "interim"
    / "sh16-native-isometric_updated.fixed.dxf"
)
DEFAULT_TABLE_DXF = (
    PROJECT_ROOT
    / "data"
    / "table"
    / "interim"
    / "sh16-native-table.fixed.dxf"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "edges"

COMPONENT_BLOCK_TYPES = {
    "H-PICPNT-91": ("球阀", "BV"),
    "H-PICPNT-87": ("蝶阀", "BFV"),
    "H-PICPNT-74": ("金属软接", "MFJ"),
    "$VALVE$00000954": ("金属软接", "MFJ"),
    "H-PICPNT-76": ("Y型汽/水过滤器", "YS"),
    "H-PICPNT-81": ("压力表", "PG"),
    "H-PICPNT-82": ("温度计", "TG"),
}

TYPE_CODES = {
    "球阀": "BV",
    "蝶阀": "BFV",
    "自动放气阀": "AAV",
    "金属软接": "MFJ",
    "Y型汽/水过滤器": "YS",
    "压力表": "PG",
    "温度计": "TG",
}

LEGEND_EDGE_TYPES = (
    "固定支架",
    "橡胶软接",
    "金属软接",
    "Y型汽/水过滤器",
    "疏水器",
    "压力表",
    "温度计",
    "水泵",
    "直通型（反冲式）除污器",
    "除垢仪(水处理器)",
    "管道坡向",
    "球阀",
    "蝶阀",
    "静态平衡阀",
    "电动调节阀",
    "定流量动态平衡阀",
    "电动开关阀",
    "消声器",
    "自动放气阀",
)

MAX_COMPONENT_TO_EDGE_DISTANCE = 400.0
VIRTUAL_PORT_MARKER_TOLERANCE = 30.0
VIRTUAL_PORT_BRIDGE_LIMIT = 600.0
INLINE_HOSE_TERMINAL_TOLERANCE = 200.0
INLINE_HOSE_GAP_LIMIT = 2_000.0
INLINE_HOSE_OPPOSING_COSINE_LIMIT = -0.95
EXPLODED_BALL_VALVE_CENTER_MIN_SIZE = 30.0
EXPLODED_BALL_VALVE_CENTER_MAX_SIZE = 60.0
EXPLODED_BALL_VALVE_LINE_SEARCH_FACTOR = 2.5
EXPLODED_BALL_VALVE_LINE_LENGTH_MIN_FACTOR = 4.0
EXPLODED_BALL_VALVE_LINE_LENGTH_MAX_FACTOR = 6.0
BOTTOM_PIPE_LEGEND_CANONICAL_BOUNDS = (
    2_219_000.0,
    2_224_000.0,
    120_000.0,
    123_500.0,
)


@dataclass(frozen=True)
class LogicalEdge:
    edge_id: str
    start_node_id: str
    end_node_id: str
    edge_type: str
    system: str
    floor_start: int
    floor_end: int
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    path_length: float
    path_points: tuple[tuple[float, float], ...]
    attribute_paths: tuple[tuple[tuple[float, float], ...], ...]
    device_label: str | None
    source_insert_handle: str | None
    connection_mode: str
    start_port_id: str | None = None
    end_port_id: str | None = None


@dataclass(frozen=True)
class VirtualPort:
    port_id: str
    node_id: str
    system: str
    sequence: int
    x: float
    y: float
    source_marker_handle: str


@dataclass(frozen=True)
class VirtualEquipmentNode:
    node_id: str
    label: str
    floor: int
    x: float
    y: float
    source_marker_handle: str
    marker_vertices: tuple[tuple[float, float], ...]
    ports: tuple[VirtualPort, ...]


@dataclass(frozen=True)
class VirtualPortBinding:
    node_id: str
    port_id: str
    system: str
    port_x: float
    port_y: float
    tee_id: str
    tee_x: float
    tee_y: float
    connection_mode: str
    bridge_start_x: float | None
    bridge_start_y: float | None
    bridge_end_x: float | None
    bridge_end_y: float | None
    bridge_length: float
    path_length: float


@dataclass(frozen=True)
class VirtualMarkerAudit:
    source_marker_handle: str
    center_x: float
    center_y: float
    vertex_count: int
    node_id: str | None
    supply_port_count: int
    return_port_count: int
    status: str


@dataclass(frozen=True)
class ComponentInstance:
    device_name: str
    equipment_type: str
    type_code: str
    x: float
    y: float
    assignment_x: float
    assignment_y: float
    source_kind: str
    source_block_name: str
    source_top_handle: str | None
    owner_equipment: str | None
    system_hint: str | None
    edge_id: str | None = None
    edge_distance: float | None = None
    assignment_status: str = "pending"


@dataclass(frozen=True)
class EdgeInventory:
    edge_id: str
    start_node_id: str
    end_node_id: str
    equipment_type: str
    device_count: int
    device_names: str


@dataclass(frozen=True)
class DanglingBranch:
    system: str
    tee_key: tuple[int, int]
    terminal_key: tuple[int, int]
    path_keys: tuple[tuple[int, int], ...]
    points: dict[tuple[int, int], tuple[float, float]]


@dataclass(frozen=True)
class InlineGapBridge:
    system: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    length: float
    connection_mode: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build adjacent-node SH16 edges and aggregate inline CAD devices "
            "as edge attributes."
        )
    )
    parser.add_argument("--dxf", type=Path, default=DEFAULT_DXF)
    parser.add_argument("--table-dxf", type=Path, default=DEFAULT_TABLE_DXF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def path_length(points: Iterable[tuple[float, float]]) -> float:
    values = list(points)
    return sum(math.dist(first, second) for first, second in zip(values, values[1:]))


def shortest_path_keys(
    adjacency: dict[tuple[int, int], list[tuple[tuple[int, int], float]]],
    start: tuple[int, int],
    goal: tuple[int, int],
    allowed: set[tuple[int, int]] | None = None,
) -> tuple[tuple[int, int], ...]:
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
            if allowed is not None and neighbor not in allowed:
                continue
            proposal = distance + weight
            if proposal + 1e-9 < distances.get(neighbor, math.inf):
                distances[neighbor] = proposal
                previous[neighbor] = node
                heapq.heappush(queue, (proposal, neighbor))
    if goal not in distances:
        raise RuntimeError(f"No network path from {start} to {goal}")
    result = [goal]
    while result[-1] != start:
        result.append(previous[result[-1]])
    result.reverse()
    return tuple(result)


def node_ids(tees: list[graph.TeeNode]) -> dict[tuple[str, tuple[int, int]], str]:
    if PREVIOUS_GRAPH:
        old = {(n.get('system',n.get('subtype','').replace('tee_','')),graph.point_key((n['x'],n['y']),graph.ENDPOINT_QUANTUM)):n['node_id'] for n in PREVIOUS_GRAPH['nodes'] if n['node_type'] in ['tee','physical_junction']}
        result={};next_id=max([int(n['node_id'][1:])for n in PREVIOUS_GRAPH['nodes']if n['node_id'].startswith('T')]+[0])+1
        for tee in tees:
            key=(tee.system,graph.point_key((tee.x,tee.y),graph.ENDPOINT_QUANTUM))
            if key in old:result[key]=old[key]
            else:result[key]=f'T{next_id:03d}';next_id+=1
        return result
    return {
        (
            tee.system,
            graph.point_key((tee.x, tee.y), graph.ENDPOINT_QUANTUM),
        ): f"T{index:03d}"
        for index, tee in enumerate(tees, start=1)
    }


def marker_scope_status(
    point: tuple[float, float], layout: graph.DrawingLayout
) -> str:
    if not (
        layout.plot_x_min <= point[0] <= layout.plot_x_max
        and layout.plot_y_min <= point[1] <= layout.plot_y_max
    ):
        return "outside_plot_bounds"
    if graph.is_excluded_detail_point(*point, layout):
        return "excluded_left_detail"
    if point[0] > layout.right_detail_x_min and point[1] < layout.right_detail_y_max:
        return "excluded_right_detail"
    return "included"


def collect_virtual_equipment_nodes(
    doc,
    segments: list[graph.Segment],
    layout: graph.DrawingLayout,
) -> tuple[list[VirtualEquipmentNode], list[VirtualMarkerAudit]]:
    """Promote unowned top-level omission symbols to virtual equipment.

    Omission marks already paired with CRAH nodes live inside numeric equipment
    INSERTs.  The remaining six-vertex DIM_SYMB polylines are top-level entities.
    Each included symbol becomes one virtual equipment node; every pipe terminal
    touching its glyph becomes a typed port.  A marker can therefore expose more
    than one supply/return circuit without being split into duplicate nodes.
    """
    markers: list[
        tuple[str, tuple[float, float], tuple[tuple[float, float], ...], str]
    ] = []
    for entity in doc.modelspace().query("LWPOLYLINE"):
        if entity.dxf.layer != "DIM_SYMB":
            continue
        vertices = tuple(
            (float(x), float(y)) for x, y, *_ in entity.get_points()
        )
        if len(vertices) != 6:
            continue
        center = equipment_graph.polyline_center(vertices)
        markers.append(
            (
                str(entity.dxf.handle),
                center,
                vertices,
                marker_scope_status(center, layout),
            )
        )

    terminals: dict[
        str, list[tuple[tuple[int, int], tuple[float, float]]]
    ] = {}
    connected_terminals: dict[str, set[tuple[int, int]]] = {}
    detected_tees = graph.detect_tee_nodes(segments, layout)
    for system in ("supply", "return"):
        adjacency, points = equipment_graph.build_owner_network(
            [item for item in segments if item.system == system], []
        )
        components, _ = connected_components(adjacency)
        main_components = {
            components[key]
            for tee in detected_tees if tee.system == system
            for key in [graph.point_key((tee.x, tee.y), graph.ENDPOINT_QUANTUM)]
            if key in components
        }
        connected_terminals[system] = {
            key for key in adjacency if components[key] in main_components
        }
        terminals[system] = [
            (key, points[key])
            for key, neighbors in adjacency.items()
            if len(neighbors) == 1
        ]

    # Plot bounds control rendering, not connectivity. Recover an out-of-frame
    # omission interface only when BOTH systems touch its glyph and follow real
    # source segments to a main-graph junction. Disconnected detail glyphs stay out.
    markers = [
        (handle, center, vertices,
         "included" if status == "outside_plot_bounds" and all(
             any(key in connected_terminals[system]
                 and equipment_graph.point_to_polyline_distance(point, vertices)
                     <= VIRTUAL_PORT_MARKER_TOLERANCE
                 for key, point in terminals[system])
             for system in ("supply", "return")
         ) else status)
        for handle, center, vertices, status in markers
    ]
    included = sorted(
        (item for item in markers if item[3] == "included"),
        key=lambda item: (marker_scope_status(item[1], layout) != "included",
                          item[1][1], item[1][0], item[0]),
    )
    node_number_by_handle = {
        handle: index for index, (handle, _, _, _) in enumerate(included, 1)
    }
    used_terminals: set[tuple[str, tuple[int, int]]] = set()
    nodes: list[VirtualEquipmentNode] = []
    audit: list[VirtualMarkerAudit] = []

    for handle, center, vertices, status in sorted(
        markers, key=lambda item: (item[1][1], item[1][0], item[0])
    ):
        node_id: str | None = None
        port_counts = {"supply": 0, "return": 0}
        if status == "included":
            number = node_number_by_handle[handle]
            node_id = f"VDEV{number:03d}"
            ports: list[VirtualPort] = []
            for system, prefix in (("supply", "S"), ("return", "R")):
                matches = sorted(
                    (
                        (key, point)
                        for key, point in terminals[system]
                        if equipment_graph.point_to_polyline_distance(
                            point, vertices
                        )
                        <= VIRTUAL_PORT_MARKER_TOLERANCE
                    ),
                    key=lambda item: (item[1][1], item[1][0]),
                )
                if not matches:
                    raise RuntimeError(
                        f"No {system} pipe terminal at standalone omission marker {handle}"
                    )
                for sequence, (key, point) in enumerate(matches, 1):
                    terminal_signature = (system, key)
                    if terminal_signature in used_terminals:
                        raise RuntimeError(
                            f"Pipe terminal reused by multiple omission markers: {point}"
                        )
                    used_terminals.add(terminal_signature)
                    ports.append(
                        VirtualPort(
                            port_id=f"{node_id}-{prefix}{sequence:02d}",
                            node_id=node_id,
                            system=system,
                            sequence=sequence,
                            x=point[0],
                            y=point[1],
                            source_marker_handle=handle,
                        )
                    )
                port_counts[system] = len(matches)
            nodes.append(
                VirtualEquipmentNode(
                    node_id=node_id,
                    label=f"待定义外部接口-{number:03d}",
                    floor=graph.drawing_band(center[1], layout),
                    x=center[0],
                    y=center[1],
                    source_marker_handle=handle,
                    marker_vertices=vertices,
                    ports=tuple(ports),
                )
            )
        audit.append(
            VirtualMarkerAudit(
                source_marker_handle=handle,
                center_x=center[0],
                center_y=center[1],
                vertex_count=len(vertices),
                node_id=node_id,
                supply_port_count=port_counts["supply"],
                return_port_count=port_counts["return"],
                status=(
                    "virtual_equipment_created" if status == "included" else status
                ),
            )
        )
    return nodes, audit


def connected_components(
    adjacency: dict[tuple[int, int], list[tuple[tuple[int, int], float]]]
) -> tuple[
    dict[tuple[int, int], int], dict[int, set[tuple[int, int]]]
]:
    component_by_key: dict[tuple[int, int], int] = {}
    keys_by_component: dict[int, set[tuple[int, int]]] = defaultdict(set)
    component = 0
    for start in adjacency:
        if start in component_by_key:
            continue
        stack = [start]
        component_by_key[start] = component
        while stack:
            key = stack.pop()
            keys_by_component[component].add(key)
            for neighbor, _ in adjacency[key]:
                if neighbor not in component_by_key:
                    component_by_key[neighbor] = component
                    stack.append(neighbor)
        component += 1
    return component_by_key, keys_by_component


def shortest_path_to_any(
    adjacency: dict[tuple[int, int], list[tuple[tuple[int, int], float]]],
    start: tuple[int, int],
    goals: set[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    distances = {start: 0.0}
    previous: dict[tuple[int, int], tuple[int, int]] = {}
    queue: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
    goal: tuple[int, int] | None = None
    while queue:
        distance, node = heapq.heappop(queue)
        if distance > distances[node] + 1e-9:
            continue
        if node in goals:
            goal = node
            break
        for neighbor, weight in adjacency.get(node, []):
            proposal = distance + weight
            if proposal + 1e-9 < distances.get(neighbor, math.inf):
                distances[neighbor] = proposal
                previous[neighbor] = node
                heapq.heappush(queue, (proposal, neighbor))
    if goal is None:
        raise RuntimeError(f"No reachable T node from virtual port {start}")
    result = [goal]
    while result[-1] != start:
        result.append(previous[result[-1]])
    result.reverse()
    return tuple(result)


def projected_point(
    point: tuple[float, float], segment: graph.Segment
) -> tuple[float, float]:
    vx = segment.end[0] - segment.start[0]
    vy = segment.end[1] - segment.start[1]
    length_squared = vx * vx + vy * vy
    if length_squared < 1e-12:
        return segment.start
    parameter = (
        (point[0] - segment.start[0]) * vx
        + (point[1] - segment.start[1]) * vy
    ) / length_squared
    parameter = max(0.0, min(1.0, parameter))
    return (
        segment.start[0] + parameter * vx,
        segment.start[1] + parameter * vy,
    )


def build_virtual_equipment_edges(
    segments: list[graph.Segment],
    tees: list[graph.TeeNode],
    virtual_nodes: list[VirtualEquipmentNode],
    layout: graph.DrawingLayout,
) -> tuple[list[LogicalEdge], list[VirtualPortBinding]]:
    """Connect every virtual port to the first T reached along its pipe.

    Most ports already belong to a one-T dangling component.  A small subset is
    separated from the main pipe by drafting gaps.  Single-port gaps are healed
    to the nearest T-containing pipe projection; multiport gaps use a one-to-one
    minimum-cost terminal assignment so dense parallel circuits keep their order.
    """
    ids = node_ids(tees)
    edges: list[LogicalEdge] = []
    bindings: list[VirtualPortBinding] = []

    for system in ("supply", "return"):
        system_segments = [item for item in segments if item.system == system]
        system_tees = [item for item in tees if item.system == system]
        tee_by_key = {
            graph.point_key((item.x, item.y), graph.ENDPOINT_QUANTUM): item
            for item in system_tees
        }
        tee_keys = set(tee_by_key)
        adjacency, points = equipment_graph.build_owner_network(
            system_segments, system_tees
        )
        component_by_key, keys_by_component = connected_components(adjacency)
        tee_components = {
            component_by_key[key] for key in tee_keys if key in component_by_key
        }
        ports_by_node = {
            node.node_id: [port for port in node.ports if port.system == system]
            for node in virtual_nodes
        }
        bridge_by_port: dict[
            str, tuple[tuple[float, float], tuple[float, float], str]
        ] = {}

        for node in virtual_nodes:
            unresolved: list[
                tuple[VirtualPort, tuple[int, int], tuple[float, float]]
            ] = []
            for port in ports_by_node[node.node_id]:
                port_key = graph.point_key(
                    (port.x, port.y), graph.ENDPOINT_QUANTUM
                )
                component = component_by_key.get(port_key)
                if component is None:
                    raise RuntimeError(f"Virtual port absent from pipe graph: {port}")
                if component in tee_components:
                    continue
                terminal_keys = [
                    key
                    for key in keys_by_component[component]
                    if len(adjacency[key]) == 1 and key != port_key
                ]
                if not terminal_keys:
                    raise RuntimeError(
                        f"No far terminal for isolated virtual port {port.port_id}"
                    )
                far_key = max(
                    terminal_keys,
                    key=lambda key: math.dist(points[port_key], points[key]),
                )
                unresolved.append((port, far_key, points[far_key]))

            if not unresolved:
                continue
            if len(unresolved) == 1:
                port, _, far_point = unresolved[0]
                eligible_segments = [
                    segment
                    for segment in system_segments
                    if component_by_key.get(
                        graph.point_key(
                            segment.start, graph.ENDPOINT_QUANTUM
                        )
                    )
                    in tee_components
                ]
                target = min(
                    (projected_point(far_point, segment) for segment in eligible_segments),
                    key=lambda point: math.dist(far_point, point),
                )
                distance = math.dist(far_point, target)
                if distance > VIRTUAL_PORT_BRIDGE_LIMIT:
                    raise RuntimeError(
                        f"Virtual port bridge too long for {port.port_id}: {distance:.3f}"
                    )
                bridge_by_port[port.port_id] = (
                    far_point,
                    target,
                    "standalone_omission_healed_to_pipe",
                )
                continue

            reachable_terminals = [
                key
                for key, neighbors in adjacency.items()
                if len(neighbors) == 1
                and component_by_key.get(key) in tee_components
            ]
            candidate_keys = sorted(
                {
                    key
                    for _, _, far_point in unresolved
                    for _, key in sorted(
                        (
                            (math.dist(far_point, points[key]), key)
                            for key in reachable_terminals
                        ),
                        key=lambda item: item[0],
                    )[:8]
                }
            )
            best: tuple[float, tuple[tuple[int, int], ...]] | None = None
            for assignment in itertools.permutations(
                candidate_keys, len(unresolved)
            ):
                cost = sum(
                    math.dist(far_point, points[target_key])
                    for (_, _, far_point), target_key in zip(
                        unresolved, assignment
                    )
                )
                if best is None or cost < best[0]:
                    best = (cost, assignment)
            if best is None:
                raise RuntimeError(
                    f"No ordered continuation candidates for {node.node_id} {system}"
                )
            for (port, _, far_point), target_key in zip(
                unresolved, best[1]
            ):
                target = points[target_key]
                distance = math.dist(far_point, target)
                if distance > VIRTUAL_PORT_BRIDGE_LIMIT:
                    raise RuntimeError(
                        f"Virtual multiport bridge too long for {port.port_id}: "
                        f"{distance:.3f}"
                    )
                bridge_by_port[port.port_id] = (
                    far_point,
                    target,
                    "standalone_multiport_omission_stitched_by_order",
                )

        augmented_segments = list(system_segments)
        augmented_segments.extend(
            graph.Segment(system, start, end)
            for start, end, _ in bridge_by_port.values()
            if math.dist(start, end) > 1e-6
        )
        augmented_adjacency, augmented_points = (
            equipment_graph.build_owner_network(
                augmented_segments, system_tees
            )
        )

        for node in virtual_nodes:
            for port in ports_by_node[node.node_id]:
                port_key = graph.point_key(
                    (port.x, port.y), graph.ENDPOINT_QUANTUM
                )
                keys = shortest_path_to_any(
                    augmented_adjacency, port_key, tee_keys
                )
                tee_key = keys[-1]
                tee = tee_by_key[tee_key]
                tee_id = ids[(system, tee_key)]
                port_to_tee = tuple(augmented_points[key] for key in keys)
                node_point = (node.x, node.y)
                if system == "supply":
                    path = tuple(reversed(port_to_tee))
                    if math.dist(path[-1], node_point) > 1e-6:
                        path = (*path, node_point)
                    start_id, end_id = tee_id, node.node_id
                    start_point, end_point = (tee.x, tee.y), node_point
                    start_port_id, end_port_id = None, port.port_id
                else:
                    path = port_to_tee
                    if math.dist(path[0], node_point) > 1e-6:
                        path = (node_point, *path)
                    start_id, end_id = node.node_id, tee_id
                    start_point, end_point = node_point, (tee.x, tee.y)
                    start_port_id, end_port_id = port.port_id, None
                bridge = bridge_by_port.get(port.port_id)
                mode = (
                    bridge[2]
                    if bridge is not None
                    else "standalone_omission_to_first_tee"
                )
                edges.append(
                    LogicalEdge(
                        edge_id="",
                        start_node_id=start_id,
                        end_node_id=end_id,
                        edge_type="tee_to_virtual_equipment",
                        system=system,
                        floor_start=(
                            node.floor
                            if start_id == node.node_id
                            else graph.drawing_band(tee.y, layout)
                        ),
                        floor_end=(
                            node.floor
                            if end_id == node.node_id
                            else graph.drawing_band(tee.y, layout)
                        ),
                        start_x=start_point[0],
                        start_y=start_point[1],
                        end_x=end_point[0],
                        end_y=end_point[1],
                        path_length=path_length(path),
                        path_points=path,
                        attribute_paths=(path,),
                        device_label=node.node_id,
                        source_insert_handle=node.source_marker_handle,
                        connection_mode=mode,
                        start_port_id=start_port_id,
                        end_port_id=end_port_id,
                    )
                )
                bindings.append(
                    VirtualPortBinding(
                        node_id=node.node_id,
                        port_id=port.port_id,
                        system=system,
                        port_x=port.x,
                        port_y=port.y,
                        tee_id=tee_id,
                        tee_x=tee.x,
                        tee_y=tee.y,
                        connection_mode=mode,
                        bridge_start_x=bridge[0][0] if bridge else None,
                        bridge_start_y=bridge[0][1] if bridge else None,
                        bridge_end_x=bridge[1][0] if bridge else None,
                        bridge_end_y=bridge[1][1] if bridge else None,
                        bridge_length=(
                            math.dist(bridge[0], bridge[1]) if bridge else 0.0
                        ),
                        path_length=path_length(path),
                    )
                )
    return edges, bindings


def build_tee_edges(
    segments: list[graph.Segment],
    tees: list[graph.TeeNode],
    layout: graph.DrawingLayout,
) -> list[LogicalEdge]:
    ids = node_ids(tees)
    result: list[LogicalEdge] = []
    signatures: set[tuple[str, str, str]] = set()

    for system in ("supply", "return"):
        system_segments = [segment for segment in segments if segment.system == system]
        system_tees = [tee for tee in tees if tee.system == system]
        adjacency, points = equipment_graph.build_owner_network(
            system_segments, system_tees
        )
        tee_keys = {
            graph.point_key((tee.x, tee.y), graph.ENDPOINT_QUANTUM): tee
            for tee in system_tees
        }

        candidates: list[tuple[tuple[int, int], tuple[int, int], tuple[tuple[int, int], ...]]] = []
        for first_key in tee_keys:
            for second_key, _ in adjacency.get(first_key, []):
                if second_key in tee_keys and first_key < second_key:
                    candidates.append((first_key, second_key, (first_key, second_key)))

        seen: set[tuple[int, int]] = set()
        for start in set(adjacency) - set(tee_keys):
            if start in seen:
                continue
            stack = [start]
            seen.add(start)
            component: set[tuple[int, int]] = set()
            boundaries: set[tuple[int, int]] = set()
            while stack:
                node = stack.pop()
                component.add(node)
                for neighbor, _ in adjacency[node]:
                    if neighbor in tee_keys:
                        boundaries.add(neighbor)
                    elif neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            if len(boundaries) != 2:
                continue
            first_key, second_key = sorted(boundaries)
            allowed = component | boundaries
            keys = shortest_path_keys(
                adjacency, first_key, second_key, allowed=allowed
            )
            candidates.append((first_key, second_key, keys))

        for first_key, second_key, keys in candidates:
            first_id = ids[(system, first_key)]
            second_id = ids[(system, second_key)]
            if second_id < first_id:
                first_id, second_id = second_id, first_id
                first_key, second_key = second_key, first_key
                keys = tuple(reversed(keys))
            signature = (system, first_id, second_id)
            if signature in signatures:
                continue
            signatures.add(signature)
            path = tuple(points[key] for key in keys)
            first_tee = tee_keys[first_key]
            second_tee = tee_keys[second_key]
            result.append(
                LogicalEdge(
                    edge_id="",
                    start_node_id=first_id,
                    end_node_id=second_id,
                    edge_type="tee_to_tee",
                    system=system,
                    floor_start=graph.drawing_band(first_tee.y, layout),
                    floor_end=graph.drawing_band(second_tee.y, layout),
                    start_x=first_tee.x,
                    start_y=first_tee.y,
                    end_x=second_tee.x,
                    end_y=second_tee.y,
                    path_length=path_length(path),
                    path_points=path,
                    attribute_paths=(path,),
                    device_label=None,
                    source_insert_handle=None,
                    connection_mode="continuous_original_cad_pipe",
                )
            )
    return result


def find_terminal_path(
    segments: list[graph.Segment],
    tee: graph.TeeNode,
    device_point: tuple[float, float],
) -> tuple[tuple[float, float], ...]:
    adjacency, points = equipment_graph.build_owner_network(segments, [tee])
    start = graph.point_key((tee.x, tee.y), graph.ENDPOINT_QUANTUM)
    if start not in adjacency:
        raise RuntimeError(f"T point is absent from owner network: {tee}")
    component = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for neighbor, _ in adjacency[node]:
            if neighbor not in component:
                component.add(neighbor)
                stack.append(neighbor)
    terminals = [
        key for key in component if key != start and len(adjacency[key]) == 1
    ]
    if not terminals:
        raise RuntimeError(f"No owner terminal found for {tee}")
    goal = min(terminals, key=lambda key: math.dist(points[key], device_point))
    keys = shortest_path_keys(adjacency, start, goal, allowed=component)
    return tuple(points[key] for key in keys)


def find_remote_omission_path(
    segments: list[graph.Segment],
    marker: equipment_graph.OmissionMarker,
    device_point: tuple[float, float],
) -> tuple[tuple[float, float], ...]:
    adjacency, points = equipment_graph.build_owner_network(segments, [])
    terminals = [key for key in adjacency if len(adjacency[key]) == 1]
    if len(terminals) < 2:
        raise RuntimeError(
            f"No remote omission path for {marker.device_label}"
        )
    marker_point = (marker.equipment_side_x, marker.equipment_side_y)
    start = min(terminals, key=lambda key: math.dist(points[key], marker_point))
    component = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for neighbor, _ in adjacency[node]:
            if neighbor not in component:
                component.add(neighbor)
                stack.append(neighbor)
    goals = [
        key
        for key in component
        if key != start and len(adjacency[key]) == 1
    ]
    if not goals:
        raise RuntimeError(
            f"No device-side terminal for {marker.device_label}"
        )
    goal = min(goals, key=lambda key: math.dist(points[key], device_point))
    keys = shortest_path_keys(adjacency, start, goal, allowed=component)
    return tuple(points[key] for key in keys)


def relation_edges_for_owned_equipment(
    doc,
    original_equipment: list[graph.EquipmentNode],
    placed_equipment: list[graph.EquipmentNode],
    tees: list[graph.TeeNode],
    owned: list[equipment_graph.OwnedEquipment],
    markers: dict[str, equipment_graph.OmissionMarker],
    layout: graph.DrawingLayout,
) -> list[LogicalEdge]:
    provisional = equipment_graph.make_provisional_matches(owned, tees)
    relations, _ = equipment_graph.finalize_matches(owned, provisional)
    owned_by_label = {item.node.label: item for item in owned}
    original_by_label = {item.label: item for item in original_equipment}
    placed_by_label = {item.label: item for item in placed_equipment}
    result: list[LogicalEdge] = []

    for relation in relations:
        owner = owned_by_label[relation.device_label]
        original = original_by_label[relation.device_label]
        placed = placed_by_label[relation.device_label]
        system_segments = [
            segment
            for segment in owner.pipe_segments
            if segment.system == relation.system
        ]
        tee = graph.TeeNode(relation.system, relation.tee_x, relation.tee_y)
        marker = markers.get(relation.device_label)
        if marker is None:
            pipe_path = find_terminal_path(
                system_segments, tee, (original.x, original.y)
            )
            attribute_paths = (pipe_path,)
            mode = "direct_existing_cad_branch"
        else:
            attachment = equipment_graph.branch_attachment(
                owner, marker, relation.system
            )
            adjacency, points = equipment_graph.build_owner_network(
                system_segments, [tee]
            )
            start_key = graph.point_key(
                (tee.x, tee.y), graph.ENDPOINT_QUANTUM
            )
            goal_key = graph.point_key(attachment, graph.ENDPOINT_QUANTUM)
            keys = shortest_path_keys(adjacency, start_key, goal_key)
            pipe_path = tuple(points[key] for key in keys)
            remote_path = find_remote_omission_path(
                system_segments,
                marker,
                (original.x, original.y),
            )
            attribute_paths = (pipe_path, remote_path)
            mode = "omission_pair_stitched_at_main_marker"

        device_point = (placed.x, placed.y)
        if math.dist(pipe_path[-1], device_point) > 1e-6:
            pipe_path = (*pipe_path, device_point)
        if marker is None:
            attribute_paths = (pipe_path,)
        else:
            attribute_paths = (pipe_path, remote_path)
        physical_path_length = sum(
            path_length(part) for part in attribute_paths
        )
        if relation.system == "supply":
            start_id, end_id = relation.tee_id, relation.device_label
            start_point, end_point = (tee.x, tee.y), device_point
            path = pipe_path
        else:
            start_id, end_id = relation.device_label, relation.tee_id
            start_point, end_point = device_point, (tee.x, tee.y)
            path = tuple(reversed(pipe_path))
        result.append(
            LogicalEdge(
                edge_id="",
                start_node_id=start_id,
                end_node_id=end_id,
                edge_type="tee_to_equipment",
                system=relation.system,
                floor_start=(
                    placed.floor
                    if start_id == relation.device_label
                    else graph.drawing_band(tee.y, layout)
                ),
                floor_end=(
                    placed.floor
                    if end_id == relation.device_label
                    else graph.drawing_band(tee.y, layout)
                ),
                start_x=start_point[0],
                start_y=start_point[1],
                end_x=end_point[0],
                end_y=end_point[1],
                path_length=physical_path_length,
                path_points=path,
                attribute_paths=attribute_paths,
                device_label=relation.device_label,
                source_insert_handle=owner.insert_handle,
                connection_mode=mode,
            )
        )
    return result


def collect_dangling_branches(
    segments: list[graph.Segment],
    tees: list[graph.TeeNode],
    system: str,
) -> list[DanglingBranch]:
    system_segments = [segment for segment in segments if segment.system == system]
    system_tees = [tee for tee in tees if tee.system == system]
    adjacency, points = equipment_graph.build_owner_network(
        system_segments, system_tees
    )
    tee_keys = {
        graph.point_key((tee.x, tee.y), graph.ENDPOINT_QUANTUM)
        for tee in system_tees
    }
    result: list[DanglingBranch] = []
    seen: set[tuple[int, int]] = set()
    for start in set(adjacency) - tee_keys:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        component: set[tuple[int, int]] = set()
        boundaries: set[tuple[int, int]] = set()
        while stack:
            node = stack.pop()
            component.add(node)
            for neighbor, _ in adjacency[node]:
                if neighbor in tee_keys:
                    boundaries.add(neighbor)
                elif neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        if len(boundaries) != 1:
            continue
        terminal_keys = [key for key in component if len(adjacency[key]) == 1]
        if len(terminal_keys) != 1:
            continue
        tee_key = next(iter(boundaries))
        terminal_key = terminal_keys[0]
        allowed = component | {tee_key}
        keys = shortest_path_keys(
            adjacency, tee_key, terminal_key, allowed=allowed
        )
        result.append(
            DanglingBranch(
                system=system,
                tee_key=tee_key,
                terminal_key=terminal_key,
                path_keys=keys,
                points=points,
            )
        )
    return result


def bridge_inline_metal_hose_gaps(
    segments: list[graph.Segment],
    tees: list[graph.TeeNode],
    insert_components: list[ComponentInstance],
) -> tuple[list[graph.Segment], list[InlineGapBridge]]:
    """Heal collinear pipe breaks caused by inline metal-hose graphics.

    These breaks are not physical graph endpoints: the metal hose remains an
    edge attribute.  A bridge is accepted only when both one-T branch terminals
    are close to a metal-hose symbol, face one another on the same axis, and are
    within the drawing-specific gap limit.
    """
    hose_points = [
        (item.assignment_x, item.assignment_y)
        for item in insert_components
        if item.equipment_type == "金属软接" and item.owner_equipment is None
    ]
    if not hose_points:
        return list(segments), []

    result = list(segments)
    bridges: list[InlineGapBridge] = []
    for system in ("supply", "return"):
        candidates: list[DanglingBranch] = []
        for branch in collect_dangling_branches(segments, tees, system):
            terminal = branch.points[branch.terminal_key]
            if min(math.dist(terminal, point) for point in hose_points) <= (
                INLINE_HOSE_TERMINAL_TOLERANCE
            ):
                candidates.append(branch)

        pairs: list[tuple[float, int, int]] = []
        for first_index, first in enumerate(candidates):
            first_terminal = first.points[first.terminal_key]
            first_inside = first.points[first.path_keys[-2]]
            for second_index in range(first_index + 1, len(candidates)):
                second = candidates[second_index]
                second_terminal = second.points[second.terminal_key]
                gap_length = math.dist(first_terminal, second_terminal)
                if gap_length > INLINE_HOSE_GAP_LIMIT:
                    continue
                second_inside = second.points[second.path_keys[-2]]
                gap = (
                    second_terminal[0] - first_terminal[0],
                    second_terminal[1] - first_terminal[1],
                )
                first_inward = (
                    first_inside[0] - first_terminal[0],
                    first_inside[1] - first_terminal[1],
                )
                second_inward = (
                    second_inside[0] - second_terminal[0],
                    second_inside[1] - second_terminal[1],
                )

                def cosine(
                    first_vector: tuple[float, float],
                    second_vector: tuple[float, float],
                ) -> float:
                    return (
                        first_vector[0] * second_vector[0]
                        + first_vector[1] * second_vector[1]
                    ) / (
                        math.hypot(*first_vector)
                        * math.hypot(*second_vector)
                    )

                if cosine(first_inward, gap) > (
                    INLINE_HOSE_OPPOSING_COSINE_LIMIT
                ):
                    continue
                reverse_gap = (-gap[0], -gap[1])
                if cosine(second_inward, reverse_gap) > (
                    INLINE_HOSE_OPPOSING_COSINE_LIMIT
                ):
                    continue
                pairs.append((gap_length, first_index, second_index))

        used: set[int] = set()
        for gap_length, first_index, second_index in sorted(pairs):
            if first_index in used or second_index in used:
                continue
            first_terminal = candidates[first_index].points[
                candidates[first_index].terminal_key
            ]
            second_terminal = candidates[second_index].points[
                candidates[second_index].terminal_key
            ]
            result.append(
                graph.Segment(system, first_terminal, second_terminal)
            )
            bridges.append(
                InlineGapBridge(
                    system=system,
                    start_x=first_terminal[0],
                    start_y=first_terminal[1],
                    end_x=second_terminal[0],
                    end_y=second_terminal[1],
                    length=gap_length,
                    connection_mode="inline_metal_hose_gap_healed",
                )
            )
            used.update({first_index, second_index})
    return result, bridges


def minimum_cost_assignment(
    equipment: list[graph.EquipmentNode],
    branches: list[DanglingBranch],
) -> dict[str, DanglingBranch]:
    nearest_indexes = sorted(
        {
            index
            for item in equipment
            for _, index in sorted(
                (
                    (
                        math.dist(
                            (item.x, item.y),
                            branch.points[branch.terminal_key],
                        ),
                        index,
                    )
                    for index, branch in enumerate(branches)
                )
            )[:6]
        }
    )
    candidates = [branches[index] for index in nearest_indexes]
    if len(candidates) < len(equipment):
        raise RuntimeError("Insufficient dangling branches for direct equipment")

    costs = tuple(
        tuple(
            math.dist(
                (item.x, item.y),
                branch.points[branch.terminal_key],
            )
            for branch in candidates
        )
        for item in equipment
    )

    @lru_cache(maxsize=None)
    def solve(
        item_index: int, used_indexes: tuple[int, ...]
    ) -> tuple[float, tuple[int, ...]]:
        if item_index == len(equipment):
            return 0.0, ()
        used = set(used_indexes)
        used_tees = {candidates[index].tee_key for index in used}
        best_cost = math.inf
        best_indexes: tuple[int, ...] = ()
        for index, branch in enumerate(candidates):
            if index in used or branch.tee_key in used_tees:
                continue
            tail_cost, tail_indexes = solve(
                item_index + 1, tuple(sorted((*used, index)))
            )
            total = costs[item_index][index] + tail_cost
            if total < best_cost:
                best_cost = total
                best_indexes = (index, *tail_indexes)
        return best_cost, best_indexes

    _, best = solve(0, ())
    if len(best) != len(equipment):
        raise RuntimeError("No one-to-one direct-equipment branch assignment")
    return {
        item.label: candidates[index]
        for item, index in zip(equipment, best)
    }


def relation_edges_for_exploded_equipment(
    segments: list[graph.Segment],
    tees: list[graph.TeeNode],
    direct: list[graph.EquipmentNode],
    layout: graph.DrawingLayout,
) -> list[LogicalEdge]:
    ids = node_ids(tees)
    tee_by_key = {
        (
            tee.system,
            graph.point_key((tee.x, tee.y), graph.ENDPOINT_QUANTUM),
        ): tee
        for tee in tees
    }
    result: list[LogicalEdge] = []
    for system in ("supply", "return"):
        branches = collect_dangling_branches(segments, tees, system)
        assignments = minimum_cost_assignment(direct, branches)
        for item in direct:
            branch = assignments[item.label]
            tee = tee_by_key[(system, branch.tee_key)]
            tee_id = ids[(system, branch.tee_key)]
            pipe_path = tuple(branch.points[key] for key in branch.path_keys)
            device_point = (item.x, item.y)
            if math.dist(pipe_path[-1], device_point) > 1e-6:
                pipe_path = (*pipe_path, device_point)
            if system == "supply":
                start_id, end_id = tee_id, item.label
                start_point, end_point = (tee.x, tee.y), device_point
                path = pipe_path
            else:
                start_id, end_id = item.label, tee_id
                start_point, end_point = device_point, (tee.x, tee.y)
                path = tuple(reversed(pipe_path))
            result.append(
                LogicalEdge(
                    edge_id="",
                    start_node_id=start_id,
                    end_node_id=end_id,
                    edge_type="tee_to_equipment",
                    system=system,
                    floor_start=(
                        item.floor
                        if start_id == item.label
                        else graph.drawing_band(tee.y, layout)
                    ),
                    floor_end=(
                        item.floor
                        if end_id == item.label
                        else graph.drawing_band(tee.y, layout)
                    ),
                    start_x=start_point[0],
                    start_y=start_point[1],
                    end_x=end_point[0],
                    end_y=end_point[1],
                    path_length=path_length(path),
                    path_points=path,
                    attribute_paths=(pipe_path,),
                    device_label=item.label,
                    source_insert_handle=None,
                    connection_mode="direct_exploded_existing_cad_branch",
                )
            )
    return result


def number_edges(edges: list[LogicalEdge]) -> list[LogicalEdge]:
    if PREVIOUS_GRAPH:
        result=[];used=set();next_id=max(int(e['edge_id'][1:])for e in PREVIOUS_GRAPH['edges'])+1
        for edge in edges:
            exact=[e for e in PREVIOUS_GRAPH['edges']if e['system']==edge.system and {e['start_node_id'],e['end_node_id']}=={edge.start_node_id,edge.end_node_id}]
            if not exact and edge.edge_type=='tee_to_equipment':exact=[e for e in PREVIOUS_GRAPH['edges']if e['system']==edge.system and e['edge_type']=='tee_to_equipment'and e.get('device_label')==edge.device_label]
            if len(exact)==1 and exact[0]['edge_id']not in used:eid=exact[0]['edge_id']
            else:eid=f'E{next_id:04d}';next_id+=1
            used.add(eid);result.append(replace(edge,edge_id=eid))
        return sorted(result,key=lambda e:e.edge_id)
    ordered = sorted(
        edges,
        key=lambda edge: (
            edge.floor_start,
            edge.floor_end,
            edge.system,
            edge.edge_type,
            edge.start_y,
            edge.start_x,
            edge.end_y,
            edge.end_x,
            edge.start_port_id or "",
            edge.end_port_id or "",
        ),
    )
    return [replace(edge, edge_id=f"E{index:04d}") for index, edge in enumerate(ordered, 1)]


def point_to_path_distance(
    point: tuple[float, float], path: tuple[tuple[float, float], ...]
) -> float:
    if len(path) == 1:
        return math.dist(point, path[0])
    return min(
        equipment_graph.point_to_segment_distance(point, first, second)
        for first, second in zip(path, path[1:])
    )


def point_to_edge_attribute_distance(
    point: tuple[float, float], edge: LogicalEdge
) -> float:
    return min(
        point_to_path_distance(point, part) for part in edge.attribute_paths
    )


def point_is_in_graph_scope(
    point: tuple[float, float], layout: graph.DrawingLayout
) -> bool:
    x, y = point
    if not (
        layout.plot_x_min <= x <= layout.plot_x_max
        and layout.plot_y_min <= y <= layout.plot_y_max
    ):
        return False
    if graph.is_excluded_detail_point(x, y, layout) or (
        x > layout.right_detail_x_min and y < layout.right_detail_y_max
    ):
        return False
    legend_x_min, legend_x_max, legend_y_min, legend_y_max = (
        BOTTOM_PIPE_LEGEND_CANONICAL_BOUNDS
    )
    return not (
        legend_x_min + layout.offset_x
        <= x
        <= legend_x_max + layout.offset_x
        and legend_y_min + layout.offset_y
        <= y
        <= legend_y_max + layout.offset_y
    )


def collect_insert_instances(
    doc,
    owned: list[equipment_graph.OwnedEquipment],
    layout: graph.DrawingLayout,
) -> list[ComponentInstance]:
    owner_by_handle = {item.insert_handle: item.node.label for item in owned}
    raw: list[ComponentInstance] = []
    for top in doc.modelspace().query("INSERT"):
        top_handle = str(top.dxf.handle)
        owner = owner_by_handle.get(top_handle)
        for insert in graph.recursive_inserts(top):
            mapping = COMPONENT_BLOCK_TYPES.get(insert.dxf.name)
            if mapping is None:
                continue
            equipment_type, type_code = mapping
            point = (float(insert.dxf.insert.x), float(insert.dxf.insert.y))
            if not point_is_in_graph_scope(point, layout):
                continue
            raw.append(
                ComponentInstance(
                    device_name="",
                    equipment_type=equipment_type,
                    type_code=type_code,
                    x=point[0],
                    y=point[1],
                    assignment_x=point[0],
                    assignment_y=point[1],
                    source_kind="block_insert",
                    source_block_name=insert.dxf.name,
                    source_top_handle=top_handle,
                    owner_equipment=owner,
                    system_hint=None,
                )
            )
    unique: dict[tuple, ComponentInstance] = {}
    for item in raw:
        key = (
            item.source_block_name,
            round(item.x, 3),
            round(item.y, 3),
            item.owner_equipment,
        )
        unique.setdefault(key, item)
    return list(unique.values())


def collect_exploded_ball_valve_instances(
    doc, layout: graph.DrawingLayout
) -> list[ComponentInstance]:
    """Recover ball valves whose INSERT blocks were exploded into primitives.

    In the two stair-step pipe groups, LibreDWG exposes each ball valve as a
    yellow center HATCH, two ELLIPSE halves and three surrounding LINEs rather
    than as an ``H-PICPNT-91`` INSERT.  The center fill is the most selective
    anchor; the ellipse and line checks prevent unrelated yellow hatches from
    being promoted to edge-device instances.
    """

    hatches: list[tuple[object, str | None]] = []
    ellipse_centers: list[tuple[float, float]] = []
    yellow_lines: list[tuple[tuple[float, float], float]] = []

    for top in doc.modelspace():
        top_handle = str(top.dxf.handle) if top.dxf.handle is not None else None
        for entity in graph.recursive_entities(top):
            if int(entity.dxf.get("color", 256)) != 2:
                continue
            entity_type = entity.dxftype()
            if entity_type == "HATCH":
                hatches.append((entity, top_handle))
            elif entity_type == "ELLIPSE":
                ellipse_centers.append(
                    (float(entity.dxf.center.x), float(entity.dxf.center.y))
                )
            elif entity_type == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                midpoint = (
                    (float(start.x) + float(end.x)) / 2.0,
                    (float(start.y) + float(end.y)) / 2.0,
                )
                yellow_lines.append(
                    (
                        midpoint,
                        math.dist(
                            (float(start.x), float(start.y)),
                            (float(end.x), float(end.y)),
                        ),
                    )
                )

    detected: dict[tuple[int, int], ComponentInstance] = {}
    for hatch, top_handle in hatches:
        bounds = bbox.extents([hatch], fast=True)
        if not bounds.has_data:
            continue
        width = float(bounds.extmax.x - bounds.extmin.x)
        height = float(bounds.extmax.y - bounds.extmin.y)
        center_size = max(width, height)
        if not (
            EXPLODED_BALL_VALVE_CENTER_MIN_SIZE
            <= center_size
            <= EXPLODED_BALL_VALVE_CENTER_MAX_SIZE
        ):
            continue
        if min(width, height) / center_size < 0.8:
            continue
        point = (
            float((bounds.extmin.x + bounds.extmax.x) / 2.0),
            float((bounds.extmin.y + bounds.extmax.y) / 2.0),
        )
        if not point_is_in_graph_scope(point, layout):
            continue

        ellipse_count = sum(
            math.dist(point, candidate) <= center_size
            for candidate in ellipse_centers
        )
        line_count = sum(
            math.dist(point, midpoint)
            <= center_size * EXPLODED_BALL_VALVE_LINE_SEARCH_FACTOR
            and center_size * EXPLODED_BALL_VALVE_LINE_LENGTH_MIN_FACTOR
            <= length
            <= center_size * EXPLODED_BALL_VALVE_LINE_LENGTH_MAX_FACTOR
            for midpoint, length in yellow_lines
        )
        if ellipse_count != 2 or line_count != 3:
            continue

        key = graph.point_key(point, 1.0)
        detected.setdefault(
            key,
            ComponentInstance(
                device_name="",
                equipment_type="球阀",
                type_code="BV",
                x=point[0],
                y=point[1],
                assignment_x=point[0],
                assignment_y=point[1],
                source_kind="exploded_geometry",
                source_block_name="EXPLODED:H-PICPNT-91",
                source_top_handle=top_handle,
                owner_equipment=None,
                system_hint=None,
            ),
        )
    return list(detected.values())


def semantic_components(
    inserts: list[ComponentInstance],
    valve_removals: list[graph.ValveStubRemoval],
    air_vent_removals: list[graph.AirVentLegRemoval],
) -> list[ComponentInstance]:
    regular = [item for item in inserts if item.equipment_type != "蝶阀"]
    butterfly_inserts = [item for item in inserts if item.equipment_type == "蝶阀"]
    unused = set(range(len(butterfly_inserts)))
    for removal in valve_removals:
        if not unused:
            raise RuntimeError("Missing butterfly-valve INSERT for a removed stub")
        index = min(
            unused,
            key=lambda value: math.dist(
                (butterfly_inserts[value].x, butterfly_inserts[value].y),
                removal.valve_port,
            ),
        )
        unused.remove(index)
        source = butterfly_inserts[index]
        regular.append(
            replace(
                source,
                assignment_x=removal.junction[0],
                assignment_y=removal.junction[1],
                source_kind="turn_display_valve_folded_to_elbow",
                system_hint=removal.system,
            )
        )
    if unused:
        raise RuntimeError(f"Unmatched butterfly-valve INSERTs: {len(unused)}")
    for removal in air_vent_removals:
        regular.append(
            ComponentInstance(
                device_name="",
                equipment_type="自动放气阀",
                type_code="AAV",
                x=removal.vent_port[0],
                y=removal.vent_port[1],
                assignment_x=removal.junction[0],
                assignment_y=removal.junction[1],
                source_kind=f"semantic_attdef_folded_{removal.action}",
                source_block_name="ATTDEF:WHAT=自动放气阀",
                source_top_handle=None,
                owner_equipment=None,
                system_hint=removal.system,
            )
        )
    return regular


def assign_components(
    components: list[ComponentInstance], edges: list[LogicalEdge]
) -> list[ComponentInstance]:
    assigned: list[ComponentInstance] = []
    for item in components:
        candidates = edges
        if item.owner_equipment is not None:
            candidates = [
                edge for edge in candidates if edge.device_label == item.owner_equipment
            ]
        if item.system_hint is not None:
            candidates = [
                edge for edge in candidates if edge.system == item.system_hint
            ]
        if not candidates:
            assigned.append(replace(item, assignment_status="unassigned_no_candidate"))
            continue
        point = (item.assignment_x, item.assignment_y)
        edge = min(
            candidates,
            key=lambda value: (
                point_to_edge_attribute_distance(point, value),
                value.edge_id,
            ),
        )
        distance = point_to_edge_attribute_distance(point, edge)
        if distance <= MAX_COMPONENT_TO_EDGE_DISTANCE:
            status = "assigned"
        elif item.owner_equipment is None:
            status = "outside_current_node_graph_no_two_node_edge"
        else:
            status = "unassigned_too_far"
        assigned.append(
            replace(
                item,
                owner_equipment=(
                    item.owner_equipment
                    or (
                        edge.device_label
                        if status == "assigned"
                        and edge.edge_type
                        in {"tee_to_equipment", "tee_to_virtual_equipment"}
                        else None
                    )
                ),
                edge_id=edge.edge_id if status == "assigned" else None,
                edge_distance=distance,
                assignment_status=status,
            )
        )

    counters: Counter[tuple[str | None, str]] = Counter()
    named: list[ComponentInstance] = []
    for item in sorted(
        assigned,
        key=lambda value: (
            value.owner_equipment or "",
            value.equipment_type,
            value.y,
            value.x,
        ),
    ):
        key = (item.owner_equipment, item.equipment_type)
        counters[key] += 1
        if item.owner_equipment:
            name = (
                f"{item.owner_equipment}/{item.equipment_type}-"
                f"{counters[key]:02d}"
            )
        else:
            name = f"{item.equipment_type}-{item.type_code}{counters[key]:04d}"
        named.append(replace(item, device_name=name))
    return named


def build_inventory(
    edges: list[LogicalEdge], components: list[ComponentInstance]
) -> list[EdgeInventory]:
    edge_by_id = {edge.edge_id: edge for edge in edges}
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for item in components:
        if item.edge_id is not None:
            grouped[(item.edge_id, item.equipment_type)].append(item.device_name)
    rows = []
    for (edge_id, equipment_type), names in sorted(grouped.items()):
        edge = edge_by_id[edge_id]
        rows.append(
            EdgeInventory(
                edge_id=edge_id,
                start_node_id=edge.start_node_id,
                end_node_id=edge.end_node_id,
                equipment_type=equipment_type,
                device_count=len(names),
                device_names=";".join(sorted(names)),
            )
        )
    return rows


def write_csv(path: Path, records: Iterable[dict]) -> None:
    rows = list(records)
    if not rows:
        raise RuntimeError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def edge_rows(
    edges: list[LogicalEdge], inventory: list[EdgeInventory]
) -> list[dict]:
    by_edge: dict[str, list[dict]] = defaultdict(list)
    for item in inventory:
        by_edge[item.edge_id].append(
            {
                "equipment_type": item.equipment_type,
                "count": item.device_count,
                "device_names": item.device_names.split(";"),
            }
        )
    rows = []
    for edge in edges:
        items = sorted(
            by_edge[edge.edge_id], key=lambda value: value["equipment_type"]
        )
        rows.append(
            {
                "edge_id": edge.edge_id,
                "start_node_id": edge.start_node_id,
                "end_node_id": edge.end_node_id,
                "start_port_id": edge.start_port_id or "",
                "end_port_id": edge.end_port_id or "",
                "edge_type": edge.edge_type,
                "system": edge.system,
                "floor_start": edge.floor_start,
                "floor_end": edge.floor_end,
                "start_x": f"{edge.start_x:.3f}",
                "start_y": f"{edge.start_y:.3f}",
                "end_x": f"{edge.end_x:.3f}",
                "end_y": f"{edge.end_y:.3f}",
                "path_length": f"{edge.path_length:.3f}",
                "equipment_type_count": len(items),
                "equipment_total_count": sum(item["count"] for item in items),
                "equipment_inventory": json.dumps(items, ensure_ascii=False),
                "connection_mode": edge.connection_mode,
            }
        )
    return rows


def component_rows(components: list[ComponentInstance]) -> list[dict]:
    return [asdict(item) for item in components]


def inventory_rows(inventory: list[EdgeInventory]) -> list[dict]:
    return [asdict(item) for item in inventory]


def topology_node_rows(
    placed_equipment: list[graph.EquipmentNode],
    virtual_equipment: list[VirtualEquipmentNode],
    tees: list[graph.TeeNode],
    layout: graph.DrawingLayout,
) -> list[dict]:
    rows = [
        {
            "node_id": item.label,
            "node_type": "equipment",
            "subtype": "CRAH",
            "floor": item.floor,
            "label": item.label,
            "x": f"{item.x:.3f}",
            "y": f"{item.y:.3f}",
            "placement_rule": item.source,
            "semantic_status": "resolved",
            "source_handle": "",
            "port_count": 2,
        }
        for item in placed_equipment
    ]
    rows.extend(
        {
            "node_id": item.node_id,
            "node_type": "virtual_equipment",
            "subtype": "external_system_interface",
            "floor": item.floor,
            "label": item.label,
            "x": f"{item.x:.3f}",
            "y": f"{item.y:.3f}",
            "placement_rule": "unowned_standalone_DIM_SYMB_center",
            "semantic_status": "unresolved",
            "source_handle": item.source_marker_handle,
            "port_count": len(item.ports),
        }
        for item in virtual_equipment
    )
    rows.extend(
        {
            "node_id": node_ids(tees)[(item.system,graph.point_key((item.x,item.y),graph.ENDPOINT_QUANTUM))],
            "node_type": "physical_junction",
            "subtype": f"tee_{item.system}",
            "floor": graph.drawing_band(item.y, layout),
            "label": "",
            "x": f"{item.x:.3f}",
            "y": f"{item.y:.3f}",
            "placement_rule": "preprocessed_three_ray_tee",
            "semantic_status": "not_applicable",
            "source_handle": "",
            "port_count": 0,
        }
        for index, item in enumerate(tees, 1)
    )
    return rows


def virtual_node_rows(nodes: list[VirtualEquipmentNode]) -> list[dict]:
    return [
        {
            "node_id": item.node_id,
            "label": item.label,
            "node_type": "virtual_equipment",
            "subtype": "external_system_interface",
            "semantic_status": "unresolved",
            "floor": item.floor,
            "x": f"{item.x:.3f}",
            "y": f"{item.y:.3f}",
            "source_marker_handle": item.source_marker_handle,
            "supply_port_count": sum(
                port.system == "supply" for port in item.ports
            ),
            "return_port_count": sum(
                port.system == "return" for port in item.ports
            ),
            "port_ids": ";".join(port.port_id for port in item.ports),
        }
        for item in nodes
    ]


def virtual_port_rows(
    nodes: list[VirtualEquipmentNode],
    bindings: list[VirtualPortBinding],
) -> list[dict]:
    binding_by_port = {item.port_id: item for item in bindings}
    rows: list[dict] = []
    for node in nodes:
        for port in node.ports:
            binding = binding_by_port[port.port_id]
            rows.append(
                {
                    "node_id": node.node_id,
                    "port_id": port.port_id,
                    "system": port.system,
                    "sequence": port.sequence,
                    "port_x": f"{port.x:.3f}",
                    "port_y": f"{port.y:.3f}",
                    "source_marker_handle": port.source_marker_handle,
                    "tee_id": binding.tee_id,
                    "tee_x": f"{binding.tee_x:.3f}",
                    "tee_y": f"{binding.tee_y:.3f}",
                    "connection_mode": binding.connection_mode,
                    "bridge_length": f"{binding.bridge_length:.3f}",
                    "path_length": f"{binding.path_length:.3f}",
                }
            )
    return rows


def node_payload(
    placed_equipment: list[graph.EquipmentNode],
    virtual_equipment: list[VirtualEquipmentNode],
    tees: list[graph.TeeNode],
    edges: list[LogicalEdge],
    inventory: list[EdgeInventory],
    layout: graph.DrawingLayout,
) -> dict:
    nodes = [
        {
            "node_id": item.label,
            "node_type": "equipment",
            "subtype": "CRAH",
            "floor": item.floor,
            "label": item.label,
            "x": item.x,
            "y": item.y,
            "placement_rule": item.source,
        }
        for item in placed_equipment
    ]
    nodes.extend(
        {
            "node_id": item.node_id,
            "node_type": "virtual_equipment",
            "subtype": "external_system_interface",
            "semantic_status": "unresolved",
            "floor": item.floor,
            "label": item.label,
            "x": item.x,
            "y": item.y,
            "placement_rule": "unowned_standalone_DIM_SYMB_center",
            "source_marker_handle": item.source_marker_handle,
            "ports": [asdict(port) for port in item.ports],
        }
        for item in virtual_equipment
    )
    nodes.extend(
        {
            "node_id": node_ids(tees)[(item.system,graph.point_key((item.x,item.y),graph.ENDPOINT_QUANTUM))],
            "node_type": "physical_junction",
            "subtype": f"tee_{item.system}",
            "floor": graph.drawing_band(item.y, layout),
            "label": "",
            "x": item.x,
            "y": item.y,
            "placement_rule": "preprocessed_three_ray_tee",
        }
        for index, item in enumerate(tees, 1)
    )
    by_edge: dict[str, list[dict]] = defaultdict(list)
    for item in inventory:
        by_edge[item.edge_id].append(
            {
                "equipment_type": item.equipment_type,
                "count": item.device_count,
                "device_names": item.device_names.split(";"),
            }
        )
    payload_edges = []
    for edge in edges:
        payload_edges.append(
            {
                **asdict(edge),
                "path_points": [list(point) for point in edge.path_points],
                "equipment_inventory": sorted(
                    by_edge[edge.edge_id],
                    key=lambda value: value["equipment_type"],
                ),
            }
        )
    return {
        "metadata": {
            "scope": "adjacent-node physical edges with inline-device attributes",
            "node_count": len(nodes),
            "equipment_node_count": len(placed_equipment),
            "virtual_equipment_node_count": len(virtual_equipment),
            "virtual_equipment_port_count": sum(
                len(item.ports) for item in virtual_equipment
            ),
            "tee_node_count": len(tees),
            "edge_count": len(edges),
            "edge_direction_note": (
                "Supply equipment edges are T-to-equipment; return equipment "
                "edges are equipment-to-T. T-to-T edges use deterministic node-ID order."
            ),
        },
        "nodes": nodes,
        "edges": payload_edges,
    }


def write_legend_catalog(
    path: Path, components: list[ComponentInstance]
) -> None:
    counts = Counter(
        item.equipment_type
        for item in components
        if item.assignment_status == "assigned"
    )
    source_blocks: dict[str, set[str]] = defaultdict(set)
    for item in components:
        source_blocks[item.equipment_type].add(item.source_block_name)
    rows = [
        {
            "legend_equipment_type": name,
            "used_in_sh16_edge_graph": "yes" if counts[name] else "no",
            "assigned_instance_count": counts[name],
            "matched_source_symbols": ";".join(sorted(source_blocks[name])),
            "graph_role": "edge_attribute_only",
        }
        for name in LEGEND_EDGE_TYPES
    ]
    write_csv(path, rows)


def save_visualization(
    output_dir: Path,
    segments: list[graph.Segment],
    equipment: list[graph.EquipmentNode],
    virtual_equipment: list[VirtualEquipmentNode],
    tees: list[graph.TeeNode],
    edges: list[LogicalEdge],
    components: list[ComponentInstance],
    layout: graph.DrawingLayout,
) -> None:
    graph.configure_plotting()
    assigned = [item for item in components if item.assignment_status == "assigned"]

    def draw(
        ax,
        floor: int | None = None,
        y_range: tuple[float, float] | None = None,
    ) -> None:
        graph.plot_base_segments(ax, segments, layout, y_range)
        for edge in edges:
            if floor is not None and not (
                edge.floor_start == floor or edge.floor_end == floor
            ):
                continue
            color = {
                "tee_to_tee": "#64748b",
                "tee_to_equipment": "#f59e0b",
                "tee_to_virtual_equipment": "#dc2626",
            }[edge.edge_type]
            ax.plot(
                [point[0] for point in edge.path_points],
                [point[1] for point in edge.path_points],
                color=color,
                linewidth=0.55 if edge.edge_type == "tee_to_tee" else 0.9,
                alpha=0.42,
                zorder=2,
            )
        graph.plot_nodes(ax, equipment, tees, layout, floor=floor)
        virtual_subset = [
            item
            for item in virtual_equipment
            if floor is None or item.floor == floor
        ]
        ax.scatter(
            [item.x for item in virtual_subset],
            [item.y for item in virtual_subset],
            s=28,
            marker="D",
            facecolors="white",
            edgecolors="#dc2626",
            linewidths=0.9,
            zorder=7,
        )
        component_subset = [
            item
            for item in assigned
            if y_range is None or y_range[0] <= item.y <= y_range[1]
        ]
        ball_valves = [
            item for item in component_subset if item.equipment_type == "球阀"
        ]
        other_components = [
            item for item in component_subset if item.equipment_type != "球阀"
        ]
        ax.scatter(
            [item.x for item in other_components],
            [item.y for item in other_components],
            s=3,
            color="#ef4444",
            alpha=0.65,
            zorder=5,
        )
        ax.scatter(
            [item.x for item in ball_valves],
            [item.y for item in ball_valves],
            s=8,
            marker="o",
            facecolors="#fff7ed",
            edgecolors="#b91c1c",
            linewidths=0.4,
            zorder=6,
        )

    fig, ax = plt.subplots(figsize=(20, 13), dpi=220)
    draw(ax)
    ax.set_xlim(layout.plot_x_min, layout.plot_x_max)
    ax.set_ylim(layout.plot_y_min, layout.plot_y_max)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(
        handles=[
            Line2D([0], [0], color="#64748b", lw=2, label="T–T 边"),
            Line2D([0], [0], color="#f59e0b", lw=2, label="T–实体设备边"),
            Line2D([0], [0], color="#dc2626", lw=2, label="T–虚拟设备边"),
            Line2D(
                [0],
                [0],
                marker="D",
                markerfacecolor="white",
                markeredgecolor="#dc2626",
                color="none",
                label="虚拟设备节点（省略符）",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                markerfacecolor="#fff7ed",
                markeredgecolor="#b91c1c",
                color="none",
                label="球阀实例",
            ),
            Line2D(
                [0],
                [0],
                marker=".",
                color="#ef4444",
                lw=0,
                label="其他边设备实例",
            ),
        ],
        loc="upper right",
        frameon=True,
        fontsize=9,
    )
    ax.set_title(
        "SH16 相邻节点边与边设备属性\n"
        f"节点 {len(equipment) + len(virtual_equipment) + len(tees)}"
        f"（实体设备 {len(equipment)} + 虚拟设备 {len(virtual_equipment)} + T {len(tees)}）；"
        f"边 {len(edges)}；边设备实例 {len(assigned)}",
        fontsize=18,
        pad=18,
    )
    fig.savefig(
        output_dir / "edge_graph_overview.png",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)

    floor_ranges = {
        1: (layout.plot_y_min, layout.floor_boundary_1_2),
        2: (layout.floor_boundary_1_2, layout.floor_boundary_2_3),
        3: (layout.floor_boundary_2_3, layout.plot_y_max),
    }
    fig, axes = plt.subplots(3, 1, figsize=(22, 17), dpi=220)
    for ax, floor in zip(axes, (3, 2, 1)):
        y_range = floor_ranges[floor]
        draw(ax, floor=floor, y_range=y_range)
        ax.set_xlim(layout.plot_x_min, layout.plot_x_max)
        ax.set_ylim(*y_range)
        ax.set_aspect("equal")
        ax.axis("off")
        node_count = (
            sum(item.floor == floor for item in equipment)
            + sum(item.floor == floor for item in virtual_equipment)
            + sum(graph.drawing_band(item.y, layout) == floor for item in tees)
        )
        ax.text(
            0.005,
            0.96,
            f"{floor}F：节点 {node_count}，虚拟设备 "
            f"{sum(item.floor == floor for item in virtual_equipment)}",
            transform=ax.transAxes,
            fontsize=11,
            va="top",
        )
    fig.suptitle("SH16 最终拓扑：实体设备、虚拟外部接口与 T 节点", fontsize=18)
    fig.savefig(
        output_dir / "edge_graph_by_floor.png",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


def save_crossover_gap_visualization(
    output_dir: Path,
    raw_segments: list[graph.Segment],
    bridges: list[graph.CrossoverGapBridge],
) -> None:
    if not bridges:
        return
    graph.configure_plotting()
    figure, axes = plt.subplots(
        len(bridges),
        2,
        figsize=(13, 4.2 * len(bridges)),
        dpi=200,
        squeeze=False,
    )
    colors = {"supply": "#d946ef", "return": "#06b6d4"}
    for row, bridge in enumerate(bridges):
        center_x = bridge.crossing_x
        center_y = bridge.crossing_y
        span = max(650.0, bridge.length * 4.0)
        nearby = [
            segment
            for segment in raw_segments
            if max(segment.start[0], segment.end[0]) >= center_x - span
            and min(segment.start[0], segment.end[0]) <= center_x + span
            and max(segment.start[1], segment.end[1]) >= center_y - span
            and min(segment.start[1], segment.end[1]) <= center_y + span
        ]
        for column, title in enumerate(("CAD 原始跨越断口", "拓扑预处理后")):
            axis = axes[row][column]
            for segment in nearby:
                axis.plot(
                    [segment.start[0], segment.end[0]],
                    [segment.start[1], segment.end[1]],
                    color=colors[segment.system],
                    linewidth=1.2,
                )
            axis.scatter(
                [bridge.start_x, bridge.end_x],
                [bridge.start_y, bridge.end_y],
                s=22,
                facecolors="white",
                edgecolors="#dc2626",
                linewidths=1.0,
                zorder=4,
            )
            if column == 1:
                axis.plot(
                    [bridge.start_x, bridge.end_x],
                    [bridge.start_y, bridge.end_y],
                    color="#16a34a",
                    linewidth=2.2,
                    linestyle="--",
                    zorder=3,
                )
                axis.scatter(
                    [bridge.crossing_x],
                    [bridge.crossing_y],
                    marker="x",
                    s=42,
                    color="#334155",
                    linewidths=1.2,
                    zorder=5,
                )
                axis.annotate(
                    "跨越点：不建节点",
                    (bridge.crossing_x, bridge.crossing_y),
                    xytext=(8, 10),
                    textcoords="offset points",
                    fontsize=8,
                    color="#334155",
                )
            axis.set_xlim(center_x - span, center_x + span)
            axis.set_ylim(center_y - span, center_y + span)
            axis.set_aspect("equal")
            axis.axis("off")
            axis.set_title(
                f"{title}（{bridge.system}，断口 {bridge.length:.1f}）",
                fontsize=10,
            )
    figure.suptitle(
        "管道上下叠跨越：仅复联断开的管道，交叉位置不产生 T 节点",
        fontsize=14,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(
        output_dir / "pipe_crossover_gap_before_after.png",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(figure)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not args.table_dxf.exists():
        raise FileNotFoundError(f"Missing converted legend DXF: {args.table_dxf}")

    doc = ezdxf.readfile(args.dxf)
    labels = graph.equipment_labels(doc)
    layout = graph.infer_drawing_layout(labels)

    raw_segments = graph.collect_pipe_segments(doc)
    segments, overshoot_trims = graph.trim_short_dangling_overshoots(raw_segments)
    segments, valve_removals = graph.remove_turn_display_valve_stubs(
        segments, graph.collect_turn_display_valve_regions(doc)
    )
    segments, air_vent_removals = graph.remove_auto_air_vent_display_legs(
        segments, graph.collect_auto_air_vent_ports(doc), layout
    )
    segments, crossover_gap_bridges = graph.bridge_pipe_crossover_gaps(segments)
    original_equipment = graph.detect_equipment_nodes(doc)
    owned, direct = equipment_graph.collect_owned_equipment(doc, original_equipment)
    insert_components = collect_insert_instances(doc, owned, layout)
    exploded_ball_valves = collect_exploded_ball_valve_instances(doc, layout)
    insert_components.extend(exploded_ball_valves)
    initial_tees = graph.detect_tee_nodes(segments, layout)
    segments, inline_gap_bridges = bridge_inline_metal_hose_gaps(
        segments, initial_tees, insert_components
    )
    tees = graph.detect_tee_nodes(segments, layout)
    markers = equipment_graph.collect_omission_markers(doc, owned)
    placed_equipment = equipment_graph.relocate_equipment_nodes(
        original_equipment, markers
    )
    virtual_equipment, virtual_marker_audit = collect_virtual_equipment_nodes(
        doc, segments, layout
    )

    edges = build_tee_edges(segments, tees, layout)
    edges.extend(
        relation_edges_for_owned_equipment(
            doc,
            original_equipment,
            placed_equipment,
            tees,
            owned,
            markers,
            layout,
        )
    )
    edges.extend(
        relation_edges_for_exploded_equipment(
            segments, tees, direct, layout
        )
    )
    virtual_edges, virtual_port_bindings = build_virtual_equipment_edges(
        segments, tees, virtual_equipment, layout
    )
    edges.extend(virtual_edges)
    edges = number_edges(edges)

    components = semantic_components(
        insert_components, valve_removals, air_vent_removals
    )
    components = assign_components(components, edges)
    inventory = build_inventory(edges, components)

    if len(placed_equipment) != 92 or not tees:
        raise RuntimeError("Node baseline changed while building edges")
    if len(exploded_ball_valves) != 90:
        raise RuntimeError(
            "Unexpected exploded ball-valve count: "
            f"{len(exploded_ball_valves)}"
        )
    virtual_port_count = sum(len(item.ports) for item in virtual_equipment)
    if len(virtual_equipment) != 30 or virtual_port_count != 62:
        raise RuntimeError(
            "Unexpected virtual omission topology: "
            f"nodes={len(virtual_equipment)}, ports={virtual_port_count}"
        )
    if len([edge for edge in edges if edge.edge_type == "tee_to_equipment"]) != 184:
        raise RuntimeError("Every equipment node must have one supply and one return edge")
    if len(
        [edge for edge in edges if edge.edge_type == "tee_to_virtual_equipment"]
    ) != virtual_port_count:
        raise RuntimeError("Every virtual equipment port must have one T edge")
    unexpected_unassigned = [
        item
        for item in components
        if item.assignment_status != "assigned"
    ]
    if unexpected_unassigned:
        maximum = max(
            (item.edge_distance or math.inf) for item in unexpected_unassigned
        )
        raise RuntimeError(
            "Unexpected unassigned edge-device instances: "
            f"{len(unexpected_unassigned)}, max distance={maximum}"
        )

    write_csv(args.output_dir / "edges.csv", edge_rows(edges, inventory))
    write_csv(
        args.output_dir / "topology_nodes.csv",
        topology_node_rows(placed_equipment, virtual_equipment, tees, layout),
    )
    write_csv(
        args.output_dir / "virtual_equipment_nodes.csv",
        virtual_node_rows(virtual_equipment),
    )
    write_csv(
        args.output_dir / "virtual_equipment_ports.csv",
        virtual_port_rows(virtual_equipment, virtual_port_bindings),
    )
    write_csv(
        args.output_dir / "virtual_omission_marker_audit.csv",
        [asdict(item) for item in virtual_marker_audit],
    )
    write_csv(
        args.output_dir / "inline_metal_hose_gap_bridges.csv",
        [asdict(item) for item in inline_gap_bridges],
    )
    write_csv(
        args.output_dir / "pipe_crossover_gap_bridges.csv",
        [asdict(item) for item in crossover_gap_bridges],
    )
    write_csv(
        args.output_dir / "edge_equipment_by_type.csv",
        inventory_rows(inventory),
    )
    write_csv(
        args.output_dir / "edge_device_instances.csv",
        component_rows(components),
    )
    boundary_components = [
        item
        for item in components
        if item.assignment_status
        == "outside_current_node_graph_no_two_node_edge"
    ]
    boundary_audit_path = args.output_dir / "boundary_tail_device_audit.csv"
    if boundary_components:
        write_csv(
            boundary_audit_path,
            component_rows(boundary_components),
        )
    elif boundary_audit_path.exists():
        boundary_audit_path.unlink()
    write_legend_catalog(args.output_dir / "legend_edge_type_catalog.csv", components)
    payload = node_payload(
        placed_equipment,
        virtual_equipment,
        tees,
        edges,
        inventory,
        layout,
    )
    (args.output_dir / "graph_with_edges.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    assigned_components = [
        item for item in components if item.assignment_status == "assigned"
    ]
    outside_components = [
        item
        for item in components
        if item.assignment_status
        == "outside_current_node_graph_no_two_node_edge"
    ]
    assigned_counts = Counter(
        item.equipment_type for item in assigned_components
    )
    edge_type_counts = Counter(edge.edge_type for edge in edges)
    system_counts = Counter(edge.system for edge in edges)
    summary = {
        "source_dxf": str(args.dxf),
        "legend_dxf": str(args.table_dxf),
        "nodes": {
            "physical_equipment": len(placed_equipment),
            "virtual_equipment": len(virtual_equipment),
            "virtual_equipment_ports": virtual_port_count,
            "tee": len(tees),
            "total": len(placed_equipment) + len(virtual_equipment) + len(tees),
        },
        "edges": {
            "total": len(edges),
            "by_type": dict(sorted(edge_type_counts.items())),
            "by_system": dict(sorted(system_counts.items())),
            "with_equipment_attributes": len(
                {item.edge_id for item in components if item.edge_id is not None}
            ),
        },
        "edge_device_instances": {
            "detected_in_drawing_scope": len(components),
            "assigned_to_adjacent_node_edges": len(assigned_components),
            "outside_current_node_graph": len(outside_components),
            "by_type": dict(sorted(assigned_counts.items())),
            "outside_current_node_graph_by_type": dict(
                sorted(Counter(item.equipment_type for item in outside_components).items())
            ),
        },
        "preprocessing_reused": {
            "overshoot_trims": len(overshoot_trims),
            "butterfly_display_legs_folded": len(valve_removals),
            "automatic_air_vent_display_legs_folded": len(air_vent_removals),
            "pipe_crossover_gaps_healed_without_junction": len(
                crossover_gap_bridges
            ),
            "inline_metal_hose_gaps_healed": len(inline_gap_bridges),
            "exploded_ball_valves_recovered": len(exploded_ball_valves),
        },
        "virtual_omission_interfaces": {
            "standalone_markers_audited": len(virtual_marker_audit),
            "virtual_nodes_created": len(virtual_equipment),
            "ports_created": virtual_port_count,
            "excluded_detail_markers": sum(
                item.status != "virtual_equipment_created"
                for item in virtual_marker_audit
            ),
            "healed_or_stitched_ports": sum(
                item.bridge_length > 0.0 for item in virtual_port_bindings
            ),
        },
        "validation": {
            "physical_node_baseline_preserved": True,
            "every_physical_equipment_has_supply_and_return_edge": True,
            "every_virtual_port_has_one_adjacent_T_edge": True,
            "no_valve_or_air_vent_promoted_to_node": True,
            "no_pipe_crossover_promoted_to_node": not any(
                math.dist((tee.x, tee.y), (bridge.crossing_x, bridge.crossing_y))
                <= graph.POINT_TOLERANCE
                for tee in tees
                for bridge in crossover_gap_bridges
            ),
            "all_detected_edge_devices_assigned_once": len(outside_components) == 0,
            "unresolved_boundary_tail_devices": len(outside_components),
        },
    }
    (args.output_dir / "edge_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = f"""# SH16 边构建结果

- 实体设备节点 {len(placed_equipment)}，未绑定省略符生成虚拟设备节点 {len(virtual_equipment)}，T 节点 {len(tees)}，合计 {len(placed_equipment) + len(virtual_equipment) + len(tees)}。
- 虚拟设备端口 {virtual_port_count} 个，全部接到沿管路首先到达的 T 节点；其中 {sum(item.bridge_length > 0.0 for item in virtual_port_bindings)} 个端口使用断口愈合或多管顺序拼接。
- 相邻节点边：{len(edges)} 条，其中 T–T 边 {edge_type_counts['tee_to_tee']} 条，T–实体设备边 {edge_type_counts['tee_to_equipment']} 条，T–虚拟设备边 {edge_type_counts['tee_to_virtual_equipment']} 条。
- 供水边 {system_counts['supply']} 条，回水边 {system_counts['return']} 条。
- 已挂接到边的设备实例：{len(assigned_components)} 个；未归属实例 {len(outside_components)} 个。
- 从炸开图元恢复球阀 {len(exploded_ball_valves)} 个。
- 识别并复联管道跨越断口 {len(crossover_gap_bridges)} 处，交叉位置不生成节点。
- 没有把球阀、蝶阀或自动放气阀提升为节点。
- 每条边按设备类型聚合 `count` 和 `device_names`，同时保留逐实例审计表。

## 边设备类型统计

"""
    report += "\n".join(
        f"- {name}: {count}" for name, count in sorted(assigned_counts.items())
    )
    (args.output_dir / "edge_report.md").write_text(report + "\n", encoding="utf-8")
    save_visualization(
        args.output_dir,
        segments,
        placed_equipment,
        virtual_equipment,
        tees,
        edges,
        components,
        layout,
    )
    save_crossover_gap_visualization(
        args.output_dir,
        raw_segments,
        crossover_gap_bridges,
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
