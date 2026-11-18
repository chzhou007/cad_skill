"""Compose lower-floor plan prefixes over the complete upper-floor parent.

Reuse original-segment and full-main contracts. Preserve all prior plan and
vertical values. Only independently verified child stages use bounded batch
reuse; this root is reconstructed and compared on every verification call.
"""
import argparse,copy,math,re,shutil,sys
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from named_lower_floor_plan_attributes import verify_output as verify_scopes,implementation_hashes as scope_hashes,MODE as SCOPE_MODE
from attach_upper_floor_plan_attributes import verify_output as verify_parent,implementation_hashes as parent_hashes,selected_path,complete_main,positive

MODE='lower_floor_plan_segment_attribute_extension_v1'
ROOT='sourceLowerFloorPlanSegmentAttributes'


def plan_values(row,edge,system):
    d=row['diameter'];metric=row['horizontal_projection']
    if (d['edge_id']!=edge['edge_id'] or d['system']!=system or d['scope_paths']!=edge['attribute_paths']
        or d.get('scope')!='native_plan_drawn_pipe_paths_only' or d.get('human_accepted') is not False
        or not d.get('lineage') or not positive(d['nominal_mm']) or not positive(metric['value_mm'])
        or row.get('whole_axis_DN_selected') is not False or row.get('whole_axis_physical_length_mm') is not None
        or any(row.get(k) is not False for k in ('physical_port_verified','human_accepted'))
        or metric.get('installed_whole_edge_length_mm') is not None or metric.get('unshown_connection_length_mm') is not None):
        raise ValueError('lower plan values lack source scope or claim unknown spans')
    expected={(pi,si):[a,b] for pi,path in enumerate(edge['attribute_paths']) for si,(a,b) in enumerate(zip(path,path[1:]))};pieces=metric.get('pieces',[])
    if (len(pieces)!=len(expected) or len({(p['path_index'],p['segment_index']) for p in pieces})!=len(pieces)
        or any(p['plan_edge']!=edge['edge_id'] or not p.get('source_line_handle') or expected.get((p['path_index'],p['segment_index']))!=p['points']
               or not positive(p['length_mm']) or abs(math.dist(*p['points'])-p['length_mm'])>.05 for p in pieces)
        or abs(sum(p['length_mm'] for p in pieces)-metric['value_mm'])>.05):raise ValueError('lower plan metric pieces lost their native identities or total')
    return d,metric


def append(parent,local,plan,mapping,scope,scope_hash,mapping_hash,parent_hash,angles):
    if ROOT in parent:raise ValueError('lower-floor plan attributes already composed')
    if any(not re.fullmatch('[0-9a-f]{64}',h) for h in (scope_hash,mapping_hash,parent_hash)):raise ValueError('invalid lower-floor evidence binding')
    if (scope.get('mode')!=SCOPE_MODE or scope.get('status')!='source_checked_lower_floor_plan_DN_and_XY_scopes_not_fused'
        or scope.get('mapping_sha256')!=mapping_hash or scope.get('source_sha256')!=mapping['source_sha256']['plan']
        or scope.get('graph_sha256')!=mapping['graph_sha256']['plan']
        or any(scope.get(k) is not False for k in ('physical_values_fused','physical_ports_verified','local_graphs_mutated','human_accepted'))
        or scope.get('whole_axis_DN_assigned')!=0 or scope.get('installed_lengths_assigned')!=0):raise ValueError('unsupported lower-floor attribute scope')
    old={e['edge_id']:e for e in parent['edges']};raw={e['edge_id']:e for e in local['edges']}
    if len(old)!=len(parent['edges']) or len(raw)!=len(local['edges']) or old.keys()!=raw.keys() or parent['nodes']!=local['nodes']:
        raise ValueError('lower-floor parent local topology differs')
    for eid,edge in old.items():
        if {k:v for k,v in edge.items() if k not in ('cross_view_attributes','axis_riser_attributes','plan_segment_attributes')}!=raw[eid]:
            raise ValueError('lower-floor parent changed local geometry or components')
    records={r['mapping_id']:r for r in mapping['records']};rows=scope['records']
    if len(records)!=4 or len(rows)!=4 or len({r['mapping_id'] for r in rows})!=4 or set(records)!={r['mapping_id'] for r in rows}:
        raise ValueError('four independently mapped lower scopes required')
    result=copy.deepcopy(parent);target={e['edge_id']:e for e in result['edges']};claimed=set();proof=[];plan_edges={e['edge_id']:e for e in plan['edges']}
    for row in rows:
        record=records[row['mapping_id']]
        if any(row[k]!=record[k] for k in ('kind','floor','system','plan_edges','iso_edges','iso_segment_scopes')):raise ValueError('lower mapping/attribute scope differs')
        if len(row['iso_edges'])!=1 or len(row['iso_segment_scopes'])!=1 or len(row['plan_edges'])!=1:raise ValueError('one local edge required per lower attribute scope')
        eid=row['iso_edges'][0];edge=old[eid];selected=row['iso_segment_scopes'][0];points=selected_path(edge,selected)
        if eid in claimed or 'cross_view_attributes' in edge or 'plan_segment_attributes' in edge or edge['system']!=row['system'] or selected['edge_id']!=eid:
            raise ValueError('lower scope repeats an existing writer or changes service')
        claimed.add(eid);diameter,metric=plan_values(row,plan_edges[row['plan_edges'][0]],row['system'])
        whole=record['kind']=='named_riser_lower_floor_segment_network_link'
        if whole:complete_main(record,local,plan,angles)
        elif record['kind']=='named_riser_lower_floor_segment_approach':
            vertical=edge.get('axis_riser_attributes',[]);paths=edge['attribute_paths'];indices=selected['segment_indices']
            if (selected.get('whole_local_edge') is not False or selected['path_index']!=0 or len(paths)!=1 or len(vertical)!=1
                or indices!=list(range(len(paths[0])-2)) or not indices):raise ValueError('lower prefix does not stop before one existing vertical tail')
            v=vertical[0];si=v['segment_index']
            if (v['path_index']!=0 or si!=indices[-1]+1 or v['scope_points']!=paths[0][si:si+2] or points[-1]!=v['scope_points'][0]
                or v['floor_pair']!=[row['floor'],row['floor']+1]
                or int(edge.get('floor_start',edge.get('start_floor',-999)))!=row['floor']
                or int(edge.get('floor_end',edge.get('end_floor',-999)))!=row['floor']+1):raise ValueError('lower prefix lost its checked vertical boundary')
        else:raise ValueError('unsupported lower-floor attribute mapping kind')
        item=dict(mapping_id=row['mapping_id'],mapping_kind=row['kind'],floor=row['floor'],system=row['system'],edge_id=eid,
            path_index=selected['path_index'],segment_indices=copy.deepcopy(selected['segment_indices']),scope_points=copy.deepcopy(points),
            scope='native_plan_matched_lower_floor_axis_segments_only',whole_local_edge=whole,plan_edges=row['plan_edges'],identifier=record['identifier'],
            equipment_anchor=record['equipment_id'],plan_riser_interface=record['plan_riser_interface'],plan_network_T=record['plan_network_T'],axis_network_T=record['iso_network_T'],
            plan_equipment_T=record['plan_equipment_T'],axis_equipment_T=record['iso_equipment_T'],nominal_mm=diameter['nominal_mm'],diameter_evidence=copy.deepcopy(diameter),
            horizontal_projection=copy.deepcopy(metric),whole_edge_nominal_mm=diameter['nominal_mm'] if whole else None,
            whole_edge_centerline_route_mm=metric['value_mm'] if whole else None,
            length_scope='complete_mapped_T_to_T_centerline_route_not_pipe_net_cut_length' if whole else 'mapped_plan_drawn_approach_only',
            pipe_net_cut_length_mm=None,unshown_connection_length_mm=None,physical_port_verified=False,source_scope_sha256=scope_hash,mapping_sha256=mapping_hash,
            attribute_parent_graph_sha256=parent_hash,source_sha256=copy.deepcopy(mapping['source_sha256']),local_graph_sha256=copy.deepcopy(mapping['graph_sha256']),human_accepted=False)
        target[eid]['plan_segment_attributes']=[item];proof.append(item)
    for eid,edge in old.items():
        if eid in claimed:
            if {k:v for k,v in target[eid].items() if k!='plan_segment_attributes'}!=edge:raise ValueError('selected lower edge lost prior values')
        elif target[eid]!=edge:raise ValueError('unselected prior edge changed')
    result[ROOT]=dict(status='source_checked_lower_floor_segment_attributes_hil_pending',records=proof,source_scope_sha256=scope_hash,
        mapping_sha256=mapping_hash,attribute_parent_graph_sha256=parent_hash,previous_plan_vertical_and_component_fields_preserved=True,human_accepted=False)
    result.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_lower_floor_plan_segment_attributes')
    return result,dict(added_segment_attribute_scopes=4,added_axis_edges=sorted(claimed),records=proof,
        complete_main_centerline_route_edges=[r['edge_id'] for r in proof if r['whole_local_edge']],previous_plan_vertical_and_component_fields_preserved=True,
        mixed_edge_whole_values_assigned=0,physical_ports_verified=False,related_HIL_confirmation_inherited=False)


def compute(paths,policy):
    for key in ('parent_graph','attribute_scope','attribute_receipt','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('lower-floor composition input changed '+key)
    directory=Path(paths['attribute_scope']).resolve().parent
    if Path(paths['attribute_scope']).resolve()!=directory/'lower-floor-plan-attributes.json' or Path(paths['attribute_receipt']).resolve()!=directory/'lower-floor-plan-attribute-receipt.json':
        raise ValueError('noncanonical lower-floor attribute scope')
    owner=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_replay_session import verify_once
    # The root itself stays uncached: child closures are checked on every call.
    scope=verify_once(directory,verify_scopes);receipt=load(paths['attribute_receipt']);parent=verify_once(Path(paths['parent_graph']).parent,verify_parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('lower parent or canonical component inventory changed')
    inputs=receipt['inputs'];mapping=load(inputs['mapping']['path']);localpath=Path(parent['native_local_graph']['path'])
    if sha(localpath)!=mapping['graph_sha256']['iso'] or sha(localpath)!=parent['native_local_graph']['sha256']:raise ValueError('lower mapping uses another local graph')
    graph,proof=append(load(paths['parent_graph']),load(localpath),load(inputs['graph']['path']),mapping,scope,
        sha(paths['attribute_scope']),sha(inputs['mapping']['path']),sha(paths['parent_graph']),policy['isometric_horizontal_directions_degrees'])
    return graph,dict(proof,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),native_local_graph=parent['native_local_graph'],
        verified_upper_parent=parent,source_scope_sha256=sha(paths['attribute_scope']),mapping_sha256=sha(inputs['mapping']['path']))


def implementation_hashes():
    result=parent_hashes();result.update(scope_hashes());result['attach_lower_floor_plan_attributes.py']=sha(__file__)
    result['native_replay_session.py']=sha(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts/native_replay_session.py')
    return result


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'lower-floor-plan-attribute-fusion-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('lower-floor composition implementation changed')
    for row in audit['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('lower-floor composition dependency changed')
    graph,proof=compute({k:v['path'] for k,v in audit['inputs'].items()},load(audit['inputs']['policy']['path']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):
        raise ValueError('lower-floor composition native reconstruction differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(audit['inputs']['devices']['path']).read_bytes():raise ValueError('lower-floor canonical components changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('parent-graph','attribute-run','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(parent_graph=a.parent_graph,attribute_scope=a.attribute_run/'lower-floor-plan-attributes.json',
        attribute_receipt=a.attribute_run/'lower-floor-plan-attribute-receipt.json',devices=a.devices,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),
        output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'lower-floor-plan-attribute-fusion-audit.json').write_bytes(encode(audit));print(dict(scopes=4,main_routes=2,mixed_whole_values_assigned=0),flush=True)


if __name__=='__main__':main()
