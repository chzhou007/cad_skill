"""Reapply the original flange owner to independently witnessed local fragments.

A whole-edge omission does not invalidate an actual LINE fragment. The private
projection below qualifies only component contact, never whole-edge continuity.
"""
import copy
import math
from collections import Counter

from native_ball_contact_reapplication import footprint, source_owners
from native_line_path_evidence import LAYERS, _on

MODE = 'native_source_fragment_ball_contact_reapplication_v1'


def fragment_view(doc, graph, routing, tol=.05):
    edges = {e['edge_id']: e for e in graph['edges']}
    if len(edges) != len(graph['edges']):
        raise ValueError('unique canonical edge IDs required')
    fragments, bindings, seen = [], {}, set()
    for row in routing['records']:
        key = (row['edge_id'], row['path_index'], row['segment_index'])
        if key in seen:
            raise ValueError('duplicate routed segment')
        seen.add(key)
        edge = edges[row['edge_id']]
        path = edge['attribute_paths'][key[1]]
        points = path[key[2]:key[2]+2]
        if len(points) != 2 or row['scope_points'] != points or row['system'] != edge['system']:
            raise ValueError('routing/current graph scope differs')
        if row.get('native_source_status') != 'single_source_line_covers' or row.get('source_line_coverage_checked') is not True:
            continue
        witnesses = row.get('native_witnesses', [])
        if len(witnesses) != 1 or witnesses[0].get('scope') != 'modelspace':
            continue
        witness = witnesses[0]
        line = doc.entitydb.get(witness['source_handle'])
        if line is None or line.dxftype() != 'LINE' or line.dxf.layer != LAYERS.get(edge['system']):
            raise ValueError('native fragment LINE/system differs')
        if line.dxf.owner != doc.modelspace().block_record_handle:
            raise ValueError('modelspace fragment must not reference a block definition')
        start, end = list(line.dxf.start), list(line.dxf.end)
        if witness['start'] != start[:2] or witness['end'] != end[:2] or witness['layer'] != line.dxf.layer:
            raise ValueError('native fragment witness differs')
        if math.dist(*points) <= tol or not all(_on(p, start[:2], end[:2], tol) for p in points):
            raise ValueError('finite original fragment not covered by native LINE')
        fid = '{}:path{}:segment{}'.format(*key)
        fragments.append(dict(edge_id=fid, system=edge['system'],
            connection_mode='continuous_original_cad_pipe', source_handles=[line.dxf.handle],
            attribute_paths=[copy.deepcopy(points)]))
        bindings[fid] = dict(edge_id=key[0], path_index=key[1], segment_index=key[2],
            source_LINE=line.dxf.handle, scope_points=copy.deepcopy(points),
            source_start_WCS=start, source_end_WCS=end,
            original_whole_edge_mode=edge.get('connection_mode'),
            whole_edge_connectivity_reclassified=False)
    expected = {(e['edge_id'], pi, si) for e in graph['edges']
        for pi, path in enumerate(e.get('attribute_paths', [])) for si in range(len(path)-1)}
    if seen != expected:
        raise ValueError('complete current routing cohort required')
    return dict(edges=fragments), bindings


def collect(doc, graph, components, routing, tol=.05):
    if not math.isfinite(tol) or tol <= 0:
        raise ValueError('positive finite original contact tolerance required')
    original = copy.deepcopy(components)
    graph_before = copy.deepcopy(graph)
    view, bindings = fragment_view(doc, graph, routing, tol)
    pipes = list(doc.modelspace().query('LINE'))
    claims = {}
    for row in original:
        if row.get('source_top_handle'):
            claims.setdefault(row['source_top_handle'], []).append(row)
    records, added = [], []
    names = {row['device_name'] for row in original}
    fields = list(original[0]) if original else []
    for insert in doc.modelspace().query('INSERT'):
        if insert.dxf.name != 'H-PICPNT-91':
            continue
        handle = insert.dxf.handle
        geometry = footprint(insert, tol)
        row = dict(source_handle=handle, geometry=geometry,
            previous_claims=copy.deepcopy(claims.get(handle, [])))
        if geometry is None:
            records.append(dict(row, status='unsupported_original_signature')); continue
        native, owners = source_owners(geometry, pipes, view, tol)
        row.update(native_candidates=native,
            fragment_candidates=[bindings[o['edge_id']] for o in owners])
        if len(native) != 1 or len(owners) != 1:
            records.append(dict(row, status='native_or_fragment_owner_unresolved')); continue
        owner = bindings[owners[0]['edge_id']]
        if claims.get(handle):
            old = claims[handle]
            agrees = len(old) == 1 and old[0]['edge_id'] == owner['edge_id'] and old[0]['equipment_type'] in ('球阀', 'ball_valve', 'Ball Valve')
            records.append(dict(row, status='existing_owner_independently_agrees' if agrees else 'existing_owner_conflict_retained'))
            continue
        name = '球阀-FRAGMENT-' + handle
        if name in names:
            raise ValueError('component identity collision')
        names.add(name)
        midpoint = [sum(c['point_WCS'][i] for c in native[0]['flange_contacts'])/2 for i in range(3)]
        component = dict.fromkeys(fields, '')
        component.update(device_name=name, equipment_type='球阀', type_code='BV',
            x=str(geometry['center'][0]), y=str(geometry['center'][1]),
            assignment_x=str(midpoint[0]), assignment_y=str(midpoint[1]),
            source_kind='block_insert', source_block_name=insert.dxf.name,
            source_top_handle=handle, owner_equipment='', system_hint=native[0]['system'],
            edge_id=owner['edge_id'], edge_distance=str(math.dist(geometry['center'], midpoint[:2])),
            assignment_status='assigned', assignment_basis=MODE)
        added.append(component)
        records.append(dict(row, status='unclaimed_source_instance_recovered', recovered_component=component))
    if graph != graph_before or components != original:
        raise ValueError('fragment contact reader mutated canonical input')
    return dict(mode=MODE, records=records, added_components=added, components=original+added,
        counts=dict(source_population=len(records), native_local_fragments=len(bindings),
            prior_components=len(original), added_components=len(added), output_components=len(original)+len(added),
            statuses=dict(Counter(r['status'] for r in records))),
        all_prior_component_rows_exact=True, source_graph_mutated=False,
        whole_edge_continuity_assigned=False, physical_values_assigned=0,
        viewer_index_adopted=False, human_accepted=False)
