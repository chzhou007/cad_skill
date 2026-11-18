"""Reconcile edge endpoint types against canonical nodes and typed boundaries."""
import argparse
import copy
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


def reconcile(graph):
    result = copy.deepcopy(graph)
    nodes_list = result['nodes']; edges = result['edges']
    nodes = {n['node_id']: n for n in nodes_list}
    anchors_list = result.get('boundary_anchors', [])
    anchors = {a['boundary_id']: a for a in anchors_list}
    if len(nodes) != len(nodes_list) or len(anchors) != len(anchors_list) or set(nodes) & set(anchors):
        raise ValueError('duplicate or colliding endpoint identifiers')
    if len({e['edge_id'] for e in edges}) != len(edges):
        raise ValueError('duplicate edge identifier')
    changes = []
    for e in edges:
        roles = {}
        for side in ('start', 'end'):
            nid = e.get(side + '_node_id'); bid = e.get(side + '_boundary_id')
            if bool(nid) == bool(bid):
                raise ValueError('endpoint must have exactly one node or boundary')
            if bid:
                if bid not in anchors:
                    raise ValueError('missing boundary')
                a = anchors[bid]
                if a.get('system') != e.get('system') or a.get('source_pipe_handle') not in e.get('source_handles', []):
                    raise ValueError('boundary source/system mismatch')
                roles[side] = {'kind': 'source_boundary', 'id': bid, 'subtype': a.get('kind')}
            else:
                if nid not in nodes:
                    raise ValueError('missing node')
                n = nodes[nid]; typ = n.get('node_type')
                kind = {'tee': 'tee', 'physical_junction': 'tee', 'equipment': 'equipment',
                        'physical_equipment': 'equipment', 'virtual_equipment': 'virtual_equipment'}.get(typ)
                if kind is None:
                    raise ValueError('unknown node type: ' + str(typ))
                roles[side] = {'kind': kind, 'id': nid, 'subtype': n.get('subtype')}
        kinds = {roles['start']['kind'], roles['end']['kind']}
        if 'source_boundary' in kinds:
            edge_type = 'source_boundary_edge'
        elif 'equipment' in kinds:
            edge_type = 'tee_to_equipment'
        elif 'virtual_equipment' in kinds:
            edge_type = 'tee_to_virtual_equipment'
        else:
            edge_type = 'tee_to_tee'
        previous = e.get('edge_type')
        e['endpoint_semantics'] = roles
        e['edge_type'] = edge_type
        if previous != edge_type:
            changes.append({'edge_id': e['edge_id'], 'previous_edge_type': previous,
                            'edge_type': edge_type, 'endpoint_semantics': roles})
    metadata = result.setdefault('metadata', {})
    metadata.update(hil_ready=False, graph_complete=False,
                    endpoint_semantics='node_and_source_boundary_reconciled_unreviewed')
    return result, changes


def main():
    cli = argparse.ArgumentParser()
    for name in ('graph', 'devices', 'output'):
        cli.add_argument('--' + name, required=True, type=Path)
    args = cli.parse_args()
    if args.output.exists():
        raise ValueError('refusing to overwrite output')
    graph = json.loads(args.graph.read_text(encoding='utf8'))
    result, changes = reconcile(graph)
    args.output.mkdir(parents=True)
    output = args.output / 'graph_with_endpoint_semantics.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    shutil.copyfile(args.devices, args.output / 'assigned_edge_device_instances.csv')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    audit = {'input_graph_sha256': sha(args.graph), 'output_graph_sha256': sha(output),
             'component_table_sha256': sha(args.devices), 'changed_edge_count': len(changes),
             'changes': changes, 'human_review': 'unreviewed', 'hil_ready': False,
             'scope': 'endpoint classification only; no source, connection or physical ownership validation'}
    (args.output / 'endpoint-semantics-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'changed_edge_count': len(changes), 'edge_types': dict(Counter(e['edge_type'] for e in result['edges']))}))


if __name__ == '__main__':
    main()
