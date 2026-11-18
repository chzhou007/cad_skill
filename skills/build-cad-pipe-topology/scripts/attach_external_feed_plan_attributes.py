"""Compose checked external pipe values and separate destination context.

Local topology stays fixed. Centre marker spans and inline gaps remain outside
the pipe DN domain; shared destination annotations never join boundary ports.
"""
import argparse,copy,math,re,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from attach_network_named_lower_plan_attributes import verify_output as verify_parent,implementation_hashes as parent_hashes
from named_external_feed_plan_attributes import verify_output as verify_attributes,implementation_hashes as attribute_hashes,MODE as ATTRIBUTE_MODE
from match_named_external_boundary_paths import MODE as MAPPING_MODE

MODE='external_feed_plan_attribute_and_destination_fusion_v1'
ROOT='sourceExternalFeedPlanAttributes'
FIELD='external_feed_plan_attributes'
NODE_FIELD='source_external_destination_context'
AUDIT='external-feed-plan-fusion-audit.json'


def positive(value):return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and value>0


def append(parent,local,mapping,attributes,destinations,hashes):
    if ROOT in parent or any(FIELD in e for e in parent['edges']) or any(NODE_FIELD in n for n in parent['nodes']):raise ValueError('external feed attributes already composed')
    if set(hashes)!={'parent','mapping','attributes','plan_destinations','axis_destinations'} or any(not re.fullmatch('[0-9a-f]{64}',v) for v in hashes.values()):raise ValueError('invalid external fusion evidence binding')
    if (mapping.get('mode')!=MAPPING_MODE or attributes.get('mode')!=ATTRIBUTE_MODE or attributes.get('mapping_sha256')!=hashes['mapping']
        or attributes.get('source_sha256')!=mapping['source_sha256'] or attributes.get('graph_sha256')!=mapping['graph_sha256']
        or any(attributes.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','human_accepted','hil_ready'))
        or attributes.get('installed_whole_lengths_assigned')!=0):raise ValueError('independent external source attributes required')
    if parent['nodes']!=local['nodes']:raise ValueError('external fusion parent changed native nodes')
    old={e['edge_id']:e for e in parent['edges']};raw={e['edge_id']:e for e in local['edges']}
    existing={'cross_view_attributes','axis_riser_attributes','plan_segment_attributes','anchored_floor_main_attributes','network_named_lower_plan_attributes'}
    if len(old)!=len(parent['edges']) or len(raw)!=len(local['edges']) or old.keys()!=raw.keys():raise ValueError('external fusion local edge identities differ')
    for eid,e in old.items():
        if {k:v for k,v in e.items() if k not in existing}!=raw[eid]:raise ValueError('parent changed native geometry or components')
    for view,side in (('plan','plan'),('iso','axis')):
        d=destinations[side]
        if d['source_sha256']!=mapping['source_sha256'][view] or d['graph_sha256']!=mapping['graph_sha256'][view] or d.get('common_marker_creates_pipe_connection') is not False:raise ValueError('destination evidence uses another source or joins ports')
    if destinations['plan']['destination']!=destinations['axis']['destination']:raise ValueError('source destinations disagree')
    mapped={r['mapping_id']:r for r in mapping['records']};rows={r['mapping_id']:r for r in attributes['records']}
    if len(mapped)<2 or len(mapped)!=len(mapping['records']) or len(rows)!=len(attributes['records']) or rows.keys()!=mapped.keys():raise ValueError('complete unique external records required')
    result=copy.deepcopy(parent);target={e['edge_id']:e for e in result['edges']};nodes={n['node_id']:n for n in result['nodes']};proof=[];node_rows={};claimed=set()
    for mid,row in rows.items():
        record=mapped[mid]
        keys=('kind','floor','system','identifier','destination','plan_edges','iso_edges','plan_boundary_node','axis_boundary_node','axis_port_id','axis_display_only_segment_index')
        if (any(row[k]!=record[k] for k in keys) or len(row['iso_edges'])!=1 or len(row['plan_edges'])!=1
            or row['destination']!=destinations['axis']['destination']):raise ValueError('external mapped attribute scope differs')
        eid=row['iso_edges'][0];edge=target[eid];nid=row['axis_boundary_node'];node=nodes[nid]
        if eid in claimed or any(k in edge for k in existing) or edge['system']!=row['system'] or nid not in (edge['start_node_id'],edge['end_node_id']):raise ValueError('external writer overlaps prior values or changes service')
        if node.get('node_type')!='virtual_equipment' or node.get('subtype')!='external_system_interface' or node['floor']!=row['floor']:raise ValueError('destination context needs an existing nonphysical external boundary')
        paths=edge['attribute_paths'];coverage=record['native_axis_path_coverage'];display=row['axis_display_only_segment_index'];gaps=set(row['axis_inline_gap_segment_indices']);indices=row['axis_pipe_segment_indices']
        if (len(paths)!=1 or len(coverage['segments'])!=len(paths[0])-1 or not indices or len(indices)!=len(set(indices)) or set(indices)&({display}|gaps)
            or set(range(len(paths[0])-1))!=set(indices)|{display}|gaps):raise ValueError('external pipe scope overlaps a marker/gap or misses a segment')
        for segment in coverage['segments']:
            i=segment['index']
            if paths[0][i:i+2]!=[segment['start'],segment['end']] or (segment['status']=='single_source_line_covers')!=(i in indices):raise ValueError('external axis source path or native coverage changed')
        port=next((p for p in node['ports'] if p['port_id']==row['axis_port_id']),None);native=record['native_axis_destination']
        if (not port or port['system']!=row['system'] or port['source_marker_handle']!=node['source_marker_handle']
            or math.dist([port['x'],port['y']],native['native_port_XYZ'][:2])>.05
            or row['axis_port_id'] not in (edge.get('start_port_id'),edge.get('end_port_id'))):raise ValueError('external boundary port differs from original named endpoint')
        d=row['diameter'];metric=row['horizontal_projection'];dn=d['nominal_mm']
        if (d['edge_id']!=row['plan_edges'][0] or d['system']!=row['system'] or dn is not None and not positive(dn)
            or dn is not None and d.get('status') not in ('direct_plan_DN','T_inherited_plan_DN') or dn is None and d.get('status') not in ('unresolved','conflict')
            or not positive(metric['value_mm']) or not metric.get('pieces') or abs(sum(p['length_mm'] for p in metric['pieces'])-metric['value_mm'])>.0001
            or any(p.get('plan_edge')!=d['edge_id'] or not p.get('source_line_handle') or not positive(p['length_mm'])
                or not isinstance(p.get('points'),list) or len(p['points'])!=2 or abs(math.dist(*p['points'])-p['length_mm'])>.05 for p in metric['pieces'])
            or row.get('inline_interiors_unknown') is not True or metric.get('joint_graphic_spans_added') is not False or metric.get('inline_joint_interior_length_mm') is not None
            or row.get('installed_whole_edge_length_mm') is not None or row.get('complete_horizontal_centerline_route_mm') is not None
            or any(row.get(k) is not False for k in ('whole_axis_edge_DN_selected','axis_named_DN_used_as_plan_seed','physical_ports_verified','external_ports_connected_to_each_other','physical_external_connection_verified','human_accepted'))):raise ValueError('external source values claim unknown whole spans or physical connections')
        item=dict(mapping_id=mid,floor=row['floor'],system=row['system'],identifier=row['identifier'],destination=row['destination'],axis_edge=eid,plan_edges=row['plan_edges'],
            axis_boundary_node=nid,axis_port_id=row['axis_port_id'],plan_boundary_node=row['plan_boundary_node'],scope='native_external_pipe_segments_only_excluding_marker_and_inline_gap',
            path_index=0,segment_indices=copy.deepcopy(indices),scope_paths=[copy.deepcopy(paths[0][i:i+2]) for i in indices],display_only_segment_index=display,inline_gap_segment_indices=sorted(gaps),
            nominal_mm=dn,diameter_evidence=copy.deepcopy(d),horizontal_projection=copy.deepcopy(metric),complete_horizontal_centerline_route_mm=None,installed_whole_edge_length_mm=None,pipe_net_cut_length_mm=None,
            whole_axis_edge_DN_selected=False,physical_ports_verified=False,physical_external_connection_verified=False,external_ports_connected_to_each_other=False,human_accepted=False,related_HIL_confirmation_inherited=False,
            source_sha256=copy.deepcopy(mapping['source_sha256']),local_graph_sha256=copy.deepcopy(mapping['graph_sha256']),mapping_sha256=hashes['mapping'],source_scope_sha256=hashes['attributes'],attribute_parent_graph_sha256=hashes['parent'])
        target[eid][FIELD]=item;proof.append(copy.deepcopy(item));claimed.add(eid)
        node_rows.setdefault(nid,[]).append(dict(port_id=port['port_id'],edge_id=eid,system=row['system'],identifier=row['identifier'],plan_boundary_node=row['plan_boundary_node'],native_port_XYZ=copy.deepcopy(native['native_port_XYZ'])))
    contexts={}
    for nid,ports in node_rows.items():
        node=nodes[nid]
        if len({p['port_id'] for p in ports})!=len(ports) or {p['port_id'] for p in ports}!={p['port_id'] for p in node['ports']}:raise ValueError('external context must account for every separate port')
        context=dict(status='source_declared_destination_external_connectivity_unknown',destination=destinations['axis']['destination'],node_id=nid,floor=node['floor'],source_marker_handle=node['source_marker_handle'],
            native_node_position=[node['x'],node['y']],ports=ports,plan_caption_evidence=copy.deepcopy(destinations['plan']['caption_evidence']),axis_caption_evidence=copy.deepcopy(destinations['axis']['caption_evidence']),
            source_sha256=copy.deepcopy(mapping['source_sha256']),local_graph_sha256=copy.deepcopy(mapping['graph_sha256']),mapping_sha256=hashes['mapping'],attribute_scope_sha256=hashes['attributes'],
            plan_destination_sha256=hashes['plan_destinations'],axis_destination_sha256=hashes['axis_destinations'],attribute_parent_graph_sha256=hashes['parent'],
            prior_label=node.get('label'),direct_connection_between_ports=False,physical_equipment=False,physical_ports_verified=False,physical_external_connection_verified=False,human_accepted=False)
        node[NODE_FIELD]=context;contexts[nid]=copy.deepcopy(context)
    for before,after in zip(parent['nodes'],result['nodes']):
        if {k:v for k,v in after.items() if k!=NODE_FIELD}!=before:raise ValueError('old node geometry, identity or semantics changed')
    for eid,before in old.items():
        if {k:v for k,v in target[eid].items() if k!=FIELD}!=before:raise ValueError('old edge attributes or components changed')
    stage=dict(mode=MODE,status='source_checked_external_pipe_attributes_and_boundary_context_hil_pending',records=proof,node_contexts=contexts,
        prior_topology_components_and_attributes_preserved=True,added_external_pipe_scopes=len(proof),source_declared_boundary_contexts=len(contexts),
        whole_physical_lengths_assigned=0,new_connections_added=0,related_HIL_confirmation_inherited=False,human_accepted=False)
    result[ROOT]=stage;result.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_external_feed_attributes_and_boundary_context')
    return result,stage


def compute(paths,policy):
    for key in ('parent_graph','attributes','attribute_receipt','devices'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('external fusion input changed '+key)
    folder=Path(paths['attributes']).resolve().parent
    if Path(paths['attributes']).name!='attributes.json' or Path(paths['attribute_receipt']).resolve()!=folder/'external-feed-plan-attribute-receipt.json':raise ValueError('noncanonical external source attribute input')
    attributes=verify_attributes(folder);parent=verify_parent(Path(paths['parent_graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('external full prefix parent or components changed')
    ar=load(paths['attribute_receipt']);mp=Path(ar['inputs']['mapping']['path']);mapping=load(mp);mr=load(ar['inputs']['mapping_receipt']['path']);mi=mr['inputs'];local=Path(parent['native_local_graph']['path'])
    if parent['native_local_graph']['sha256']!=attributes['graph_sha256']['iso'] or sha(local)!=attributes['graph_sha256']['iso']:raise ValueError('external attributes use another local axis')
    destinations={k:load(mi[v]['path']) for k,v in (('plan','plan_destinations'),('axis','axis_destinations'))}
    hashes=dict(parent=sha(paths['parent_graph']),mapping=sha(mp),attributes=sha(paths['attributes']),plan_destinations=sha(mi['plan_destinations']['path']),axis_destinations=sha(mi['axis_destinations']['path']))
    graph,stage=append(load(paths['parent_graph']),load(local),mapping,attributes,destinations,hashes)
    return graph,dict(stage=stage,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),verified_prefix_parent=parent,native_local_graph=parent['native_local_graph'],
        mapping_path=str(mp),attribute_scope_path=str(Path(paths['attributes']).resolve()),destination_evidence_paths={k:str(Path(mi[v]['path']).resolve()) for k,v in (('plan','plan_destinations'),('axis','axis_destinations'))})


def implementation_hashes():
    result=parent_hashes();result.update(attribute_hashes());result[Path(__file__).name]=sha(__file__);return result


def verify_output(directory):
    directory=Path(directory);audit=load(directory/AUDIT)
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('external fusion implementation changed')
    for row in audit['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('external fusion dependency changed')
    graph,proof=compute({k:r['path'] for k,r in audit['inputs'].items()},load(audit['inputs']['policy']['path']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('external fusion native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(audit['inputs']['devices']['path']).read_bytes():raise ValueError('external fusion canonical components changed')
    return audit


def main():
    p=argparse.ArgumentParser()
    for key in ('parent-graph','attribute-run','devices','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();paths=dict(parent_graph=a.parent_graph,attributes=a.attribute_run/'attributes.json',attribute_receipt=a.attribute_run/'external-feed-plan-attribute-receipt.json',devices=a.devices,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    graph,proof=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'graph_with_edges.json';target.write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    (a.output/AUDIT).write_bytes(encode(dict(proof,mode=MODE,inputs={k:dict(path=str(Path(v).resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(external_scopes=proof['stage']['added_external_pipe_scopes'],boundary_contexts=proof['stage']['source_declared_boundary_contexts'],new_connections_added=0),flush=True)

if __name__=='__main__':main()
