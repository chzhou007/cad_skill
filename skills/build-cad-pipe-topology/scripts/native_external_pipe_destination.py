"""Read an external-destination caption for separate named pipe frontiers.

The common drawing marker is annotation, never a hydraulic connection. This
read-only sidecar assigns no pipe length, whole-edge DN or physical port.
"""
import argparse,math,re
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_named_riser_evidence import underlines,xyz,label,LAYERS
from native_dn_text_position import supported
from crossview_equipment_branch_inventory import index_graph

MODE='native_grouped_external_pipe_destination_v1'

def on_segment(p,a,b,tol=.05):
    if any(len(x)!=3 or any(not math.isfinite(v) for v in x) for x in (p,a,b)):return False
    delta=[y-x for x,y in zip(a,b)];den=sum(v*v for v in delta)
    if den<=tol*tol:return False
    t=sum((p[i]-a[i])*delta[i] for i in range(3))/den
    return -tol/math.sqrt(den)<=t<=1+tol/math.sqrt(den) and math.dist(p,[a[i]+t*delta[i] for i in range(3)])<=tol

def chain(doc,spec,text_layers,leader_layers):
    text=doc.entitydb.get(spec['text_handle'])
    if text is None or text not in doc.modelspace() or not supported(text) or text.dxf.layer not in text_layers or text.plain_text()!=spec['expected_text'] or '\ufffd' in text.plain_text():
        raise ValueError('readable native external caption/name required')
    under=underlines(doc,text,leader_layers)
    if len(under)!=1 or under[0].dxf.handle!=spec['underline_handle']:raise ValueError('external caption underline differs or is ambiguous')
    joins=[]
    for line in doc.modelspace().query('LINE'):
        if line is under[0] or line.dxf.layer not in leader_layers:continue
        for a in xyz(under[0]):
            for i,b in enumerate(xyz(line)):
                if math.dist(a,b)<=.05:joins.append((line,i))
    if len(joins)!=1 or joins[0][0].dxf.handle!=spec['leader_handle']:raise ValueError('external caption leader differs or is ambiguous')
    leader,index=joins[0];tip=xyz(leader)[1-index]
    return dict(text_handle=text.dxf.handle,text=text.plain_text(),text_position=list(text.dxf.insert),rotation=text.dxf.rotation,
        underline_handle=under[0].dxf.handle,underline_XYZ=xyz(under[0]),leader_handle=leader.dxf.handle,leader_XYZ=xyz(leader),target_point=tip)

def collect(doc,graph,policy,source_hash,graph_hash):
    if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:
        raise ValueError('external destination source/graph differs')
    text_layers=set(policy.get('text_layers',[]));leader_layers=set(policy.get('leader_layers',[]));members=policy.get('members',[])
    if not text_layers or not leader_layers or len(members)<2 or len({m['node_id'] for m in members})!=len(members) or len({m['text_handle'] for m in members})!=len(members):
        raise ValueError('explicit distinct frontier members required')
    caption=chain(doc,policy['caption'],text_layers,leader_layers);match=re.fullmatch(r'接至([^\s\r\n]{2,})',caption['text'])
    if not match or match[1]!=policy.get('destination'):raise ValueError('unsupported external-destination wording')
    marker=doc.entitydb.get(policy['marker_handle'])
    if (marker is None or marker not in doc.modelspace() or marker.dxftype()!='LWPOLYLINE' or marker.dxf.layer!=policy.get('marker_layer')
        or marker.closed or marker.has_arc or marker.has_width or tuple(marker.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.)):
        raise ValueError('unsupported external drawing marker')
    vertices=[[float(x),float(y),float(marker.dxf.elevation)] for x,y in marker.get_points('xy')]
    if len(vertices)<3 or any(not math.isfinite(v) for p in vertices for v in p) or any(math.dist(a,b)<=.05 for a,b in zip(vertices,vertices[1:])):
        raise ValueError('external marker geometry invalid')
    if len([v for v in vertices[1:-1] if math.dist(v,caption['target_point'])<=.05])!=1:raise ValueError('caption does not target one native marker vertex')
    nodes,edges,adj=index_graph(graph);rows=[];claimed_lines=set();names=set();floors=set()
    for spec in members:
        proof=chain(doc,spec,text_layers,leader_layers);named=label(proof['text']);nid=spec['node_id'];node=nodes.get(nid);line=doc.entitydb.get(spec['source_line_handle'])
        if named['identifier']!=spec['identifier'] or named['identifier'] in names:raise ValueError('frontier native identifier duplicated or changed')
        names.add(named['identifier'])
        if (node is None or node.get('node_type')!='virtual_equipment' or node.get('system')!=named['system'] or len(adj[nid])!=1 or adj[nid][0]['system']!=named['system']
            or line is None or line not in doc.modelspace() or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[named['system']]
            or line.dxf.handle not in node.get('source_handles',[]) or line.dxf.handle not in adj[nid][0].get('source_handles',[])):
            raise ValueError('named frontier lacks unique native pipe/graph ownership')
        tip=proof['target_point'];contacts=[p for p in xyz(line) if math.dist(p,tip)<=.05]
        if len(contacts)!=1 or math.dist(tip[:2],[node['x'],node['y']])>.05 or not any(on_segment(tip,a,b) for a,b in zip(vertices,vertices[1:])):
            raise ValueError('name leader does not target its own pipe endpoint on the marker')
        if line.dxf.handle in claimed_lines:raise ValueError('frontier source LINE repeated')
        claimed_lines.add(line.dxf.handle);floors.add(node.get('floor'))
        rows.append(dict(node_id=nid,edge_id=adj[nid][0]['edge_id'],identifier=named['identifier'],system=named['system'],floor=node.get('floor'),
            destination=match[1],destination_status='source_declared_external_destination',native_name_evidence=proof,source_line_handle=line.dxf.handle,native_pipe_XYZ=xyz(line),
            boundary_position=list(tip),local_nominal_mm_observed=named['nominal_mm_observed'],whole_edge_DN_verified=False,physical_external_connection_verified=False,
            physical_port_verified=False,physical_length_mm=None,human_accepted=False))
    if len(floors)!=1 or None in floors:raise ValueError('external group crosses unqualified floors')
    all_contacts=set()
    for line in doc.modelspace().query('LINE'):
        if line.dxf.layer in LAYERS.values() and any(on_segment(p,a,b) for p in xyz(line) for a,b in zip(vertices,vertices[1:])):all_contacts.add(line.dxf.handle)
    if all_contacts!=claimed_lines:raise ValueError('external marker has additional or missing native pipe frontiers')
    return dict(mode=MODE,status='source_declared_destinations_not_hydraulic_connection',source_sha256=source_hash,graph_sha256=graph_hash,records=rows,
        destination=match[1],caption_evidence=caption,marker_evidence=dict(handle=marker.dxf.handle,layer=marker.dxf.layer,vertices_WCS=vertices,annotation_only=True),
        common_marker_creates_pipe_connection=False,nodes_merged=0,new_connections_added=0,graph_mutated=False,physical_values_assigned=0,human_accepted=False,hil_ready=False)

def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in (Path(__file__).name,'native_named_riser_evidence.py','native_dn_text_position.py','native_line_path_evidence.py','crossview_equipment_branch_inventory.py','source_readability.py')}

def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'external-destination-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('external destination implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('external destination input changed')
    paths={k:Path(r['path']) for k,r in receipt['inputs'].items()};doc,preflight=read_source(paths['source']);data=collect(doc,load(paths['graph']),load(paths['policy']),sha(paths['source']),sha(paths['graph']));data['source_preflight']=preflight
    if encode(data)!=(directory/'external-destinations.json').read_bytes() or sha(directory/'external-destinations.json')!=receipt['output_sha256']:raise ValueError('external destination native replay differs')
    return data

def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    doc,preflight=read_source(a.source);data=collect(doc,load(a.graph),load(a.policy),sha(a.source),sha(a.graph));data['source_preflight']=preflight
    a.output.mkdir(parents=True);target=a.output/'external-destinations.json';target.write_bytes(encode(data))
    (a.output/'external-destination-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(getattr(a,k).resolve()),sha256=sha(getattr(a,k))) for k in ('source','graph','policy')},implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(named_frontiers=len(data['records']),destination=data['destination'],new_connections_added=0),flush=True)
if __name__=='__main__':main()
