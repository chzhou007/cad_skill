"""Attach explicit paired owners using native glyphs and preserved pipe scopes."""
import argparse
import copy
import importlib
from pathlib import Path
import shutil

from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from source_terminal_pair_inventory import scan
from calibrated_equipment_interface_ownership import equipment, native_interface
from calibrated_ownership_scope_composition import SCOPE_FIELDS
from confirmed_equipment_interfaces import apply as attach_interfaces

MODE = 'source_reviewed_paired_interface_owners_v1'
DECISIONS = {'是，两组分别接对应设备，供回水独立', '是，这对接口归属该设备，供回水独立'}
PARENTS = {'native_circle_path_normalization': 'normalize_plan_circle_paths',
           'inherited_wave_pair_continuity': 'inherited_wave_pair_continuity'}


def bindings(question):
    """Use the reviewed ordered groups; proximity never chooses an owner."""
    answer = question.get('answer', {})
    if answer.get('decision') not in DECISIONS or answer['decision'] not in question['options']:
        raise ValueError('not an explicit supported paired-owner confirmation')
    source = question['source_evidence']
    owners = source.get('equipment_ids', [source.get('equipment_id')])
    interfaces = source.get('interface_ids', [])
    if (not owners or any(not isinstance(x, str) or not x for x in owners)
            or len(owners) != len(set(owners)) or len(interfaces) != len(owners) * 2
            or len(interfaces) != len(set(interfaces))):
        raise ValueError('reviewed ordered paired scope is incomplete')
    return [(nid, did) for index, did in enumerate(owners)
            for nid in interfaces[2 * index:2 * index + 2]]


def compose(graph, policy, inventory, source_hash, graph_hash, question_by_interface):
    targets = {row['equipment_id'] for row in policy['connections']}
    if any(targets & {e.get('start_node_id'), e.get('end_node_id')} for e in graph['edges']):
        raise ValueError('selected equipment already has connections; explicit reconciliation required')
    out, base = attach_interfaces(graph, policy, inventory, source_hash, graph_hash)
    old = {e['edge_id']: e for e in graph['edges']}
    records = []
    selected = {row['edge_id']: row for row in policy['connections']}
    for edge in out['edges']:
        eid = edge['edge_id']
        if eid not in selected:
            if encode(edge) != encode(old[eid]):
                raise ValueError('unrelated edge changed during endpoint reconciliation')
            continue
        row = selected[eid]
        before = old[eid]
        if before.get('cross_view_attributes') is not None or before.get('equipment_connector_length_mm') is not None:
            raise ValueError('local ownership must precede fusion or measured connector reconciliation')
        prior = {key: copy.deepcopy(before[key]) for key in SCOPE_FIELDS if key in before}
        for key in ('path_length_scope', 'drawing_path_length'):
            if key in prior:
                edge[key] = copy.deepcopy(prior[key])
        status = prior.get('physical_length_status')
        if isinstance(status, str) and any(t in status.lower() for t in ('unknown', 'pending', 'unverified')):
            edge['physical_length_status'] = status
        edge['path_length_complete'] = False
        edge['physical_length'] = 'unknown'
        edge['equipment_connector_length_mm'] = None
        edge['equipment_connector_length_status'] = 'unshown_interface_to_equipment_unknown'
        lineage = copy.deepcopy(before.get('length_scope_evidence', []))
        if not isinstance(lineage, list):
            raise ValueError('invalid inherited length-scope lineage')
        question = question_by_interface[row['interface_id']]
        evidence = dict(edge_id=eid, equipment_id=row['equipment_id'],
            retired_interface_id=row['interface_id'], system=row['system'],
            question_id=question['id'], explicit_answer=question['answer'],
            prior_length_scope=prior, source_sha256=source_hash, input_graph_sha256=graph_hash,
            original_edge=copy.deepcopy(before), physical_port_verified=False,
            equipment_connector_length_mm=None, human_accepted=False)
        lineage.append(dict(kind='reviewed_logical_owner_with_prior_pipe_scope', **evidence))
        edge['length_scope_evidence'] = lineage
        edge['reviewed_interface_owner'] = evidence
        records.append(evidence)
        for key in ('system', 'path', 'path_points', 'attribute_paths', 'source_handles', 'path_length'):
            if edge.get(key) != before.get(key):
                raise ValueError('source pipe geometry or drawing length changed')
    old_equipment = {n['node_id']: n for n in graph['nodes'] if n.get('node_type') == 'equipment'}
    new_equipment = {n['node_id']: n for n in out['nodes'] if n.get('node_type') == 'equipment'}
    if set(old_equipment) != set(new_equipment):
        raise ValueError('equipment instances were lost or created')
    out['sourceReviewedInterfaceOwners'] = dict(mode=MODE, source_sha256=source_hash,
        input_graph_sha256=graph_hash, records=records, supply_return_independent=True,
        source_paths_and_prior_scopes_preserved=True, physical_ports_verified=False, human_accepted=False)
    out['derivedEvidenceInvalidation'] = dict(previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),
        reason='explicit paired interface owners applied; logical endpoint semantics changed',
        recompute=['source_comparison', 'branch_inventory', 'crossview_mapping', 'diameter_inheritance', 'length_fusion', 'human_acceptance'],
        historical_annotations_preserved=True)
    return out, dict(records=records, underlying_interface_audit=base)


def implementation_hashes():
    names = ('confirmed_equipment_interfaces', 'calibrated_equipment_interface_ownership',
             'calibrated_ownership_scope_composition', 'source_terminal_pair_inventory',
             'source_readability', 'edge_endpoint_semantics')
    result = {name: sha(Path(importlib.import_module(name).__file__)) for name in names}
    result[Path(__file__).name] = sha(Path(__file__))
    return result


def compute(paths, selection):
    for key, path in paths.items():
        if sha(path) != selection['inputs'][key]['sha256']:
            raise ValueError('reviewed-owner input changed: ' + key)
    doc, readable = read_source(paths['source'])
    graph = load(paths['graph'])
    source_hash, graph_hash = sha(paths['source']), sha(paths['graph'])
    if graph['metadata']['source_sha256'] != source_hash:
        raise ValueError('native source/graph mismatch')
    module = PARENTS.get(selection.get('parent_mode'))
    if not module:
        raise ValueError('unsupported parent mode')
    parent = importlib.import_module(module).verify_output(Path(paths['graph']).parent)
    if parent['output_graph_sha256'] != graph_hash:
        raise ValueError('independent parent replay differs')
    reply, definitions, receipt = load(paths['reply']), load(paths['definitions']), load(paths['receipt'])
    if receipt['input']['sha256'] != sha(paths['reply']) or reply['schema'] != 'sh16-expert-batch-review-v1':
        raise ValueError('expert response archive binding differs')
    def questions(value):
        return {q['id']: (q, s['image']) for group in ('sections', 'followup_sections')
                for s in value[group] for q in s['questions']}
    raw, canonical = questions(reply), questions(definitions)
    archived = {row['question_id']: row for row in receipt['records']}
    wanted = selection.get('questions', [])
    if not wanted or len(wanted) != len(set(wanted)):
        raise ValueError('empty or duplicate review scope')
    bodies = equipment(doc, graph)
    nodes = {n['node_id']: n for n in graph['nodes']}
    degree = {nid: [e for e in graph['edges'] if nid in (e.get('start_node_id'), e.get('end_node_id'))] for nid in nodes}
    connections, question_by_interface, native_records, confirmed_questions = [], {}, [], []
    for qid in wanted:
        question, image = raw[qid]
        definition, expected_image = canonical[qid]
        if image != expected_image or any(question.get(k) != definition.get(k) for k in ('text', 'options', 'source_evidence')):
            raise ValueError('reviewed question or Pair changed')
        if archived[qid]['explicit_answer'] != question['answer']:
            raise ValueError('validated answer differs from raw export')
        pair = selection['pairs'][qid]
        if sha(pair['path']) != image['sha256'] or pair['sha256'] != image['sha256']:
            raise ValueError('reviewed Pair bytes differ')
        source_scope = question['source_evidence']
        if source_scope['source_sha256'] != source_hash:
            raise ValueError('reviewed source identity differs')
        if source_scope.get('graph_sha256', graph_hash) != graph_hash:
            raise ValueError('reviewed graph requires a separate source-scope migration')
        confirmed_questions.append(copy.deepcopy(question))
        for nid, did in bindings(question):
            if nid in question_by_interface or nid not in nodes or did not in bodies or len(degree[nid]) != 1:
                raise ValueError('reviewed interface identity/degree is ambiguous')
            if len(bodies[did]['source_caption_handles']) != 1:
                raise ValueError('native equipment caption is not unique')
            edge = degree[nid][0]
            native = native_interface(doc, nodes[nid], edge)
            question_by_interface[nid] = question
            native_records.append(dict(interface=native, equipment_id=did, native_body=bodies[did]))
            connections.append(dict(interface_id=nid, edge_id=edge['edge_id'], equipment_id=did,
                system=nodes[nid]['system'], interface_handle=nodes[nid]['source_handle'], equipment_handle=nodes[did]['source_handle']))
    inventory_policy = dict(selection['inventory_scope'], source_sha256=source_hash, graph_sha256=graph_hash)
    inventory = scan(doc, graph, inventory_policy, source_hash, graph_hash)
    policy = dict(source_sha256=source_hash, graph_sha256=graph_hash, connections=connections,
        confirmation=dict(confirmed_by='user', question='Explicit reviewed ordered equipment/interface pairs',
                          answer='Scoped paired-owner confirmations; see original records',
                          records=confirmed_questions, response_sha256=sha(paths['reply'])))
    result, audit = compose(graph, policy, inventory, source_hash, graph_hash, question_by_interface)
    audit.update(native_records=native_records, source_preflight=readable,
        parent_graph_sha256=graph_hash, parent_mode=selection['parent_mode'])
    return result, audit


def verify_output(directory):
    directory = Path(directory)
    audit = load(directory / 'reviewed-interface-owner-audit.json')
    if audit['mode'] != MODE or audit['implementation_sha256'] != implementation_hashes():
        raise ValueError('reviewed-owner implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path']) != item['sha256']:
            raise ValueError('reviewed-owner input changed')
    paths = {key: value['path'] for key, value in audit['inputs'].items() if key != 'selection'}
    result, proof = compute(paths, load(audit['inputs']['selection']['path']))
    if (sha(directory / 'graph_with_edges.json') != audit['output_graph_sha256']
            or encode(result) != (directory / 'graph_with_edges.json').read_bytes() or proof != audit['proof']):
        raise ValueError('reviewed-owner native replay differs')
    if (directory / 'assigned_edge_device_instances.csv').read_bytes() != Path(paths['devices']).read_bytes():
        raise ValueError('reviewed-owner component inventory changed')
    return audit


def main():
    parser = argparse.ArgumentParser()
    for key in ('source', 'graph', 'devices', 'reply', 'receipt', 'definitions', 'selection', 'output', 'verify-output'):
        parser.add_argument('--' + key, type=Path)
    args = parser.parse_args()
    if args.verify_output:
        if any(getattr(args, key) for key in ('source', 'graph', 'devices', 'reply', 'receipt', 'definitions', 'selection', 'output')):
            parser.error('verification cannot override archived inputs')
        audit = verify_output(args.verify_output)
        print(dict(source_replay='passed', logical_links=len(audit['proof']['records']), human_accepted=False), flush=True)
        return
    keys = ('source', 'graph', 'devices', 'reply', 'receipt', 'definitions')
    if not all(getattr(args, key) for key in keys + ('selection', 'output')):
        parser.error('all pinned native inputs, selection and a new output are required')
    if args.output.exists():
        raise FileExistsError(args.output)
    paths = {key: getattr(args, key) for key in keys}
    result, proof = compute(paths, load(args.selection))
    args.output.mkdir(parents=True)
    graph_path = args.output / 'graph_with_edges.json'
    graph_path.write_bytes(encode(result))
    shutil.copyfile(args.devices, args.output / 'assigned_edge_device_instances.csv')
    paths['selection'] = args.selection
    audit = dict(mode=MODE, proof=proof, implementation_sha256=implementation_hashes(),
        inputs={key: dict(path=str(Path(value).resolve()), sha256=sha(value)) for key, value in paths.items()},
        output_graph_sha256=sha(graph_path), human_accepted=False, hil_ready=False)
    (args.output / 'reviewed-interface-owner-audit.json').write_bytes(encode(audit))
    print(dict(logical_links=len(proof['records']), equipment=len({r['equipment_id'] for r in proof['records']}),
               physical_lengths_assigned=0, human_accepted=False), flush=True)


if __name__ == '__main__':
    main()
