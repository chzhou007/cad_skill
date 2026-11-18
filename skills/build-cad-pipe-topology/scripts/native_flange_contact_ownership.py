"""Resolve known balancing symbols through actual WCS flange contacts.

This is a fallback for a complete source signature whose centre is offset
from its pipe. It does not widen centre snapping or use INSERT proximity.
"""
import copy
import math
from collections import Counter

from native_balancing_valve_recovery import ports
from native_line_path_evidence import LAYERS, _on

MODE = 'native_complete_balancing_flange_contact_ownership_v1'


def footprint(insert, tol=.05):
    if insert.dxf.name != '平衡阀':
        return None
    geometry = ports(insert, tol)
    if geometry is None:
        return None
    lines = sorted([(list(e.dxf.start), list(e.dxf.end)) for e in insert.virtual_entities()], key=lambda ab: math.dist(*ab), reverse=True)
    corners = lines[0] + lines[1]
    eps = max(math.dist(*lines[0]) * 1e-6, 1e-7)
    flanges = [ab for ab in lines[2:] if all(any(math.dist(p, q) <= eps for q in corners) for p in ab)]
    if len(flanges) != 2:
        return None
    return dict(geometry, flanges_WCS=flanges)


def flange_contacts(geometry, start, end, tol=.05):
    """Both finite flange strokes must meet the same parallel, same-Z pipe."""
    if not math.isfinite(tol) or tol <= 0:
        raise ValueError('positive finite contact tolerance required')
    if not all(math.isfinite(value) for point in (start, end) for value in point):
        raise ValueError('finite native pipe coordinates required')
    vector = [end[i] - start[i] for i in range(3)]
    axis = [geometry['ports_WCS'][1][i] - geometry['ports_WCS'][0][i] for i in range(2)]
    length, axis_length = math.hypot(*vector[:2]), math.hypot(*axis)
    if min(length, axis_length) <= tol:
        return None
    cross = lambda a, b: a[0] * b[1] - a[1] * b[0]
    if abs(cross(vector, axis)) > tol * max(length, axis_length):
        return None
    contacts = []
    for a, b in geometry['flanges_WCS']:
        flange = [b[i] - a[i] for i in range(3)]
        denominator = cross(vector, flange)
        if abs(denominator) <= 1e-12 * length * math.hypot(*flange[:2]):
            return None
        offset = [a[i] - start[i] for i in range(2)]
        t, u = cross(offset, flange) / denominator, cross(offset, vector) / denominator
        if not -tol / length <= t <= 1 + tol / length:
            return None
        if not -tol / math.dist(a, b) <= u <= 1 + tol / math.dist(a, b):
            return None
        contact = [start[i] + t * vector[i] for i in range(3)]
        native = [a[i] + u * flange[i] for i in range(3)]
        if math.dist(contact, native) > tol:
            return None
        contacts.append(dict(point_WCS=contact, source_flange_WCS=copy.deepcopy([a, b]), pipe_fraction=t, flange_fraction=u))
    if math.dist(contacts[0]['point_WCS'], contacts[1]['point_WCS']) <= tol:
        return None
    return contacts


def classify(insert, pipes, graph, tol=.05):
    geometry = footprint(insert, tol)
    row = dict(source_handle=insert.dxf.handle, source_block_name=insert.dxf.name,
               raw_INSERT_origin=list(insert.dxf.insert), geometry=geometry,
               native_pipe_candidates=[], graph_candidates=[], assigned_edge_id=None)
    if geometry is None:
        return dict(row, status='unsupported_complete_native_signature')
    systems = {value: key for key, value in LAYERS.items()}
    for line in pipes:
        if line.dxftype() != 'LINE' or line.dxf.layer not in systems:
            continue
        start, end = list(line.dxf.start), list(line.dxf.end)
        contacts = flange_contacts(geometry, start, end, tol)
        if contacts is not None:
            row['native_pipe_candidates'].append(dict(source_LINE=line.dxf.handle, system=systems[line.dxf.layer], layer=line.dxf.layer, start=start, end=end, flange_contacts=contacts))
    if len(row['native_pipe_candidates']) != 1:
        return dict(row, status='no_unique_native_double_flange_contact')
    native = row['native_pipe_candidates'][0]
    points = [contact['point_WCS'] for contact in native['flange_contacts']]
    for edge in graph['edges']:
        if edge.get('system') != native['system'] or edge.get('connection_mode') != 'continuous_original_cad_pipe':
            continue
        if edge.get('source_handles') is not None and native['source_LINE'] not in edge['source_handles']:
            continue
        for pi, path in enumerate(edge.get('attribute_paths', [])):
            for si, (a, b) in enumerate(zip(path, path[1:])):
                if math.dist(a[:2], b[:2]) <= tol:
                    continue
                if all(_on(point[:2], a[:2], b[:2], tol) for point in points) and all(_on(point[:2], native['start'][:2], native['end'][:2], tol) for point in (a, b)):
                    row['graph_candidates'].append(dict(edge_id=edge['edge_id'], path_index=pi, segment_index=si, points=copy.deepcopy([a, b])))
    if len(row['graph_candidates']) != 1:
        return dict(row, status='no_unique_graph_contact_interval')
    midpoint = [(points[0][i] + points[1][i]) / 2 for i in range(3)]
    return dict(row, status='unique_native_double_flange_and_graph_contact', assigned_edge_id=row['graph_candidates'][0]['edge_id'], system=native['system'], contact_midpoint_WCS=midpoint, symbol_centre_offset_mm=math.dist(midpoint, geometry['center_WCS']), original_symbol_geometry_moved=False, physical_connector_length_assigned=False)


def recover(doc, graph, components, unresolved_handles, tol=.05):
    if not math.isfinite(tol) or tol <= 0:
        raise ValueError('positive finite contact tolerance required')
    if len({edge['edge_id'] for edge in graph['edges']}) != len(graph['edges']):
        raise ValueError('duplicate current graph edge IDs')
    selected = set(unresolved_handles)
    if len(selected) != len(unresolved_handles):
        raise ValueError('duplicate fallback source handles')
    if selected & {row.get('source_top_handle') for row in components}:
        raise ValueError('fallback cannot replace an existing component claim')
    inserts = {ent.dxf.handle: ent for ent in doc.modelspace().query('INSERT') if ent.dxf.name == '平衡阀'}
    if not selected <= inserts.keys():
        raise ValueError('fallback source population differs')
    old = copy.deepcopy(components)
    rows, added = [], []
    pipes = list(doc.modelspace().query('LINE'))
    for handle in sorted(selected):
        row = classify(inserts[handle], pipes, graph, tol)
        rows.append(row)
        if row['assigned_edge_id'] is None:
            continue
        name = '平衡阀-NATIVE-' + handle
        if any(previous.get('device_name') == name for previous in old + added):
            raise ValueError('native component identity collision')
        x, y = row['geometry']['center']
        a, b = row['contact_midpoint_WCS'][:2]
        added.append(dict(device_name=name, equipment_type='balancing_valve', type_code='BAL', x=str(x), y=str(y), assignment_x=str(a), assignment_y=str(b), source_kind='block_insert', source_block_name=inserts[handle].dxf.name, source_top_handle=handle, owner_equipment='', system_hint=row['system'], edge_id=row['assigned_edge_id'], edge_distance=str(row['symbol_centre_offset_mm']), assignment_status='assigned', original_edge_id='', assignment_basis=MODE, original_device_name='', original_owner_equipment=''))
    return dict(mode=MODE, records=rows, added_components=added, components=old + added, counts=dict(prior_components=len(old), added_components=len(added), output_components=len(old) + len(added), statuses=dict(Counter(row['status'] for row in rows))), prior_components_unchanged=True, source_graph_unchanged=True, source_symbol_geometry_unchanged=True, unknown_physical_parameters_filled=0, human_accepted=False)
