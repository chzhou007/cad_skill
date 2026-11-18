"""Read separate named axis boundary ports under a common destination marker.

The marker and node-centre display spans are annotation. No port-to-port
hydraulic connection or pipe DN/length is introduced.
"""
import argparse,math,re
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_external_pipe_destination import chain,on_segment
from native_named_riser_evidence import xyz,label,LAYERS
from crossview_equipment_branch_inventory import index_graph

MODE='native_named_external_boundary_ports_v1'


def collect(doc,graph,policy,source_hash,graph_hash):
    if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('external port source/graph differs')
    text_layers=set(policy.get('text_layers',[]));leader_layers=set(policy.get('leader_layers',[]))
    if not text_layers or not leader_layers:raise ValueError('explicit native text/leader layers required')
    caption=chain(doc,policy['caption'],text_layers,leader_layers);wording=re.fullmatch(r'接(?:至)?([^\s\r\n]{2,})',caption['text'])
    if not wording or wording[1]!=policy['destination']:raise ValueError('unsupported external port caption')
    marker=doc.entitydb.get(policy['marker_handle'])
    if (marker is None or marker not in doc.modelspace() or marker.dxftype()!='LWPOLYLINE' or marker.dxf.layer!=policy['marker_layer']
        or marker.closed or marker.has_arc or marker.has_width or tuple(marker.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.)):raise ValueError('unsupported native boundary marker')
    vertices=[[float(x),float(y),float(marker.dxf.elevation)] for x,y in marker.get_points('xy')]
    if (len(vertices)<3 or any(not math.isfinite(v) for p in vertices for v in p) or any(math.dist(a,b)<=.05 for a,b in zip(vertices,vertices[1:]))
        or not any(on_segment(caption['target_point'],a,b) for a,b in zip(vertices,vertices[1:]))):raise ValueError('caption does not target the native boundary marker')
    nodes,edges,adj=index_graph(graph);node=nodes.get(policy['node_id']);members=policy.get('members',[])
    if (not node or node.get('node_type')!='virtual_equipment' or node.get('subtype')!='external_system_interface'
        or node.get('source_marker_handle')!=marker.dxf.handle or len(members)<2 or len(members)!=len(node.get('ports',[]))
        or len({m['port_id'] for m in members})!=len(members) or len({m['edge_id'] for m in members})!=len(members)
        or len({m['text_handle'] for m in members})!=len(members)):raise ValueError('complete separate virtual boundary ports required')
    ports={p['port_id']:p for p in node['ports']}
    if len(ports)!=len(node['ports']) or set(ports)!={m['port_id'] for m in members} or {e['edge_id'] for e in adj[node['node_id']]}!={m['edge_id'] for m in members}:raise ValueError('boundary graph port/edge membership differs')
    rows=[];claimed=set();names=set()
    for spec in members:
        native=chain(doc,spec,text_layers,leader_layers);parsed=label(native['text']);port=ports[spec['port_id']];edge=edges[spec['edge_id']];line=doc.entitydb.get(spec['source_line_handle'])
        if (parsed['identifier']!=spec['identifier'] or parsed['identifier'] in names or port.get('system')!=parsed['system'] or edge.get('system')!=parsed['system']
            or port.get('node_id')!=node['node_id'] or port.get('source_marker_handle')!=marker.dxf.handle
            or edge.get('source_insert_handle')!=marker.dxf.handle or line is None or line not in doc.modelspace()
            or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[parsed['system']] or line.dxf.handle in claimed):raise ValueError('native named port ownership or system differs')
        tip=native['target_point'];ends=xyz(line)
        if (sum(math.dist(tip,p)<=.05 for p in ends)!=1 or math.dist(tip[:2],[port['x'],port['y']])>.05
            or not any(on_segment(tip,a,b) for a,b in zip(vertices,vertices[1:]))):raise ValueError('name leader does not target its native pipe endpoint and port')
        paths=edge.get('attribute_paths',[])
        if len(paths)!=1 or len(paths[0])<3:raise ValueError('boundary path lacks native pipe after its display span')
        start=edge['start_node_id']==node['node_id'];ordered=paths[0] if start else list(reversed(paths[0]));port_key='start_port_id' if start else 'end_port_id'
        if (node['node_id'] not in (edge['start_node_id'],edge['end_node_id']) or edge.get(port_key)!=port['port_id']
            or math.dist(ordered[0],[node['x'],node['y']])>.05 or math.dist(ordered[1],tip[:2])>.05
            or not all(on_segment([*p,tip[2]],*ends) for p in ordered[1:3])):raise ValueError('graph display span or first native pipe segment differs')
        claimed.add(line.dxf.handle);names.add(parsed['identifier'])
        rows.append(dict(node_id=node['node_id'],port_id=port['port_id'],edge_id=edge['edge_id'],floor=node['floor'],system=parsed['system'],identifier=parsed['identifier'],
            destination=wording[1],native_name=native,nominal_mm_observed=parsed['nominal_mm_observed'],native_port_XYZ=tip,source_line_handle=line.dxf.handle,
            source_line_XYZ=ends,display_only_centre_span=[ordered[0],ordered[1]],physical_port_verified=False,physical_length_mm=None,whole_edge_DN_verified=False,human_accepted=False))
    contacts={e.dxf.handle for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS.values() and any(on_segment(p,a,b) for p in xyz(e) for a,b in zip(vertices,vertices[1:]))}
    if contacts!=claimed:raise ValueError('native boundary has extra or missing pipe contacts')
    return dict(mode=MODE,status='source_declared_separate_external_ports_not_hydraulic_connection',source_sha256=source_hash,graph_sha256=graph_hash,
        destination=wording[1],records=rows,caption_evidence=caption,marker_evidence=dict(handle=marker.dxf.handle,vertices_WCS=vertices,annotation_only=True),
        common_marker_creates_pipe_connection=False,nodes_merged=0,new_connections_added=0,graph_mutated=False,physical_values_assigned=0,human_accepted=False,hil_ready=False)


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in (Path(__file__).name,'native_external_pipe_destination.py','native_named_riser_evidence.py','native_dn_text_position.py','native_line_path_evidence.py','crossview_equipment_branch_inventory.py','source_readability.py')}


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'external-port-destination-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('external port implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('external port input changed')
    paths={k:Path(v['path']) for k,v in receipt['inputs'].items()};doc,preflight=read_source(paths['source']);data=collect(doc,load(paths['graph']),load(paths['policy']),sha(paths['source']),sha(paths['graph']));data['source_preflight']=preflight
    if encode(data)!=(directory/'external-port-destinations.json').read_bytes() or sha(directory/'external-port-destinations.json')!=receipt['output_sha256']:raise ValueError('external port native replay differs')
    return data


def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    doc,preflight=read_source(a.source);data=collect(doc,load(a.graph),load(a.policy),sha(a.source),sha(a.graph));data['source_preflight']=preflight
    a.output.mkdir(parents=True);target=a.output/'external-port-destinations.json';target.write_bytes(encode(data))
    (a.output/'external-port-destination-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(getattr(a,k).resolve()),sha256=sha(getattr(a,k))) for k in ('source','graph','policy')},implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(separate_named_ports=len(data['records']),destination=data['destination'],new_connections_added=0),flush=True)

if __name__=='__main__':main()
