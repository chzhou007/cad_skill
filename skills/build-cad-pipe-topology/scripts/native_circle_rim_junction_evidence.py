"""Replay reviewed radial circle contacts without inventing a pipe to the center."""
import math
from source_reviewed_circle_connections import load_review,candidate
from native_line_path_evidence import LAYERS,_on

def circle_contact(doc,graph,node,edge,source_hash):
    meta=edge.get('source_circle_connection') or {}
    comparison=meta.get('source_comparison') or {}
    if comparison.get('source_sha256',source_hash)!=source_hash or comparison.get('review_kind')!='technical_native_source_comparison' or comparison.get('human_accepted') is not False:raise ValueError('invalid circle technical comparison binding')
    review=load_review(dict(comparison,source_sha256=source_hash),source_hash)
    handle=meta.get('circle_handle');row=review.get(handle)
    if not row:raise ValueError('circle contact lacks pinned technical source review')
    if comparison.get('pair_sha256')!=row.get('pair_sha256'):raise ValueError('circle contact Pair binding differs')
    reverse={v:k for k,v in LAYERS.items()}
    c=doc.entitydb.get(handle)
    if c is None or c.dxftype()!='CIRCLE':raise ValueError('circle contact source missing')
    spec=dict(handle=handle,system=reverse.get(c.dxf.layer),center=(c.dxf.center.x,c.dxf.center.y),radius=c.dxf.radius)
    segments=[dict(handle=l.dxf.handle,system=reverse[l.dxf.layer],a=(l.dxf.start.x,l.dxf.start.y),b=(l.dxf.end.x,l.dxf.end.y)) for l in doc.modelspace().query('LINE') if l.dxf.layer in reverse]
    main,(branch,_,rim)=candidate(doc,spec,segments,review,graph=graph)
    point=[node['x'],node['y']]
    if (edge.get('system')!=row['system'] or node.get('system')!=row['system']
        or math.dist(point,spec['center'])>.05 or math.dist(point,meta.get('center',[]))>.05
        or math.dist(rim,meta.get('branch_rim',[]))>.05
        or meta.get('main_pipe_handle')!=main['handle'] or meta.get('branch_pipe_handle')!=branch['handle']
        or branch['handle'] not in edge.get('source_handles',[])
        or abs(meta.get('graphic_radius_not_physical_length',-1)-c.dxf.radius)>.05
        or meta.get('physical_length')!='unknown'):
        raise ValueError('circle contact graph/source binding differs')
    paths=edge.get('attribute_paths',[])
    if len(paths)!=1 or len(paths[0])<2:raise ValueError('circle branch needs one source path')
    path=paths[0]
    ends=[p for p in (path[0],path[-1]) if math.dist(p,rim)<=.05]
    if len(ends)!=1 or any(not _on(p,branch['a'],branch['b'],.05) for p in path):raise ValueError('circle branch includes radius or leaves native source LINE')
    other=path[1] if math.dist(path[0],rim)<=.05 else path[-2]
    if math.dist(other,rim)<=.05:raise ValueError('zero circle branch ray')
    return dict(edge_id=edge['edge_id'],scope='source_reviewed_circle_rim',source_branch_line_handle=branch['handle'],source_main_line_handle=main['handle'],
        circle_handle=handle,center=point,branch_rim=list(rim),graph_segment=[list(rim),other],
        source_comparison=meta['source_comparison'],physical_connector_length=None,
        status='logical_circle_contact_source_replayed_no_center_pipe')

def collect(doc,graph,node_id,source_hash,graph_hash):
    nodes={n['node_id']:n for n in graph['nodes']};node=nodes[node_id];p=[node['x'],node['y']]
    incident=[e for e in graph['edges'] if node_id in (e.get('start_node_id'),e.get('end_node_id'))]
    if node.get('node_type') not in ('tee','physical_junction') or node.get('review_required') is True or len(incident)!=3 or len({e['edge_id'] for e in incident})!=3 or {e.get('system') for e in incident}!={node.get('system')} or node.get('system') not in LAYERS:raise ValueError('circle T incidence is unresolved or mixed')
    circles=[e for e in incident if e.get('source_circle_connection')]
    if len(circles)!=1:raise ValueError('circle T must have one reviewed branch')
    branch=circles[0];rim=circle_contact(doc,graph,node,branch,source_hash);rays=[];directions=[]
    for edge in incident:
        if edge is branch:
            item=rim;a,b=item['graph_segment']
        else:
            touches=[]
            for path in edge.get('attribute_paths',[]):
                for a,b in zip(path,path[1:]):
                    if math.dist(a,p)<=.05 and math.dist(b,p)>.05:touches.append((a,b))
                    elif math.dist(b,p)<=.05 and math.dist(a,p)>.05:touches.append((b,a))
            if len(touches)!=1:raise ValueError('circle main graph ray not unique')
            a,b=touches[0]
            hits=[l.dxf.handle for l in doc.modelspace().query('LINE') if l.dxf.layer==LAYERS[edge['system']] and _on(a,list(l.dxf.start)[:2],list(l.dxf.end)[:2],.05) and _on(b,list(l.dxf.start)[:2],list(l.dxf.end)[:2],.05)]
            if hits!=[rim['source_main_line_handle']] or hits[0] not in edge.get('source_handles',[]):raise ValueError('circle main source ray ambiguous or changed')
            item=dict(edge_id=edge['edge_id'],source_line_handle=hits[0],graph_segment=[a,b])
        length=math.dist(a,b);v=[(b[i]-a[i])/length for i in (0,1)]
        if any(sum(x*y for x,y in zip(v,u))>math.cos(math.radians(.1)) for u in directions):raise ValueError('coincident circle T rays')
        directions.append(v);rays.append(dict(item,direction=v))
    return dict(status='native_circle_ray_evidence_unreviewed',source_sha256=source_hash,graph_sha256=graph_hash,
        junctions=[dict(node_id=node_id,system=node['system'],position=p,source_rays=rays,status='source_circle_contact_replayed_not_human_accepted')],
        graph_mutated=False,hil_ready=False,limitations=['Source circle establishes scoped logical contact; radius and rim-to-center span are not measured pipe length.','Equipment ports, cross-view identity, DN and installed lengths need separate evidence.'])
