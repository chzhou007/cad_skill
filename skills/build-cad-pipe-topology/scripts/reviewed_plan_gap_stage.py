"""Formal family tail for exact reviewed plan discontinuities."""
import subprocess
import sys
from pathlib import Path

from confirm_crossview_paths import load, sha, encode

SETTINGS = {'reply', 'receipt', 'definitions', 'pair', 'overview', 'native_context', 'policy'}
DESTINATION = 'topology-reviewed-drawing-gaps'
STAGE = 'reports/reviewed-drawing-gap-stage.json'


def load_policy_map(path, eligible=None):
    if path is None:
        return {}
    path = Path(path).resolve()
    data = load(path)
    if not isinstance(data, dict) or (eligible is not None and set(data) - set(eligible)):
        raise ValueError('reviewed gap map contains unrecognized task IDs')
    result = {}
    for task, values in data.items():
        if not isinstance(task, str) or not task or not isinstance(values, dict) or set(values) != SETTINGS:
            raise ValueError('reviewed gap map accepts only original review inputs and policy')
        if any(not isinstance(v, str) or not v.strip() for v in values.values()):
            raise ValueError('invalid reviewed gap evidence path')
        resolved = {k: (Path(v) if Path(v).is_absolute() else path.parent / v).resolve() for k, v in values.items()}
        if any(not p.is_file() for p in resolved.values()):
            raise ValueError('missing reviewed gap evidence')
        result[task] = resolved
    return result


def run_stage(source, graph, settings, task_root):
    source, graph, task_root = (Path(p).resolve() for p in (source, graph, task_root))
    if not graph.is_relative_to(task_root):
        raise ValueError('reviewed gap parent must be the current task graph')
    if set(settings) != SETTINGS:
        raise ValueError('reviewed gap entry cannot override local inputs or output')
    paths = dict(source=source, graph=graph, devices=graph.parent / 'assigned_edge_device_instances.csv',
                 **{k: Path(v).resolve() for k, v in settings.items()})
    before = {k: sha(v) for k, v in paths.items()}
    destination, stage = task_root / DESTINATION, task_root / STAGE
    if destination.exists() or stage.exists():
        raise FileExistsError('reviewed gap family output already exists')
    from reconstruct_reviewed_plan_gaps import verify_output, MODE
    command = [sys.executable, '-X', 'utf8', str(Path(__file__).with_name('reconstruct_reviewed_plan_gaps.py'))]
    for key, value in paths.items():
        command += ['--' + key.replace('_', '-'), str(value)]
    subprocess.run(command + ['--output', str(destination)], check=True)
    audit = verify_output(destination)
    target = destination / 'graph_with_edges.json'
    current = load(target)
    scope = current['sourceReviewedDrawingGapContinuity']
    if any(sha(p) != before[k] for k, p in paths.items()):
        raise ValueError('reviewed gap inputs changed during execution')
    if (audit['mode'] != MODE or audit['output_graph_sha256'] != sha(target)
            or any(audit['inputs'][k]['sha256'] != before[k]
                   or Path(audit['inputs'][k]['path']).resolve() != p for k, p in paths.items())
            or scope.get('input_graph_sha256') != before['graph'] or scope.get('source_sha256') != before['source']
            or scope.get('physical_Ts_added') != 0 or scope.get('physical_lengths_assigned') != 0
            or scope.get('human_accepted') is not False or scope.get('supply_return_independent') is not True
            or current.get('metadata', {}).get('hil_ready') is not False
            or current.get('derivedEvidenceInvalidation', {}).get('historical_annotations_preserved') is not True):
        raise ValueError('reviewed gap family evidence or invalidation differs')
    receipt = dict(status='reviewed_drawing_gap_routes_native_replayed_mapping_and_HIL_pending',
        source_sha256=before['source'], parent_graph_sha256=before['graph'], graph_sha256=sha(target),
        artifact_directory=str(destination), audit_sha256=sha(destination / 'reviewed-drawing-gap-audit.json'),
        entry_sha256=sha(__file__), logical_continuations=len(scope['records']),
        retired_drawing_terminals=len(scope['retired_node_snapshots']), physical_Ts_added=0,
        recompute_required=current['derivedEvidenceInvalidation']['recompute'],
        physical_lengths_assigned=0, human_accepted=False, hil_ready=False)
    stage.parent.mkdir(parents=True, exist_ok=True)
    stage.write_bytes(encode(receipt))
    return target, audit
