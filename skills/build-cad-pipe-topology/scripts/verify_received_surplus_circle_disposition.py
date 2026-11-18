"""Bind a received two-circle drafting erratum to an existing native disposition.

This verifies that the exact source circles from the archived question's context
are display-only and were never materialized as graph junctions. Independent
sideview/owner evidence protects the real interface pairs. It does not assign
equipment owners from a short erratum comment and never edits a source or graph.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

MODE = 'received_surplus_circle_existing_native_disposition_v1'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf8')


def load(path):
    text = Path(path).read_text(encoding='utf-8-sig').strip()
    return json.loads(text.removeprefix('window.REVIEW_CASES = ').removesuffix(';'))


def check_pin(spec):
    require(set(spec) == {'path', 'sha256'} and sha(spec['path']) == spec['sha256'],
            'bound source, answer or current graph changed')
    return Path(spec['path'])


def questions(data):
    return [(section, question) for field in ('sections', 'followup_sections')
            for section in data.get(field, []) for question in section['questions']]


def bind_answer(definitions, reply, original_question, render_audit, manifest):
    qid = manifest['question_id']
    matches = [(s, q) for s, q in questions(definitions) if q['id'] == qid]
    exported = [(s, q) for s, q in questions(reply) if q['id'] == qid]
    require(len(matches) == len(exported) == 1, 'one archived explicit erratum question required')
    section, question = matches[0]
    other, answered = exported[0]
    require(question == original_question and all(answered.get(k) == question.get(k)
            for k in ('id', 'text', 'options', 'source_evidence'))
            and section['image'] == other['image']
            and section.get('contexts', []) == other.get('contexts', []),
            'original question, source scope or Pair differs')
    answer = answered.get('answer', {})
    require(answer == reply.get('browser_answer_snapshot', {}).get(qid)
            and answer.get('decision') == manifest['expected_decision']
            and answer.get('decision') in question['options']
            and answer.get('comment') == manifest['expected_comment']
            and bool(answer.get('updated_at')),
            'explicit scoped drafting erratum answer differs')
    evidence = question['source_evidence']
    pair_hash = manifest['inputs']['pair']['sha256']
    require(section['image']['sha256'] == pair_hash == answer.get('source_pair_sha256')
            == evidence['pair_sha256'] == render_audit['pair_sha256'], 'Pair binding differs')
    require(evidence['source_sha256'] == render_audit['source_sha256']
            == manifest['inputs']['source']['sha256']
            and evidence['graph_sha256'] == render_audit['graph_sha256']
            == manifest['inputs']['reviewed_graph']['sha256'], 'archived native scope differs')
    circles = render_audit['main_circle_context_only']
    require(len(circles) == 2 and len({c['handle'] for c in circles}) == 2
            and {c['handle'] for c in circles} == {c['circle_handle'] for c in manifest['circles']},
            'exact two main-context circles required; interface glyphs cannot be substituted')
    require(set(evidence['interface_ids']) == {x['abbreviated_interface'] for x in manifest['interfaces']}
            and set(evidence['canonical_interface_ids']) == {x['canonical_interface'] for x in manifest['interfaces']}
            and set(evidence['equipment_ids']) == {x['equipment_id'] for x in manifest['interfaces']},
            'protected interface or equipment scope differs')
    return dict(question_id=qid, explicit_answer=answer, pair_sha256=pair_hash,
                source_circle_handles=sorted(c['handle'] for c in circles),
                scope_binding='two_main_context_only_circles_of_the_archived_answered_Pair',
                equipment_ownership_inferred_from_erratum=False)


def position(point, a, b):
    vector = [b[i] - a[i] for i in range(2)]
    length2 = sum(v * v for v in vector)
    if length2 == 0:
        return -1.0, math.dist(point, a[:2]), 0.0
    t = sum((point[i] - a[i]) * vector[i] for i in range(2)) / length2
    return t, math.dist(point, [a[i] + t * vector[i] for i in range(2)]), math.sqrt(length2)


def contains_value(value, expected):
    if isinstance(value, dict):
        return any(contains_value(v, expected) for v in value.values())
    if isinstance(value, list):
        return any(contains_value(v, expected) for v in value)
    return value == expected


def circle_disposition(doc, graph, binding, archived_circle, tolerance=0.05):
    from ezdxf import bbox
    handle, main_handle = binding['circle_handle'], binding['main_line_handle']
    circle, line = doc.entitydb.get(handle), doc.entitydb.get(main_handle)
    require(circle is not None and line is not None and circle.dxftype() == 'CIRCLE'
            and line.dxftype() == 'LINE' and circle in doc.modelspace() and line in doc.modelspace(),
            'native modelspace circle and through LINE required')
    require(circle.dxf.layer == line.dxf.layer == binding['layer'], 'source service layer changed')
    center = list(circle.ocs().to_wcs(circle.dxf.center))
    point, radius = center[:2], circle.dxf.radius
    require(radius > 0 and math.dist(center, archived_circle['center']) <= tolerance
            and abs(radius - archived_circle['radius']) <= tolerance
            and circle.dxf.layer == archived_circle['layer'], 'archived source circle changed')
    start, end = list(line.dxf.start), list(line.dxf.end)
    t, distance, length = position(point, start, end)
    require(distance <= tolerance and min(t, 1 - t) * length > radius + tolerance,
            'circle must lie strictly within one unbroken native pipe LINE')
    nearby = []
    for entity in doc.modelspace().query('LINE'):
        if entity.dxf.layer != binding['layer']:
            continue
        a, b = list(entity.dxf.start), list(entity.dxf.end)
        u, gap, span = position(point, a, b)
        closest = math.dist(point, a[:2]) if u < 0 else math.dist(point, b[:2]) if u > 1 else gap
        if closest <= radius + tolerance:
            nearby.append(entity.dxf.handle)
    require(set(nearby) == {main_handle}, 'additional local same-service source LINE needs reconciliation')
    for entity in doc.modelspace():
        if entity.dxf.layer != binding['layer'] or entity.dxftype() not in ('LWPOLYLINE', 'POLYLINE', 'ARC', 'ELLIPSE', 'SPLINE', 'INSERT'):
            continue
        bounds = bbox.extents([entity], fast=True)
        require(bounds.has_data, 'unsupported native same-service geometry needs a qualified reader')
        crosses_scope = (bounds.extmax.x >= point[0] - radius - tolerance
                         and bounds.extmin.x <= point[0] + radius + tolerance
                         and bounds.extmax.y >= point[1] - radius - tolerance
                         and bounds.extmin.y <= point[1] + radius + tolerance)
        require(not crosses_scope, 'additional local same-service source geometry needs reconciliation')
    require(not any(contains_value(item, handle) for item in graph['nodes'] + graph['edges']),
            'surplus circle is an active graph identity or attribute source')
    require(not any(math.dist(point, [n['x'], n['y']]) <= radius + tolerance for n in graph['nodes']),
            'graph node at surplus-circle source extent')
    hits = []
    for edge in graph['edges']:
        for path in edge.get('attribute_paths', []):
            for a, b in zip(path, path[1:]):
                u, gap, span = position(point, a, b)
                if gap <= tolerance and min(u, 1 - u) * span > radius + tolerance:
                    hits.append((edge, a, b))
    require(len(hits) == 1, 'one continuous graph pipe through surplus-circle extent required')
    edge, a, b = hits[0]
    source_positions = [position(p, start, end) for p in (a, b)]
    require(edge['edge_id'] == binding['current_edge_id'] and edge['system'] == binding['system']
            and main_handle in edge.get('source_handles', [])
            and all(gap <= tolerance and -tolerance <= u * span <= span + tolerance
                    for u, gap, span in source_positions),
            'current continuous pipe is not the exact native source owner')
    return dict(circle_handle=handle, native_center=center, radius=radius, system=edge['system'],
                source_line_handle=main_handle, source_line_start=start, source_line_end=end,
                native_line_fraction=t, current_edge_id=edge['edge_id'],
                current_edge_endpoints=[edge['start_node_id'], edge['end_node_id']],
                source_circle_retained_in_CAD=True, active_graph_circle_references=0,
                active_graph_nodes_within_circle=0, local_same_service_source_lines=nearby,
                disposition='source_graphic_only_existing_unbroken_main_no_physical_T_or_interface',
                new_connection_or_attribute_assigned=False)


def protect_interfaces(graph, bindings):
    aliases = graph['confirmedSideviewCanonicalization']['records']
    owners = graph['sourceOrderedSideviewEquipmentOwnership']['records']
    nodes = {n['node_id']: n for n in graph['nodes']}
    edges = {e['edge_id']: e for e in graph['edges']}
    result = []
    require(len(bindings) == 4 and len({b['canonical_interface'] for b in bindings}) == 4,
            'two complete paired interfaces required')
    for spec in bindings:
        found = [a for a in aliases if all(a.get(k) == spec[k]
                 for k in ('question_id', 'abbreviated_interface', 'canonical_interface', 'canonical_edge', 'system'))]
        require(len(found) == 1, 'protected original sideview alias changed')
        records = [o for o in owners if o['original_canonical_interface_id'] == spec['canonical_interface']]
        require(len(records) == 1, 'protected interface lacks independent ordered-owner evidence')
        owner = records[0]
        require(owner['question_id'] == spec['question_id'] and owner['equipment_id'] == spec['equipment_id']
                and owner['edge_id'] == spec['canonical_edge'] and owner['system'] == spec['system']
                and owner['body_evidence']['ownership_basis'] == 'complete_native_row_order_checked_against_independent_owners'
                and owner['physical_port_verified'] is False and owner['interface_to_equipment_length_known'] is False,
                'independent owner or unknown physical scope changed')
        edge = edges[spec['canonical_edge']]
        require(spec['equipment_id'] in nodes and nodes[spec['equipment_id']]['node_type'] == 'equipment'
                and spec['equipment_id'] in [edge['start_node_id'], edge['end_node_id']]
                and edge['system'] == spec['system'] and edge.get('equipment_connector_length_mm') is None
                and edge.get('physical_length') == 'unknown'
                and spec['canonical_interface'] not in nodes and spec['abbreviated_interface'] not in nodes,
                'protected equipment service lost, duplicated or assigned an unsupported physical length')
        result.append(dict(spec, ownership_proof='independent_native_row_and_sideview_alias_not_erratum_comment'))
    require({(r['equipment_id'], r['system']) for r in result}
            == {(r['equipment_id'], s) for r in result for s in ('supply', 'return')},
            'supply/return equipment pairs incomplete')
    return result


def compute(manifest):
    import ezdxf
    inputs = manifest['inputs']
    paths = {k: check_pin(v) for k, v in inputs.items()}
    require(manifest['schema'] == MODE, 'unsupported surplus-circle manifest')
    graph = load(paths['current_graph'])
    require(graph.get('metadata', {}).get('source_sha256') == inputs['source']['sha256']
            == graph['confirmedSideviewCanonicalization']['source_sha256']
            == graph['sourceOrderedSideviewEquipmentOwnership']['source_sha256'],
            'current graph does not belong to the original reviewed native source')
    audit, ordered_evidence = load(paths['owner_audit']), load(paths['owner_evidence'])
    require(audit['output_graph_sha256'] == inputs['current_graph']['sha256']
            and audit['output_evidence_sha256'] == inputs['owner_evidence']['sha256']
            and audit['output_devices_sha256'] == inputs['components']['sha256'],
            'current native owner graph/evidence/component receipt differs')
    # The existing owner hashes its nested evidence with its historical encoder.
    native_row_bytes = (json.dumps(ordered_evidence['evidence'], ensure_ascii=False, indent=2) + '\n').encode('utf8')
    require(graph['sourceOrderedSideviewEquipmentOwnership']['ordered_row_evidence_sha256']
            == hashlib.sha256(native_row_bytes).hexdigest(), 'current native row evidence changed')
    render = load(paths['render_audit'])
    answer = bind_answer(load(paths['definitions']), load(paths['reply']), load(paths['question']), render, manifest)
    doc = ezdxf.readfile(paths['source'])
    archived = {c['handle']: c for c in render['main_circle_context_only']}
    records = [circle_disposition(doc, graph, b, archived[b['circle_handle']]) for b in manifest['circles']]
    require({r['system'] for r in records} == {'supply', 'return'}, 'independent supply/return circles required')
    interfaces = protect_interfaces(graph, manifest['interfaces'])
    for value in inputs.values():
        check_pin(value)
    return dict(mode=MODE, status='received_erratum_existing_native_disposition_verified', inputs=inputs,
                answer_binding=answer, records=records, protected_interfaces=interfaces,
                native_source_read_fresh=True, current_native_graph_disposition_checked=True,
                owner_reconstruction_reexecuted=False, full_raw_reconstruction_claimed=False,
                graph_mutated=False, source_mutated=False, component_assignments_changed=False,
                physical_values_assigned=0, retired_new_nodes=0, new_hil_question_ids=[],
                human_accepted=False, scope='Exact two archived C circles only; existing real B1/B2 interface pairs preserved.')


def produce(manifest_path, output):
    output = Path(output)
    require(not output.exists(), 'fresh surplus-circle verification output required')
    implementation = sha(__file__)
    proof = compute(load(manifest_path))
    require(implementation == sha(__file__), 'verification implementation changed')
    output.mkdir(parents=True)
    target = output / 'surplus-circle-disposition.json'
    target.write_bytes(encode(proof))
    (output / 'receipt.json').write_bytes(encode(dict(mode=MODE, manifest=dict(path=str(Path(manifest_path).resolve()), sha256=sha(manifest_path)), implementation_sha256=implementation, output_sha256=sha(target))))
    return proof


def verify(output):
    output = Path(output)
    receipt = load(output / 'receipt.json')
    require(receipt['mode'] == MODE and receipt['implementation_sha256'] == sha(__file__)
            and sha(output / 'surplus-circle-disposition.json') == receipt['output_sha256'], 'surplus-circle receipt changed')
    fresh = compute(load(check_pin(receipt['manifest'])))
    require(encode(fresh) == (output / 'surplus-circle-disposition.json').read_bytes(), 'independent native circle disposition differs')
    return fresh


def main():
    parser = argparse.ArgumentParser()
    for key in ('manifest', 'output', 'verify-output'):
        parser.add_argument('--' + key, type=Path)
    args = parser.parse_args()
    if args.verify_output:
        require(args.manifest is None and args.output is None, 'verification uses original fixed inputs')
        result = verify(args.verify_output)
    else:
        require(args.manifest is not None and args.output is not None, 'manifest and fresh output required')
        result = produce(args.manifest, args.output)
    print(json.dumps(dict(status=result['status'], circles=len(result['records']), protected_interfaces=len(result['protected_interfaces']), graph_mutated=False, human_accepted=False)))


if __name__ == '__main__':
    main()
