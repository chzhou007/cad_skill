"""Replay original native calibration fragments and bind current-graph targets.

An old control fragment can now belong to a longer merged edge. Calibration
must retain its original local reading scope; assigning that control to the
whole new edge broadens annotation competition and is not a valid rebase.
"""
import copy
import types

from calibrated_direct_dn_evidence import collect as calibrated_collect
from source_direct_dn_evidence import collect as strict_collect


def control_lineage(graph, original, policy, source_hash, graph_hash, original_hash):
    if (policy.get('source_sha256') != source_hash or policy.get('graph_sha256') != original_hash
            or graph.get('metadata', {}).get('source_sha256') != source_hash
            or original.get('metadata', {}).get('source_sha256') != source_hash):
        raise ValueError('Calibration source or original graph differs')
    before = {e['edge_id']: e for e in original['edges']}
    after = {e['edge_id']: e for e in graph['edges']}
    if len(before) != len(original['edges']) or len(after) != len(graph['edges']):
        raise ValueError('Duplicate calibration graph identities')
    aliases = graph.get('sourceTwoArmCircleContinuity', {}).get('edge_id_aliases', {})
    archived = {e['edge_id']: e for edge in graph['edges'] for e in edge.get('source_circle_continuity', {}).get('prior_edge_snapshots', [])}
    rows = []
    for spec in policy.get('controls', []):
        old_id = spec['edge_id']; old = before.get(old_id)
        current_id = aliases.get(old_id, old_id); current = after.get(current_id)
        if old is None or current is None or spec['source_line_handle'] not in old.get('source_handles', []) or spec['source_line_handle'] not in current.get('source_handles', []):
            raise ValueError('Native calibration control owner is missing')
        if old_id != current_id:
            if archived.get(old_id) != old:
                raise ValueError('Retired calibration control fragment changed')
        elif any(old.get(k) != current.get(k) for k in ('system', 'source_handles', 'path', 'path_points', 'attribute_paths', 'path_length')):
            raise ValueError('Unmerged calibration control source geometry changed')
        rows.append(dict(text_handle=spec['text_handle'], source_line_handle=spec['source_line_handle'],
            original_edge_id=old_id, current_edge_id=current_id, original_control_scope_retained=True,
            current_whole_edge_DN_assigned=False, original_graph_sha256=original_hash, current_graph_sha256=graph_hash))
    for target in policy.get('selections', []):
        old = before.get(target['edge_id']); current = after.get(target['edge_id'])
        if old is None or current is None or any(old.get(k) != current.get(k) for k in ('system', 'source_handles', 'attribute_paths')):
            raise ValueError('Changed target needs a dedicated current segment binding')
    return rows


def collect(doc, graph, original, origin_policy, source_hash, graph_hash, original_hash):
    lineage = control_lineage(graph, original, origin_policy, source_hash, graph_hash, original_hash)
    controls = {row['text_handle']: row for row in origin_policy.get('controls', [])}
    by_text = {row['text_handle']: row for row in lineage}
    current_policy = copy.deepcopy(origin_policy)
    current_policy['graph_sha256'] = graph_hash

    def native_control(document, current, selection, sh, gh):
        specs = selection.get('selections', [])
        if (current is not graph or sh != source_hash or gh != graph_hash or len(specs) != 1
                or specs[0] != controls.get(specs[0]['text_handle'])):
            raise ValueError('Control reader cannot bypass a target or another source scope')
        reading = dict(selection, graph_sha256=original_hash)
        result = strict_collect(document, original, reading, sh, original_hash)
        for row in result['observations']:
            row['native_control_fragment_scope'] = copy.deepcopy(by_text[row['source_text']['handle']])
        return result

    # Use an explicit private dependency namespace. Historical collectors and
    # their process globals remain unchanged for every other consumer.
    namespace = dict(calibrated_collect.__globals__)
    namespace['strict_collect'] = native_control
    current_reader = types.FunctionType(calibrated_collect.__code__, namespace, calibrated_collect.__name__)
    result = current_reader(doc, graph, current_policy, source_hash, graph_hash)
    result['native_calibration_control_rebase'] = dict(
        original_graph_sha256=original_hash, current_graph_sha256=graph_hash, controls=lineage,
        source_controls_replayed=True, current_targets_replayed=True,
        original_policy_or_graph_mutated=False, collector_globals_changed=False,
        target_annotation_guards_unchanged=True, current_whole_edge_DN_assigned=0, human_accepted=False)
    return result
