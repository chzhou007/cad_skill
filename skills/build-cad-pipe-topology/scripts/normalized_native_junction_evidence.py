"""Replay the original isometric normalization before qualifying a normalized T.

This reader qualifies an existing graph ray; it does not repair a graph or turn
the source drawing gap into a measured pipe length.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

import pipe_geometry as pg
from native_line_path_evidence import LAYERS, _on
from topology_normalization import trim_elbow_overshoots, snap_near_junction_endpoints


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode('utf8')).hexdigest()


def replay(doc, config):
    """Use the unchanged source collector, legacy trim and normalization order."""
    from legacy_v17 import analyze_graph as geometry
    source_index = {}
    def key(a, b):
        return tuple(sorted(tuple(round(v, 5) for v in p) for p in (a, b)))
    for top in doc.modelspace():
        for e in geometry.recursive_entities(top):
            if e.dxftype() == 'LINE' and e.dxf.layer in config['system_layers']:
                k = (config['system_layers'][e.dxf.layer], key(tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]))
                source_index.setdefault(k, set()).add(top.dxf.handle)
    old_layers, old_tol = geometry.get_system_layers, pg.TOL
    try:
        geometry.get_system_layers = lambda unused: config['system_layers']
        segments = geometry.collect_pipe_segments(doc)
        segments, _ = geometry.trim_short_dangling_overshoots(segments)
        pg.set_tolerance(geometry.POINT_TOLERANCE)
        rows = [dict(a=s.start, b=s.end, system=s.system,
                     handle='SOURCE-SEGMENT-' + str(i),
                     source_handles=sorted(source_index.get((s.system, key(s.start, s.end)), [])),
                     source_handle_scope='top_level_owner') for i, s in enumerate(segments)]
        rows, elbows = trim_elbow_overshoots(rows, config['elbow_overshoot'])
        rows, snaps = snap_near_junction_endpoints(rows, config.get('near_junction'))
    finally:
        geometry.get_system_layers = old_layers
        pg.set_tolerance(old_tol)
    return rows, dict(config=config, elbow_overshoots=elbows, junction_snaps=snaps)


def source_lines(doc):
    from legacy_v17 import analyze_graph as geometry
    return [(top.dxf.handle, e.dxf.layer, list(e.dxf.start), list(e.dxf.end))
            for top in doc.modelspace() for e in geometry.recursive_entities(top)
            if e.dxftype() == 'LINE']


class NormalizedJunctionEvidence:
    def __init__(self, doc, graph, source_hash, graph_hash, audit_spec):
        raw = Path(audit_spec['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != audit_spec['sha256']:
            raise ValueError('normalization audit hash mismatch')
        audit = json.loads(raw)
        config = audit['config']
        if config.get('previous_source_sha256') != source_hash:
            raise ValueError('normalization source hash mismatch')
        if config['system_layers'] != {v: k for k, v in LAYERS.items()}:
            raise ValueError('normalization system profile mismatch')
        rows, fresh = replay(doc, config)
        if digest(fresh) != digest(audit):
            raise ValueError('normalization audit does not replay from the source')
        self.doc, self.graph = doc, graph
        self.source_hash, self.graph_hash = source_hash, graph_hash
        self.audit_spec = copy.deepcopy(audit_spec)
        self.rows, self.audit = rows, fresh
        self.graph_digest, self.line_digest = digest(graph), digest(source_lines(doc))

    def check(self, doc, graph, source_hash, graph_hash):
        if (doc is not self.doc or graph is not self.graph
                or (source_hash, graph_hash) != (self.source_hash, self.graph_hash)
                or digest(graph) != self.graph_digest
                or digest(source_lines(doc)) != self.line_digest):
            raise ValueError('normalization evidence context changed')
        raw = Path(self.audit_spec['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != self.audit_spec['sha256']:
            raise ValueError('normalization audit changed after replay')

    def ray(self, system, at, other, handle=None, tol=.05):
        hits = []
        for record in self.audit['junction_snaps']:
            if (record['status'] != 'applied' or record.get('action') != 'extend'
                    or record.get('physical_length') != 'unknown'
                    or len(record['source_handles']) != 1
                    or math.dist(at, record['semantic_endpoint']) > tol):
                continue
            h = record['source_handles'][0]
            if handle is not None and h != handle:
                continue
            native = self.doc.entitydb.get(h)
            mains = [self.doc.entitydb.get(m) for m in record['main_source_handles']]
            # Nested/unknown owners need their own explicit transform evidence.
            if (native is None or native.dxftype() != 'LINE' or native not in self.doc.modelspace()
                    or native.dxf.layer != LAYERS[system]
                    or not mains or any(m is None or m.dxftype() != 'LINE'
                        or m not in self.doc.modelspace() or m.dxf.layer != LAYERS[system]
                        for m in mains)):
                continue
            z = native.dxf.start.z
            if (abs(native.dxf.end.z - z) > tol or any(abs(p.z-z) > tol
                    for m in mains for p in (m.dxf.start, m.dxf.end))):
                continue
            segments = [s for s in self.rows if s['source_handles'] == [h]
                        and s['system'] == system and _on(at, s['a'], s['b'], tol)
                        and _on(other, s['a'], s['b'], tol)]
            if len(segments) != 1:
                continue
            hits.append(dict(scope='normalized_modelspace_line', source_line_handle=h,
                normalization=copy.deepcopy(record), normalization_audit=copy.deepcopy(self.audit_spec),
                normalized_segment=[list(segments[0]['a']), list(segments[0]['b'])],
                physical_gap_length=None, source_gap_is_measured=False))
        if len(hits) != 1:
            raise ValueError('normalized T ray is not uniquely replayed')
        return hits[0]

    def contacts(self, system, point, rays, tol=.05):
        owners = set()
        for s in self.rows:
            if s['system'] == system and _on(point, s['a'], s['b'], tol):
                if not s['source_handles']:
                    raise ValueError('normalized contact has no original source owner')
                owners.update(s['source_handles'])
        expected = {r.get('source_line_handle', r.get('source_insert_handle')) for r in rays}
        if owners != expected:
            raise ValueError('unaccounted normalized same-system contact')
        return sorted(owners)


def prepare(doc, graph, source_hash, graph_hash, audit_spec):
    return NormalizedJunctionEvidence(doc, graph, source_hash, graph_hash, audit_spec)


class _ProjectedSource:
    """Private LINE view; original DXF entities, blocks and graph stay intact."""
    def __init__(self, original, replacements):
        self.original, self.replacements = original, replacements
        self.entitydb = dict(original.entitydb)
        self.entitydb.update(replacements)

    def modelspace(self):
        return self

    def __contains__(self, entity):
        return entity in self.original.modelspace() or entity in self.replacements.values()

    def query(self, expression):
        return [self.replacements.get(e.dxf.handle, e)
                for e in self.original.modelspace().query(expression)]


def collect(doc, graph, node_id, source_hash, graph_hash, normalization):
    """Compose the unchanged native T guard with a replayed semantic LINE view."""
    from crossview_equipment_branch_inventory import native_tee, index_graph
    normalization.check(doc, graph, source_hash, graph_hash)
    try:
        return native_tee(doc, graph, node_id, source_hash, graph_hash)
    except ValueError as exc:
        if str(exc) not in ('selected ray insert mismatch', 'native T ray is not uniquely witnessed'):
            raise
        original_error = exc
    nodes, _, adjacency = index_graph(graph)
    node = nodes[node_id]; point = [node['x'], node['y']]
    replacements, proofs = {}, {}
    for edge in adjacency[node_id]:
        rays = []
        for path in edge.get('attribute_paths', []):
            for a, b in zip(path, path[1:]):
                if math.dist(a, point) <= .05 and math.dist(b, point) > .05:
                    rays.append((a, b))
                elif math.dist(b, point) <= .05 and math.dist(a, point) > .05:
                    rays.append((b, a))
        if len(rays) != 1:
            raise ValueError('missing or ambiguous graph T ray')
        at, other = rays[0]
        try:
            proof = normalization.ray(edge['system'], at, other)
        except ValueError as exc:
            if str(exc) != 'normalized T ray is not uniquely replayed':
                raise
            continue
        h = proof['source_line_handle']; entity = doc.entitydb[h].copy()
        entity.dxf.handle = h
        a, b = proof['normalized_segment']; z = doc.entitydb[h].dxf.start.z
        entity.dxf.start, entity.dxf.end = (*a, z), (*b, z)
        replacements[h] = entity; proofs[edge['edge_id']] = proof
    if not replacements:
        raise original_error
    projected = _ProjectedSource(doc, replacements)
    result = native_tee(projected, graph, node_id, source_hash, graph_hash)
    row = result['junctions'][0]
    for ray in row['source_rays']:
        if ray['edge_id'] in proofs:
            if ray.get('source_line_handle') != proofs[ray['edge_id']]['source_line_handle']:
                raise ValueError('normalized source owner differs from original native guard')
            ray.update(copy.deepcopy(proofs[ray['edge_id']]))
    row['normalized_source_contacts'] = normalization.contacts(row['system'], point, row['source_rays'])
    row['native_line_contacts'] = []
    for line in doc.modelspace().query('LINE'):
        a, b = tuple(line.dxf.start)[:2], tuple(line.dxf.end)[:2]
        if line.dxf.layer in LAYERS.values() and _on(point, a, b, .05):
            row['native_line_contacts'].append(dict(handle=line.dxf.handle, layer=line.dxf.layer,
                contact='endpoint' if min(math.dist(point, a), math.dist(point, b)) <= .05 else 'interior'))
    row['opposite_system_contacts'] = [x for x in row['native_line_contacts'] if x['layer'] != LAYERS[row['system']]]
    row['normalization_replayed'] = True
    result['status'] = 'normalization_replayed_native_ray_evidence_unreviewed'
    result['limitations'].append('The normalized LINE view is semantic connectivity evidence only. Raw source gap coverage and physical length remain unknown; the original DXF and graph are unchanged.')
    normalization.check(doc, graph, source_hash, graph_hash)
    return result


MODE = 'replayed_isometric_normalization_native_T_evidence_v1'


def implementations():
    import importlib
    from confirm_crossview_paths import sha
    names = ('crossview_equipment_branch_inventory', 'native_junction_ray_evidence',
             'native_line_path_evidence', 'topology_normalization', 'pipe_geometry',
             'source_readability', 'legacy_v17.analyze_graph')
    return dict(entry=sha(__file__), **{n: sha(importlib.import_module(n).__file__) for n in names})


def compute(manifest):
    from confirm_crossview_paths import load, sha
    from source_readability import read_source
    inputs = manifest['inputs']
    def checked():
        if any(sha(v['path']) != v['sha256'] for v in inputs.values()):
            raise ValueError('normalized native T input changed')
    checked()
    doc, preflight = read_source(inputs['source']['path'])
    graph = load(inputs['graph']['path'])
    context = prepare(doc, graph, inputs['source']['sha256'], inputs['graph']['sha256'], inputs['normalization_audit'])
    records, held = [], []
    # Discover the complete applied cohort by semantic geometry, never hardcode
    # a node ID or widen a tolerance to select this drawing's known example.
    for snap in context.audit['junction_snaps']:
        if snap['status'] != 'applied':
            held.append(dict(normalization=copy.deepcopy(snap), status='original_normalization_pending'))
            continue
        candidates = [n['node_id'] for n in graph['nodes']
            if n.get('node_type') in ('tee', 'physical_junction')
            and math.dist((n['x'], n['y']), snap['semantic_endpoint']) <= .05]
        if len(candidates) != 1:
            held.append(dict(normalization=copy.deepcopy(snap), candidates=candidates,
                             status='normalized_T_identity_not_unique'))
            continue
        node_id = candidates[0]
        try:
            proof = collect(doc, graph, node_id, inputs['source']['sha256'], inputs['graph']['sha256'], context)
            records.append(dict(node_id=node_id, evidence=proof))
        except ValueError as exc:
            held.append(dict(node_id=node_id, normalization=copy.deepcopy(snap),
                             status='native_T_evidence_held', reason=str(exc)))
    checked()
    return dict(mode=MODE, inputs=inputs, source_preflight=preflight, records=records, held=held,
        original_normalization_replayed=True, discovery='complete_original_junction_snap_audit',
        graph_mutated=False, source_mutated=False, physical_gap_lengths_assigned=0,
        DN_values_assigned=0, length_values_assigned=0, human_accepted=False, whole_goal_complete=False)


def produce(manifest, output):
    from confirm_crossview_paths import load, sha, encode
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    code = implementations(); result = compute(load(manifest))
    if implementations() != code:
        raise ValueError('normalized native T implementation changed')
    output.mkdir(parents=True)
    target = output/'normalized-native-junctions.json'; target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,
        manifest=dict(path=str(Path(manifest).resolve()), sha256=sha(manifest)),
        implementation_sha256=code, output_sha256=sha(target))))
    return result


def verify_output(output):
    from confirm_crossview_paths import load, sha, encode
    output = Path(output); receipt = load(output/'receipt.json'); target = output/'normalized-native-junctions.json'
    if (receipt['mode'] != MODE or receipt['implementation_sha256'] != implementations()
            or sha(receipt['manifest']['path']) != receipt['manifest']['sha256']
            or sha(target) != receipt['output_sha256']):
        raise ValueError('normalized native T receipt changed')
    fresh = compute(load(receipt['manifest']['path']))
    if encode(fresh) != target.read_bytes():
        raise ValueError('normalized native T replay differs')
    return fresh


def main():
    import argparse
    from confirm_crossview_paths import encode
    p = argparse.ArgumentParser()
    for name in ('manifest', 'output', 'verify-output'):
        p.add_argument('--'+name, type=Path)
    a = p.parse_args()
    if not a.verify_output and not (a.manifest and a.output):
        p.error('manifest and fresh output required')
    result = verify_output(a.verify_output) if a.verify_output else produce(a.manifest, a.output)
    print(encode(dict(mode=MODE, qualified=len(result['records']), held=len(result['held']),
                      DN_values_assigned=0, length_values_assigned=0)).decode(), flush=True)


if __name__ == '__main__':
    main()
