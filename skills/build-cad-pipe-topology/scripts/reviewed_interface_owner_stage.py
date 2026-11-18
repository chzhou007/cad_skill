"""Formal family tail; task-owned local inputs, immutable expert evidence."""
import json
from pathlib import Path
import subprocess
import sys

from confirm_crossview_paths import load, sha, encode

SETTINGS = {'reply', 'receipt', 'definitions', 'selection'}
DESTINATION = 'topology-reviewed-interface-owners'
STAGE = 'reports/reviewed-interface-owners-stage.json'


def load_policy_map(path, eligible=None):
    if path is None:
        return {}
    path = Path(path).resolve()
    data = load(path)
    if not isinstance(data, dict) or (eligible is not None and set(data) - set(eligible)):
        raise ValueError('reviewed owner map contains unrecognized task IDs')
    result = {}
    for task, values in data.items():
        if not isinstance(task, str) or not task or not isinstance(values, dict) or set(values) != SETTINGS:
            raise ValueError('reviewed owner map accepts only pinned review evidence')
        if any(not isinstance(v, str) or not v.strip() for v in values.values()):
            raise ValueError('invalid reviewed owner evidence path')
        resolved = {k: (Path(v) if Path(v).is_absolute() else path.parent / v).resolve() for k, v in values.items()}
        if any(not p.is_file() for p in resolved.values()):
            raise ValueError('missing reviewed owner evidence')
        result[task] = resolved
    return result


def run_stage(source, graph, settings, task_root):
    source, graph, task_root = (Path(p).resolve() for p in (source, graph, task_root))
    if not graph.is_relative_to(task_root):
        raise ValueError('reviewed owner parent must be the current task graph')
    if set(settings) != SETTINGS:
        raise ValueError('reviewed owner entry cannot override local inputs or output')
    paths = dict(source=source, graph=graph, devices=graph.parent / 'assigned_edge_device_instances.csv',
                 **{k: Path(v).resolve() for k, v in settings.items()})
    before = {k: sha(v) for k, v in paths.items()}
    destination, stage = task_root / DESTINATION, task_root / STAGE
    if destination.exists() or stage.exists():
        raise FileExistsError('reviewed owner family output already exists')
    from attach_reviewed_interface_owners import verify_output, MODE
    command = [sys.executable, '-X', 'utf8', str(Path(__file__).with_name('attach_reviewed_interface_owners.py'))]
    for key, value in paths.items():
        command += ['--' + key, str(value)]
    subprocess.run(command + ['--output', str(destination)], check=True)
    audit = verify_output(destination)
    target = destination / 'graph_with_edges.json'
    current = load(target)
    scope = current['sourceReviewedInterfaceOwners']
    if any(sha(p) != before[k] for k, p in paths.items()):
        raise ValueError('reviewed owner inputs changed during execution')
    if (audit['mode'] != MODE or audit['output_graph_sha256'] != sha(target)
            or any(audit['inputs'][k]['sha256'] != before[k]
                   or Path(audit['inputs'][k]['path']).resolve() != p for k, p in paths.items())
            or scope.get('input_graph_sha256') != before['graph']
            or scope.get('source_sha256') != before['source']
            or scope.get('physical_ports_verified') is not False
            or scope.get('human_accepted') is not False
            or current.get('metadata', {}).get('hil_ready') is not False
            or current.get('derivedEvidenceInvalidation', {}).get('historical_annotations_preserved') is not True):
        raise ValueError('reviewed owner family evidence or invalidation differs')
    receipt = dict(status='reviewed_logical_owners_native_replayed_mapping_and_HIL_pending',
        source_sha256=before['source'], parent_graph_sha256=before['graph'], graph_sha256=sha(target),
        artifact_directory=str(destination), audit_sha256=sha(destination / 'reviewed-interface-owner-audit.json'),
        entry_sha256=sha(__file__), logical_service_links=len(scope['records']),
        equipment_owners=len({r['equipment_id'] for r in scope['records']}),
        recompute_required=current['derivedEvidenceInvalidation']['recompute'],
        physical_lengths_assigned=0, human_accepted=False, hil_ready=False)
    stage.parent.mkdir(parents=True, exist_ok=True)
    stage.write_bytes(encode(receipt))
    return target, audit
