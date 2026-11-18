"""Formal ceiling entry for source-calibrated confirmed-view ownership."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def load_policy_map(path, eligible=None):
    if path is None:
        return {}
    path = Path(path)
    values = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(values, dict) or any(
        not isinstance(k, str) or not k or not isinstance(v, str) or not v.strip()
        for k, v in values.items()
    )):
        raise ValueError('invalid source sideview equipment ownership map')
    if eligible is not None and set(values) - set(eligible):
        raise ValueError('sideview ownership map contains unrecognized ceiling task IDs')
    return {k: (Path(v) if Path(v).is_absolute() else path.resolve().parent / v)
            for k, v in values.items()}


def run_stage(source, graph, policy, task_root):
    from reconstruct_sideview_equipment_ownership import verify_output
    graph = Path(graph).resolve()
    task_root = Path(task_root).resolve()
    destination = task_root / 'topology-source-sideview-equipment-ownership'
    subprocess.run([
        sys.executable, '-X', 'utf8',
        str(Path(__file__).with_name('reconstruct_sideview_equipment_ownership.py')),
        '--source', str(source), '--graph', str(graph),
        '--devices', str(graph.parent / 'assigned_edge_device_instances.csv'),
        '--policy', str(policy), '--output', str(destination)
    ], check=True)
    audit = verify_output(destination)
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    receipt = dict(
        status='native_confirmed_sideview_logical_ownership_source_checked',
        source_sha256=digest(source), parent_graph_sha256=digest(graph),
        graph_sha256=audit['output_graph_sha256'], artifact_directory=str(destination),
        audit_sha256=digest(destination / 'sideview-equipment-ownership-audit.json'),
        physical_ports_verified=False, detail_view_metric_verified=False,
        human_accepted=False, hil_ready=False)
    report = task_root / 'reports/source-sideview-equipment-ownership-stage.json'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return destination / 'graph_with_edges.json', audit
