"""Native caption -> leader -> two-bar marker -> pipe-frontier evidence.

This reader does not bridge a source gap, assign a device, retire a node or
measure a physical span. A selected symbol must have an explicit Chinese
reserved-branch/capped declaration and an exact native leader contact.
"""
import math,re
from native_line_path_evidence import LAYERS

TOL=.05


def xy(p):return [float(p[0]),float(p[1])]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sub(a,b):return [x-y for x,y in zip(a,b)]
def unit(v):
    length=math.hypot(*v)
    if not math.isfinite(length) or length<=TOL:raise ValueError('degenerate native direction')
    return [x/length for x in v]


def native(doc,handle,kind):
    e=doc.entitydb.get(handle)
    if e is None or e.dxftype()!=kind or e.dxf.owner!=doc.modelspace().block_record_handle:
        raise ValueError('selected native modelspace '+kind+' missing')
    return e


def text_frame(e):
    normal=tuple(e.dxf.get('extrusion',(0,0,1)))
    if abs(normal[0])+abs(normal[1])>1e-10 or abs(abs(normal[2])-1)>1e-10:
        raise ValueError('caption is outside supported source plane')
    angle=math.radians(e.dxf.get('rotation',0));flags=e.dxf.get('text_generation_flag',0)
    u=e.ocs().to_wcs((math.cos(angle),math.sin(angle),0));v=e.ocs().to_wcs((-math.sin(angle),math.cos(angle),0))
    u=[float(x)*(-1 if flags&2 else 1) for x in list(u)[:2]];v=[float(x)*(-1 if flags&4 else 1) for x in list(v)[:2]]
    height=float(e.dxf.height);p=list(e.ocs().to_wcs(e.dxf.insert))
    if not math.isfinite(height) or height<=0 or any(not math.isfinite(x) for x in p+u+v):raise ValueError('invalid native caption frame')
    if e.dxf.get('halign',0) or e.dxf.get('valign',0):raise ValueError('aligned caption needs a separate source frame')
    return p,u,v,height


def frontier_geometry(doc,node,pipe_handle,bars):
    pipe=native(doc,pipe_handle,'LINE')
    if pipe.dxf.layer!=LAYERS.get(node.get('system')) or pipe_handle not in node.get('source_handles',[]):
        raise ValueError('typed source frontier differs')
    ends=[list(pipe.dxf.start),list(pipe.dxf.end)];p=[node['x'],node['y']]
    if math.dist(xy(ends[0]),p)>math.dist(xy(ends[1]),p):ends.reverse()
    if math.dist(xy(ends[0]),p)>TOL:raise ValueError('pipe misses selected frontier')
    axis=unit(sub(xy(ends[0]),xy(ends[1])));centres=[];lengths=[]
    for bar in bars:
        a,b=list(bar.dxf.start),list(bar.dxf.end);d=sub(xy(b),xy(a));direction=unit(d)
        if abs(dot(direction,axis))>1e-8:raise ValueError('marker is not transverse to selected pipe')
        c=[(x+y)/2 for x,y in zip(a,b)];delta=sub(xy(c),p)
        if abs(delta[0]*axis[1]-delta[1]*axis[0])>TOL:raise ValueError('marker misses selected pipe axis')
        centres.append(c);lengths.append(math.hypot(*d))
    spacing=dot(sub(xy(centres[1]),xy(centres[0])),axis);offset=dot(sub(xy(centres[0]),p),axis)
    if not 1.2<=lengths[0]/lengths[1]<=2.0 or not .2*lengths[0]<=spacing<=.8*lengths[0]:raise ValueError('unsupported complete two-bar signature')
    if not -TOL<=offset<=spacing/2+TOL:raise ValueError('pipe frontier is outside the bounded marker projection')
    return dict(source_pipe_handle=pipe_handle,source_pipe_layer=pipe.dxf.layer,source_pipe_endpoints=ends,
        marker_centres=centres,marker_lengths_xy=lengths,marker_spacing_xy=spacing,frontier_to_first_marker_offset_xy=offset,
        source_xyz_retained=True,contact_semantics='source_annotation_projection_only_not_a_physical_connection')


def collect(doc,graph,source_sha256,selections):
    if graph.get('metadata',{}).get('source_sha256')!=source_sha256:raise ValueError('source identity mismatch')
    if not selections or len({r['node_id'] for r in selections})!=len(selections):raise ValueError('empty or duplicate annotation selection')
    nodes={n['node_id']:n for n in graph['nodes']}
    if len(nodes)!=len(graph['nodes']):raise ValueError('duplicate graph nodes')
    records=[];used_markers=set()
    for choice in selections:
        node=nodes.get(choice['node_id'])
        if not node or node.get('node_type')!='virtual_equipment' or node.get('subtype')!='unresolved_source_terminal':raise ValueError('selected frontier is not an unresolved drawing leaf')
        incident=[e for e in graph['edges'] if node['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
        if len(incident)!=1 or incident[0]['system']!=node['system'] or choice['pipe_handle'] not in incident[0].get('source_handles',[]):raise ValueError('frontier is not uniquely source-owned by one same-system edge')
        caption=native(doc,choice['caption_handle'],'TEXT');qualifier=native(doc,choice['qualifier_handle'],'TEXT')
        text=caption.plain_text().strip();match=re.fullmatch(r'预留支管接口[/／]共([1-9][0-9]*)处',text)
        if not match or qualifier.plain_text().strip()!='盲板封堵':raise ValueError('explicit reserved-branch and capped declaration required')
        p,u,v,h=text_frame(caption);q,qu,qv,qh=text_frame(qualifier)
        if caption.dxf.layer!=qualifier.dxf.layer or abs(qh/h-1)>.01 or dot(u,qu)<1-1e-8 or dot(v,qv)<1-1e-8:
            raise ValueError('caption pair frames differ')
        delta=sub(xy(q),xy(p));qx,qy=dot(delta,u),dot(delta,v)
        if abs(qx)>.05*h or not -2.5*h<=qy<=-.8*h:raise ValueError('capped qualifier is not in the caption frame')
        handles=choice['marker_handles']
        if len(handles)!=2 or len(set(handles))!=2 or used_markers.intersection(handles):raise ValueError('two unique marker strokes required')
        bars=[native(doc,handle,'LINE') for handle in handles]
        if any(e.dxf.layer!=caption.dxf.layer for e in bars):raise ValueError('marker and caption layers differ')
        witness=frontier_geometry(doc,node,choice['pipe_handle'],bars)
        path=choice['leader_handles']
        if not 1<=len(path)<=8 or len(set(path))!=len(path):raise ValueError('bounded native leader chain required')
        tip=xy(witness['marker_centres'][1]);cursor=tip;chain=[]
        for handle in reversed(path):
            line=native(doc,handle,'LINE')
            if line.dxf.layer!=caption.dxf.layer:raise ValueError('leader and caption layers differ')
            a,b=list(line.dxf.start),list(line.dxf.end)
            if math.dist(xy(a),cursor)<math.dist(xy(b),cursor):a,b=b,a
            if math.dist(xy(b),cursor)>TOL:raise ValueError('leader misses marker or breaks within chain')
            chain.append(dict(handle=handle,start=a,end=b));cursor=xy(a)
        delta=sub(cursor,xy(p));cx,cy=dot(delta,u),dot(delta,v)
        if not -.5*h<=cx<=.05*h or not qy<=cy<=.05*h:raise ValueError('leader root is outside paired Chinese caption frame')
        candidates=[]
        for other in nodes.values():
            if other.get('node_type')!='virtual_equipment' or other.get('subtype')!='unresolved_source_terminal':continue
            for handle in other.get('source_handles',[]):
                try:frontier_geometry(doc,other,handle,bars)
                except (ValueError,KeyError,TypeError):continue
                candidates.append((other['node_id'],handle))
        if candidates!=[(node['node_id'],choice['pipe_handle'])]:raise ValueError('caption marker has competing native pipe-frontier interpretations')
        used_markers.update(handles)
        records.append(dict(node_id=node['node_id'],edge_id=incident[0]['edge_id'],system=node['system'],
            role='reserved_capped_branch_annotation',status='native_caption_leader_marker_frontier_witness_only',
            caption=dict(handle=caption.dxf.handle,text=text,insert_wcs=p,height=h,declared_group_quantity=int(match.group(1))),
            qualifier=dict(handle=qualifier.dxf.handle,text=qualifier.plain_text(),insert_wcs=q),
            marker_handles=list(handles),leader_chain=list(reversed(chain)),source_geometry=witness,
            quantity_expanded_into_ports=False,physical_connection_assigned=False,physical_length_mm=None,
            remote_equipment_or_port_identity='unknown',human_accepted=False))
    return dict(mode='native_capped_branch_annotation_witness_v1',source_sha256=source_sha256,records=records,
        graph_mutated=False,topology_nodes_retired=0,connections_added=0,physical_lengths_assigned=0,hil_ready=False)


def compute(paths):
    from confirm_crossview_paths import load,sha
    from source_readability import read_source
    policy=load(paths['policy'])
    if policy['source_sha256']!=sha(paths['source']) or policy['graph_sha256']!=sha(paths['graph']):raise ValueError('annotation policy input hashes differ')
    doc,preflight=read_source(paths['source']);graph=load(paths['graph'])
    inventory=collect(doc,graph,preflight['source_sha256'],policy['selections'])
    inventory.update(graph_sha256=sha(paths['graph']),source_preflight=preflight,
        limitations=['Selected native modelspace TEXT and LINE declarations only; no automatic nearest-neighbour or nested/proxy interpretation.',
            'Quantity belongs to the source callout and is not expanded into pipes, equipment or ports.',
            'Projected marker offset is preserved evidence, not snapping or measured physical connector length.',
            'Node classification, topology, system ownership, mapping, attributes and HIL acceptance are not modified.'])
    return inventory


def verify_output(directory):
    from pathlib import Path
    from confirm_crossview_paths import load,sha,encode
    directory=Path(directory);audit=load(directory/'native-capped-branch-annotations-audit.json')
    if audit['owner_sha256']!=sha(__file__) or any(sha(row['path'])!=row['sha256'] for row in audit['inputs'].values()):raise ValueError('native annotation owner or inputs changed')
    inventory=compute({key:row['path'] for key,row in audit['inputs'].items()})
    target=directory/'inventory.json'
    if encode(inventory)!=target.read_bytes() or sha(target)!=audit['output_inventory_sha256']:raise ValueError('native capped-branch annotation replay differs')
    return audit


def main():
    import argparse
    from pathlib import Path
    from confirm_crossview_paths import sha,encode
    parser=argparse.ArgumentParser()
    for key in ('source','graph','policy','output','verify_output'):parser.add_argument('--'+key.replace('_','-'),type=Path)
    args=parser.parse_args()
    if args.verify_output:
        if any((args.source,args.graph,args.policy,args.output)):raise ValueError('verification cannot override saved native inputs')
        audit=verify_output(args.verify_output);print(dict(source_replay='passed',records=audit['records'],topology_changed=False),flush=True);return
    if not all((args.source,args.graph,args.policy,args.output)):parser.error('source, graph, policy and output required')
    if args.output.exists():raise FileExistsError(args.output)
    paths={key:getattr(args,key).resolve() for key in ('source','graph','policy')};hashes={key:sha(path) for key,path in paths.items()}
    inventory=compute(paths)
    if any(sha(paths[key])!=digest for key,digest in hashes.items()):raise ValueError('native annotation input changed during extraction')
    args.output.mkdir(parents=True);target=args.output/'inventory.json';target.write_bytes(encode(inventory))
    audit=dict(mode=inventory['mode'],owner_sha256=sha(__file__),inputs={key:dict(path=str(path),sha256=hashes[key]) for key,path in paths.items()},
        output_inventory_sha256=sha(target),records=len(inventory['records']),graph_mutated=False,hil_ready=False,human_accepted=False)
    (args.output/'native-capped-branch-annotations-audit.json').write_bytes(encode(audit))
    print(dict(status='native_caption_leader_marker_frontier_evidence',records=len(inventory['records']),topology_changed=False),flush=True)


if __name__=='__main__':main()
