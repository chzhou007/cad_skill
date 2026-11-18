"""Replay local continuity descendants before their unchanged source ancestor."""
import copy
import hashlib
import json
import sys
from pathlib import Path

OWNER = Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def check(root, report, graph_hash, graph_path):
    if str(OWNER) not in sys.path:
        sys.path.insert(0, str(OWNER))
    from source_comparison_gate import check as check_parent, graph_comparison_blockers
    root, graph_path = Path(root).resolve(), Path(graph_path).resolve()
    graph = load(graph_path)
    pending_T = 'sourcePendingNativeJunctionResolution' in graph
    folder = 'topology-pending-native-junctions' if pending_T else 'topology-two-arm-circle-continuity'
    audit_name = 'pending-native-junction-audit.json' if pending_T else 'two-arm-circle-continuity-audit.json'
    if graph_path.name != 'graph_with_edges.json' or graph_path.parent not in (root, root/folder):
        raise ValueError('Circle continuity graph outside its declared stage')
    if pending_T:
        from resolve_pending_native_junctions import verify_output
        scope = graph['sourcePendingNativeJunctionResolution']
        resolved = {r['node_id'] for r in scope['records']}
        if scope.get('added_nodes') != 0 or scope.get('added_edges') != 0 or scope.get('physical_lengths_assigned') != 0:
            raise ValueError('Pending T stage changed physical inventory or assigned length')
    else:
        from normalize_two_arm_circle_continuity import verify_output
        scope = graph['sourceTwoArmCircleContinuity']
        resolved = {n['node_id'] for n in scope['retired_nodes']}
        if scope.get('physical_Ts_added') != 0 or scope.get('physical_connector_lengths_assigned') != 0:
            raise ValueError('Two-arm continuation invented a T or physical connector length')
    audit = verify_output(graph_path.parent)
    parent = Path(audit['inputs']['graph']['path']).resolve()
    parent_hash = audit['inputs']['graph']['sha256']
    if (audit['output_graph_sha256'] != graph_hash or digest(graph_path) != graph_hash or digest(parent) != parent_hash
            or scope.get('human_accepted') is not False or graph.get('metadata', {}).get('hil_ready') is not False
            or not graph.get('derivedEvidenceInvalidation', {}).get('historical_annotations_preserved')):
        raise ValueError('Circle continuity evidence or invalidation differs')
    if graph_path.parent != root:
        stage = load(root/'reports'/(folder+'-stage.json'))
        if (stage.get('graph_sha256') != graph_hash or stage.get('parent_graph_sha256') != parent_hash
                or stage.get('source_sha256') != audit['inputs']['source']['sha256']
                or stage.get('artifact_directory') != str(graph_path.parent)
                or stage.get('audit_sha256') != digest(graph_path.parent/audit_name)
                or stage.get('entry_sha256') != digest(OWNER/'plan_circle_continuity_family_stage.py')
                or stage.get('hil_ready') is not False):
            raise ValueError('Stale circle family stage receipt')
    parent_root = parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
    result = copy.deepcopy(check_parent(report, parent_hash, parent_root, parent))
    result['plan_circle_continuity_parent_comparison'] = copy.deepcopy(result)
    previous = result.get('graph_unresolved_node_blockers', [])
    current, _ = graph_comparison_blockers(graph)
    old_ids, new_ids = [{n['node_id'] for n in rows} for rows in (previous, current)]
    if not (old_ids-new_ids) <= resolved or new_ids-old_ids:
        raise ValueError('Continuity stage changed unrelated unresolved semantics')
    message = f'{len(previous)} graph nodes have unresolved source-terminal or equipment-overlap semantics'
    result['pending'] = [v for v in result['pending'] if v != message]
    if current:
        result['pending'].append(f'{len(current)} graph nodes have unresolved source-terminal or equipment-overlap semantics')
    result['pending'].append('local circle/junction reconstruction replayed; inventory, mapping, DN/length fusion and HIL must use the new graph version')
    result.update(status='failed' if result['errors'] else 'pending', graph_sha256=graph_hash,
                  graph_unresolved_node_blockers=current, hil_ready=False)
    result['pending_native_junction_stage' if pending_T else 'two_arm_circle_continuity_stage'] = dict(
        source_replay='passed', parent_graph_sha256=parent_hash, resolved_temporary_node_ids=sorted(resolved),
        physical_lengths_assigned=0, unrelated_parent_issues_preserved=True,
        current_full_source_comparison_complete=False, human_accepted=False)
    return result
