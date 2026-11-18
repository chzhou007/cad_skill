"""Build a versioned rendered index from independently recovered native rows.

The original builder owns symbol paths, projection and source attributes.
This module preserves the entire old graph except declared new instance/type
and per-edge inventory additions; it never infers pipe connectivity.
"""
import copy,math
from build_visualization import normalize_instance_position,load_symbol
from instance_geometry import source_paths
from source_evidence import attributes as native_attributes
MODE='native_recovered_component_rendered_graph_bridge_v1'
TYPE_FIELDS=('edge_id','start_node_id','end_node_id','system','floor_start','floor_end','attribute_paths')


def edge_bases(graph):
    return {e['edge_id']:[copy.deepcopy(e.get(k))for k in TYPE_FIELDS]for e in graph['edges']}


def build(parent,native,proof,doc,type_policy,source_proof_hash,parent_graph_hash):
    if proof.get('prior_components_unchanged')is not True or proof.get('source_graph_unchanged')is not True or proof.get('resistance_parameters_assigned')!=0 or proof.get('human_accepted')is not False:raise ValueError('complete source-qualified component inventory required')
    prior=proof['components'][:proof['counts']['prior_components']];add=proof['added_components']
    if len(add)!=proof['counts']['added_components']or proof['components']!=prior+add or not add:raise ValueError('native component population differs')
    old_names={x['source_device_name']:x for x in parent['instances']}
    if len(old_names)!=len(parent['instances'])or len(prior)!=len(old_names)or {r['device_name']for r in prior}!=old_names.keys():raise ValueError('rendered parent omits or duplicates an original component')
    for row in prior:
        if old_names[row['device_name']]['edge_id']!=row['edge_id']:raise ValueError('old canonical/rendered component owner differs')
    if parent.get('sourceRecoveredNativeComponentIndex'):raise ValueError('native recovered index already applied')
    result=copy.deepcopy(parent);edges={e['edge_id']:e for e in result['edges']};native_edges={e['edge_id']:e for e in native['edges']}
    if edges.keys()!=native_edges.keys():raise ValueError('native/rendered edge population differs')
    code,label=type_policy['code'],type_policy['label'];block=type_policy['symbol']['block']
    if code in result['symbols']or any(t['code']==code for t in result['types']):raise ValueError('recovered type competes with an existing type')
    records={r['source_handle']:r for r in proof['records']};claimed={x.get('source_top_handle')for x in result['instances']};ids={x['id']for x in result['instances']};names={x['name']for x in result['instances']};previous={};new=[];tf=result['transform']
    def project(point):return [(point[0]-tf['originX'])/tf['scale'],(tf['originY']-point[1])/tf['scale']]
    for row in add:
        handle=row['source_top_handle'];record=records[handle];eid=row['edge_id'];edge=edges[eid];source=native_edges[eid]
        if handle in claimed or record['status']!='recovered_unique_native_ports_and_graph_segment'or record['assigned_edge_id']!=eid or record['device_name']!=row['device_name']or record['system']!=edge['system']or row['system_hint']!=edge['system']:raise ValueError('new source instance has conflicting identity or owner')
        if any(edge.get(k)!=source.get(k)for k in('edge_id','start_node_id','end_node_id','system','attribute_paths')):raise ValueError('new component native/rendered pipe extent differs')
        insert=doc.entitydb.get(handle)
        if insert is None or insert not in doc.modelspace()or insert.dxftype()!='INSERT'or insert.dxf.name!=block or row['source_block_name']!=block or row['equipment_type']not in type_policy['source_names']:raise ValueError('new type lacks its exact modelspace native block')
        item=copy.deepcopy(row);normalize_instance_position(item,row['device_name'])
        if math.dist([item['x'],item['y']],record['geometry']['center_WCS'][:2])>1e-6:raise ValueError('recovered position differs from transformed native ports')
        stable_id='I-NATIVE-'+handle;name=label+'-NATIVE-'+handle
        if stable_id in ids or name in names:raise ValueError('recovered component ID or name collision')
        item.pop('equipment_type');item.pop('device_name');item.update(id=stable_id,type=code,label=label,name=name,source_device_name=row['device_name'],related_edge_ids=[eid],display_source_chain=[handle],display_source_status='native_signature_ports_and_exact_top_handle_replayed',display_source_rule=MODE)
        item['px'],item['py']=project([item['assignment_x'],item['assignment_y']]);item['sourceX'],item['sourceY']=project([item['x'],item['y']]);geometry=source_paths(doc,chain=[handle])
        if not geometry:raise ValueError('new native component geometry empty')
        item['sourceGeometry']=[dict(points=[project(p)for p in path['points']],fill=path['fill'])for path in geometry];native_attributes(doc,item)
        if eid not in previous:previous[eid]=copy.deepcopy(edge.get('equipment_inventory',[]))
        inventory=next((r for r in edge.get('equipment_inventory',[])if r['type']==code),None)
        if inventory is None:edge.setdefault('equipment_inventory',[]).append(dict(type=code,label=label,count=1,device_names=[name]))
        else:inventory['count']+=1;inventory['device_names'].append(name)
        result['instances'].append(item);new.append(item);claimed.add(handle);ids.add(stable_id);names.add(name)
    result['symbols'][code]=load_symbol(type_policy['symbol'],dict(main=doc),label);result['types'].append(dict(code=code,label=label,block=block))
    audit=dict(mode=MODE,parent_graph_sha256=parent_graph_hash,native_inventory_sha256=source_proof_hash,added_instance_ids=[x['id']for x in new],added_type=code,previous_edge_inventories=previous,original_instances_preserved=len(parent['instances']),new_instances=len(new),output_instances=len(result['instances']),all_pipe_connections_and_attribute_paths_unchanged=True,unknown_physical_parameters_assigned=0,related_HIL_confirmation_inherited=False,human_accepted=False)
    result['sourceRecoveredNativeComponentIndex']=audit
    if restore(result,audit)!=parent:raise ValueError('restoring declared component changes did not recover exact original graph')
    return result,audit


def restore(graph,audit):
    result=copy.deepcopy(graph);ids=set(audit['added_instance_ids']);code=audit['added_type']
    if len(ids)!=len(audit['added_instance_ids'])or len([x for x in result['instances']if x['id']in ids])!=len(ids):raise ValueError('recovered component index population differs')
    result['instances']=[x for x in result['instances']if x['id']not in ids];result['types']=[x for x in result['types']if x['code']!=code];del result['symbols'][code]
    edges={e['edge_id']:e for e in result['edges']}
    for eid,previous in audit['previous_edge_inventories'].items():edges[eid]['equipment_inventory']=copy.deepcopy(previous)
    del result['sourceRecoveredNativeComponentIndex'];return result
