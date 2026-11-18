"""Apply source-qualified owner corrections and a recovered component to an index."""
import copy,math
from build_visualization import normalize_instance_position
from instance_geometry import source_paths
from source_evidence import attributes as native_attributes
from recovered_component_graph_bridge import edge_bases

MODE='native_contact_owner_rendered_index_application_v1'
ROOT='sourceNativeContactOwnerApplication'

def restore(graph,audit):
    result=copy.deepcopy(graph);added=set(audit['added_instance_ids']);previous=audit['previous_instances']
    if len([item for item in result['instances']if item['id']in added])!=len(added):raise ValueError('contact index added population differs')
    result['instances']=[copy.deepcopy(previous.get(item['id'],item))for item in result['instances']if item['id']not in added]
    edges={edge['edge_id']:edge for edge in result['edges']}
    for eid,value in audit['previous_edge_inventories'].items():edges[eid]['equipment_inventory']=copy.deepcopy(value)
    del result[ROOT]
    return result

def apply(parent,native_axis,inventory,added,doc,type_policy,source_hash,parent_hash):
    if ROOT in parent:raise ValueError('contact index already applied')
    if inventory.get('all_component_ids_and_counts_conserved')is not True or inventory.get('source_graph_and_symbol_geometry_unchanged')is not True:raise ValueError('native owner conservation proof required')
    if any(row.get('human_accepted')is not False for row in (inventory,added)):raise ValueError('technical source proof must not inherit acceptance')
    result=copy.deepcopy(parent);instances={item['source_top_handle']:item for item in result['instances']if item.get('source_top_handle')};edges={edge['edge_id']:edge for edge in result['edges']};native={edge['edge_id']:edge for edge in native_axis['edges']}
    if edges.keys()!=native.keys():raise ValueError('native/rendered edge population differs')
    tf=result['transform'];project=lambda p:[(p[0]-tf['originX'])/tf['scale'],(tf['originY']-p[1])/tf['scale']]
    before={};affected=set();new=[]
    for change in inventory['changes']:
        h=change['source_handle'];item=instances.get(h);prior,after=change['before'],change['after']
        if item is None or item['source_device_name']!=prior['device_name']or item['edge_id']!=prior['edge_id']or prior['device_name']!=after['device_name']or prior['owner_equipment']!=after['owner_equipment']:raise ValueError('old rendered component identity or equipment membership differs')
        before[item['id']]=copy.deepcopy(item)
        for eid in (prior['edge_id'],after['edge_id']):
            if any(edges[eid].get(key)!=native[eid].get(key)for key in ('edge_id','start_node_id','end_node_id','system','attribute_paths')):raise ValueError('changed component pipe scope differs')
            affected.add(eid)
        if edges[prior['edge_id']]['system']!=edges[after['edge_id']]['system']:raise ValueError('contact correction crosses systems')
        for key in ('edge_id','assignment_x','assignment_y','edge_distance','assignment_status','assignment_basis','original_edge_id'):
            item[key]=float(after[key])if key in ('assignment_x','assignment_y','edge_distance')else after[key]
        item['related_edge_ids']=[after['edge_id']];item['px'],item['py']=project([item['assignment_x'],item['assignment_y']])
        if any(item.get(key)!=before[item['id']].get(key)for key in ('id','name','type','label','source_device_name','owner_equipment','x','y','sourceGeometry')):raise ValueError('source contact correction changed symbol or equipment identity')
    rows=added['added_components'];records={row['source_handle']:row for row in added['records']}
    code,label=type_policy['code'],type_policy['label']
    if code not in result['symbols']or not any(row['code']==code for row in result['types']):raise ValueError('original source-recovered component type missing')
    for row in rows:
        h=row['source_top_handle'];record=records[h];eid=row['edge_id']
        if h in instances or record['assigned_edge_id']!=eid or record['status']!='unique_native_double_flange_and_graph_contact':raise ValueError('additional source component lacks unique native contact')
        if any(edges[eid].get(key)!=native[eid].get(key)for key in ('edge_id','start_node_id','end_node_id','system','attribute_paths'))or edges[eid]['system']!=row['system_hint']:raise ValueError('additional native component pipe scope differs')
        insert=doc.entitydb.get(h)
        if insert is None or insert not in doc.modelspace()or insert.dxf.name!=type_policy['symbol']['block']:raise ValueError('additional component source handle differs')
        item=copy.deepcopy(row);normalize_instance_position(item,row['device_name'])
        if math.dist([item['x'],item['y']],record['geometry']['center_WCS'][:2])>1e-6:raise ValueError('additional native symbol centre differs')
        item.pop('device_name');item.pop('equipment_type');item.update(id='I-NATIVE-'+h,name=label+'-NATIVE-'+h,type=code,label=label,source_device_name=row['device_name'],related_edge_ids=[eid],display_source_chain=[h],display_source_status='native_complete_double_flange_contact_replayed',display_source_rule=MODE)
        item['px'],item['py']=project([item['assignment_x'],item['assignment_y']]);item['sourceX'],item['sourceY']=project([item['x'],item['y']])
        paths=source_paths(doc,chain=[h])
        if not paths:raise ValueError('additional source symbol geometry empty')
        item['sourceGeometry']=[dict(points=[project(p)for p in path['points']],fill=path['fill'])for path in paths];native_attributes(doc,item)
        if any(previous['id']==item['id']for previous in result['instances']):raise ValueError('additional component ID collision')
        result['instances'].append(item);instances[h]=item;new.append(item['id']);affected.add(eid)
    previous_inventory={eid:copy.deepcopy(edges[eid].get('equipment_inventory',[]))for eid in sorted(affected)}
    for eid in sorted(affected):
        groups={};order=[group['type']for group in previous_inventory[eid]]
        for item in result['instances']:
            if item['edge_id']!=eid:continue
            key=item['type']
            if key not in order:order.append(key)
            group=groups.setdefault(key,dict(type=key,label=item['label'],count=0,device_names=[]));group['count']+=1;group['device_names'].append(item['name'])
        edges[eid]['equipment_inventory']=[groups[key]for key in order if key in groups]
    audit=dict(mode=MODE,parent_graph_sha256=parent_hash,native_owner_proof_sha256=source_hash,previous_instances=before,previous_edge_inventories=previous_inventory,added_instance_ids=new,old_instances=len(parent['instances']),corrected_instances=len(before),output_instances=len(result['instances']),all_pipe_bases_unchanged=True,source_symbol_geometry_unchanged=True,related_confirmation_inherited=False,human_accepted=False)
    result[ROOT]=audit
    if edge_bases(result)!=edge_bases(parent)or restore(result,audit)!=parent:raise ValueError('contact changes cannot restore exact original graph')
    return result,audit
