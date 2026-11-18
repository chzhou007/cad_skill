"""Restore explicitly reviewed collinear same-service drafting discontinuities."""
import argparse
import collections
import copy
import csv
import importlib
import math
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from reviewed_source_question import bind_question
from inherited_wave_pair_continuity import contact as native_pipe_contact, csv_bytes
from native_path_coverage_audit import audit as native_path_audit
from normalize_two_arm_circle_continuity import reassign_components
from edge_endpoint_semantics import reconcile

MODE = 'explicit_reviewed_same_service_plan_gap_continuity_v1'
KEYS = ('source', 'graph', 'devices', 'reply', 'receipt', 'definitions', 'pair', 'overview', 'native_context')
ALLOWED = {'edge_id', 'start_node_id', 'end_node_id', 'edge_type', 'system', 'start_floor', 'end_floor',
           'path', 'attribute_paths', 'path_length', 'source_handles', 'equipment_counts', 'equipment_names',
           'path_points', 'endpoint_semantics', 'start_port_id', 'end_port_id'}


def source_pairs(doc, graph, question):
    if question['answer']['decision'] != '两处均各自连续，供回水独立':
        raise ValueError('explicit independent continuity confirmation required')
    scope = question['source_evidence']
    nodes = {n['node_id']: n for n in graph['nodes']}
    edges = {e['edge_id']: e for e in graph['edges']}
    proof = []
    used = set()
    for system in ('supply', 'return'):
        pair = scope[system + '_nodes']
        if len(pair) != 2 or len(set(pair)) != 2 or used.intersection(pair):
            raise ValueError('reviewed paired endpoint scope is incomplete')
        used.update(pair)
        contacts, incident = [], []
        for nid in pair:
            n = nodes[nid]
            found = [e for e in edges.values() if nid in (e['start_node_id'], e['end_node_id'])]
            if (n.get('system') != system or n.get('subtype') != 'unresolved_source_terminal' or len(found) != 1):
                raise ValueError('reviewed gap endpoint system or degree differs')
            edge = found[0]
            if edge['system'] != system or set(edge) - ALLOWED:
                raise ValueError('reviewed gap has unsupported attributes or service')
            c = native_pipe_contact(doc, edge, [n['x'], n['y']], system)
            contacts.append(c)
            incident.append(edge['edge_id'])
        if incident[0] == incident[1] or nodes[pair[0]]['floor'] != nodes[pair[1]]['floor']:
            raise ValueError('reviewed continuity cannot collapse a route or join floors')
        a, b = [c['XYZ'] for c in contacts]
        distance = math.dist(a, b)
        if (distance <= .05 or abs(distance - scope['gap_drawing_units']) > .05 or abs(a[2] - b[2]) > .05):
            raise ValueError('reviewed graphical gap or native Z differs')
        for point, target, c in [(a, b, contacts[0]), (b, a, contacts[1])]:
            other = max(c['line_XYZ'], key=lambda p: math.dist(p, point))
            outward = [point[i] - other[i] for i in range(3)]
            delta = [target[i] - point[i] for i in range(3)]
            norm = math.sqrt(sum(x*x for x in outward))
            projection = sum(x*y for x, y in zip(outward, delta)) / norm
            residual = math.sqrt(sum((delta[i] - projection*outward[i]/norm)**2 for i in range(3)))
            if projection <= 0 or residual > .05:
                raise ValueError('native endpoints do not face across the same collinear gap')
        coverage = native_path_audit(doc, graph, dict(source_sha256=scope['source_sha256'],
            graph_sha256=scope['graph_sha256'], edges=incident), scope['source_sha256'], scope['graph_sha256'])
        if any(s['status'] != 'single_source_line_covers' for e in coverage['edges'] for s in e['segments']):
            raise ValueError('original pipe fragment lacks unique native source coverage')
        proof.append(dict(system=system, nodes=pair, edge_ids=incident, contacts=contacts,
            gap_drawing_units=distance, physical_gap_length_mm=None, source_coverage=coverage,
            question_id=question['id'], explicit_answer=question['answer']))
    return proof


def merge(graph, rows, proofs, retained, source_hash, graph_hash):
    out = copy.deepcopy(graph)
    nodes = {n['node_id']: n for n in graph['nodes']}
    edges = {e['edge_id']: e for e in graph['edges']}
    selected, retired, aliases, replacements, records = set(), set(), {}, {}, []
    for proof in proofs:
        system, pair, ids = proof['system'], proof['nodes'], proof['edge_ids']
        keep = retained[system]
        if keep not in ids or len(set(ids)) != 2 or selected.intersection(ids):
            raise ValueError('retained edge or independent pair scope differs')
        selected.update(ids)
        i = ids.index(keep)
        j = 1-i
        left, right = edges[ids[i]], edges[ids[j]]
        if any(set(e) - ALLOWED for e in (left, right)):
            raise ValueError('edge attributes require explicit composition before continuity')
        if any(e['system'] != system for e in (left, right)):
            raise ValueError('supply and return cannot be merged')
        outer = lambda e, n: e['end_node_id'] if e['start_node_id'] == n else e['start_node_id']
        start, end = outer(left, pair[i]), outer(right, pair[j])
        if start == end or start in pair or end in pair:
            raise ValueError('reviewed fragment chain is not an open route')
        def oriented(edge, first):
            paths = copy.deepcopy(edge['attribute_paths'])
            display = copy.deepcopy(edge['path_points'])
            if edge['start_node_id'] != first:
                paths = [list(reversed(p)) for p in reversed(paths)]
                display.reverse()
            return paths, display
        first_paths, first_display = oriented(left, start)
        last_paths, last_display = oriented(right, pair[j])
        paths = first_paths + last_paths
        names = left['equipment_names'] + right['equipment_names']
        if len(names) != len(set(names)):
            raise ValueError('inline component is duplicated across fragments')
        native_length = sum(math.dist(a, b) for path in paths for a, b in zip(path, path[1:]))
        if abs(native_length - left['path_length'] - right['path_length']) > .05:
            raise ValueError('original native pipe length is not conserved')
        edge = copy.deepcopy(left)
        for side in ('start', 'end'):
            edge.pop(side + '_port_id', None)
        edge.update(start_node_id=start, end_node_id=end, start_floor=nodes[start]['floor'], end_floor=nodes[end]['floor'],
            path=first_display+last_display, path_points=first_display+last_display, attribute_paths=paths,
            path_length=native_length, drawing_path_length=sum(math.dist(a,b) for a,b in zip(first_display+last_display,(first_display+last_display)[1:])),
            path_length_scope='known_native_pipe_fragments_excluding_reviewed_drawing_gap', path_length_complete=False,
            physical_length='unknown', physical_length_mm=None, connection_mode='source_reviewed_drawing_gap_continuity',
            source_handles=list(dict.fromkeys(left['source_handles']+right['source_handles'])), equipment_names=names,
            equipment_counts=dict(collections.Counter(left['equipment_counts'])+collections.Counter(right['equipment_counts'])))
        for side, nid, original in [('start', start, left), ('end', end, right)]:
            original_side = 'start' if original['start_node_id'] == nid else 'end'
            if original.get(original_side + '_port_id'):
                edge[side + '_port_id'] = original[original_side + '_port_id']
        record = dict(proof, retained_edge=keep, retired_edge=right['edge_id'], source_sha256=source_hash,
            input_graph_sha256=graph_hash, original_edge_snapshots=[copy.deepcopy(edges[eid]) for eid in ids],
            physical_Ts_added=0, physical_gap_length_mm=None, human_accepted=False)
        edge['reviewed_drawing_gap_continuity'] = copy.deepcopy(record)
        replacements[keep] = edge
        retired.update(pair)
        aliases[right['edge_id']] = keep
        records.append(record)
    out['nodes'] = [n for n in out['nodes'] if n['node_id'] not in retired]
    typed, _ = reconcile(dict(nodes=out['nodes'], edges=list(replacements.values()), boundary_anchors=out.get('boundary_anchors', [])))
    replacements = {e['edge_id']: e for e in typed['edges']}
    out['edges'] = [replacements.get(e['edge_id'], e) for e in out['edges'] if e['edge_id'] not in aliases]
    out['virtual_equipment_ports'] = [p for p in out.get('virtual_equipment_ports', [])
        if p.get('node_id') not in retired and p.get('virtual_equipment_id') not in retired]
    rows = reassign_components(rows, aliases, out['edges'])
    for edge in out['edges']:
        found = [r for r in rows if r['edge_id'] == edge['edge_id']]
        if (collections.Counter(r['device_name'] for r in found) != collections.Counter(edge['equipment_names'])
                or collections.Counter(r['equipment_type'] for r in found) != collections.Counter(edge['equipment_counts'])):
            raise ValueError('merged component graph and canonical table differ')
        if edge['edge_id'] not in replacements and edge != edges[edge['edge_id']]:
            raise ValueError('unrelated edge changed')
    out['sourceReviewedDrawingGapContinuity'] = dict(mode=MODE, source_sha256=source_hash,
        input_graph_sha256=graph_hash, records=records, edge_id_mapping=aliases,
        retired_node_snapshots=[copy.deepcopy(nodes[n]) for n in sorted(retired)],
        prior_evidence_graph_scope=graph_hash, physical_Ts_added=0, physical_lengths_assigned=0,
        supply_return_independent=True, human_accepted=False)
    out['derivedEvidenceInvalidation'] = dict(previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),
        reason='reviewed drawing gaps change complete paths between existing Ts',
        recompute=['source_comparison', 'branch_inventory', 'crossview_mapping', 'diameter_inheritance', 'length_fusion', 'HIL'],
        historical_annotations_preserved=True)
    out['metadata'].update(hil_ready=False, graph_complete=False, review_status='unreviewed_after_reviewed_drawing_gap_reconstruction')
    return out, rows


def compute(paths, policy):
    question = bind_question(paths, policy)
    doc, readability = read_source(paths['source'])
    from resolve_pending_native_junctions import verify_output as verify_parent
    parent = verify_parent(Path(paths['graph']).parent)
    if parent['output_graph_sha256'] != sha(paths['graph']):
        raise ValueError('current pending-junction parent replay differs')
    graph = load(paths['graph'])
    if graph['metadata']['source_sha256'] != sha(paths['source']):
        raise ValueError('graph source identity differs')
    proofs = source_pairs(doc, graph, question)
    with Path(paths['devices']).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    result, rows = merge(graph, rows, proofs, policy['retained_edges'], sha(paths['source']), sha(paths['graph']))
    return result, rows, fields, dict(source_preflight=readability, source_pairs=proofs,
        nodes_before=len(graph['nodes']), nodes_after=len(result['nodes']), edges_before=len(graph['edges']),
        edges_after=len(result['edges']), equipment_instances_preserved=True, physical_lengths_assigned=0)


def implementation_hashes():
    names = ('reviewed_source_question', 'inherited_wave_pair_continuity', 'normalize_two_arm_circle_continuity',
             'native_path_coverage_audit', 'native_line_path_evidence', 'edge_endpoint_semantics', 'source_readability')
    return dict({n: sha(importlib.import_module(n).__file__) for n in names}, entry=sha(__file__))


def verify_output(directory):
    directory = Path(directory)
    audit = load(directory / 'reviewed-drawing-gap-audit.json')
    if audit['mode'] != MODE or audit['implementation_sha256'] != implementation_hashes():
        raise ValueError('reviewed drawing-gap implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('reviewed drawing-gap input changed')
    paths = {k: v['path'] for k, v in audit['inputs'].items() if k != 'policy'}
    result, rows, fields, proof = compute(paths, load(audit['inputs']['policy']['path']))
    if (sha(directory / 'graph_with_edges.json') != audit['output_graph_sha256']
            or encode(result) != (directory / 'graph_with_edges.json').read_bytes() or proof != audit['proof']
            or csv_bytes(fields, rows) != (directory / 'assigned_edge_device_instances.csv').read_bytes()):
        raise ValueError('reviewed drawing-gap independent native replay differs')
    return audit


def main():
    parser = argparse.ArgumentParser()
    for key in KEYS + ('policy', 'output', 'verify-output'):
        parser.add_argument('--' + key.replace('_', '-'), type=Path)
    args = parser.parse_args()
    if args.verify_output:
        if any(getattr(args, k) for k in KEYS + ('policy', 'output')):
            parser.error('verification cannot override archived inputs')
        print(dict(native_replay='passed', graph_sha256=verify_output(args.verify_output)['output_graph_sha256']), flush=True)
        return
    if not all(getattr(args, k) for k in KEYS + ('policy', 'output')):
        parser.error('all pinned original inputs, policy and fresh output required')
    if args.output.exists():
        raise FileExistsError(args.output)
    paths = {k: getattr(args, k) for k in KEYS}
    result, rows, fields, proof = compute(paths, load(args.policy))
    args.output.mkdir(parents=True)
    target = args.output / 'graph_with_edges.json'
    target.write_bytes(encode(result))
    (args.output / 'assigned_edge_device_instances.csv').write_bytes(csv_bytes(fields, rows))
    paths['policy'] = args.policy
    audit = dict(mode=MODE, inputs={k: dict(path=str(Path(v).resolve()), sha256=sha(v)) for k, v in paths.items()},
        implementation_sha256=implementation_hashes(), proof=proof, output_graph_sha256=sha(target),
        hil_ready=False, human_accepted=False)
    (args.output / 'reviewed-drawing-gap-audit.json').write_bytes(encode(audit))
    print(dict(nodes=len(result['nodes']), edges=len(result['edges']), service_continuations=2,
        physical_lengths_assigned=0, human_accepted=False), flush=True)


if __name__ == '__main__':
    main()
