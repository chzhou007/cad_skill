from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import ezdxf
import matplotlib.pyplot as plt
from ezdxf import bbox as ezdxf_bbox
from matplotlib.lines import Line2D


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DXF = PROJECT_ROOT / "data" / "interim" / "sh16-native-isometric.fixed.dxf"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs"

# The SH16 layout is anchored to a stable equipment label. All scope bounds
# translate with that anchor, so a model-space move does not change floor bands
# or bring explanatory detail panels into the physical graph.
LAYOUT_ANCHOR_LABEL = "CRAH-4#-1-1"
CANONICAL_ANCHOR = (2_231_944.029906254, 130_877.5098815536)
CANONICAL_FLOOR_BOUNDARIES = (144_000.0, 168_000.0)
CANONICAL_LEFT_DETAIL_BOUNDS = (2_210_000.0, 188_000.0)
CANONICAL_RIGHT_DETAIL_BOUNDS = (2_286_500.0, 146_500.0)
CANONICAL_PLOT_BOUNDS = (2_207_000.0, 2_300_000.0, 118_000.0, 194_000.0)

POINT_TOLERANCE = 0.2
ENDPOINT_QUANTUM = 0.1
ANGLE_TOLERANCE_DEGREES = 1.0
MAX_DANGLING_OVERSHOOT_LENGTH = 10.0
MAX_DANGLING_OVERSHOOT_RATIO = 0.10
MIN_OVERSHOOT_INTERSECTION_ANGLE_DEGREES = 20.0
MAX_CROSSOVER_GAP_LENGTH = 250.0
MIN_CROSSOVER_INTERSECTION_ANGLE_DEGREES = 20.0
MAX_VALVE_DISPLAY_STUB_LENGTH = 200.0
MAX_AUTO_AIR_VENT_DISPLAY_LEG_LENGTH = 1_000.0
TURN_DISPLAY_VALVE_BLOCK_NAMES = {
    "$VALVE$00000954",
    "H-PICPNT-87",
    "H-PICPNT-91",
}
AUTO_AIR_VENT_LABELS = {"自动排气阀", "自动放气阀"}


@dataclass(frozen=True)
class Segment:
    system: str
    start: tuple[float, float]
    end: tuple[float, float]


@dataclass(frozen=True)
class DrawingLayout:
    offset_x: float
    offset_y: float
    floor_boundary_1_2: float
    floor_boundary_2_3: float
    left_detail_x_max: float
    left_detail_y_min: float
    right_detail_x_min: float
    right_detail_y_max: float
    plot_x_min: float
    plot_x_max: float
    plot_y_min: float
    plot_y_max: float


@dataclass(frozen=True)
class TeeNode:
    system: str
    x: float
    y: float


@dataclass(frozen=True)
class OvershootTrim:
    system: str
    original_endpoint: tuple[float, float]
    junction: tuple[float, float]
    length: float


@dataclass(frozen=True)
class CrossoverGapBridge:
    system: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    crossing_x: float
    crossing_y: float
    crossed_system: str
    length: float
    crossing_angle_degrees: float
    connection_mode: str = "drafting_crossover_gap_healed_without_junction"


@dataclass(frozen=True)
class ValveRegion:
    block_name: str
    min_x: float
    min_y: float
    max_x: float
    max_y: float


@dataclass(frozen=True)
class ValveStubRemoval:
    system: str
    block_name: str
    valve_port: tuple[float, float]
    junction: tuple[float, float]
    length: float


@dataclass(frozen=True)
class AirVentLegRemoval:
    system: str
    vent_port: tuple[float, float]
    junction: tuple[float, float]
    length: float
    action: str


@dataclass(frozen=True)
class EquipmentNode:
    label: str
    floor: int
    sequence: int
    x: float
    y: float
    source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract first-layer equipment and tee nodes from the SH16 CAD system diagram."
    )
    parser.add_argument("--dxf", type=Path, default=DEFAULT_DXF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def recursive_entities(entity, depth: int = 0) -> Iterator:
    if entity.dxftype() == "INSERT" and depth < 8:
        for child in entity.virtual_entities():
            yield from recursive_entities(child, depth + 1)
    else:
        yield entity


def point_key(point: tuple[float, float], quantum: float) -> tuple[int, int]:
    return round(point[0] / quantum), round(point[1] / quantum)


def get_system_layers(doc) -> dict[str, str]:
    # ACI 6 is the magenta chilled-water supply layer; ACI 4 is the cyan
    # chilled-water return layer in this drawing.
    supply = next(layer.dxf.name for layer in doc.layers if layer.dxf.color == 6)
    return_ = next(layer.dxf.name for layer in doc.layers if layer.dxf.color == 4)
    return {supply: "supply", return_: "return"}


def collect_pipe_segments(doc) -> list[Segment]:
    system_layers = get_system_layers(doc)
    segments: list[Segment] = []
    for top_level in doc.modelspace():
        for entity in recursive_entities(top_level):
            if entity.dxftype() != "LINE" or entity.dxf.layer not in system_layers:
                continue
            start = (float(entity.dxf.start.x), float(entity.dxf.start.y))
            end = (float(entity.dxf.end.x), float(entity.dxf.end.y))
            if math.dist(start, end) > 1e-6:
                segments.append(Segment(system_layers[entity.dxf.layer], start, end))

    unique: dict[tuple, Segment] = {}
    for segment in segments:
        endpoints = sorted(
            [point_key(segment.start, 0.01), point_key(segment.end, 0.01)]
        )
        unique.setdefault((segment.system, *endpoints), segment)
    return list(unique.values())


def projection_parameter(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
    tolerance: float = POINT_TOLERANCE,
) -> float | None:
    vx, vy = end[0] - start[0], end[1] - start[1]
    wx, wy = point[0] - start[0], point[1] - start[1]
    length_squared = vx * vx + vy * vy
    if length_squared < 1e-12:
        return None
    t = (wx * vx + wy * vy) / length_squared
    length = math.sqrt(length_squared)
    if t < -tolerance / length or t > 1.0 + tolerance / length:
        return None
    projected = (start[0] + t * vx, start[1] + t * vy)
    if math.dist(point, projected) > tolerance:
        return None
    return t


def segment_intersection_parameters(
    first: Segment, second: Segment
) -> tuple[tuple[float, float], float, float, float] | None:
    """Return the 2-D intersection and parameters for two non-parallel segments."""
    first_vector = (
        first.end[0] - first.start[0],
        first.end[1] - first.start[1],
    )
    second_vector = (
        second.end[0] - second.start[0],
        second.end[1] - second.start[1],
    )
    first_length = math.hypot(*first_vector)
    second_length = math.hypot(*second_vector)
    if first_length < 1e-9 or second_length < 1e-9:
        return None

    cross = (
        first_vector[0] * second_vector[1]
        - first_vector[1] * second_vector[0]
    )
    if abs(cross) < 1e-9 * first_length * second_length:
        return None

    delta = (
        second.start[0] - first.start[0],
        second.start[1] - first.start[1],
    )
    first_parameter = (
        delta[0] * second_vector[1] - delta[1] * second_vector[0]
    ) / cross
    second_parameter = (
        delta[0] * first_vector[1] - delta[1] * first_vector[0]
    ) / cross
    if not (
        -1e-9 <= first_parameter <= 1.0 + 1e-9
        and -1e-9 <= second_parameter <= 1.0 + 1e-9
    ):
        return None

    point = (
        first.start[0] + first_parameter * first_vector[0],
        first.start[1] + first_parameter * first_vector[1],
    )
    sine_angle = abs(cross) / (first_length * second_length)
    return point, first_parameter, second_parameter, sine_angle


def trim_short_dangling_overshoots(
    segments: list[Segment],
) -> tuple[list[Segment], list[OvershootTrim]]:
    """Trim tiny dangling stubs that run just beyond a crossing pipe.

    A trim is deliberately conservative: both lines must belong to the same
    system, the host line must pass through the intersection, the near
    endpoint must otherwise be dangling, and the stub must be short in both
    absolute and relative terms. This restores a drafting-imprecise T without
    turning ordinary line crossings into connected junctions.
    """
    by_system: dict[str, list[tuple[int, Segment]]] = defaultdict(list)
    for index, segment in enumerate(segments):
        by_system[segment.system].append((index, segment))

    dangling: dict[tuple[int, str], bool] = {}
    for system_segments in by_system.values():
        for index, segment in system_segments:
            for endpoint_name, endpoint in (
                ("start", segment.start),
                ("end", segment.end),
            ):
                dangling[(index, endpoint_name)] = not any(
                    other_index != index
                    and projection_parameter(endpoint, other.start, other.end)
                    is not None
                    for other_index, other in system_segments
                )

    minimum_sine = math.sin(
        math.radians(MIN_OVERSHOOT_INTERSECTION_ANGLE_DEGREES)
    )
    cuts: dict[tuple[int, str], tuple[float, tuple[float, float]]] = {}

    for system_segments in by_system.values():
        for offset, (first_index, first) in enumerate(system_segments):
            for second_index, second in system_segments[offset + 1 :]:
                intersection = segment_intersection_parameters(first, second)
                if intersection is None:
                    continue
                point, first_parameter, second_parameter, sine_angle = intersection
                if sine_angle < minimum_sine:
                    continue

                for index, segment, parameter, host_parameter in (
                    (first_index, first, first_parameter, second_parameter),
                    (second_index, second, second_parameter, first_parameter),
                ):
                    # The host must continue in both directions so that cutting
                    # the dangling line creates exactly the intended T topology.
                    if not (1e-6 < host_parameter < 1.0 - 1e-6):
                        continue
                    if not (1e-6 < parameter < 1.0 - 1e-6):
                        continue

                    segment_length = math.dist(segment.start, segment.end)
                    if parameter <= 0.5:
                        endpoint_name = "start"
                        endpoint = segment.start
                        stub_length = parameter * segment_length
                    else:
                        endpoint_name = "end"
                        endpoint = segment.end
                        stub_length = (1.0 - parameter) * segment_length

                    if not dangling[(index, endpoint_name)]:
                        continue
                    if not (
                        POINT_TOLERANCE < stub_length
                        <= MAX_DANGLING_OVERSHOOT_LENGTH
                    ):
                        continue
                    if stub_length / segment_length > MAX_DANGLING_OVERSHOOT_RATIO:
                        continue

                    key = (index, endpoint_name)
                    previous = cuts.get(key)
                    if previous is None or stub_length < previous[0]:
                        cuts[key] = (stub_length, point)

    cleaned = list(segments)
    trims: list[OvershootTrim] = []
    for (index, endpoint_name), (stub_length, point) in cuts.items():
        segment = cleaned[index]
        original_endpoint = (
            segment.start if endpoint_name == "start" else segment.end
        )
        if endpoint_name == "start":
            cleaned[index] = Segment(segment.system, point, segment.end)
        else:
            cleaned[index] = Segment(segment.system, segment.start, point)
        trims.append(
            OvershootTrim(
                system=segment.system,
                original_endpoint=original_endpoint,
                junction=point,
                length=stub_length,
            )
        )

    return cleaned, sorted(
        trims,
        key=lambda trim: (trim.junction[1], trim.junction[0], trim.system),
    )


def bridge_pipe_crossover_gaps(
    segments: list[Segment],
) -> tuple[list[Segment], list[CrossoverGapBridge]]:
    """Heal drafting gaps that indicate one pipe crossing another without joining.

    The broken pipe must have two dangling, collinear ends that point away from
    one another.  The short gap between them must cross exactly one non-collinear
    pipe in its interior.  Adding only the missing same-system span preserves the
    broken pipe's continuity; the crossing itself remains an interior point of
    both segments and therefore is deliberately not promoted to a graph node.
    """

    by_system: dict[str, list[tuple[int, Segment]]] = defaultdict(list)
    for index, segment in enumerate(segments):
        by_system[segment.system].append((index, segment))

    dangling: dict[str, list[tuple[int, tuple[float, float], tuple[float, float]]]] = (
        defaultdict(list)
    )
    for system, system_segments in by_system.items():
        for index, segment in system_segments:
            for endpoint, other_endpoint in (
                (segment.start, segment.end),
                (segment.end, segment.start),
            ):
                touching = {
                    other_index
                    for other_index, other in system_segments
                    if projection_parameter(endpoint, other.start, other.end)
                    is not None
                }
                if touching == {index}:
                    dangling[system].append((index, endpoint, other_endpoint))

    collinear_cosine = math.cos(math.radians(ANGLE_TOLERANCE_DEGREES))
    minimum_crossing_sine = math.sin(
        math.radians(MIN_CROSSOVER_INTERSECTION_ANGLE_DEGREES)
    )
    candidates: list[
        tuple[
            float,
            str,
            int,
            int,
            tuple[float, float],
            tuple[float, float],
            tuple[float, float],
            str,
            float,
        ]
    ] = []

    for system, endpoints in dangling.items():
        for offset, (first_index, first, first_other) in enumerate(endpoints):
            for second_index, second, second_other in endpoints[offset + 1 :]:
                if first_index == second_index:
                    continue
                gap_length = math.dist(first, second)
                if not (
                    POINT_TOLERANCE < gap_length <= MAX_CROSSOVER_GAP_LENGTH
                ):
                    continue

                gap_unit = (
                    (second[0] - first[0]) / gap_length,
                    (second[1] - first[1]) / gap_length,
                )
                first_ray_length = math.dist(first, first_other)
                second_ray_length = math.dist(second, second_other)
                if first_ray_length < 1e-9 or second_ray_length < 1e-9:
                    continue
                first_ray = (
                    (first_other[0] - first[0]) / first_ray_length,
                    (first_other[1] - first[1]) / first_ray_length,
                )
                second_ray = (
                    (second_other[0] - second[0]) / second_ray_length,
                    (second_other[1] - second[1]) / second_ray_length,
                )
                if (
                    first_ray[0] * gap_unit[0] + first_ray[1] * gap_unit[1]
                    > -collinear_cosine
                    or second_ray[0] * gap_unit[0]
                    + second_ray[1] * gap_unit[1]
                    < collinear_cosine
                ):
                    continue

                bridge = Segment(system, first, second)
                crossings: list[tuple[tuple[float, float], str, float]] = []
                for host_index, host in enumerate(segments):
                    if host_index in {first_index, second_index}:
                        continue
                    intersection = segment_intersection_parameters(bridge, host)
                    if intersection is None:
                        continue
                    point, bridge_parameter, host_parameter, sine_angle = intersection
                    if not (
                        1e-6 < bridge_parameter < 1.0 - 1e-6
                        and 1e-6 < host_parameter < 1.0 - 1e-6
                        and sine_angle >= minimum_crossing_sine
                    ):
                        continue
                    crossings.append((point, host.system, sine_angle))

                if len(crossings) != 1:
                    continue
                crossing, crossed_system, sine_angle = crossings[0]
                candidates.append(
                    (
                        gap_length,
                        system,
                        first_index,
                        second_index,
                        first,
                        second,
                        crossing,
                        crossed_system,
                        math.degrees(math.asin(min(1.0, sine_angle))),
                    )
                )

    used_segments: set[int] = set()
    bridges: list[CrossoverGapBridge] = []
    cleaned = list(segments)
    for (
        gap_length,
        system,
        first_index,
        second_index,
        first,
        second,
        crossing,
        crossed_system,
        crossing_angle,
    ) in sorted(candidates):
        if first_index in used_segments or second_index in used_segments:
            continue
        used_segments.update({first_index, second_index})
        cleaned.append(Segment(system, first, second))
        bridges.append(
            CrossoverGapBridge(
                system=system,
                start_x=first[0],
                start_y=first[1],
                end_x=second[0],
                end_y=second[1],
                crossing_x=crossing[0],
                crossing_y=crossing[1],
                crossed_system=crossed_system,
                length=gap_length,
                crossing_angle_degrees=crossing_angle,
            )
        )

    return cleaned, sorted(
        bridges,
        key=lambda item: (item.crossing_y, item.crossing_x, item.system),
    )


def add_unique_ray(rays: list[tuple[float, float]], dx: float, dy: float) -> None:
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return
    unit = (dx / length, dy / length)
    cosine_limit = math.cos(math.radians(ANGLE_TOLERANCE_DEGREES))
    if not any(unit[0] * ray[0] + unit[1] * ray[1] > cosine_limit for ray in rays):
        rays.append(unit)


def rays_at_point(
    point: tuple[float, float],
    segments: list[Segment],
    skip_index: int | None = None,
) -> list[tuple[float, float]]:
    rays: list[tuple[float, float]] = []
    for index, segment in enumerate(segments):
        if index == skip_index:
            continue
        parameter = projection_parameter(point, segment.start, segment.end)
        if parameter is None:
            continue
        if parameter <= 1e-5:
            add_unique_ray(
                rays,
                segment.end[0] - point[0],
                segment.end[1] - point[1],
            )
        elif parameter >= 1.0 - 1e-5:
            add_unique_ray(
                rays,
                segment.start[0] - point[0],
                segment.start[1] - point[1],
            )
        else:
            add_unique_ray(
                rays,
                segment.start[0] - point[0],
                segment.start[1] - point[1],
            )
            add_unique_ray(
                rays,
                segment.end[0] - point[0],
                segment.end[1] - point[1],
            )
    return rays


def has_opposite_ray_pair(rays: list[tuple[float, float]]) -> bool:
    return any(
        rays[first][0] * rays[second][0]
        + rays[first][1] * rays[second][1]
        < -0.999
        for first in range(len(rays))
        for second in range(first + 1, len(rays))
    )


def recursive_inserts(entity, depth: int = 0) -> Iterator:
    """Yield an INSERT and all transformed INSERTs nested inside it."""
    if entity.dxftype() != "INSERT" or depth >= 8:
        return
    yield entity
    for child in entity.virtual_entities():
        if child.dxftype() == "INSERT":
            yield from recursive_inserts(child, depth + 1)


def collect_turn_display_valve_regions(doc) -> list[ValveRegion]:
    regions: list[ValveRegion] = []
    for top_level in doc.modelspace().query("INSERT"):
        for insert in recursive_inserts(top_level):
            if insert.dxf.name not in TURN_DISPLAY_VALVE_BLOCK_NAMES:
                continue
            bounds = ezdxf_bbox.extents([insert], fast=True)
            if not bounds.has_data:
                continue
            regions.append(
                ValveRegion(
                    block_name=insert.dxf.name,
                    min_x=float(bounds.extmin.x),
                    min_y=float(bounds.extmin.y),
                    max_x=float(bounds.extmax.x),
                    max_y=float(bounds.extmax.y),
                )
            )
    return regions


def point_in_valve_region(
    point: tuple[float, float], valve: ValveRegion
) -> bool:
    return (
        valve.min_x - POINT_TOLERANCE
        <= point[0]
        <= valve.max_x + POINT_TOLERANCE
        and valve.min_y - POINT_TOLERANCE
        <= point[1]
        <= valve.max_y + POINT_TOLERANCE
    )


def remove_turn_display_valve_stubs(
    segments: list[Segment], valve_regions: list[ValveRegion]
) -> tuple[list[Segment], list[ValveStubRemoval]]:
    """Remove a valve's short display-only leg from an otherwise real elbow.

    Some valve symbols are moved just off a pipe corner for readability and
    joined back to that corner by a short pipe-colored line. Geometrically the
    line creates a three-ray point, but physically the remaining two pipe rays
    form only an elbow. A candidate is removed only when its valve-side end is
    dangling and deleting it changes an exact T into a non-collinear two-ray
    corner.
    """
    by_system: dict[str, list[tuple[int, Segment]]] = defaultdict(list)
    for index, segment in enumerate(segments):
        by_system[segment.system].append((index, segment))

    removals_by_index: dict[int, ValveStubRemoval] = {}
    for valve in valve_regions:
        for system_segments in by_system.values():
            local_segments = [segment for _, segment in system_segments]
            local_to_global = [index for index, _ in system_segments]
            for local_index, segment in enumerate(local_segments):
                segment_length = math.dist(segment.start, segment.end)
                if segment_length > MAX_VALVE_DISPLAY_STUB_LENGTH:
                    continue

                start_inside = point_in_valve_region(segment.start, valve)
                end_inside = point_in_valve_region(segment.end, valve)
                if start_inside == end_inside:
                    continue
                valve_port = segment.start if start_inside else segment.end
                junction = segment.end if start_inside else segment.start

                # A real through-pipe has another pipe line at the valve-side
                # endpoint; the display leg is dangling there.
                if any(
                    other_index != local_index
                    and projection_parameter(
                        valve_port, other.start, other.end
                    )
                    is not None
                    for other_index, other in enumerate(local_segments)
                ):
                    continue

                rays_before = rays_at_point(junction, local_segments)
                rays_after = rays_at_point(
                    junction, local_segments, skip_index=local_index
                )
                if not (
                    len(rays_before) == 3
                    and has_opposite_ray_pair(rays_before)
                    and len(rays_after) == 2
                    and not has_opposite_ray_pair(rays_after)
                ):
                    continue

                global_index = local_to_global[local_index]
                removals_by_index[global_index] = ValveStubRemoval(
                    system=segment.system,
                    block_name=valve.block_name,
                    valve_port=valve_port,
                    junction=junction,
                    length=segment_length,
                )

    cleaned = [
        segment
        for index, segment in enumerate(segments)
        if index not in removals_by_index
    ]
    removals = sorted(
        removals_by_index.values(),
        key=lambda item: (item.junction[1], item.junction[0], item.system),
    )
    return cleaned, removals


def collect_auto_air_vent_ports(doc) -> list[tuple[float, float]]:
    """Collect semantic connection points exported for automatic air vents."""
    ports: dict[tuple[int, int], tuple[float, float]] = {}
    for attribute in doc.modelspace().query("ATTDEF"):
        if attribute.dxf.tag.upper() != "WHAT":
            continue
        if attribute.dxf.text.strip() not in AUTO_AIR_VENT_LABELS:
            continue
        point = (
            float(attribute.dxf.insert.x),
            float(attribute.dxf.insert.y),
        )
        ports[point_key(point, ENDPOINT_QUANTUM)] = point
    return sorted(ports.values(), key=lambda point: (point[1], point[0]))


def remove_auto_air_vent_display_legs(
    segments: list[Segment],
    vent_ports: list[tuple[float, float]],
    layout: DrawingLayout | None = None,
) -> tuple[list[Segment], list[AirVentLegRemoval]]:
    """Fold display legs from automatic air vents back to their pipe elbows.

    LibreDWG exports these four symbols as primitive geometry plus a semantic
    ATTDEF anchor. The pipe-colored display leg can either be a standalone
    segment or the short end of a longer segment passing through the elbow.
    In both cases the leg is removed only when the result is a non-collinear
    two-ray corner.
    """
    cleaned = list(segments)
    removals: list[AirVentLegRemoval] = []

    for vent_port in vent_ports:
        tee_nodes = detect_tee_nodes(cleaned, layout)
        candidates: list[
            tuple[float, int, Segment, tuple[float, float], bool]
        ] = []
        for index, segment in enumerate(cleaned):
            port_at_start = math.dist(vent_port, segment.start) <= POINT_TOLERANCE
            port_at_end = math.dist(vent_port, segment.end) <= POINT_TOLERANCE
            if port_at_start == port_at_end:
                continue

            for tee in tee_nodes:
                if tee.system != segment.system:
                    continue
                junction = (tee.x, tee.y)
                if (
                    projection_parameter(
                        junction, segment.start, segment.end
                    )
                    is None
                ):
                    continue
                leg_length = math.dist(vent_port, junction)
                if not (
                    POINT_TOLERANCE < leg_length
                    <= MAX_AUTO_AIR_VENT_DISPLAY_LEG_LENGTH
                ):
                    continue
                candidates.append(
                    (
                        leg_length,
                        index,
                        segment,
                        junction,
                        port_at_start,
                    )
                )

        accepted = False
        for leg_length, index, segment, junction, port_at_start in sorted(
            candidates, key=lambda item: item[0]
        ):
            if port_at_start:
                remaining_endpoint = segment.end
                replacement = (
                    None
                    if math.dist(junction, remaining_endpoint) <= POINT_TOLERANCE
                    else Segment(segment.system, junction, remaining_endpoint)
                )
            else:
                remaining_endpoint = segment.start
                replacement = (
                    None
                    if math.dist(junction, remaining_endpoint) <= POINT_TOLERANCE
                    else Segment(segment.system, remaining_endpoint, junction)
                )

            trial = list(cleaned)
            action = "remove"
            if replacement is None:
                del trial[index]
            else:
                trial[index] = replacement
                action = "trim"

            system_segments = [
                item for item in trial if item.system == segment.system
            ]
            rays_after = rays_at_point(junction, system_segments)
            if len(rays_after) != 2 or has_opposite_ray_pair(rays_after):
                continue

            cleaned = trial
            removals.append(
                AirVentLegRemoval(
                    system=segment.system,
                    vent_port=vent_port,
                    junction=junction,
                    length=leg_length,
                    action=action,
                )
            )
            accepted = True
            break

        if not accepted:
            continue

    return cleaned, sorted(
        removals,
        key=lambda item: (item.junction[1], item.junction[0], item.system),
    )


def is_excluded_detail_point(
    x: float, y: float, layout: DrawingLayout | None
) -> bool:
    return (
        layout is not None
        and x < layout.left_detail_x_max
        and y > layout.left_detail_y_min
    )


def is_excluded_visual_segment(
    segment: Segment, layout: DrawingLayout | None
) -> bool:
    x = (segment.start[0] + segment.end[0]) / 2.0
    y = (segment.start[1] + segment.end[1]) / 2.0
    return is_excluded_detail_point(x, y, layout) or (
        layout is not None
        and x > layout.right_detail_x_min
        and y < layout.right_detail_y_max
    )


def detect_tee_nodes(
    segments: list[Segment], layout: DrawingLayout | None = None
) -> list[TeeNode]:
    by_system: dict[str, list[Segment]] = defaultdict(list)
    candidates: dict[tuple, tuple[str, tuple[float, float]]] = {}
    for segment in segments:
        by_system[segment.system].append(segment)
        candidates[(segment.system, point_key(segment.start, ENDPOINT_QUANTUM))] = (
            segment.system,
            segment.start,
        )
        candidates[(segment.system, point_key(segment.end, ENDPOINT_QUANTUM))] = (
            segment.system,
            segment.end,
        )

    tee_nodes: list[TeeNode] = []
    for system, point in candidates.values():
        rays = rays_at_point(point, by_system[system])
        if (
            len(rays) == 3
            and not is_excluded_detail_point(*point, layout)
        ):
            tee_nodes.append(TeeNode(system, point[0], point[1]))

    # Preserve the existing straight-run T ordering, then append genuine
    # three-way isometric corners. Source display legs are removed before this
    # detector; a three-ray junction need not contain an opposite ray pair.
    return sorted(tee_nodes, key=lambda node: (
        not has_opposite_ray_pair(rays_at_point((node.x, node.y), by_system[node.system])),
        node.y, node.x, node.system,
    ))


def equipment_labels(doc) -> list[tuple[str, int, int, float, float]]:
    label_pattern = re.compile(r"CRAH-4#-(\d+)-(\d+)")
    labels = []
    for text in doc.modelspace().query("TEXT"):
        match = label_pattern.fullmatch(text.dxf.text)
        if match:
            labels.append(
                (
                    text.dxf.text,
                    int(match.group(1)),
                    int(match.group(2)),
                    float(text.dxf.insert.x),
                    float(text.dxf.insert.y),
                )
            )
    return sorted(labels, key=lambda item: (item[1], item[2]))


def infer_drawing_layout(
    labels: list[tuple[str, int, int, float, float]],
) -> DrawingLayout:
    """Translate canonical SH16 scope bounds with a stable equipment label."""
    if not labels:
        raise RuntimeError("Cannot infer drawing layout without equipment labels")

    anchor = next(
        (label for label in labels if label[0] == LAYOUT_ANCHOR_LABEL),
        None,
    )
    if anchor is None:
        raise RuntimeError(f"Missing drawing layout anchor: {LAYOUT_ANCHOR_LABEL}")
    offset_x = anchor[3] - CANONICAL_ANCHOR[0]
    offset_y = anchor[4] - CANONICAL_ANCHOR[1]

    return DrawingLayout(
        offset_x=offset_x,
        offset_y=offset_y,
        floor_boundary_1_2=CANONICAL_FLOOR_BOUNDARIES[0] + offset_y,
        floor_boundary_2_3=CANONICAL_FLOOR_BOUNDARIES[1] + offset_y,
        left_detail_x_max=CANONICAL_LEFT_DETAIL_BOUNDS[0] + offset_x,
        left_detail_y_min=CANONICAL_LEFT_DETAIL_BOUNDS[1] + offset_y,
        right_detail_x_min=CANONICAL_RIGHT_DETAIL_BOUNDS[0] + offset_x,
        right_detail_y_max=CANONICAL_RIGHT_DETAIL_BOUNDS[1] + offset_y,
        plot_x_min=CANONICAL_PLOT_BOUNDS[0] + offset_x,
        plot_x_max=CANONICAL_PLOT_BOUNDS[1] + offset_x,
        plot_y_min=CANONICAL_PLOT_BOUNDS[2] + offset_y,
        plot_y_max=CANONICAL_PLOT_BOUNDS[3] + offset_y,
    )


def numeric_block_centers(doc, equipment_layer: str) -> list[tuple[float, float, str]]:
    centers = []
    for insert in doc.modelspace().query("INSERT"):
        if insert.dxf.name not in {"1", "2", "3", "4", "5", "7"}:
            continue
        points = []
        for entity in insert.virtual_entities():
            if entity.dxftype() == "LINE" and entity.dxf.layer == equipment_layer:
                points.extend(
                    [
                        (float(entity.dxf.start.x), float(entity.dxf.start.y)),
                        (float(entity.dxf.end.x), float(entity.dxf.end.y)),
                    ]
                )
        if points:
            centers.append(
                (
                    (min(p[0] for p in points) + max(p[0] for p in points)) / 2.0,
                    (min(p[1] for p in points) + max(p[1] for p in points)) / 2.0,
                    f"block:{insert.dxf.name}",
                )
            )
    return centers


def top_level_equipment_components(doc, equipment_layer: str) -> list[tuple[float, float]]:
    lines = [
        entity
        for entity in doc.modelspace().query("LINE")
        if entity.dxf.layer == equipment_layer
    ]
    endpoint_index: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, line in enumerate(lines):
        endpoint_index[point_key((line.dxf.start.x, line.dxf.start.y), 0.1)].append(index)
        endpoint_index[point_key((line.dxf.end.x, line.dxf.end.y), 0.1)].append(index)

    adjacency: dict[int, set[int]] = defaultdict(set)
    for indexes in endpoint_index.values():
        for index in indexes:
            adjacency[index].update(indexes)

    seen: set[int] = set()
    components: list[tuple[float, float]] = []
    for start_index in range(len(lines)):
        if start_index in seen:
            continue
        stack = [start_index]
        seen.add(start_index)
        indexes = []
        while stack:
            index = stack.pop()
            indexes.append(index)
            for neighbor in adjacency[index]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)

        # The six exploded CRAH boxes have 8 or 12 connected outline lines.
        if len(indexes) < 8:
            continue
        points = []
        for index in indexes:
            line = lines[index]
            points.extend(
                [
                    (float(line.dxf.start.x), float(line.dxf.start.y)),
                    (float(line.dxf.end.x), float(line.dxf.end.y)),
                ]
            )
        xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
        ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
        if xmax - xmin < 5_000 and ymax - ymin < 5_000:
            components.append(((xmin + xmax) / 2.0, (ymin + ymax) / 2.0))
    return components


def match_centers_to_labels(
    centers: Iterable[tuple[float, float, str]],
    labels: list[tuple[str, int, int, float, float]],
    max_distance: float,
    already_used: set[str] | None = None,
) -> tuple[list[EquipmentNode], set[str]]:
    used = set() if already_used is None else set(already_used)
    centers = list(centers)
    pairs = []
    for center_index, (x, y, source) in enumerate(centers):
        for label_index, label in enumerate(labels):
            if label[0] in used:
                continue
            distance = math.hypot(x - label[3], y - label[4])
            if distance <= max_distance:
                pairs.append((distance, center_index, label_index))
    pairs.sort()

    assigned_centers: set[int] = set()
    nodes: list[EquipmentNode] = []
    for _, center_index, label_index in pairs:
        label, floor, sequence, _, _ = labels[label_index]
        if center_index in assigned_centers or label in used:
            continue
        x, y, source = centers[center_index]
        nodes.append(EquipmentNode(label, floor, sequence, x, y, source))
        assigned_centers.add(center_index)
        used.add(label)
    return nodes, used


def detect_equipment_nodes(doc) -> list[EquipmentNode]:
    labels = equipment_labels(doc)
    equipment_layer = next(
        layer.dxf.name
        for layer in doc.layers
        if layer.dxf.color == 3 and layer.dxf.name.endswith("平面")
    )

    block_nodes, used = match_centers_to_labels(
        numeric_block_centers(doc, equipment_layer), labels, max_distance=5_000
    )
    missing_labels = [label for label in labels if label[0] not in used]
    component_centers = [
        (x, y, "exploded-outline")
        for x, y in top_level_equipment_components(doc, equipment_layer)
    ]
    exploded_nodes, used = match_centers_to_labels(
        component_centers,
        missing_labels,
        max_distance=5_000,
        already_used=used,
    )
    nodes = sorted(block_nodes + exploded_nodes, key=lambda node: (node.floor, node.sequence))

    missing = [label[0] for label in labels if label[0] not in used]
    if missing:
        raise RuntimeError(f"Unmatched equipment labels: {missing}")
    if len(nodes) != len(labels):
        raise RuntimeError(
            f"Equipment center mismatch: {len(nodes)} centers for {len(labels)} labels"
        )
    return nodes


def drawing_band(y: float, layout: DrawingLayout) -> int:
    if y < layout.floor_boundary_1_2:
        return 1
    if y < layout.floor_boundary_2_3:
        return 2
    return 3


def write_nodes_csv(
    path: Path,
    equipment: list[EquipmentNode],
    tees: list[TeeNode],
    layout: DrawingLayout,
) -> None:
    fields = [
        "node_id",
        "node_type",
        "subtype",
        "floor_band",
        "label",
        "x",
        "y",
        "detection_rule",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for node in equipment:
            writer.writerow(
                {
                    "node_id": node.label,
                    "node_type": "equipment",
                    "subtype": "CRAH",
                    "floor_band": node.floor,
                    "label": node.label,
                    "x": f"{node.x:.3f}",
                    "y": f"{node.y:.3f}",
                    "detection_rule": node.source,
                }
            )
        for index, node in enumerate(tees, start=1):
            writer.writerow(
                {
                    "node_id": f"T{index:03d}",
                    "node_type": "physical_junction",
                    "subtype": f"tee_{node.system}",
                    "floor_band": drawing_band(node.y, layout),
                    "label": "",
                    "x": f"{node.x:.3f}",
                    "y": f"{node.y:.3f}",
                    "detection_rule": "three_unique_rays_with_opposite_pair",
                }
            )


def configure_plotting() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def plot_base_segments(
    ax,
    segments: list[Segment],
    layout: DrawingLayout,
    y_range: tuple[float, float] | None = None,
) -> None:
    for segment in segments:
        if is_excluded_visual_segment(segment, layout):
            continue
        if y_range is not None:
            ymin, ymax = y_range
            if max(segment.start[1], segment.end[1]) < ymin or min(
                segment.start[1], segment.end[1]
            ) > ymax:
                continue
        color = "#d8b4fe" if segment.system == "supply" else "#a5f3fc"
        ax.plot(
            [segment.start[0], segment.end[0]],
            [segment.start[1], segment.end[1]],
            color=color,
            linewidth=0.55,
            alpha=0.72,
            zorder=1,
        )


def plot_nodes(
    ax,
    equipment: list[EquipmentNode],
    tees: list[TeeNode],
    layout: DrawingLayout,
    floor: int | None = None,
    add_equipment_labels: bool = False,
) -> None:
    equipment_subset = [node for node in equipment if floor is None or node.floor == floor]
    tee_subset = [
        node
        for node in tees
        if floor is None or drawing_band(node.y, layout) == floor
    ]

    for system, color in [("supply", "#7c3aed"), ("return", "#0891b2")]:
        nodes = [node for node in tee_subset if node.system == system]
        ax.scatter(
            [node.x for node in nodes],
            [node.y for node in nodes],
            s=13 if floor is None else 24,
            c=color,
            edgecolors="white",
            linewidths=0.25,
            zorder=3,
        )

    ax.scatter(
        [node.x for node in equipment_subset],
        [node.y for node in equipment_subset],
        s=42 if floor is None else 64,
        marker="s",
        c="#f59e0b",
        edgecolors="#7c2d12",
        linewidths=0.7,
        zorder=4,
    )
    if add_equipment_labels:
        for node in equipment_subset:
            ax.annotate(
                f"{node.floor}-{node.sequence}",
                (node.x, node.y),
                xytext=(2, 2),
                textcoords="offset points",
                fontsize=5.2,
                color="#78350f",
                zorder=5,
            )


def legend_handles() -> list[Line2D]:
    return [
        Line2D([0], [0], marker="s", color="none", markerfacecolor="#f59e0b", markeredgecolor="#7c2d12", markersize=8, label="设备节点（CRAH）"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#7c3aed", markersize=7, label="T 节点（供水）"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#0891b2", markersize=7, label="T 节点（回水）"),
    ]


def save_visualizations(
    output_dir: Path,
    segments: list[Segment],
    equipment: list[EquipmentNode],
    tees: list[TeeNode],
    layout: DrawingLayout,
) -> None:
    configure_plotting()

    fig, ax = plt.subplots(figsize=(20, 13), dpi=220)
    plot_base_segments(ax, segments, layout)
    plot_nodes(ax, equipment, tees, layout)
    ax.set_xlim(layout.plot_x_min, layout.plot_x_max)
    ax.set_ylim(layout.plot_y_min, layout.plot_y_max)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(handles=legend_handles(), loc="upper right", frameon=True, fontsize=10)
    ax.set_title(
        f"SH16 空调水系统图：第一层图结构简化\n"
        f"设备节点 {len(equipment)} + T 型物理节点 {len(tees)} = 总节点 {len(equipment) + len(tees)}",
        fontsize=18,
        pad=18,
    )
    fig.savefig(
        output_dir / "simplified_graph_overview.png",
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.12,
        facecolor="white",
    )
    plt.close(fig)

    ranges = {
        1: (layout.plot_y_min, layout.floor_boundary_1_2),
        2: (layout.floor_boundary_1_2, layout.floor_boundary_2_3),
        3: (layout.floor_boundary_2_3, layout.plot_y_max),
    }
    fig, axes = plt.subplots(3, 1, figsize=(22, 17), dpi=220)
    for axis, floor in zip(axes, [3, 2, 1]):
        y_range = ranges[floor]
        plot_base_segments(axis, segments, layout, y_range)
        plot_nodes(
            axis,
            equipment,
            tees,
            layout,
            floor=floor,
            add_equipment_labels=True,
        )
        equipment_count = sum(node.floor == floor for node in equipment)
        tee_count = sum(drawing_band(node.y, layout) == floor for node in tees)
        axis.set_xlim(layout.plot_x_min, layout.plot_x_max)
        axis.set_ylim(*y_range)
        axis.set_aspect("equal")
        axis.axis("off")
        axis.text(
            0.01,
            0.96,
            f"{floor}F 图带：设备 {equipment_count}，T 节点 {tee_count}，小计 {equipment_count + tee_count}",
            transform=axis.transAxes,
            ha="left",
            va="top",
            fontsize=12,
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.88, "edgecolor": "#d1d5db"},
        )
    axes[0].legend(handles=legend_handles(), loc="upper right", frameon=True, fontsize=9)
    fig.suptitle(
        f"按楼层图带核对节点（总计 {len(equipment) + len(tees)}）",
        fontsize=18,
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    fig.savefig(
        output_dir / "simplified_graph_by_floor.png",
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.12,
        facecolor="white",
    )
    plt.close(fig)


def build_summary(
    equipment: list[EquipmentNode],
    tees: list[TeeNode],
    overshoot_trims: list[OvershootTrim],
    valve_stub_removals: list[ValveStubRemoval],
    air_vent_leg_removals: list[AirVentLegRemoval],
    crossover_gap_bridges: list[CrossoverGapBridge],
    layout: DrawingLayout,
    tee_counts_by_stage: dict[str, int],
) -> dict:
    equipment_by_floor = Counter(node.floor for node in equipment)
    tees_by_floor = Counter(drawing_band(node.y, layout) for node in tees)
    tees_by_system = Counter(node.system for node in tees)
    return {
        "source_scope": "SH16 空调水系统主图",
        "node_definition": {
            "equipment": "带 CRAH 编号的非阀门设备图形，每台折叠为 1 个设备节点",
            "physical_junction": "同一供水或回水管网上形成三条唯一射线且含一对反向共线射线的 T 型连通点",
        },
        "excluded": [
            "阀门、软接、仪表和标注不计为节点",
            "图框和文字不计为节点",
            "双层水氟换热器接管示意图、冷冻水型机房专用空调接管示意图、水氟换热器接管示意图不计入主系统实例",
            "本轮未把管线端点和普通弯头定义为节点",
        ],
        "counts": {
            "equipment_nodes": len(equipment),
            "tee_junction_nodes": len(tees),
            "total_nodes": len(equipment) + len(tees),
            "equipment_by_floor": {str(k): equipment_by_floor[k] for k in sorted(equipment_by_floor)},
            "tee_by_floor_band": {str(k): tees_by_floor[k] for k in sorted(tees_by_floor)},
            "tee_by_system": dict(sorted(tees_by_system.items())),
        },
        "preprocessing": {
            "tee_counts_by_stage": tee_counts_by_stage,
            "short_dangling_overshoots_trimmed": len(overshoot_trims),
            "trimmed_by_system": dict(
                sorted(Counter(trim.system for trim in overshoot_trims).items())
            ),
            "turn_display_valve_stubs_removed": len(valve_stub_removals),
            "valve_stub_removals_by_block": dict(
                sorted(
                    Counter(
                        removal.block_name for removal in valve_stub_removals
                    ).items()
                )
            ),
            "auto_air_vent_display_legs_removed": len(
                air_vent_leg_removals
            ),
            "auto_air_vent_removals_by_system": dict(
                sorted(
                    Counter(
                        removal.system for removal in air_vent_leg_removals
                    ).items()
                )
            ),
            "pipe_crossover_gaps_healed_without_junction": len(
                crossover_gap_bridges
            ),
            "pipe_crossover_bridges_by_system": dict(
                sorted(
                    Counter(item.system for item in crossover_gap_bridges).items()
                )
            ),
        },
        "parameters": {
            "point_tolerance": POINT_TOLERANCE,
            "endpoint_quantum": ENDPOINT_QUANTUM,
            "angle_tolerance_degrees": ANGLE_TOLERANCE_DEGREES,
            "max_dangling_overshoot_length": MAX_DANGLING_OVERSHOOT_LENGTH,
            "max_dangling_overshoot_ratio": MAX_DANGLING_OVERSHOOT_RATIO,
            "min_overshoot_intersection_angle_degrees": MIN_OVERSHOOT_INTERSECTION_ANGLE_DEGREES,
            "max_crossover_gap_length": MAX_CROSSOVER_GAP_LENGTH,
            "min_crossover_intersection_angle_degrees": MIN_CROSSOVER_INTERSECTION_ANGLE_DEGREES,
            "max_valve_display_stub_length": MAX_VALVE_DISPLAY_STUB_LENGTH,
            "turn_display_valve_block_names": sorted(
                TURN_DISPLAY_VALVE_BLOCK_NAMES
            ),
            "max_auto_air_vent_display_leg_length": MAX_AUTO_AIR_VENT_DISPLAY_LEG_LENGTH,
            "auto_air_vent_labels": sorted(AUTO_AIR_VENT_LABELS),
            "inferred_layout": {
                "anchor_label": LAYOUT_ANCHOR_LABEL,
                "offset_x": layout.offset_x,
                "offset_y": layout.offset_y,
                "floor_boundary_1_2": layout.floor_boundary_1_2,
                "floor_boundary_2_3": layout.floor_boundary_2_3,
                "left_detail_x_max": layout.left_detail_x_max,
                "left_detail_y_min": layout.left_detail_y_min,
                "right_detail_x_min": layout.right_detail_x_min,
                "right_detail_y_max": layout.right_detail_y_max,
            },
        },
    }


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.readfile(args.dxf)
    labels = equipment_labels(doc)
    layout = infer_drawing_layout(labels)

    raw_segments = collect_pipe_segments(doc)
    raw_tee_count = len(detect_tee_nodes(raw_segments, layout))
    segments, overshoot_trims = trim_short_dangling_overshoots(raw_segments)
    overshoot_tee_count = len(detect_tee_nodes(segments, layout))
    valve_regions = collect_turn_display_valve_regions(doc)
    segments, valve_stub_removals = remove_turn_display_valve_stubs(
        segments, valve_regions
    )
    valve_tee_count = len(detect_tee_nodes(segments, layout))
    air_vent_ports = collect_auto_air_vent_ports(doc)
    segments, air_vent_leg_removals = remove_auto_air_vent_display_legs(
        segments, air_vent_ports, layout
    )
    segments, crossover_gap_bridges = bridge_pipe_crossover_gaps(segments)
    equipment = detect_equipment_nodes(doc)
    tees = detect_tee_nodes(segments, layout)
    tee_counts_by_stage = {
        "raw": raw_tee_count,
        "after_overshoot_trim": overshoot_tee_count,
        "after_valve_stub_removal": valve_tee_count,
        "after_auto_air_vent_removal": len(tees),
        "after_crossover_gap_healing": len(tees),
    }

    summary = build_summary(
        equipment,
        tees,
        overshoot_trims,
        valve_stub_removals,
        air_vent_leg_removals,
        crossover_gap_bridges,
        layout,
        tee_counts_by_stage,
    )
    summary["source_file"] = str(args.dxf.resolve())
    (args.output_dir / "node_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_nodes_csv(args.output_dir / "nodes.csv", equipment, tees, layout)
    save_visualizations(args.output_dir, segments, equipment, tees, layout)

    print(json.dumps(summary["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
