"""Extend a complete axis parent with independently mapped floor main values."""
import argparse,copy,math,re,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from anchored_floor_main_plan_attributes import verify_output as verify_attributes,implementation_hashes as attribute_hashes,preserve_known_main_values
from adopt_wave_rebased_plan_scopes import verify_output as verify_parent,implementation_hashes as parent_hashes

MODE='anchored_floor_main_attribute_fusion_v1'
ROOT='sourceAnchoredFloorMainAttributes'
FIELD='anchored_floor_main_attributes'

def horizontal_domain(graph,record,angles):
    nodes={n['node_id']:n for n in graph['nodes']};edge=next(e for e in graph['edges'] if e['edge_id']==record['iso_edges'][0])
    if (not angles or any(isinstance(a,bool) or not isinstance(a,(int,float)) or not math.isfinite(a) or abs(a%180-90)<.5 for a in angles)
        or edge['system']!=record['system'] or edge.get('source_wave_omission') or edge.get('source_view_context')
        or {edge['start_node_id'],edge['end_node_id']}!={record['iso_start'],record['iso_end']}):raise ValueError('main horizontal source domain differs')
    for names in (('floor_start','start_floor'),('floor_end','end_floor')):
        values=[edge[k] for k in names if k in edge]
        if not values or any(v!=record['floor'] for v in values):raise ValueError('main crosses floor boundary')
    if len(edge['attribute_paths'])!=1:raise ValueError('separate axis paths require their own extent reader')
    points=edge['attribute_paths'][0]
    for key,pt in zip(('start_node_id','end_node_id'),(points[0],points[-1])):
        node=nodes[edge[key]]
        if node.get('node_type') not in ('tee','physical_junction') or node.get('floor')!=record['floor'] or node.get('review_required') is True or math.dist(pt,[node['x'],node['y']])>.05:
            raise ValueError('main needs both current same-floor native Ts')
    for a,b in zip(points,points[1:]):
        if math.dist(a,b)<=.05:raise ValueError('degenerate axis main segment')
        bearing=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%180
        if not any(min(abs(bearing-v%180),180-abs(bearing-v%180))<=.1 for v in angles):raise ValueError('axis main contains unproved horizontal direction')
    return points

def append(parent,local,plan,mapping,attributes,hashes,angles):
    if ROOT in parent or any(FIELD in e for e in parent['edges']):raise ValueError('anchored main attributes already composed')
    if any(not re.fullmatch('[0-9a-f]{64}',v) for v in hashes.values()):raise ValueError('invalid main evidence hash')
    if (attributes['mapping_sha256']!=hashes['mapping'] or attributes['graph_sha256']!={'plan':mapping['plan_graph_sha256'],'iso':mapping['iso_graph_sha256']}
        or attributes['source_sha256']!=mapping['source_sha256'] or attributes['physical_values_fused'] is not False or attributes['human_accepted'] is not False):
        raise ValueError('main mapping and attribute source version differs')
    if parent['nodes']!=local['nodes']:raise ValueError('main composition parent changed local nodes')
    old={e['edge_id']:e for e in parent['edges']};raw={e['edge_id']:e for e in local['edges']}
    if len(old)!=len(parent['edges']) or old.keys()!=raw.keys():raise ValueError('main composition local edge set differs')
    for eid,edge in old.items():
        if {k:v for k,v in edge.items() if k not in ('cross_view_attributes','axis_riser_attributes','plan_segment_attributes')}!=raw[eid]:raise ValueError('parent main geometry or components changed')
    preserve_known_main_values(parent,attributes['records'],mapping['floor'])
    records={r['mapping_id']:r for r in mapping['records']};values={r['mapping_id']:r for r in attributes['records']}
    if len(records)!=len(mapping['records']) or len(values)!=len(attributes['records']) or records.keys()!=values.keys():raise ValueError('complete unique main mapping and attributes required')
    retained={r['current_main_mapping_id'] for r in mapping['evidence']['historical_scope_lineage'] if r.get('current_main_mapping_id')}
    retained.update(mapping['evidence']['preserved_floor_attributes']['named_main_mapping_ids'])
    if not retained<=records.keys() or len(retained)!=mapping['historical_main_paths']:raise ValueError('historical main scope differs')
    result=copy.deepcopy(parent);target={e['edge_id']:e for e in result['edges']};proof=[];claimed=set()
    for mid,row in values.items():
        record=records[mid]
        if any(row[k]!=record[k] for k in ('floor','system','plan_edges','iso_edges')) or len(row['iso_edges'])!=1 or len(row['plan_edges'])!=1:raise ValueError('main value mapping differs')
        if mid in retained:continue
        eid=row['iso_edges'][0];edge=target[eid]
        if eid in claimed or any(k in edge for k in ('cross_view_attributes','plan_segment_attributes','axis_riser_attributes')):raise ValueError('main writer overlaps prior attributes')
        claimed.add(eid);points=horizontal_domain(local,record,angles);dn=row['diameter'];metric=row['horizontal_projection'];value=dn['nominal_mm']
        if dn['edge_id']!=row['plan_edges'][0] or dn['system']!=row['system'] or (value is None and dn['status'] not in ('conflict','unresolved')):
            raise ValueError('main DN evidence scope differs')
        if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0):raise ValueError('invalid main DN')
        mm=metric['value_mm'];pieces=metric['pieces']
        if isinstance(mm,bool) or not isinstance(mm,(int,float)) or not math.isfinite(mm) or mm<=0 or not pieces or abs(sum(p['length_mm'] for p in pieces)-mm)>.0001:
            raise ValueError('main metric evidence differs')
        partial=row['inline_interiors_unknown']
        if partial and (metric.get('joint_graphic_spans_added') is not False or metric.get('inline_joint_interior_length_mm') is not None):raise ValueError('inline graphic length cannot be physical')
        item=dict(mapping_id=mid,floor=row['floor'],system=row['system'],axis_edge=eid,plan_edges=row['plan_edges'],iso_edges=row['iso_edges'],
            status='source_checked_anchored_floor_main_attributes_human_pending',scope='native_same_floor_T_to_T_main',scope_paths=copy.deepcopy([points]),
            nominal_mm=value,diameter_evidence=copy.deepcopy(dn),horizontal_projection=copy.deepcopy(metric),inline_interiors_unknown=partial,
            complete_horizontal_centerline_route_mm=None if partial else mm,pipe_net_cut_length_mm=None,installed_whole_edge_length_mm=None,
            physical_ports_verified=False,human_accepted=False,related_HIL_confirmation_inherited=False,source_sha256=copy.deepcopy(mapping['source_sha256']),
            local_graph_sha256=copy.deepcopy(attributes['graph_sha256']),mapping_sha256=hashes['mapping'],attribute_scope_sha256=hashes['attributes'],parent_graph_sha256=hashes['parent'])
        edge[FIELD]=item;proof.append(copy.deepcopy(item))
    if len(proof)!=mapping['additional_main_paths']:raise ValueError('additional main attribute scope incomplete')
    for eid,edge in old.items():
        if {k:v for k,v in target[eid].items() if k!=FIELD}!=edge:raise ValueError('prior edge values or source evidence changed')
    stage=dict(mode=MODE,status='source_checked_additional_floor_main_attributes_hil_pending',floor=mapping['floor'],records=proof,
        prior_main_values_preserved=len(retained),prior_topology_components_and_attributes_preserved=True,related_HIL_confirmation_inherited=False,
        added_main_attributes=len(proof),known_DN_records=sum(r['nominal_mm'] is not None for r in proof),conflict_DN_records=sum(r['nominal_mm'] is None for r in proof),
        inline_interiors_unknown=sum(r['inline_interiors_unknown'] for r in proof),human_accepted=False)
    result[ROOT]=stage;result.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_anchored_floor_main_attributes')
    return result,stage

def compute(paths,policy):
    for key in ('parent_graph','attributes','attribute_receipt','devices'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('main fusion input changed '+key)
    folder=Path(paths['attributes']).resolve().parent
    if Path(paths['attributes']).name!='attributes.json' or Path(paths['attribute_receipt']).resolve()!=folder/'floor-main-attribute-receipt.json':raise ValueError('noncanonical main attribute input')
    attributes=verify_attributes(folder);parent=verify_parent(Path(paths['parent_graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('main parent or components changed')
    receipt=load(paths['attribute_receipt']);mp=Path(receipt['inputs']['mapping']['path']);mapping=load(mp)
    local_inputs=load(receipt['inputs']['mapping_receipt']['path'])['local_inputs']
    for view in ('plan','iso'):
        if sha(local_inputs[view+'_graph']['path'])!=attributes['graph_sha256'][view]:raise ValueError('main local graph changed')
    if parent['native_local_graph']['sha256']!=attributes['graph_sha256']['iso']:raise ValueError('main parent axis differs')
    graph,stage=append(load(paths['parent_graph']),load(local_inputs['iso_graph']['path']),load(local_inputs['plan_graph']['path']),mapping,attributes,
        dict(parent=sha(paths['parent_graph']),mapping=sha(mp),attributes=sha(paths['attributes'])),policy['isometric_horizontal_directions_degrees'])
    return graph,dict(stage=stage,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),
        verified_wave_parent=parent,native_local_graph=parent['native_local_graph'],mapping_path=str(mp),attribute_scope_path=str(Path(paths['attributes']).resolve()))

def implementation_hashes():
    result=parent_hashes();result.update(attribute_hashes());result[Path(__file__).name]=sha(__file__);return result

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'anchored-main-fusion-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('main fusion implementation changed')
    for row in audit['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('main fusion dependency changed')
    graph,proof=compute({k:r['path'] for k,r in audit['inputs'].items()},load(audit['inputs']['policy']['path']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('main fusion native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(audit['inputs']['devices']['path']).read_bytes():raise ValueError('main fusion components changed')
    return audit

def main():
    p=argparse.ArgumentParser()
    for k in ('parent-graph','attribute-run','devices','policy','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();paths=dict(parent_graph=a.parent_graph,attributes=a.attribute_run/'attributes.json',attribute_receipt=a.attribute_run/'floor-main-attribute-receipt.json',devices=a.devices,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    graph,proof=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'graph_with_edges.json';target.write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    (a.output/'anchored-main-fusion-audit.json').write_bytes(encode(dict(proof,mode=MODE,implementation_sha256=implementation_hashes(),inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},output_graph_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(added=proof['stage']['added_main_attributes'],known_DN=proof['stage']['known_DN_records'],unknown_DN=proof['stage']['conflict_DN_records']),flush=True)
if __name__=='__main__':main()
