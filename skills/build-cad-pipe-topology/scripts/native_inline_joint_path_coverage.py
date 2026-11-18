"""Read existing pipe paths through source-qualified inline spline joints.

Separate plan paths and axis paths containing a marker span share this audit.
Native LINE coverage stays strict; a marker supplies continuity, never length.
"""
import argparse,copy,csv,math
from pathlib import Path
from confirm_crossview_paths import sha,load,encode
from source_readability import read_source
from native_line_path_evidence import LAYERS
from native_path_coverage_audit import audit as line_audit
from repair_native_flexible_joints import fingerprint


def _handle(row):return row.get('source_top_handle') or row.get('source_handle')
def _pair(a,b,c,d,tol):return (math.dist(a,c)<=tol and math.dist(b,d)<=tol) or (math.dist(a,d)<=tol and math.dist(b,c)<=tol)


def native_joint(doc,graph,edge,row,block_name,digest,tol):
    h=_handle(row);ins=doc.entitydb.get(h)
    if (not h or ins is None or ins.dxftype()!='INSERT' or ins not in doc.modelspace() or ins.dxf.name!=block_name
        or row.get('source_block_name')!=block_name or row.get('assignment_status')!='assigned' or row.get('edge_id')!=edge['edge_id']
        or row.get('equipment_type') not in ('flexible_joint','金属软接')):raise ValueError('native inline joint inventory or source differs')
    parts=list(ins.virtual_entities());points=[e.dxf.location for e in parts if e.dxftype()=='POINT'];bars=[e for e in parts if e.dxftype()=='LINE']
    if sorted(e.dxftype() for e in parts)!=['LINE','LINE','POINT','POINT','SPLINE']:raise ValueError('unsupported transformed inline joint')
    if any(not math.isfinite(v) for p in points for v in p) or math.dist(points[0],points[1])<=tol:raise ValueError('invalid native inline joint points')
    if any(sum(math.dist(p,(bar.dxf.start+bar.dxf.end)/2)<=tol for bar in bars)!=1 for p in points):raise ValueError('native inline joint bars and points disagree')
    names=edge.get('equipment_names',[])+[n for item in edge.get('equipment_inventory',[]) for n in item.get('device_names',[])]
    if not row.get('device_name') or names.count(row['device_name'])!=1:raise ValueError('inline joint graph component identity differs')
    metadata=edge.get('source_flexible_joints',[])
    if metadata:
        refs=[r for r in metadata if r['source_handle']==h]
        if (len(refs)!=1 or refs[0].get('source_block')!=block_name or refs[0].get('physical_length')!='unknown'
            or refs[0].get('parameter_status')!='unknown_not_zero'
            or not _pair(*refs[0]['source_contact_points'],*(list(p)[:2] for p in points),tol)):
            raise ValueError('retained flexible-joint evidence differs from source')
    typed=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS.values()];contacts=[]
    axis=points[1]-points[0];axis=axis/axis.magnitude
    for index,point in enumerate(points):
        hits=[line for line in typed if min(math.dist(point,line.dxf.start),math.dist(point,line.dxf.end))<=tol]
        if len(hits)!=1 or hits[0].dxf.layer!=LAYERS[edge['system']]:raise ValueError('joint contact missing, duplicated or on another system/XYZ')
        line=hits[0];other=line.dxf.end if math.dist(point,line.dxf.start)<=tol else line.dxf.start;ray=other-point
        if ray.magnitude<=tol or (ray.normalize().dot(axis) if index==0 else -ray.normalize().dot(axis))>-math.cos(math.radians(1)):
            raise ValueError('joint pipe rays do not continue outward')
        contacts.append(dict(source_line_handle=line.dxf.handle,point_wcs=list(point),line_endpoints_wcs=[list(line.dxf.start),list(line.dxf.end)]))
    return dict(source_handle=h,source_block=block_name,block_fingerprint_sha256=digest,device_name=row['device_name'],
        edge_id=edge['edge_id'],system=edge['system'],contacts=contacts,contact_points_wcs=[list(p) for p in points],
        graphic_span_units=math.dist(points[0],points[1]),physical_length_mm=None,physical_port_verified=False,human_accepted=False)


def collect(doc,graph,inventory,policy,hashes,tol=.05):
    if tol!=.05:raise ValueError('inline joint coverage uses the original .05 tolerance')
    for key in ('source_sha256','graph_sha256','inventory_sha256'):
        if policy.get(key)!=hashes.get(key):raise ValueError('inline joint coverage input differs '+key)
    name=policy.get('block_name');digest=policy.get('block_fingerprint_sha256')
    if name not in doc.blocks or fingerprint(doc.blocks[name])!=digest:raise ValueError('calibrated inline joint template differs')
    if sorted(e.dxftype() for e in doc.blocks[name])!=['LINE','LINE','POINT','POINT','SPLINE']:raise ValueError('unsupported inline joint template')
    ids=policy.get('edges',[]);edges={e['edge_id']:e for e in graph['edges']};nodes={n['node_id']:n for n in graph['nodes']}
    if not ids or len(ids)!=len(set(ids)) or len(edges)!=len(graph['edges']) or len(nodes)!=len(graph['nodes']):raise ValueError('invalid inline joint path selections')
    owned={};records=[]
    for eid in ids:
        edge=edges.get(eid)
        if not edge or edge.get('system') not in LAYERS or edge.get('source_insert_handle') or not edge.get('attribute_paths'):raise ValueError('unsupported selected inline joint edge')
        rows=[r for r in inventory if r.get('edge_id')==eid and r.get('equipment_type') in ('flexible_joint','金属软接')]
        if not rows:raise ValueError('selected path lacks assigned native inline joint')
        joints=[]
        for row in rows:
            h=_handle(row)
            if h in owned or sum(_handle(r)==h for r in inventory)!=1:raise ValueError('inline joint inventory ownership is not unique')
            if any(e['edge_id']!=eid and any(r.get('source_handle')==h for r in e.get('source_flexible_joints',[])) for e in graph['edges']):raise ValueError('inline joint is attached to another graph edge')
            joints.append(native_joint(doc,graph,edge,row,name,digest,tol));owned[h]=eid
        if edge.get('source_flexible_joints') and {r['source_handle'] for r in edge['source_flexible_joints']}!={j['source_handle'] for j in joints}:raise ValueError('native joint metadata population differs')
        pieces=[];path_proofs=[];encoded_joint_segments=set()
        for pi,path in enumerate(edge.get('attribute_paths',[])):
            if len(path)<2:raise ValueError('empty original inline path')
            private=dict(graph,edges=[dict(edge,attribute_paths=[path])])
            proof=line_audit(doc,private,dict(source_sha256=hashes['source_sha256'],graph_sha256=hashes['graph_sha256'],edges=[eid]),hashes['source_sha256'],hashes['graph_sha256'])
            path_proofs.append(dict(original_path_index=pi,private_source_path_projection=True,coverage=proof))
            for segment in proof['edges'][0]['segments']:
                if segment['status']=='single_source_line_covers':
                    pieces.append(dict(kind='native_pipe',original_path_index=pi,segment_index=segment['index'],points=[segment['start'],segment['end']],source_line_handle=segment['witnesses'][0]['source_handle'],drawing_length=segment['drawing_length']))
                else:
                    matches=[j for j in joints if _pair(segment['start'],segment['end'],*(p[:2] for p in j['contact_points_wcs']),tol)]
                    if segment['status']!='no_witness_in_scoped_search' or len(matches)!=1 or matches[0]['source_handle'] in encoded_joint_segments:
                        raise ValueError('unwitnessed or ambiguous path segment is not one qualified joint span')
                    encoded_joint_segments.add(matches[0]['source_handle'])
        for joint in joints:pieces.append(dict(kind='native_inline_joint',source_handle=joint['source_handle'],points=[p[:2] for p in joint['contact_points_wcs']],physical_length_mm=None))
        # Check the edge's private pipe/joint sequence. No intersections are
        # introduced, and this sequence is never written back as physical pipe.
        vertices=[];adj={}
        def vertex(point):
            hit=[i for i,p in enumerate(vertices) if math.dist(point,p)<=tol]
            if len(hit)>1:raise ValueError('ambiguous private inline path vertex')
            if hit:return hit[0]
            vertices.append(point);adj[len(vertices)-1]=[];return len(vertices)-1
        endpoints=[]
        for i,piece in enumerate(pieces):
            a,b=map(vertex,piece['points'])
            if a==b:raise ValueError('degenerate inline coverage piece')
            adj[a].append((b,i));adj[b].append((a,i));endpoints.append((a,b))
        source_nodes=[nodes[edge[side+'_node_id']] for side in ('start','end')]
        ends=[vertex([n['x'],n['y']]) for n in source_nodes]
        if ends[0]==ends[1] or any(len(items)!=(1 if v in ends else 2) for v,items in adj.items()):raise ValueError('pipe/joint pieces do not form one endpoint-bounded chain')
        current=ends[0];visited=set();order=[]
        while current!=ends[1]:
            choices=[(peer,i) for peer,i in adj[current] if i not in visited]
            if len(choices)!=1:raise ValueError('ambiguous or cyclic inline sequence')
            current,index=choices[0];visited.add(index);order.append(index)
        if len(visited)!=len(pieces):raise ValueError('disconnected pipe/joint fragment remains')
        records.append(dict(edge_id=eid,system=edge['system'],status='native_pipe_and_inline_joint_chain_source_checked',
            original_attribute_paths=copy.deepcopy(edge['attribute_paths']),native_path_proofs=path_proofs,joints=joints,
            private_ordered_pieces=[pieces[i] for i in order],source_drawn_pipe_length_units=sum(p.get('drawing_length',0) for p in pieces),
            joint_spans_excluded_from_pipe_length=True,physical_length_mm=None,physical_ports_verified=False,human_accepted=False))
    return dict(mode='native_inline_joint_path_coverage_v1',records=records,**hashes,graph_mutated=False,
        new_connections_added=0,physical_lengths_assigned=0,human_accepted=False,hil_ready=False)


def implementation_hashes():
    return {n:sha(Path(__file__).with_name(n)) for n in ('native_inline_joint_path_coverage.py','native_path_coverage_audit.py','native_line_path_evidence.py','repair_native_flexible_joints.py','source_readability.py','confirm_crossview_paths.py')}


def compute(paths,policy):
    for key in ('source','graph','inventory','template_origin'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('inline coverage dependency changed '+key)
    origin=load(paths['template_origin'])
    if (origin.get('confirmation_basis')!='source_geometry_calibrated' or origin.get('block_name')!=policy.get('block_name')
        or origin.get('block_fingerprint_sha256')!=policy.get('block_fingerprint_sha256') or not origin.get('expert_evidence')):
        raise ValueError('inline coverage lacks the preserved source-calibrated template origin')
    doc,preflight=read_source(Path(paths['source']));graph=load(paths['graph'])
    with Path(paths['inventory']).open(encoding='utf-8-sig',newline='') as stream:inventory=list(csv.DictReader(stream))
    hashes={key+'_sha256':sha(paths[key]) for key in ('source','graph','inventory')}
    result=collect(doc,graph,inventory,policy,hashes)
    result.update(source_preflight=preflight,template_origin=dict(path=str(Path(paths['template_origin']).resolve()),sha256=sha(paths['template_origin'])))
    for key in ('source','graph','inventory','template_origin'):
        if sha(paths[key])!=policy[key+'_sha256']:raise ValueError('inline coverage input changed during audit '+key)
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'inline-joint-coverage-receipt.json')
    if receipt.get('mode')!='native_inline_joint_path_coverage_v1' or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('inline coverage implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('inline coverage input changed')
    paths={key:item['path'] for key,item in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'inline-joint-coverage.json').read_bytes() or sha(directory/'inline-joint-coverage.json')!=receipt['output_sha256']:
        raise ValueError('inline joint coverage independent source replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','inventory','template-origin','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths={key:getattr(a,key) for key in ('source','graph','inventory','template_origin','policy')}
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'inline-joint-coverage.json';target.write_bytes(encode(result))
    (a.output/'inline-joint-coverage-receipt.json').write_bytes(encode(dict(mode='native_inline_joint_path_coverage_v1',
        inputs={key:dict(path=str(value.resolve()),sha256=sha(value)) for key,value in paths.items()},
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(edges=len(result['records']),joints=sum(len(r['joints']) for r in result['records']),physical_lengths_assigned=0),flush=True)

if __name__=='__main__':main()
