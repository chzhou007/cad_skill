"""Resolve scoped joint colour errors using confirmed upstream-main evidence.

This changes component ownership only. Native layers, graph connectivity,
ports and lengths are retained. The source contact conflict remains history.
"""
import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path

from inline_system_conflict_triage import triage
from native_path_coverage_audit import audit as coverage_audit
from native_junction_ray_evidence import collect as junction_audit
from repair_exploded_joint_ownership import _inventory
from source_readability import read_source

RULE = 'expert_confirmed_no_system_change_follow_upstream_main'


def repair(doc, graph, rows, policy, hashes, tol=.05):
    for key in ('source_sha256', 'graph_sha256', 'devices_sha256'):
        if policy.get(key) != hashes.get(key):
            raise ValueError('input hash mismatch: ' + key)
    if not math.isfinite(tol) or not 0 < tol <= .05:
        raise ValueError('invalid tolerance')
    confirmation = policy.get('confirmation', {})
    if (confirmation.get('rule') != RULE or confirmation.get('status') != 'user_confirmed'
            or not confirmation.get('source_reference') or not confirmation.get('statement')):
        raise ValueError('explicit expert rule confirmation required')
    selected = policy.get('joints')
    if (not isinstance(selected, list) or not selected
            or len({s['joint_handle'] for s in selected}) != len(selected)):
        raise ValueError('invalid or duplicate selected joints')
    _inventory(graph, rows)
    # Recreate native contacts, full same-system source route and three tee rays.
    conflicts = triage(doc, graph, hashes['source_sha256'], tol)
    by_joint = {r['joint_handle']: r for r in conflicts['records']}
    coverage = coverage_audit(doc, graph, policy['coverage_policy'],
                              hashes['source_sha256'], hashes['graph_sha256'], tol)
    junctions = junction_audit(doc, graph, policy['junction_policy'],
                               hashes['source_sha256'], hashes['graph_sha256'], tol)
    by_edge = {r['edge_id']: r for r in coverage['edges']}
    by_tee = {r['node_id']: r for r in junctions['junctions']}
    edges = {e['edge_id']: e for e in graph['edges']}
    nodes = {n['node_id']: n for n in graph['nodes']}
    expected_edges = {s['to_edge'] for s in selected}
    if set(by_edge) != expected_edges or set(by_tee) != {s['upstream_tee'] for s in selected}:
        raise ValueError('upstream evidence scope mismatch')
    changes = []
    g = copy.deepcopy(graph)
    records = copy.deepcopy(rows)
    gedges = {e['edge_id']: e for e in g['edges']}
    for spec in selected:
        handle = spec['joint_handle']
        conflict = by_joint.get(handle)
        matches = [r for r in records if r.get('source_top_handle') == handle]
        target = edges.get(spec['to_edge'])
        if (not conflict or len(matches) != 1 or not target
                or matches[0].get('equipment_type') != '金属软接'
                or matches[0].get('assignment_status') != 'assigned'):
            raise ValueError('selected component is not unique')
        row = matches[0]
        if (row['device_name'] != conflict['component_name']
                or row['device_name'] != spec['device_name']
                or row['edge_id'] != spec['from_edge']
                or conflict['assigned_edge_id'] != spec['from_edge']
                or conflict['witness_edge_ids'] != [spec['to_edge']]):
            raise ValueError('selected ownership or unique witness mismatch')
        evidence = by_edge[spec['to_edge']]
        tee = by_tee[spec['upstream_tee']]
        if (evidence['system'] != tee['system'] or target['system'] != tee['system']
                or spec['upstream_tee'] not in (target['start_node_id'], target['end_node_id'])):
            raise ValueError('upstream tee system mismatch')
        owner = target.get('device_label')
        if (not owner or owner not in (target['start_node_id'], target['end_node_id'])
                or nodes.get(owner, {}).get('node_type') not in ('equipment', 'physical_equipment')):
            raise ValueError('target logical equipment missing')
        contacts = [c for c in conflict['contacts']
                    if c['lines'][0]['source_handle'] == spec['upstream_contact_line']]
        if len(contacts) != 1 or contacts[0]['lines'][0]['system'] != target['system']:
            raise ValueError('upstream contact mismatch')
        contact = contacts[0]
        segments = evidence['segments']
        # Orient the route from its source tee towards this joint. The final
        # graphical connector to equipment stays explicitly unwitnessed.
        if math.dist(segments[0]['start'], tee['position']) <= tol:
            ordered = segments
        elif math.dist(segments[-1]['end'], tee['position']) <= tol:
            ordered = [dict(s, start=s['end'], end=s['start']) for s in reversed(segments)]
        else:
            raise ValueError('source route does not begin at upstream tee')
        prefix = []
        for segment in ordered:
            if segment['status'] != 'single_source_line_covers':
                break
            if len(segment['witnesses']) != 1:
                raise ValueError('ambiguous upstream source segment')
            prefix.append(segment)
        if (not prefix or math.dist(prefix[-1]['end'], contact['midpoint'][:2]) > tol
                or prefix[-1]['witnesses'][0]['source_handle'] != spec['upstream_contact_line']):
            raise ValueError('continuous source route does not reach selected joint')
        if len(prefix) == len(ordered):
            raise ValueError('unexpected fully covered route; review scope required')
        old_name = row['device_name']
        new_name = spec.get('new_device_name', old_name)
        if (not isinstance(new_name, str) or not new_name
                or any(r is not row and r['device_name'] == new_name for r in records)):
            raise ValueError('duplicate or invalid replacement component name')
        origin = gedges[row['edge_id']]
        destination = gedges[target['edge_id']]
        item = next((i for i in origin['equipment_inventory']
                     if i['equipment_type'] == row['equipment_type']), None)
        if item is None or item['device_names'].count(old_name) != 1:
            raise ValueError('source inventory mismatch')
        item['device_names'].remove(old_name)
        item['count'] -= 1
        if item['count'] == 0:
            origin['equipment_inventory'].remove(item)
        dest_item = next((i for i in destination['equipment_inventory']
                          if i['equipment_type'] == row['equipment_type']), None)
        if dest_item is None:
            dest_item = {'equipment_type': row['equipment_type'], 'count': 0, 'device_names': []}
            destination['equipment_inventory'].append(dest_item)
        dest_item['device_names'].append(new_name)
        dest_item['count'] += 1
        from pipe_geometry import segdist
        distance = min(segdist((float(row['assignment_x']), float(row['assignment_y'])), a, b)
                       for path in target['attribute_paths'] for a, b in zip(path, path[1:]))
        record = {
            'joint_handle': handle, 'original_device_name': old_name, 'device_name': new_name,
            'from_edge': spec['from_edge'], 'to_edge': target['edge_id'],
            'system': target['system'], 'upstream_tee': spec['upstream_tee'],
            'original_owner_equipment': row.get('owner_equipment'),
            'logical_owner_equipment': owner,
            'source_line_handles': [s['witnesses'][0]['source_handle'] for s in prefix],
            'original_conflict': copy.deepcopy(next(c for c in graph['sourceInlineSystemConflicts']
                                                    if c['joint_handle'] == handle)),
            'confirmation': copy.deepcopy(confirmation),
            'source_sha256': hashes['source_sha256'],
            'status': 'source_colour_error_resolved_by_confirmed_upstream_rule',
            'physical_port_verified': False, 'physical_length': 'unknown',
            'whole_graph_human_accepted': False,
        }
        row.update(original_device_name=old_name, device_name=new_name,
                   original_owner_equipment=row.get('owner_equipment', ''),
                   owner_equipment=owner, original_edge_id=spec['from_edge'],
                   edge_id=target['edge_id'], edge_distance=str(distance),
                   system_hint=target['system'], assignment_basis=RULE)
        destination.setdefault('source_inline_system_resolutions', []).append(copy.deepcopy(record))
        changes.append(record)
    selected_handles = {s['joint_handle'] for s in selected}
    g['sourceInlineSystemConflicts'] = [c for c in g['sourceInlineSystemConflicts']
                                      if c['joint_handle'] not in selected_handles]
    g.setdefault('sourceInlineSystemResolutions', []).extend(copy.deepcopy(changes))
    g.setdefault('metadata', {}).update(hil_ready=False, review_status='unreviewed')
    _inventory(g, records)
    # Preserve physical component identity even when a misleading generated
    # device name or logical equipment label has been corrected.
    identity = lambda rs: sorted((r.get('source_top_handle', ''), r['equipment_type'],
                                 r.get('x', ''), r.get('y', '')) for r in rs)
    if identity(rows) != identity(records):
        raise ValueError('physical component identity changed')
    if g['nodes'] != graph['nodes']:
        raise ValueError('node topology changed')
    for before, after in zip(graph['edges'], g['edges']):
        excluded = {'equipment_inventory', 'source_inline_system_resolutions'}
        if {k:v for k,v in before.items() if k not in excluded} != {k:v for k,v in after.items() if k not in excluded}:
            raise ValueError('edge topology or physical attributes changed')
    return g, records, dict(status='scoped_upstream_system_repair_not_graph_acceptance',
        **hashes, changes=changes, coverage=coverage, junctions=junctions,
        remaining_conflicts=len(g['sourceInlineSystemConflicts']), hil_ready=False,
        dependent_evidence_status='input_graph_and_inventory_only_rebuild_for_output')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('source', 'graph', 'devices', 'policy', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    doc, proof = read_source(a.source)
    sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    with a.devices.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f); fields = reader.fieldnames; rows = list(reader)
    g, records, report = repair(doc, json.loads(a.graph.read_text(encoding='utf8')), rows,
        json.loads(a.policy.read_text(encoding='utf8')), dict(source_sha256=proof['source_sha256'],
        graph_sha256=sha(a.graph), devices_sha256=sha(a.devices)))
    a.output.mkdir(parents=True, exist_ok=False)
    target = a.output / 'graph_with_edges.json'
    target.write_text(json.dumps(g, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    fields = list(dict.fromkeys(fields + [k for r in records for k in r]))
    with (a.output/'edge_device_instances.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(records)
    report.update(output_graph_sha256=sha(target), policy_sha256=sha(a.policy),
                  output_devices_sha256=sha(a.output/'edge_device_instances.csv'),
                  script_sha256=sha(__file__), source_preflight=proof,
                  input_files={key:str(getattr(a,key).resolve())
                               for key in ('source','graph','devices','policy')})
    (a.output/'upstream-system-repair-audit.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'scoped_joints':len(report['changes']),
        'moved':sum(r['from_edge']!=r['to_edge'] for r in report['changes']),
        'remaining_conflicts':report['remaining_conflicts'], 'hil_ready':False}))


def verify_output(graph_path):
    """Reproduce a correction before accepting its claimed conflict removal."""
    graph_path = Path(graph_path)
    report_path = graph_path.parent/'upstream-system-repair-audit.json'
    report = json.loads(report_path.read_text(encoding='utf8'))
    sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    inputs = {key:Path(report['input_files'][key]) for key in ('source','graph','devices','policy')}
    if (report.get('output_graph_sha256') != sha(graph_path)
            or report.get('script_sha256') != sha(__file__)
            or report.get('policy_sha256') != sha(inputs['policy'])):
        raise ValueError('upstream repair output, script or policy changed')
    doc, proof = read_source(inputs['source'])
    hashes = dict(source_sha256=proof['source_sha256'], graph_sha256=sha(inputs['graph']),
                  devices_sha256=sha(inputs['devices']))
    if any(report.get(k)!=v for k,v in hashes.items()):
        raise ValueError('upstream repair input changed')
    with inputs['devices'].open(encoding='utf-8-sig',newline='') as f:
        rows = list(csv.DictReader(f))
    original = json.loads(inputs['graph'].read_text(encoding='utf8'))
    if original.get('sourceFloorLabelRepair'):
        from repair_source_floor_labels import verify_output as verify_floor_output
        verify_floor_output(inputs['graph'])
    result, inventory, audit = repair(doc,
        original,rows,
        json.loads(inputs['policy'].read_text(encoding='utf8')),hashes)
    corrected = graph_path.parent/'edge_device_instances.csv'
    with corrected.open(encoding='utf-8-sig',newline='') as f:
        output_rows = list(csv.DictReader(f))
    # CSV adds blank values for optional fields absent on unaffected rows.
    fields=set().union(*(r.keys() for r in output_rows))
    normalized=[{k:str(r.get(k,'')) for k in fields} for r in inventory]
    if (result != json.loads(graph_path.read_text(encoding='utf8'))
            or output_rows != normalized
            or report.get('output_devices_sha256') != sha(corrected)
            or report.get('changes') != audit['changes']
            or report.get('coverage') != audit['coverage']
            or report.get('junctions') != audit['junctions']):
        raise ValueError('upstream repair is not reproducible')
    return {'status':'source_reproduced_scoped_system_repair','joints':len(audit['changes']),
            'graph_sha256':sha(graph_path),'hil_ready':False}


if __name__ == '__main__':
    main()
