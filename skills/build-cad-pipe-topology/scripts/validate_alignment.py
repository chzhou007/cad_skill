from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a CAD-pipe-topology result against an alignment case."
    )
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--actual", type=Path)
    parser.add_argument("--skip-integrity", action="store_true")
    return parser.parse_args()


def nested_value(payload: dict[str, Any], dotted_key: str) -> Any:
    value: Any = payload
    for part in dotted_key.split("."):
        value = value[part]
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    args = parse_args()
    case_dir = args.case.resolve()
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    actual = (
        args.actual.resolve()
        if args.actual is not None
        else case_dir / "expected" / "outputs" / "edges"
    )
    failures: list[str] = []

    if not args.skip_integrity:
        for relative, expected_hash in manifest["sha256"].items():
            path = case_dir / relative
            if not path.exists():
                failures.append(f"missing fixture file: {relative}")
            elif sha256(path) != expected_hash:
                failures.append(f"fixture hash mismatch: {relative}")

    summary_path = actual / "edge_summary.json"
    if not summary_path.exists():
        failures.append(f"missing actual summary: {summary_path}")
    else:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for key, expected in manifest["summary_metrics"].items():
            try:
                observed = nested_value(summary, key)
            except (KeyError, TypeError):
                failures.append(f"missing summary metric: {key}")
                continue
            if observed != expected:
                failures.append(
                    f"summary metric {key}: expected {expected!r}, got {observed!r}"
                )

    for name in manifest["required_output_files"]:
        if not (actual / name).exists():
            failures.append(f"missing output file: {name}")

    nodes_path = actual / "topology_nodes.csv"
    edges_path = actual / "edges.csv"
    devices_path = actual / "edge_device_instances.csv"
    inventory_path = actual / "edge_equipment_by_type.csv"
    crossover_path = actual / "pipe_crossover_gap_bridges.csv"
    nodes = read_csv(nodes_path) if nodes_path.exists() else []
    edges = read_csv(edges_path) if edges_path.exists() else []
    devices = read_csv(devices_path) if devices_path.exists() else []
    inventory = read_csv(inventory_path) if inventory_path.exists() else []
    crossover_bridges = read_csv(crossover_path) if crossover_path.exists() else []

    observed_rows = {
        "topology_nodes.csv": len(nodes),
        "edges.csv": len(edges),
        "edge_device_instances.csv": len(devices),
        "pipe_crossover_gap_bridges.csv": len(crossover_bridges),
    }
    for name, expected in manifest["csv_row_counts"].items():
        if observed_rows.get(name) != expected:
            failures.append(
                f"row count {name}: expected {expected}, got {observed_rows.get(name)}"
            )

    names = [row["device_name"] for row in devices]
    duplicate_names = [name for name, count in Counter(names).items() if count > 1]
    if duplicate_names:
        failures.append(f"duplicate device names: {len(duplicate_names)}")
    unassigned = [row for row in devices if row["assignment_status"] != "assigned"]
    if unassigned:
        failures.append(f"unassigned device instances: {len(unassigned)}")

    node_ids = [row["node_id"] for row in nodes]
    edge_ids = [row["edge_id"] for row in edges]
    if len(node_ids) != len(set(node_ids)):
        failures.append("duplicate node IDs")
    if len(edge_ids) != len(set(edge_ids)):
        failures.append("duplicate edge IDs")
    node_id_set = set(node_ids)
    edge_id_set = set(edge_ids)
    bad_endpoints = [
        row["edge_id"]
        for row in edges
        if row["start_node_id"] not in node_id_set
        or row["end_node_id"] not in node_id_set
    ]
    if bad_endpoints:
        failures.append(f"edges with missing endpoint nodes: {len(bad_endpoints)}")
    bad_device_edges = [
        row["device_name"] for row in devices if row["edge_id"] not in edge_id_set
    ]
    if bad_device_edges:
        failures.append(f"devices referencing missing edges: {len(bad_device_edges)}")

    crossover_node_conflicts = []
    for bridge in crossover_bridges:
        crossing = (float(bridge["crossing_x"]), float(bridge["crossing_y"]))
        if any(
            math.dist((float(node["x"]), float(node["y"])), crossing) <= 0.2
            for node in nodes
        ):
            crossover_node_conflicts.append(crossing)
    if crossover_node_conflicts:
        failures.append(
            "pipe crossover coordinates promoted to nodes: "
            f"{len(crossover_node_conflicts)}"
        )

    # Geometry-specific expectations prevent count-only baselines from accepting
    # missing junctions or dropping their third incident branch.
    degree = Counter(endpoint for edge in edges
                     for endpoint in (edge["start_node_id"], edge["end_node_id"]))
    by_id = {node["node_id"]: node for node in nodes}
    for expected in manifest.get("junction_expectations", []):
        node = by_id.get(expected["node_id"])
        if node is None or node.get("node_type") != "physical_junction":
            failures.append(f"missing physical junction: {expected['node_id']}")
            continue
        if math.dist((float(node["x"]), float(node["y"])),
                     (expected["x"], expected["y"])) > 0.2:
            failures.append(f"junction coordinate mismatch: {expected['node_id']}")
        if degree[expected["node_id"]] != expected["degree"]:
            failures.append(f"junction degree mismatch: {expected['node_id']}")

    grouped_devices: dict[tuple[str, str], list[str]] = {}
    for row in devices:
        grouped_devices.setdefault(
            (row["edge_id"], row["equipment_type"]), []
        ).append(row["device_name"])
    grouped_inventory: dict[tuple[str, str], tuple[int, set[str]]] = {}
    for row in inventory:
        grouped_inventory[(row["edge_id"], row["equipment_type"])] = (
            int(row["device_count"]),
            {name for name in row["device_names"].split(";") if name},
        )
    if set(grouped_devices) != set(grouped_inventory):
        failures.append("device aggregation keys do not match instance keys")
    else:
        inconsistent_groups = 0
        for key, device_names in grouped_devices.items():
            count, inventory_names = grouped_inventory[key]
            if count != len(device_names) or inventory_names != set(device_names):
                inconsistent_groups += 1
        if inconsistent_groups:
            failures.append(
                f"device aggregation content mismatches: {inconsistent_groups}"
            )

    type_counts = Counter(row["equipment_type"] for row in devices)
    for name, expected in manifest["device_type_counts"].items():
        if type_counts[name] != expected:
            failures.append(
                f"device type {name}: expected {expected}, got {type_counts[name]}"
            )
    source_counts = Counter(row["source_kind"] for row in devices)
    for name, expected in manifest["source_kind_counts"].items():
        if source_counts[name] != expected:
            failures.append(
                f"source kind {name}: expected {expected}, got {source_counts[name]}"
            )

    if failures:
        print("ALIGNMENT FAILED")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("ALIGNMENT PASSED")
    print(
        json.dumps(
            {
                "case_id": manifest["case_id"],
                "nodes": len(nodes),
                "edges": len(edges),
                "edge_devices": len(devices),
                "ball_valves": type_counts["球阀"],
                "exploded_geometry": source_counts["exploded_geometry"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
