"""Compose upper-floor plan evidence on exact original axis segment domains.

Keep existing plan/vertical attributes immutable. A mixed edge receives only a
horizontal suffix record. A source-checked bent T-to-T main may carry complete
centreline route values; net cut lengths and unshown connectors remain unknown.
"""
import argparse,copy,math,re,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from named_upper_floor_plan_attributes import verify_output as verify_scopes,implementation_hashes as scope_hashes,MODE as SCOPE_MODE
from attach_named_riser_plan_attributes import verify_output as verify_parent,implementation_hashes as parent_hashes
from native_touching_plan_path_chunks import project

MODE='upper_floor_plan_segment_attribute_extension_v1'
ROOT='sourceUpperFloorPlanSegmentAttributes'


def positive(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and value>0


def selected_path(edge,scope):
    pi=scope['path_index'];indices=scope['segment_indices'];paths=edge['attribute_paths']
    if (isinstance(pi,bool) or not isinstance(pi,int) or not 0<=pi<len(paths) or not indices
        or any(isinstance(i,bool) or not isinstance(i,int) for i in indices)
        or indices!=list(range(indices[0],indices[-1]+1)) or indices[0]<0 or indices[-1]>=len(paths[pi])-1):
        raise ValueError('invalid upper-floor original segment limits')
    points=paths[pi][indices[0]:indices[-1]+2]
    if scope['scope_paths']!=[points] or any(not positive(math.dist(a,b)) for a,b in zip(points,points[1:])):
        raise ValueError('upper-floor selected points no longer match local axis segments')
    return points


def complete_main(record,local,plan,angles):
    """Require the full existing same-floor T-to-T path in both native views."""
    if not angles or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)
                         or abs(v%180-90)<.5 for v in angles):raise ValueError('invalid source isometric horizontal directions')
    floor=record['floor']
    for graph,key in ((local,'iso'),(plan,'plan')):
        nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
        ids=record[key+'_edges']
        if len(ids)!=1:raise ValueError('complete main must be one separately mapped local edge')
        edge=edges[ids[0]]
        if ({edge['start_node_id'],edge['end_node_id']}!={record[key+'_network_T'],record[key+'_equipment_T']}
            or edge['system']!=record['system'] or edge.get('source_wave_omission') or edge.get('source_view_context')
            or any(not [edge[k] for k in names if k in edge] or any(edge[k]!=floor for k in names if k in edge)
                   for names in (('floor_start','start_floor'),('floor_end','end_floor')))):
            raise ValueError('main endpoints, system, floor or source domain differ')
        for nid in (edge['start_node_id'],edge['end_node_id']):
            node=nodes[nid]
            if node.get('node_type') not in ('tee','physical_junction') or node.get('floor')!=floor or node.get('review_required') is True:
                raise ValueError('complete main needs independently checked physical endpoint Ts')
        if key=='plan':
            projection,_,_=project(graph,ids,floor);points=next(e for e in projection['edges'] if e['edge_id']==ids[0])['attribute_paths'][0]
        else:
            scope=record['iso_segment_scopes'][0];points=selected_path(edge,scope)
            if scope.get('whole_local_edge') is not True or edge['attribute_paths']!=[points]:raise ValueError('main scope does not cover the whole local edge')
            for a,b in zip(points,points[1:]):
                bearing=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%180
                if not any(min(abs(bearing-v%180),180-abs(bearing-v%180))<=.1 for v in angles):
                    raise ValueError('axis main includes an unproved in-plane direction')
        endpoints=[[nodes[edge[k]]['x'],nodes[edge[k]]['y']] for k in ('start_node_id','end_node_id')]
        if any(math.dist(a,b)>.05 for a,b in zip((points[0],points[-1]),endpoints)):
            raise ValueError('full main path does not reach both actual Ts')


def append(parent,local,plan,mapping,scope,scope_hash,mapping_hash,parent_hash,angles):
    if ROOT in parent or any('plan_segment_attributes' in e for e in parent['edges']):raise ValueError('upper-floor segment attributes already composed')
    if any(not re.fullmatch('[0-9a-f]{64}',h) for h in (scope_hash,mapping_hash,parent_hash)):raise ValueError('invalid upper-floor evidence binding')
    if (scope.get('mode')!=SCOPE_MODE or scope.get('status')!='source_checked_upper_floor_plan_DN_and_XY_scopes_not_fused'
        or scope.get('mapping_sha256')!=mapping_hash or scope.get('source_sha256')!=mapping['source_sha256']['plan']
        or scope.get('graph_sha256')!=mapping['graph_sha256']['plan']
        or any(scope.get(k) is not False for k in ('physical_values_fused','physical_ports_verified','local_graphs_mutated','human_accepted'))
        or scope.get('whole_axis_DN_assigned')!=0 or scope.get('installed_lengths_assigned')!=0):raise ValueError('unsupported upper-floor source scope')
    old={e['edge_id']:e for e in parent['edges']};raw={e['edge_id']:e for e in local['edges']}
    if len(old)!=len(parent['edges']) or len(raw)!=len(local['edges']) or old.keys()!=raw.keys() or parent['nodes']!=local['nodes']:
        raise ValueError('upper-floor composition local topology differs')
    for eid,edge in old.items():
        if {k:v for k,v in edge.items() if k not in ('cross_view_attributes','axis_riser_attributes')}!=raw[eid]:
            raise ValueError('prior attribute parent changed local edge geometry or components')
    records={r['mapping_id']:r for r in mapping['records']};rows=scope['records']
    if len(records)!=4 or len(rows)!=4 or len({r['mapping_id'] for r in rows})!=4 or set(records)!={r['mapping_id'] for r in rows}:
        raise ValueError('four exact mapped plan attribute scopes required')
    result=copy.deepcopy(parent);target={e['edge_id']:e for e in result['edges']};proof=[];claimed=set()
    for row in rows:
        record=records[row['mapping_id']]
        if any(row[k]!=record[k] for k in ('kind','floor','system','plan_edges','iso_edges','iso_segment_scopes')):
            raise ValueError('upper-floor attributes refer to a different mapping scope')
        if len(row['iso_edges'])!=1 or len(row['iso_segment_scopes'])!=1 or len(row['plan_edges'])!=1:raise ValueError('one existing edge required per mapped scope')
        eid=row['iso_edges'][0];edge=old[eid];selected=row['iso_segment_scopes'][0];points=selected_path(edge,selected)
        if eid in claimed or 'cross_view_attributes' in edge or edge['system']!=row['system'] or selected['edge_id']!=eid:
            raise ValueError('repeated attribute writer or changed axis service')
        claimed.add(eid);pid=row['plan_edges'][0];pe=next(e for e in plan['edges'] if e['edge_id']==pid)
        diameter=row['diameter'];metric=row['horizontal_projection']
        if (diameter['edge_id']!=pid or diameter['system']!=row['system'] or diameter['scope_paths']!=pe['attribute_paths']
            or diameter.get('scope')!='native_plan_drawn_pipe_paths_only' or diameter.get('human_accepted') is not False
            or not diameter.get('lineage') or not positive(diameter['nominal_mm']) or not positive(metric['value_mm'])
            or row.get('whole_axis_DN_selected') is not False or row.get('whole_axis_physical_length_mm') is not None
            or any(row.get(k) is not False for k in ('physical_port_verified','human_accepted'))
            or metric.get('installed_whole_edge_length_mm') is not None or metric.get('unshown_connection_length_mm') is not None):
            raise ValueError('upper-floor values lack native scope or claim unknown physical spans')
        expected={(pi,si):[a,b] for pi,path in enumerate(pe['attribute_paths']) for si,(a,b) in enumerate(zip(path,path[1:]))}
        pieces=metric.get('pieces',[])
        if (len(pieces)!=len(expected) or len({(p['path_index'],p['segment_index']) for p in pieces})!=len(pieces)
            or any(p['plan_edge']!=pid or not p.get('source_line_handle') or expected.get((p['path_index'],p['segment_index']))!=p['points']
                   or not positive(p['length_mm']) or abs(math.dist(*p['points'])-p['length_mm'])>.05 for p in pieces)
            or abs(sum(p['length_mm'] for p in pieces)-metric['value_mm'])>.05):raise ValueError('plan metric pieces lost native path identities or millimetre total')
        whole=record['kind']=='named_riser_floor_segment_network_link'
        if whole:complete_main(record,local,plan,angles)
        elif record['kind']=='named_riser_floor_segment_approach':
            vertical=edge.get('axis_riser_attributes',[])
            if (selected.get('whole_local_edge') is not False or not vertical or selected['path_index']!=0
                or selected['segment_indices'][0]!=1 or any(v['path_index']==selected['path_index'] and v['segment_index'] in selected['segment_indices'] for v in vertical)
                or edge['attribute_paths'][0][selected['segment_indices'][0]-1]!=edge['attribute_paths'][0][0]):
                raise ValueError('upper approach lost its independently checked vertical boundary')
        else:raise ValueError('unsupported upper-floor mapping kind')
        item=dict(mapping_id=row['mapping_id'],mapping_kind=row['kind'],floor=row['floor'],system=row['system'],
            edge_id=eid,path_index=selected['path_index'],segment_indices=copy.deepcopy(selected['segment_indices']),scope_points=copy.deepcopy(points),
            scope='native_plan_matched_upper_floor_axis_segments_only',whole_local_edge=whole,plan_edges=row['plan_edges'],
            identifier=record['identifier'],equipment_anchor=record['equipment_id'],plan_riser_interface=record['plan_riser_interface'],
            plan_network_T=record['plan_network_T'],axis_network_T=record['iso_network_T'],plan_equipment_T=record['plan_equipment_T'],axis_equipment_T=record['iso_equipment_T'],
            nominal_mm=diameter['nominal_mm'],diameter_evidence=copy.deepcopy(diameter),horizontal_projection=copy.deepcopy(metric),
            whole_edge_nominal_mm=diameter['nominal_mm'] if whole else None,
            whole_edge_centerline_route_mm=metric['value_mm'] if whole else None,
            length_scope='complete_mapped_T_to_T_centerline_route_not_pipe_net_cut_length' if whole else 'mapped_plan_drawn_approach_only',
            pipe_net_cut_length_mm=None,unshown_connection_length_mm=None,physical_port_verified=False,
            source_scope_sha256=scope_hash,mapping_sha256=mapping_hash,attribute_parent_graph_sha256=parent_hash,
            source_sha256=copy.deepcopy(mapping['source_sha256']),local_graph_sha256=copy.deepcopy(mapping['graph_sha256']),human_accepted=False)
        target[eid]['plan_segment_attributes']=[item];proof.append(item)
    for eid,edge in old.items():
        after=target[eid]
        if {k:v for k,v in after.items() if k!='plan_segment_attributes'}!=edge:raise ValueError('prior plan, vertical or component fields changed')
    result[ROOT]=dict(status='source_checked_upper_floor_segment_attributes_hil_pending',records=proof,
        source_scope_sha256=scope_hash,mapping_sha256=mapping_hash,attribute_parent_graph_sha256=parent_hash,
        previous_plan_vertical_and_component_fields_preserved=True,human_accepted=False)
    result.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_upper_floor_plan_segment_attributes')
    return result,dict(added_segment_attribute_scopes=len(proof),added_axis_edges=sorted(claimed),
        complete_main_centerline_route_edges=[r['edge_id'] for r in proof if r['whole_local_edge']],
        previous_plan_vertical_and_component_fields_preserved=True,mixed_edge_whole_values_assigned=0,
        physical_ports_verified=False,related_HIL_confirmation_inherited=False,records=proof)


def compute(paths,policy):
    for key in ('parent_graph','attribute_scope','attribute_receipt','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('upper-floor attachment input changed '+key)
    directory=Path(paths['attribute_scope']).resolve().parent
    if Path(paths['attribute_scope']).resolve()!=directory/'upper-floor-plan-attributes.json' or Path(paths['attribute_receipt']).resolve()!=directory/'upper-floor-plan-attribute-receipt.json':
        raise ValueError('noncanonical upper-floor scope input')
    scope=verify_scopes(directory);receipt=load(paths['attribute_receipt']);parent=verify_parent(Path(paths['parent_graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('upper-floor parent or canonical components changed')
    localpath=Path(parent['native_local_graph']['path']);inputs=receipt['inputs'];mapping=load(inputs['mapping']['path'])
    if sha(localpath)!=mapping['graph_sha256']['iso'] or sha(localpath)!=parent['native_local_graph']['sha256']:raise ValueError('upper-floor mapping uses another local axis graph')
    graph,proof=append(load(paths['parent_graph']),load(localpath),load(inputs['graph']['path']),mapping,scope,
        sha(paths['attribute_scope']),sha(inputs['mapping']['path']),sha(paths['parent_graph']),policy['isometric_horizontal_directions_degrees'])
    return graph,dict(proof,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),
        native_local_graph=parent['native_local_graph'],verified_named_parent=parent,source_scope_sha256=sha(paths['attribute_scope']),mapping_sha256=sha(inputs['mapping']['path']))


def implementation_hashes():
    result=parent_hashes();result.update(scope_hashes());result['attach_upper_floor_plan_attributes.py']=sha(__file__);return result


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'upper-floor-plan-attribute-fusion-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('upper-floor fusion implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('upper-floor fusion dependency changed')
    graph,proof=compute({k:v['path'] for k,v in audit['inputs'].items()},load(audit['inputs']['policy']['path']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):
        raise ValueError('upper-floor fusion native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(audit['inputs']['devices']['path']).read_bytes():raise ValueError('upper-floor components changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('parent-graph','attribute-run','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(parent_graph=a.parent_graph,attribute_scope=a.attribute_run/'upper-floor-plan-attributes.json',
        attribute_receipt=a.attribute_run/'upper-floor-plan-attribute-receipt.json',devices=a.devices,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),
        output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'upper-floor-plan-attribute-fusion-audit.json').write_bytes(encode(audit));print(dict(scopes=4,main_centerline_routes=len(audit['complete_main_centerline_route_edges']),mixed_whole_values=0),flush=True)


if __name__=='__main__':main()
