"""Consume new logical ownership before retained native topology ancestors."""
import copy
from pathlib import Path
import sys

OWNER = Path(__file__).resolve().parents[2] / 'build-cad-pipe-topology/scripts'


def check(root, report, graph_hash, graph_path):
    if str(OWNER) not in sys.path:
        sys.path.insert(0, str(OWNER))
    from attach_reviewed_interface_owners import verify_output, MODE
    from reviewed_interface_owner_stage import DESTINATION, STAGE
    from confirm_crossview_paths import load, sha
    from source_comparison_gate import check as check_parent, graph_comparison_blockers
    root, path = Path(root).resolve(), Path(graph_path).resolve()
    if path.name != 'graph_with_edges.json' or path.parent not in (root, root / DESTINATION):
        raise ValueError('reviewed owner graph outside declared stage')
    audit = verify_output(path.parent)
    graph = load(path)
    scope = graph['sourceReviewedInterfaceOwners']
    parent = Path(audit['inputs']['graph']['path']).resolve()
    parent_hash = audit['inputs']['graph']['sha256']
    if (audit['mode'] != MODE or sha(path) != graph_hash or audit['output_graph_sha256'] != graph_hash
            or sha(parent) != parent_hash or scope.get('input_graph_sha256') != parent_hash
            or scope.get('source_sha256') != audit['inputs']['source']['sha256']
            or scope.get('physical_ports_verified') is not False or scope.get('human_accepted') is not False
            or graph.get('metadata', {}).get('hil_ready') is not False):
        raise ValueError('reviewed owner evidence or invalidation differs')
    if path.parent != root:
        stage = load(root / STAGE)
        if (stage.get('graph_sha256') != graph_hash or stage.get('parent_graph_sha256') != parent_hash
                or stage.get('source_sha256') != scope['source_sha256']
                or stage.get('artifact_directory') != str(path.parent)
                or stage.get('audit_sha256') != sha(path.parent / 'reviewed-interface-owner-audit.json')
                or stage.get('entry_sha256') != sha(OWNER / 'reviewed_interface_owner_stage.py')
                or stage.get('hil_ready') is not False):
            raise ValueError('stale reviewed owner family stage receipt')
    parent_mode = audit['proof']['parent_mode']
    if parent_mode not in ('native_circle_path_normalization', 'inherited_wave_pair_continuity'):
        raise ValueError('unsupported reviewed owner parent comparison mode')
    # The historical normalization consumer owns its artifact directory;
    # the wave consumer also supports a receipt under the family task root.
    parent_root = parent.parent if parent_mode == 'native_circle_path_normalization' else (
        parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent)
    result = copy.deepcopy(check_parent(report, parent_hash, parent_root, parent))
    result['reviewed_interface_owner_parent_comparison'] = copy.deepcopy(result)
    if result['errors']:
        result.update(status='failed', graph_sha256=graph_hash, hil_ready=False, human_accepted=False,
            reviewed_interface_owner_stage=dict(source_replay='passed', parent_comparison_failed=True,
                parent_graph_sha256=parent_hash, whole_source_comparison_complete=False, human_accepted=False))
        return result
    previous = result.get('graph_unresolved_node_blockers', [])
    current, _ = graph_comparison_blockers(graph)
    retired = {r['retired_interface_id'] for r in scope['records']}
    old_ids = {r['node_id'] for r in previous}
    new_ids = {r['node_id'] for r in current}
    if not old_ids - new_ids <= retired or new_ids - old_ids:
        raise ValueError('reviewed ownership changed an unrelated unresolved node')
    old_message = f'{len(previous)} graph nodes have unresolved source-terminal or equipment-overlap semantics'
    result['pending'] = [m for m in result['pending'] if m != old_message]
    if current:
        result['pending'].append(f'{len(current)} graph nodes have unresolved source-terminal or equipment-overlap semantics')
    result['graph_unresolved_node_blockers'] = current
    result['pending'].append('reviewed logical equipment owners checked; physical ports, branch inventory, mapping, DN/length and HIL require revalidation')
    result.update(status='failed' if result['errors'] else 'pending', graph_sha256=graph_hash,
        hil_ready=False, human_accepted=False, reviewed_interface_owner_stage=dict(
            source_replay='passed', parent_graph_sha256=parent_hash, logical_service_links=len(scope['records']),
            equipment_owners=len({r['equipment_id'] for r in scope['records']}),
            retired_interfaces=sorted(retired), physical_lengths_assigned=0,
            unrelated_parent_issues_preserved=True, whole_source_comparison_complete=False, human_accepted=False))
    return result
