"""Consume reviewed path reconstruction before retained circle/T ancestry."""
import copy
from pathlib import Path
import sys

OWNER = Path(__file__).resolve().parents[2] / 'build-cad-pipe-topology/scripts'


def check(root, report, graph_hash, graph_path):
    if str(OWNER) not in sys.path:
        sys.path.insert(0, str(OWNER))
    from reconstruct_reviewed_plan_gaps import verify_output, MODE
    from reviewed_plan_gap_stage import DESTINATION, STAGE
    from confirm_crossview_paths import load, sha
    from source_comparison_gate import check as check_parent, graph_comparison_blockers
    root, path = Path(root).resolve(), Path(graph_path).resolve()
    if path.name != 'graph_with_edges.json' or path.parent not in (root, root / DESTINATION):
        raise ValueError('reviewed gap graph outside declared stage')
    audit = verify_output(path.parent)
    graph = load(path)
    scope = graph['sourceReviewedDrawingGapContinuity']
    parent = Path(audit['inputs']['graph']['path']).resolve()
    parent_hash = audit['inputs']['graph']['sha256']
    if (audit['mode'] != MODE or sha(path) != graph_hash or audit['output_graph_sha256'] != graph_hash
            or sha(parent) != parent_hash or scope.get('input_graph_sha256') != parent_hash
            or scope.get('source_sha256') != audit['inputs']['source']['sha256']
            or scope.get('physical_Ts_added') != 0 or scope.get('physical_lengths_assigned') != 0
            or scope.get('supply_return_independent') is not True or scope.get('human_accepted') is not False
            or graph.get('metadata', {}).get('hil_ready') is not False):
        raise ValueError('reviewed gap evidence or invalidation differs')
    if path.parent != root:
        stage = load(root / STAGE)
        if (stage.get('graph_sha256') != graph_hash or stage.get('parent_graph_sha256') != parent_hash
                or stage.get('source_sha256') != scope['source_sha256']
                or stage.get('artifact_directory') != str(path.parent)
                or stage.get('audit_sha256') != sha(path.parent / 'reviewed-drawing-gap-audit.json')
                or stage.get('entry_sha256') != sha(OWNER / 'reviewed_plan_gap_stage.py')
                or stage.get('hil_ready') is not False):
            raise ValueError('stale reviewed gap family stage receipt')
    parent_root = parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
    result = copy.deepcopy(check_parent(report, parent_hash, parent_root, parent))
    result['reviewed_drawing_gap_parent_comparison'] = copy.deepcopy(result)
    if result['errors']:
        result.update(status='failed', graph_sha256=graph_hash, hil_ready=False, human_accepted=False,
            reviewed_drawing_gap_stage=dict(source_replay='passed', parent_comparison_failed=True,
                parent_graph_sha256=parent_hash, whole_source_comparison_complete=False, human_accepted=False))
        return result
    previous = result.get('graph_unresolved_node_blockers', [])
    current, _ = graph_comparison_blockers(graph)
    retired = {n['node_id'] for n in scope['retired_node_snapshots']}
    old_ids, new_ids = [{n['node_id'] for n in rows} for rows in (previous, current)]
    if old_ids - new_ids != retired or new_ids - old_ids:
        raise ValueError('reviewed gap changed an unrelated unresolved node')
    message = f'{len(previous)} graph nodes have unresolved source-terminal or equipment-overlap semantics'
    result['pending'] = [v for v in result['pending'] if v != message]
    if current:
        result['pending'].append(f'{len(current)} graph nodes have unresolved source-terminal or equipment-overlap semantics')
    result['pending'].append('reviewed drawing gap routes checked; current branch inventory, mapping, DN/length and HIL require revalidation')
    result.update(status='pending', graph_sha256=graph_hash, graph_unresolved_node_blockers=current,
        hil_ready=False, human_accepted=False, reviewed_drawing_gap_stage=dict(source_replay='passed',
            parent_graph_sha256=parent_hash, logical_continuations=len(scope['records']),
            retired_drawing_terminals=sorted(retired), physical_Ts_added=0, physical_lengths_assigned=0,
            unrelated_parent_issues_preserved=True, whole_source_comparison_complete=False, human_accepted=False))
    return result
