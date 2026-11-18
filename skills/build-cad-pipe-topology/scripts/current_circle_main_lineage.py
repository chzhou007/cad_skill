"""Replay reviewed circle rays through subsequent source-bound splits/merges.

The historical reader remains unchanged. Only its main-membership dependency
is extended in a private namespace; native circle, branch, XYZ and ray guards
still execute on the current graph and original DXF.
"""
import types
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
from repair_confirmed_circle_junctions import slice_path
from source_reviewed_circle_branch_evidence import collect as original_collect
from source_reviewed_circle_branch_evidence import circle_rays as original_rays
from source_reviewed_circle_branch_evidence import main_membership as original_membership


def parent_graph(parents, digest, source_hash):
    selected = [p for p in parents if p.get('sha256') == digest]
    if len(selected) != 1 or sha(selected[0]['path']) != digest:
        raise ValueError('current circle lineage needs one unchanged original parent')
    graph = load(selected[0]['path'])
    if graph.get('metadata', {}).get('source_sha256') != source_hash:
        raise ValueError('circle lineage parent belongs to another source')
    return graph


def roots(graph):
    for key in ('sourceReviewedCircleJunctionRepair', 'userConfirmedCircleJunctionRepair', 'userConfirmedOverlappingBranches'):
        root = graph.get(key)
        seen = set()
        while isinstance(root, dict):
            if id(root) in seen:
                raise ValueError('cyclic current circle lineage roots')
            seen.add(id(root))
            yield key, root
            root = root.get('previous_repair')


def membership(doc, graph, edge, record, source_hash, parents, receipts, seen=()):
    if edge['edge_id'] in record.get('main_child_edges', []):
        return
    key = (sha_bytes(graph), edge['edge_id'])
    if key in seen:
        raise ValueError('cyclic current circle edge lineage')
    continuity = edge.get('source_circle_continuity')
    if continuity:
        root = graph.get('sourceTwoArmCircleContinuity', {})
        snapshots = continuity.get('prior_edge_snapshots', [])
        candidates = [p for p in parents if p.get('role') == 'two_arm_origin']
        if len(candidates) != 1:
            raise ValueError('merged circle main needs one pinned continuity origin')
        parent = parent_graph(parents, candidates[0]['sha256'], source_hash)
        from normalize_two_arm_circle_continuity import collect, normalize
        contacts = collect(doc, parent, [r['circle_handle'] for r in root.get('records', [])])
        expected, aliases = normalize(parent, contacts)
        if contacts != root.get('records') or aliases != root.get('edge_id_aliases'):
            raise ValueError('current merged circle source proof changed')
        generated = [e for e in expected['edges'] if e['edge_id'] == edge['edge_id']]
        fields = ('system', 'start_node_id', 'end_node_id', 'start_floor', 'end_floor',
                  'source_handles', 'path', 'path_points', 'attribute_paths', 'path_length', 'source_circle_continuity')
        if len(generated) != 1 or any(edge.get(k) != generated[0].get(k) for k in fields):
            raise ValueError('merged circle main differs from original native normalization')
        matching = [old for old in snapshots if old['edge_id'] in record.get('main_child_edges', [])]
        if len(matching) != 1:
            raise ValueError('merged main has no unique reviewed ancestor')
        old = matching[0]
        original = [e for e in parent['edges'] if e['edge_id'] == old['edge_id']]
        if original != [old] or aliases.get(old['edge_id']) != edge['edge_id']:
            raise ValueError('merged reviewed ancestor snapshot changed')
        original_membership(parent, old, record, source_hash)
        receipts.append(dict(kind='native_two_arm_merge', current_edge_id=edge['edge_id'],
            original_edge_id=old['edge_id'], parent_sha256=candidates[0]['sha256'], native_contacts_replayed=True))
        return
    split = edge.get('split_source_edge', {})
    parent_id, digest = split.get('edge_id'), split.get('source_graph_sha256')
    matches = [(name, root) for name, root in roots(graph)
        if root.get('input_graph_sha256') == digest and root.get('source_sha256') == source_hash
        and any(r.get('main_source_edge', r.get('main_edge')) == parent_id
                and edge['edge_id'] in r.get('main_child_edges', []) for r in root.get('records', []))]
    if len(matches) != 1:
        raise ValueError('current main split lacks one original repair owner')
    parent = parent_graph(parents, digest, source_hash)
    previous = [e for e in parent['edges'] if e['edge_id'] == parent_id]
    interval = split.get('interval_native_units')
    if len(previous) != 1 or previous[0].get('system') != edge.get('system') or not isinstance(interval, list) or len(interval) != 2:
        raise ValueError('current split main parent or interval differs')
    old = previous[0]
    if (edge.get('path') != slice_path(old['path'], *interval)
            or not set(edge.get('source_handles', [])) <= set(old.get('source_handles', []))):
        raise ValueError('current split main leaves its pinned original interval')
    # The old edge and its exact source interval remain immutable. Current ray
    # geometry is independently checked by the unchanged original circle reader.
    membership(doc, parent, old, record, source_hash, parents, receipts, seen + (key,))
    receipts.append(dict(kind='source_bound_main_split', repair_root=matches[0][0],
        current_edge_id=edge['edge_id'], original_edge_id=parent_id,
        parent_sha256=digest, interval_native_units=list(interval)))


def sha_bytes(value):
    import hashlib
    return hashlib.sha256(encode(value)).hexdigest()


def collect(doc, graph, node_id, source_hash, graph_hash, parents):
    receipts = []
    rays_namespace = dict(original_rays.__globals__)
    rays_namespace['main_membership'] = lambda g, e, r, sh: membership(doc, g, e, r, sh, parents, receipts)
    rays = types.FunctionType(original_rays.__code__, rays_namespace, original_rays.__name__)
    namespace = dict(original_collect.__globals__)
    namespace['circle_rays'] = rays
    reader = types.FunctionType(original_collect.__code__, namespace, original_collect.__name__)
    result = reader(doc, graph, node_id, source_hash, graph_hash)
    if not receipts:
        raise ValueError('current-circle extension requires an actual source-bound lineage change')
    result['current_main_lineage'] = receipts
    result['historical_reader_or_globals_changed'] = False
    result['physical_values_assigned'] = 0
    return result


def implementation_hashes():
    return {name: sha(Path(__file__).with_name(name)) for name in (
        Path(__file__).name, 'source_reviewed_circle_branch_evidence.py',
        'repair_confirmed_circle_junctions.py', 'normalize_two_arm_circle_continuity.py')}
