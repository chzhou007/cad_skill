"""Retain proven source equipment instances without guessing labels or pipe ports."""
import argparse
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path

from native_equipment_body import body_straight_segments
from source_readability import read_source


def preserve(doc, graph, bindings, policy, source_hash, graph_hash, bindings_hash, tol=.05):
    if (policy.get('source_sha256') != source_hash or policy.get('graph_sha256') != graph_hash
            or policy.get('bindings_sha256') != bindings_hash
            or graph.get('metadata', {}).get('source_sha256') != source_hash):
        raise ValueError('stale source, graph or bindings')
    items = {r['source_handle']: r for r in bindings}
    nodes = {n['node_id']: n for n in graph['nodes']}
    if len(items) != len(bindings) or len(nodes) != len(graph['nodes']):
        raise ValueError('duplicate source or graph identity')
    floor = policy.get('floor')
    if not isinstance(floor, int) or isinstance(floor, bool):
        raise ValueError('invalid floor')
    existing = [n.get('source_handle') for n in graph['nodes'] if n.get('node_type') == 'equipment' and n.get('source_handle')]
    if len(existing) != len(set(existing)):
        raise ValueError('source equipment represented multiple times')
    missing = set(items) - set(existing)
    expected = policy.get('expected_missing_source_handles')
    if not isinstance(expected, list) or len(expected) != len(set(expected)) or missing != set(expected):
        raise ValueError('unexpected missing equipment inventory')
    out = copy.deepcopy(graph)
    added = []
    for handle in sorted(missing):
        row = items[handle]
        entity = doc.entitydb.get(handle)
        if (entity is None or entity.dxftype() != 'INSERT' or entity not in doc.modelspace()
                or entity.dxf.layer != '空调' or entity.dxf.name != row.get('source_block')):
            raise ValueError('equipment source mismatch')
        body, unsupported = body_straight_segments(entity)
        if not body or unsupported:
            raise ValueError('equipment body unsupported')
        box = [[min(p[i] for segment in body for p in segment) for i in (0, 1)],
               [max(p[i] for segment in body for p in segment) for i in (0, 1)]]
        old = row.get('bounds')
        if (not isinstance(old, list) or len(old) != 2
                or any(not math.isfinite(float(old[j][i])) or abs(box[j][i]-old[j][i]) > tol for j in (0, 1) for i in (0, 1))):
            raise ValueError('equipment body bounds mismatch')
        node_id = 'EQ-SOURCE-' + handle
        if node_id in nodes:
            raise ValueError('pending equipment ID collision')
        node = {'node_id': node_id, 'node_type': 'equipment', 'subtype': 'CRAH', 'floor': floor,
                'label': '设备身份待核-' + handle, 'x': (box[0][0]+box[1][0])/2, 'y': (box[0][1]+box[1][1])/2,
                'source_handle': handle, 'source_block': row['source_block'],
                'identity_status': 'unresolved', 'connection_status': 'ports_unresolved',
                'source_label_candidates': row.get('label_candidates', []),
                'parameter_candidates': row.get('parameter_candidates', []),
                'source_instance_evidence': {'source_sha256': source_hash, 'source_bounds': box,
                                             'label_confirmed': False, 'ports_inferred': False}}
        out['nodes'].append(node)
        added.append(node_id)
    out.setdefault('metadata', {}).update(hil_ready=False, graph_complete=False, review_status='unreviewed')
    comparison = out.setdefault('preHilComparison', {})
    comparison.setdefault('families', []).append({'id': 'unidentified-source-equipment', 'status': 'algorithm_pending',
                                                   'disposition': 'Resolve each source equipment identity and port ownership.'})
    comparison['status'] = 'pending'
    return out, {'status': 'source_instances_retained_identity_and_ports_unresolved', 'source_sha256': source_hash,
                 'input_graph_sha256': graph_hash, 'bindings_sha256': bindings_hash,
                 'added_nodes': added, 'added_edges': [], 'hil_ready': False, 'human_accepted': False}


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'graph', 'bindings', 'devices', 'policy', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    load = lambda p: json.loads(p.read_text(encoding='utf8'))
    doc, proof = read_source(args.source)
    policy = load(args.policy)
    if policy.get('devices_sha256') != sha(args.devices):
        raise ValueError('device inventory hash mismatch')
    out, audit = preserve(doc, load(args.graph), load(args.bindings), policy, proof['source_sha256'], sha(args.graph), sha(args.bindings))
    args.output.mkdir(parents=True, exist_ok=False)
    target = args.output / 'graph_with_pending_equipment.json'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    shutil.copyfile(args.devices, args.output / 'assigned_edge_device_instances.csv')
    audit.update(output_graph_sha256=sha(target), devices_sha256=sha(args.devices), policy_sha256=sha(args.policy),
                 script_sha256=sha(Path(__file__)), source_preflight=proof)
    (args.output / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'status': audit['status'], 'added': len(audit['added_nodes'])}))


if __name__ == '__main__':
    main()
