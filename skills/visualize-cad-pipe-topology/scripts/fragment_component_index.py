"""Adopt source-proved instances only where the existing view profiles agree."""
import copy
from anchor_bounded_main_paths import component_profiles
from build_visualization import normalize_instance_position
from instance_geometry import source_paths
from source_evidence import attributes as native_attributes

MODE = 'native_fragment_component_index_v1'
AUDIT = 'sourceNativeFragmentComponentIndex'


def classify(provider, inventory):
    rows = {r['edge_id']: r for r in provider['records']}
    records = []
    for component in inventory['added_components']:
        eid = component['edge_id']; row = rows[eid]
        observations = row['correspondence_observations']
        result = dict(source_handle=component['source_top_handle'], axis_edge_id=eid,
            status='unsupported_existing_component_scope_retained', adopted=False)
        if len(observations) != 1:
            records.append(result); continue
        obs = observations[0]
        floor = str(obs.get('floor'))
        if (obs['domain'] != 'separate_named_external_port'
            or obs.get('grouped_axis_edges') != [eid]
            or len(obs['plan_edges']) != 1
            or floor not in provider['plan_exploded_component_reading_inventories']):
            records.append(result); continue
        plan = provider['plan_exploded_component_reading_inventories'][floor]['rows']
        expected = component_profiles(plan, obs['plan_edges'])
        actual = component_profiles(inventory['components'], [eid])
        agrees = expected == actual
        result.update(mapping_id=obs['mapping_id'], floor=int(floor),
            domain=obs['domain'], plan_edges=copy.deepcopy(obs['plan_edges']),
            plan_profile=expected, axis_profile=actual,
            status='current_native_profiles_agree' if agrees else 'source_detail_profile_difference',
            adopted=agrees, new_correspondence_assigned=False)
        records.append(result)
    return records


def build(parent, native, inventory, classifications, doc, parent_hash, proof_hash):
    old = inventory['components'][:inventory['counts']['prior_components']]
    by_name = {r['source_device_name']: r for r in parent['instances']}
    if len(by_name) != len(old) or {r['device_name'] for r in old} != set(by_name):
        raise ValueError('complete original rendered component population required')
    if any(by_name[r['device_name']]['edge_id'] != r['edge_id'] for r in old):
        raise ValueError('old source/rendered component ownership differs')
    if parent.get(AUDIT): raise ValueError('fragment index already applied')
    allowed = {r['source_handle'] for r in classifications if r['adopted'] is True}
    added = [r for r in inventory['added_components'] if r['source_top_handle'] in allowed]
    if not added or len(added) != len(allowed): raise ValueError('qualified added population required')
    types = [t for t in parent['types'] if t.get('block') == 'H-PICPNT-91']
    if len(types) != 1 or types[0]['code'] not in parent['symbols']:
        raise ValueError('one existing native ball valve display type required')
    display = types[0]; code, label = display['code'], display['label']
    result = copy.deepcopy(parent); edges = {e['edge_id']: e for e in result['edges']}
    native_edges = {e['edge_id']: e for e in native['edges']}
    if edges.keys() != native_edges.keys(): raise ValueError('pipe population differs')
    source_records = {r['source_handle']: r for r in inventory['records']}
    claimed = {r.get('source_top_handle') for r in parent['instances']}
    ids = {r['id'] for r in parent['instances']}; names = {r['name'] for r in parent['instances']}
    previous, created = {}, []
    transform = parent['transform']
    def project(p):
        return [(p[0]-transform['originX'])/transform['scale'],
                (transform['originY']-p[1])/transform['scale']]
    for row in added:
        handle, eid = row['source_top_handle'], row['edge_id']
        record = source_records[handle]; edge = edges[eid]; original_edge = native_edges[eid]
        if (handle in claimed or record['status'] != 'unclaimed_source_instance_recovered'
            or record['recovered_component'] != row or len(record['fragment_candidates']) != 1
            or record['fragment_candidates'][0]['edge_id'] != eid
            or row['system_hint'] != edge['system']):
            raise ValueError('qualified fragment owner differs')
        if any(edge.get(k) != original_edge.get(k) for k in
               ('edge_id', 'start_node_id', 'end_node_id', 'system', 'attribute_paths')):
            raise ValueError('native/rendered pipe scope differs')
        insert = doc.entitydb.get(handle)
        if insert is None or insert.dxftype() != 'INSERT' or insert.dxf.name != display['block']:
            raise ValueError('exact existing native display block required')
        item = copy.deepcopy(row); normalize_instance_position(item, row['device_name'])
        iid, name = 'I-FRAGMENT-'+handle, label+'-FRAGMENT-'+handle
        if iid in ids or name in names: raise ValueError('component identity collision')
        item.pop('equipment_type'); item.pop('device_name')
        item.update(id=iid, type=code, label=label, name=name,
            source_device_name=row['device_name'], related_edge_ids=[eid],
            display_source_chain=[handle], display_source_status='verified_unique_named_block_insert_chain',
            display_source_rule=MODE)
        item['px'], item['py'] = project([item['assignment_x'], item['assignment_y']])
        item['sourceX'], item['sourceY'] = project([item['x'], item['y']])
        geometry = source_paths(doc, chain=[handle])
        if not geometry: raise ValueError('native symbol geometry empty')
        item['sourceGeometry'] = [dict(points=[project(p) for p in g['points']], fill=g['fill']) for g in geometry]
        native_attributes(doc, item)
        if eid not in previous: previous[eid] = copy.deepcopy(edge.get('equipment_inventory', []))
        inv = next((r for r in edge['equipment_inventory'] if r['type'] == code), None)
        if inv is None:
            edge['equipment_inventory'].append(dict(type=code, label=label, count=1, device_names=[name]))
        else:
            inv['count'] += 1; inv['device_names'].append(name)
        result['instances'].append(item); created.append(item); ids.add(iid); names.add(name); claimed.add(handle)
    audit = dict(mode=MODE, parent_graph_sha256=parent_hash, native_proof_sha256=proof_hash,
        added_instances=[dict(id=r['id'], source_handle=r['source_top_handle'], edge_id=r['edge_id'], type=r['type'], name=r['name']) for r in created],
        previous_edge_inventories=previous, prior_instances=len(parent['instances']),
        added_count=len(created), current_instances=len(result['instances']),
        pipe_graph_restoration_exact=True, unknown_physical_parameters_assigned=0,
        human_confirmation_inherited=False, human_accepted=False)
    result[AUDIT] = audit
    if restore(result) != parent: raise ValueError('exact pipe/old-instance restoration failed')
    return result, audit


def restore(graph):
    result = copy.deepcopy(graph); audit = result.pop(AUDIT)
    ids = {r['id'] for r in audit['added_instances']}
    if len(ids) != audit['added_count'] or sum(r['id'] in ids for r in result['instances']) != len(ids):
        raise ValueError('overlay component population differs')
    result['instances'] = [r for r in result['instances'] if r['id'] not in ids]
    for edge in result['edges']:
        if edge['edge_id'] in audit['previous_edge_inventories']:
            edge['equipment_inventory'] = copy.deepcopy(audit['previous_edge_inventories'][edge['edge_id']])
    return result
