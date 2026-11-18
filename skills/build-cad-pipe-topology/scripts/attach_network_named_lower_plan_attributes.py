"""Attach plan-derived named prefixes without overwriting their axis risers.

This root retains the complete additional-main parent. Its verifier replays
both source owners; the pure composer reuses existing segment/metric guards.
"""
import argparse,copy,re,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from attach_anchored_floor_main_attributes import verify_output as verify_parent,implementation_hashes as parent_hashes
from network_named_lower_plan_attributes import verify_output as verify_scopes,implementation_hashes as scope_hashes,MODE as SCOPE_MODE
from match_network_named_lower_approaches import MODE as MAPPING_MODE
from attach_lower_floor_plan_attributes import plan_values
from attach_upper_floor_plan_attributes import selected_path

MODE='network_named_lower_plan_attribute_fusion_v1'
ROOT='sourceNetworkNamedLowerPlanAttributes'
FIELD='network_named_lower_plan_attributes'
AUDIT='network-named-lower-plan-fusion-audit.json'


def append(parent,local,plan,mapping,scopes,hashes):
    if ROOT in parent or any(FIELD in e for e in parent['edges']):raise ValueError('named-network attributes already composed')
    if set(hashes)!={'parent','mapping','attributes'} or any(not re.fullmatch('[0-9a-f]{64}',v) for v in hashes.values()):raise ValueError('invalid named-network binding')
    if (mapping.get('mode')!=MAPPING_MODE or scopes.get('mode')!=SCOPE_MODE or scopes.get('mapping_sha256')!=hashes['mapping']
        or scopes.get('graph_sha256')!=mapping['graph_sha256'] or scopes.get('source_sha256')!=mapping['source_sha256']
        or any(scopes.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','physical_ports_verified','human_accepted','hil_ready'))
        or scopes.get('installed_lengths_assigned')!=0):raise ValueError('named-network attribute source differs')
    old={e['edge_id']:e for e in parent['edges']};raw={e['edge_id']:e for e in local['edges']}
    if len(old)!=len(parent['edges']) or len(raw)!=len(local['edges']) or old.keys()!=raw.keys() or parent['nodes']!=local['nodes']:raise ValueError('local topology differs')
    existing={'cross_view_attributes','axis_riser_attributes','plan_segment_attributes','anchored_floor_main_attributes'}
    for eid,edge in old.items():
        if {k:v for k,v in edge.items() if k not in existing}!=raw[eid]:raise ValueError('parent geometry or components changed')
    rows={r['mapping_id']:r for r in scopes['records']};mapped={r['mapping_id']:r for r in mapping['records']}
    if len(rows)!=2 or len(scopes['records'])!=2 or len(mapped)!=2 or len(mapping['records'])!=2 or rows.keys()!=mapped.keys():raise ValueError('two unique named services required')
    result=copy.deepcopy(parent);target={e['edge_id']:e for e in result['edges']};plan_edges={e['edge_id']:e for e in plan['edges']};proof=[];claimed=set();systems=set()
    for mid,row in rows.items():
        record=mapped[mid]
        if any(row[k]!=record[k] for k in ('kind','floor','system','identifier','plan_edges','iso_edges','iso_segment_scopes','plan_riser_interface','plan_network_T','axis_network_T')):raise ValueError('named-network scope differs')
        if (row['kind']!='network_anchored_named_lower_floor_approach' or row['system'] not in ('supply','return') or row['system'] in systems
            or len(row['iso_edges'])!=1 or len(row['plan_edges'])!=1 or len(row['iso_segment_scopes'])!=1):raise ValueError('independent paired prefixes required')
        systems.add(row['system']);eid=row['iso_edges'][0];edge=old[eid];selection=row['iso_segment_scopes'][0];points=selected_path(edge,selection)
        if eid in claimed or edge['system']!=row['system'] or any(k in edge for k in ('cross_view_attributes','plan_segment_attributes','anchored_floor_main_attributes')):raise ValueError('prefix writer overlaps existing evidence')
        claimed.add(eid);paths=edge['attribute_paths'];indices=selection['segment_indices'];vertical=edge.get('axis_riser_attributes',[])
        if (selection['edge_id']!=eid or selection.get('whole_local_edge') is not False or selection['path_index']!=0 or len(paths)!=1
            or indices!=list(range(len(paths[0])-2)) or not indices or len(vertical)!=1):raise ValueError('prefix overlaps or omits vertical boundary')
        v=vertical[0];retained=record['retained_vertical_scope']
        if (v['path_index']!=0 or v['segment_index']!=indices[-1]+1 or v['scope_points']!=paths[0][-2:]
            or points[-1]!=v['scope_points'][0] or v['floor_pair']!=[row['floor'],row['floor']+1]
            or edge.get('floor_start',edge.get('start_floor'))!=row['floor'] or edge.get('floor_end',edge.get('end_floor'))!=row['floor']+1
            or any(v[k]!=retained[k] for k in ('edge_id','segment_index','scope_points','floor_pair','source_line_handle'))):raise ValueError('retained axis riser differs')
        if row.get('plan_glyph_radius_added_to_length') is not False or row.get('whole_axis_DN_assigned') is not False or row.get('installed_whole_edge_length_mm') is not None:raise ValueError('prefix claims unshown physical values')
        diameter,metric=plan_values(row,plan_edges[row['plan_edges'][0]],row['system'])
        item=dict(mapping_id=mid,mapping_kind=row['kind'],edge_id=eid,floor=row['floor'],system=row['system'],identifier=row['identifier'],
            plan_edges=row['plan_edges'],path_index=0,segment_indices=copy.deepcopy(indices),scope_points=copy.deepcopy(points),
            scope='native_network_named_lower_floor_prefix_only',plan_riser_interface=row['plan_riser_interface'],plan_network_T=row['plan_network_T'],axis_network_T=row['axis_network_T'],
            independent_adjoining_main_mapping_id=record['independent_adjoining_main_mapping_id'],retained_vertical_scope=copy.deepcopy(retained),
            nominal_mm=diameter['nominal_mm'],diameter_evidence=copy.deepcopy(diameter),horizontal_projection=copy.deepcopy(metric),
            whole_local_edge=False,whole_edge_nominal_mm=None,whole_edge_centerline_route_mm=None,whole_edge_physical_length_mm=None,
            length_scope='mapped_plan_drawn_approach_only',pipe_net_cut_length_mm=None,unshown_connection_length_mm=None,
            source_sha256=copy.deepcopy(mapping['source_sha256']),local_graph_sha256=copy.deepcopy(mapping['graph_sha256']),
            mapping_sha256=hashes['mapping'],source_scope_sha256=hashes['attributes'],attribute_parent_graph_sha256=hashes['parent'],
            physical_port_verified=False,human_accepted=False,related_HIL_confirmation_inherited=False)
        target[eid][FIELD]=item;proof.append(copy.deepcopy(item))
    for eid,edge in old.items():
        if {k:v for k,v in target[eid].items() if k!=FIELD}!=edge:raise ValueError('old attributes or components lost')
    stage=dict(mode=MODE,status='source_checked_named_network_prefix_attributes_hil_pending',records=proof,added_prefix_scopes=2,
        prior_topology_components_and_attributes_preserved=True,whole_mixed_edge_values_assigned=0,related_HIL_confirmation_inherited=False,human_accepted=False)
    result[ROOT]=stage;result.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_network_named_prefix_attributes')
    return result,stage


def compute(paths,policy):
    for key in ('parent_graph','attributes','attribute_receipt','devices'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('named prefix fusion input changed '+key)
    folder=Path(paths['attributes']).resolve().parent
    if Path(paths['attributes']).name!='attributes.json' or Path(paths['attribute_receipt']).resolve()!=folder/'network-named-plan-attribute-receipt.json':raise ValueError('noncanonical prefix attribute input')
    scopes=verify_scopes(folder);parent=verify_parent(Path(paths['parent_graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('complete main parent or components changed')
    receipt=load(paths['attribute_receipt']);mp=Path(receipt['inputs']['mapping']['path']);mapping=load(mp)
    source_inputs=load(receipt['inputs']['mapping_receipt']['path'])['inputs']
    main_inputs=load(source_inputs['main_receipt']['path'])['local_inputs']
    for view in ('plan','iso'):
        if sha(main_inputs[view+'_graph']['path'])!=scopes['graph_sha256'][view]:raise ValueError('prefix mapping local graph changed')
    if parent['native_local_graph']['sha256']!=scopes['graph_sha256']['iso']:raise ValueError('prefix parent axis differs')
    graph,stage=append(load(paths['parent_graph']),load(main_inputs['iso_graph']['path']),load(main_inputs['plan_graph']['path']),mapping,scopes,
        dict(parent=sha(paths['parent_graph']),mapping=sha(mp),attributes=sha(paths['attributes'])))
    return graph,dict(stage=stage,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),
        verified_main_parent=parent,native_local_graph=parent['native_local_graph'],mapping_path=str(mp),attribute_scope_path=str(Path(paths['attributes']).resolve()))


def implementation_hashes():
    result=parent_hashes();result.update(scope_hashes())
    for name in (Path(__file__).name,'attach_lower_floor_plan_attributes.py','attach_upper_floor_plan_attributes.py'):result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);audit=load(directory/AUDIT)
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('prefix fusion implementation changed')
    for row in audit['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('prefix fusion dependency changed')
    graph,proof=compute({k:r['path'] for k,r in audit['inputs'].items()},load(audit['inputs']['policy']['path']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('prefix fusion native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(audit['inputs']['devices']['path']).read_bytes():raise ValueError('prefix fusion components changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for k in ('parent-graph','attribute-run','devices','policy','output'):parser.add_argument('--'+k,type=Path,required=True)
    args=parser.parse_args();paths=dict(parent_graph=args.parent_graph,attributes=args.attribute_run/'attributes.json',attribute_receipt=args.attribute_run/'network-named-plan-attribute-receipt.json',devices=args.devices,policy=args.policy)
    if args.output.exists():raise FileExistsError(args.output)
    graph,proof=compute(paths,load(args.policy));args.output.mkdir(parents=True);target=args.output/'graph_with_edges.json';target.write_bytes(encode(graph));shutil.copyfile(args.devices,args.output/'edge_device_instances.csv')
    (args.output/AUDIT).write_bytes(encode(dict(proof,mode=MODE,implementation_sha256=implementation_hashes(),inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},output_graph_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(added_prefix_scopes=2,whole_mixed_edge_values_assigned=0),flush=True)

if __name__=='__main__':main()
