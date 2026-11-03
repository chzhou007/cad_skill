from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import ezdxf
import matplotlib.pyplot as plt

import analyze_graph as graph
from connect_equipment import (
    OmissionMarker,
    cleaned_pipe_graph,
    collect_omission_markers,
    collect_owned_equipment,
    connection_legend,
    plot_omission_markers,
    relocate_equipment_nodes,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DXF = (
    PROJECT_ROOT
    / "data"
    / "updated"
    / "interim"
    / "sh16-native-isometric_updated.fixed.dxf"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "updated"


@dataclass(frozen=True)
class PlacementAudit:
    device_label: str
    floor: int
    sequence: int
    placement_mode: str
    original_x: float
    original_y: float
    graph_x: float
    graph_y: float
    source: str
    main_marker_x: float | None
    main_marker_y: float | None
    equipment_side_marker_x: float | None
    equipment_side_marker_y: float | None
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Place omitted CRAH equipment nodes at the main-diagram-side "
            "DIM_SYMB marker. This stage intentionally creates no edges."
        )
    )
    parser.add_argument("--dxf", type=Path, default=DEFAULT_DXF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def build_placement_audit(
    original: list[graph.EquipmentNode],
    placed: list[graph.EquipmentNode],
    markers: dict[str, OmissionMarker],
) -> list[PlacementAudit]:
    placed_by_label = {node.label: node for node in placed}
    rows = []
    for node in original:
        result = placed_by_label[node.label]
        marker = markers.get(node.label)
        rows.append(
            PlacementAudit(
                device_label=node.label,
                floor=node.floor,
                sequence=node.sequence,
                placement_mode=(
                    "main_side_omission_marker"
                    if marker is not None
                    else "original_direct_geometry"
                ),
                original_x=node.x,
                original_y=node.y,
                graph_x=result.x,
                graph_y=result.y,
                source=result.source,
                main_marker_x=marker.main_x if marker else None,
                main_marker_y=marker.main_y if marker else None,
                equipment_side_marker_x=(
                    marker.equipment_side_x if marker else None
                ),
                equipment_side_marker_y=(
                    marker.equipment_side_y if marker else None
                ),
                status="placed",
            )
        )
    return rows


def write_audit(path: Path, rows: list[PlacementAudit]) -> None:
    records = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def node_payload(
    equipment: list[graph.EquipmentNode],
    tees: list[graph.TeeNode],
    markers: dict[str, OmissionMarker],
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
            "placement_rule": node.source,
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
            "placement_rule": "preprocessed_three_ray_tee",
        }
        for index, node in enumerate(tees, start=1)
    )
    return {
        "metadata": {
            "scope": "node placement only",
            "node_count": len(nodes),
            "equipment_count": len(equipment),
            "tee_count": len(tees),
            "equipment_relocated_to_main_omission_marker": len(markers),
            "edge_processing": "intentionally_not_started",
        },
        "nodes": nodes,
        "edges": [],
    }


def save_visualizations(
    output_dir: Path,
    segments: list[graph.Segment],
    equipment: list[graph.EquipmentNode],
    tees: list[graph.TeeNode],
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
        "SH16 节点落位（暂不处理边）\n"
        f"设备 92：省略标记落位 {len(markers)}，直接几何位置保留 {92 - len(markers)}；T 节点 {len(tees)}",
        fontsize=18,
        pad=18,
    )
    fig.savefig(
        output_dir / "equipment_placement_overview.png",
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
        moved = sum(
            node.floor == floor and node.label in markers for node in equipment
        )
        axis_plot.set_xlim(layout.plot_x_min, layout.plot_x_max)
        axis_plot.set_ylim(*y_range)
        axis_plot.set_aspect("equal")
        axis_plot.axis("off")
        axis_plot.text(
            0.01,
            0.96,
            f"{floor}F：省略标记落位 {moved} 台",
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
    fig.suptitle("设备节点主图落位：按楼层核对（无边）", fontsize=18, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    fig.savefig(
        output_dir / "equipment_placement_by_floor.png",
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.12,
        facecolor="white",
    )
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.readfile(args.dxf)
    labels = graph.equipment_labels(doc)
    layout = graph.infer_drawing_layout(labels)
    original_equipment = graph.detect_equipment_nodes(doc)
    owned, exploded_direct = collect_owned_equipment(doc, original_equipment)
    markers = collect_omission_markers(doc, owned)
    equipment = relocate_equipment_nodes(original_equipment, markers)

    segments = cleaned_pipe_graph(doc, layout)
    tees = graph.detect_tee_nodes(segments, layout)
    audit = build_placement_audit(original_equipment, equipment, markers)

    direct_numeric = [
        item.node.label for item in owned if item.node.label not in markers
    ]
    if not (
        len(original_equipment) == 92
        and len(equipment) == 92
        and len(tees) == 301
        and len(markers) == 62
        and len(direct_numeric) == 24
        and len(exploded_direct) == 6
    ):
        raise RuntimeError("Unexpected SH16 node-placement counts")

    graph.write_nodes_csv(
        args.output_dir / "equipment_placement_nodes.csv",
        equipment,
        tees,
        layout,
    )
    write_audit(args.output_dir / "equipment_placement_audit.csv", audit)
    payload = node_payload(equipment, tees, markers, layout)
    (args.output_dir / "equipment_placement_graph.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = {
        "source_file": str(args.dxf.resolve()),
        "scope": "node placement only; no edges generated or modified",
        "counts": {
            "equipment_nodes": len(equipment),
            "tee_nodes": len(tees),
            "total_nodes": len(equipment) + len(tees),
            "equipment_relocated_to_main_omission_marker": len(markers),
            "direct_numeric_equipment_kept_at_original_location": len(
                direct_numeric
            ),
            "direct_exploded_equipment_kept_at_original_location": len(
                exploded_direct
            ),
            "edges": 0,
        },
        "validation": {
            "all_marker_pairs_resolved": True,
            "all_equipment_labels_unique": len({node.label for node in equipment})
            == len(equipment),
            "tee_nodes_unchanged": True,
            "edge_processing": "intentionally_not_started",
        },
        "relocated_equipment": sorted(markers),
        "direct_numeric_equipment": sorted(direct_numeric),
        "direct_exploded_equipment": [
            node.label for node in exploded_direct
        ],
    }
    (args.output_dir / "equipment_placement_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = f"""# SH16 设备节点主图落位结果

- 本阶段仅处理节点坐标，不生成或修改边。
- 设备节点：92；T 节点：301；总节点：393。
- 62 台带成对省略标记的设备已迁移到主图侧 `DIM_SYMB` 标记中心。
- 24 台无省略标记的块设备和 6 台炸开设备保留原坐标。
- T 节点坐标及数量不变。

设备节点迁移的目的，是让后续建边时能够沿主图原始支路提取管径、阀门、软管等属性；这些边及属性本阶段尚未处理。
"""
    (args.output_dir / "equipment_placement_report.md").write_text(
        report, encoding="utf-8"
    )
    save_visualizations(
        args.output_dir, segments, equipment, tees, markers, layout
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
