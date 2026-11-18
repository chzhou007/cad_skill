"""Formal family tail: native two-arm continuity, then exact pending-T resolution."""
import json
import subprocess
import sys
from pathlib import Path

from confirm_crossview_paths import encode, load, sha


def load_policy_map(path, eligible=None):
    if path is None:
        return {}
    path = Path(path).resolve()
    values = load(path)
    if not isinstance(values, dict) or (eligible is not None and set(values)-set(eligible)):
        raise ValueError('Unrecognized circle continuity family task')
    result = {}
    for task, settings in values.items():
        if (not isinstance(task, str) or not task or not isinstance(settings, dict)
                or set(settings) not in ({'continuity_policy'}, {'continuity_policy', 'pending_junction_policy'})):
            raise ValueError('Only continuity and optional pending junction policies are allowed')
        current = {}
        for key, value in settings.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Invalid circle continuity policy path')
            target = (Path(value) if Path(value).is_absolute() else path.parent/value).resolve()
            if not target.is_file():
                raise ValueError('Missing circle continuity policy')
            current[key] = target
        result[task] = current
    return result


def run_stage(source, graph, settings, task_root):
    source, graph, task_root = [Path(p).resolve() for p in (source, graph, task_root)]
    if not graph.is_relative_to(task_root):
        raise ValueError('Circle family parent must be the current task graph')
    if set(settings) not in ({'continuity_policy'}, {'continuity_policy', 'pending_junction_policy'}):
        raise ValueError('Circle family cannot override source, graph, components or output')
    from normalize_two_arm_circle_continuity import verify_output as verify_circle
    from resolve_pending_native_junctions import verify_output as verify_junction
    stages = [('continuity_policy', 'normalize_two_arm_circle_continuity.py', 'topology-two-arm-circle-continuity',
               'two-arm-circle-continuity-audit.json', verify_circle)]
    if 'pending_junction_policy' in settings:
        stages.append(('pending_junction_policy', 'resolve_pending_native_junctions.py', 'topology-pending-native-junctions',
                       'pending-native-junction-audit.json', verify_junction))
    receipts = []
    for key, script, folder, audit_name, verify in stages:
        policy = Path(settings[key]).resolve()
        devices = graph.parent/'assigned_edge_device_instances.csv'
        before = {k: sha(p) for k, p in dict(source=source, graph=graph, devices=devices, policy=policy).items()}
        destination = task_root/folder
        stage = task_root/'reports'/(folder+'-stage.json')
        if destination.exists() or stage.exists():
            raise FileExistsError('Circle family output already exists')
        command = [sys.executable, '-X', 'utf8', str(Path(__file__).with_name(script))]
        for flag, value in dict(source=source, graph=graph, devices=devices, policy=policy, output=destination).items():
            command += ['--'+flag, str(value)]
        subprocess.run(command, check=True)
        audit = verify(destination)
        if any(sha(p) != before[k] for k, p in dict(source=source, graph=graph, devices=devices, policy=policy).items()):
            raise ValueError('Circle family input changed during execution')
        target = destination/'graph_with_edges.json'
        if (audit['output_graph_sha256'] != sha(target) or audit['inputs']['graph']['sha256'] != before['graph']
                or audit['inputs']['source']['sha256'] != before['source'] or audit['human_accepted'] is not False
                or load(target).get('metadata', {}).get('hil_ready') is not False):
            raise ValueError('Circle family replay or invalidation differs')
        receipt = dict(status='native_stage_rebuilt_and_independently_replayed_downstream_pending',
            source_sha256=before['source'], parent_graph_sha256=before['graph'], graph_sha256=sha(target),
            artifact_directory=str(destination), audit_sha256=sha(destination/audit_name), entry_sha256=sha(__file__),
            recompute_required=['inventory', 'mapping', 'DN_scope', 'length_attributes', 'source_comparison', 'HIL'],
            physical_lengths_assigned=0, human_accepted=False, hil_ready=False)
        stage.parent.mkdir(parents=True, exist_ok=True)
        stage.write_bytes(encode(receipt))
        receipts.append(receipt)
        graph = target
    return graph, receipts
