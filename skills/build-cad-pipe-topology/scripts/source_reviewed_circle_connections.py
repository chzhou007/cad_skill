"""Source-reviewed circle-rim connections, distinct from expert confirmations."""
import hashlib,json,math
from pathlib import Path
from cad_ceiling_native_rules import radial_circle_connection_candidate,match_out_of_plane_symbol,on

def load_review(policy,source_hash):
    if not policy:return {}
    if policy.get('source_sha256')!=source_hash:raise ValueError('circle source review source mismatch')
    path=Path(policy['review_manifest'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=policy['review_sha256']:raise ValueError('circle source review stale')
    review=json.loads(path.read_text(encoding='utf8'))
    if review.get('source_sha256')!=source_hash or review.get('review_kind')!='technical_native_source_comparison':raise ValueError('invalid circle source review')
    rows={}
    for row in review['connections']:
        if row['circle_handle'] in rows:raise ValueError('duplicate reviewed circle')
        image=Path(row['pair_image'])
        if hashlib.sha256(image.read_bytes()).hexdigest()!=row['pair_sha256']:raise ValueError('stale circle source pair')
        if row.get('disposition')!='direct_same_system_circle_rim_contact':raise ValueError('unsupported circle review disposition')
        rows[row['circle_handle']]=row
    return rows

def verified_repeated_plan_z(doc,graph,row,circle,main,branch,tol=.05):
    """Check exact 3-D source signature against one previously confirmed plan tee.

    The default compares the complete branch signature under XY translation.
    The explicit remote-boundary mode compares the rim, directions and endpoint
    Z values while allowing another branch length; neither mode normalizes Z.
    The user's confirmation belongs to the control only.
    """
    reference=row.get('confirmed_plan_control')
    if not isinstance(reference,dict) or not isinstance(graph,dict):raise ValueError('missing confirmed plan control')
    audit=graph.get('userConfirmedCircleJunctionRepair') or {}
    confirm=audit.get('confirmation') or {}
    if confirm.get('confirmed_by')!='user' or not confirm.get('answer') or audit.get('source_sha256')!=graph.get('metadata',{}).get('source_sha256'):
        raise ValueError('plan control lacks source-bound user confirmation')
    records=[r for r in audit.get('records',[]) if r.get('circle_handle')==reference.get('circle_handle') and r.get('system')==row['system']]
    if len(records)!=1:raise ValueError('plan control confirmation not unique')
    rec=records[0];nodes={n['node_id']:n for n in graph['nodes']};node=nodes.get(rec['tee'])
    if not node or node.get('system')!=row['system'] or node.get('user_confirmed_circle',{}).get('circle_handle')!=reference['circle_handle']:
        raise ValueError('plan control junction missing')
    if node.get('user_confirmed_circle',{}).get('confirmation')!=confirm:
        raise ValueError('plan control confirmation evidence differs')
    incident=[e for e in graph['edges'] if rec['tee'] in (e.get('start_node_id'),e.get('end_node_id'))]
    if len(incident)!=3 or any(e.get('system')!=row['system'] for e in incident) or not any(e['edge_id']==rec['branch_edge'] for e in incident):
        raise ValueError('plan control current connection invalid')
    from source_circle_rim_tee_screen import LAYERS
    rc,rm,rb=[doc.entitydb.get(reference.get(k)) for k in ('circle_handle','main_handle','branch_handle')]
    if any(e is None or e not in doc.modelspace() for e in (rc,rm,rb)) or [e.dxftype() for e in (rc,rm,rb)]!=['CIRCLE','LINE','LINE']:
        raise ValueError('native plan control missing')
    if tuple(rc.dxf.extrusion)!=(0.,0.,1.) or rc.dxf.layer!=circle.dxf.layer or abs(rc.dxf.radius-circle.dxf.radius)>tol:
        raise ValueError('plan control symbol differs')
    if math.dist((rc.dxf.center.x,rc.dxf.center.y),(node['x'],node['y']))>tol:
        raise ValueError('plan control source location differs')
    if not all(LAYERS.get(e.dxf.layer)==row['system'] for e in (rm,rb,main,branch)):
        raise ValueError('plan control source systems differ')
    if reference['branch_handle'] not in next(e for e in incident if e['edge_id']==rec['branch_edge']).get('source_handles',[]):
        raise ValueError('plan control branch identity differs')
    if sum(reference['main_handle'] in e.get('source_handles',[]) for e in incident)!=2:
        raise ValueError('plan control main identity differs')
    target_edges=[e for e in graph['edges'] if row['branch_handle'] in e.get('source_handles',[]) and e.get('system')==row['system']]
    if len(target_edges)!=1:raise ValueError('candidate branch is not unique')
    terminal=[nodes.get(target_edges[0].get(k)) for k in ('start_node_id','end_node_id')]
    terminal=[n for n in terminal if n and n.get('subtype')=='unresolved_source_terminal'
              and abs(math.dist((n['x'],n['y']),(circle.dxf.center.x,circle.dxf.center.y))-circle.dxf.radius)<=tol]
    if len(terminal)!=1 or terminal[0].get('floor')!=node.get('floor') or node.get('floor') is None:
        raise ValueError('plan control and candidate floors differ or are unknown')
    mode=row.get('plan_control_match','exact_3d_signature')
    if mode not in ('exact_3d_signature','same_rim_variable_unknown_remote'):
        raise ValueError('unsupported plan control matching mode')
    if mode=='same_rim_variable_unknown_remote':
        edge=target_edges[0];anchor_ids=[edge.get('start_boundary_id'),edge.get('end_boundary_id')]
        anchors=[a for a in graph.get('boundary_anchors',[]) if a.get('boundary_id') in anchor_ids]
        remote_nodes=[nodes.get(edge.get(k)) for k in ('start_node_id','end_node_id')]
        remote_nodes=[n for n in remote_nodes if n and n['node_id']!=terminal[0]['node_id']]
        remote=anchors+remote_nodes
        if len(remote)!=1 or remote[0].get('system')!=row['system']:
            raise ValueError('candidate remote boundary is not unique')
        end=remote[0]
        if anchors:
            if end.get('source_pipe_handle')!=row['branch_handle'] or end.get('connectivity_beyond_boundary')!='unknown':
                raise ValueError('candidate remote boundary semantics are not unknown')
        elif end.get('subtype')!='unresolved_source_terminal' or end.get('floor')!=node.get('floor'):
            raise ValueError('candidate remote endpoint is not unresolved')
        far=max((branch.dxf.start,branch.dxf.end),key=lambda p:math.dist((p.x,p.y),(circle.dxf.center.x,circle.dxf.center.y)))
        if math.dist((end['x'],end['y']),(far.x,far.y))>tol:
            raise ValueError('candidate remote boundary differs from source endpoint')
    def signature(c,m,b):
        o=c.dxf.center
        pts=sorted([(p.x-o.x,p.y-o.y,p.z) for p in (b.dxf.start,b.dxf.end)],key=lambda p:math.hypot(p[0],p[1]))
        dx=m.dxf.end.x-m.dxf.start.x;dy=m.dxf.end.y-m.dxf.start.y;length=math.hypot(dx,dy)
        if length<=tol:raise ValueError('degenerate plan main')
        ux,uy=dx/length,dy/length
        if ux < -1e-9 or (abs(ux)<=1e-9 and uy<0):ux,uy=-ux,-uy
        direction=(ux,uy)
        if mode=='same_rim_variable_unknown_remote':
            near,far=pts;far_dist=math.hypot(far[0],far[1])
            if abs(math.hypot(near[0],near[1])-c.dxf.radius)>tol or far_dist<=c.dxf.radius+tol:
                raise ValueError('control branch endpoints are not distinct from circle rim')
            return [o.z,c.dxf.radius,*near,far[0]/far_dist,far[1]/far_dist,far[2],*direction,*sorted((m.dxf.start.z,m.dxf.end.z))]
        return [o.z,c.dxf.radius,*pts[0],*pts[1],*direction,*sorted((m.dxf.start.z,m.dxf.end.z))]
    left,right=signature(rc,rm,rb),signature(circle,main,branch)
    if not all(math.isfinite(x) and math.isfinite(y) and abs(x-y)<=tol for x,y in zip(left,right)):
        raise ValueError('3D plan signature differs from confirmed control')
    return True


def candidate(doc,circle,segments,review,tol=.05,graph=None):
    if circle['handle'] not in review:return None
    row=review[circle['handle']]
    # A connection circle is a drafting symbol. A reviewed mismatch may use
    # the two independently classified native pipe layers, never the circle
    # alone, to determine the service. All geometry/Z/interface guards remain.
    if row.get('system_evidence') is not None:
        from source_circle_rim_tee_screen import LAYERS
        if row['system_evidence']!='both_native_pipe_layers':raise ValueError('unsupported circle system evidence')
        native_symbol=doc.entitydb.get(circle['handle'])
        if not native_symbol or native_symbol.dxf.layer!=row.get('source_circle_layer'):raise ValueError('reviewed symbol layer changed')
        for key in ('main_handle','branch_handle'):
            line=doc.entitydb.get(row[key])
            if not line or line.dxftype()!='LINE' or LAYERS.get(line.dxf.layer)!=row['system']:raise ValueError('reviewed pipe systems do not agree')
        circle=dict(circle,system=row['system'])
    if circle['system']!=row['system'] or abs(circle['radius']-row['radius'])>tol:raise ValueError('reviewed circle class mismatch')
    match=radial_circle_connection_candidate(circle,segments,tol)
    if match is None:raise ValueError('reviewed circle contact no longer unique')
    main,(branch,side,end)=match
    if (main['handle'],branch['handle'])!=(row['main_handle'],row['branch_handle']):raise ValueError('reviewed circle contact handles mismatch')
    native=doc.entitydb.get(circle['handle'])
    if native is None or native.dxftype()!='CIRCLE' or native not in doc.modelspace() or tuple(native.dxf.extrusion)!=(0.,0.,1.):raise ValueError('unsupported reviewed circle transform')
    center=circle['center'];z=native.dxf.center.z
    if not math.isfinite(z):raise ValueError('invalid source Z')
    native_lines=[];z_conflict=False
    for segment in (main,branch):
        entity=doc.entitydb.get(segment['handle'])
        if entity is None or entity.dxftype()!='LINE' or entity not in doc.modelspace():raise ValueError('reviewed pipe is not native LINE')
        if any(not math.isfinite(p.z) for p in (entity.dxf.start,entity.dxf.end)):raise ValueError('invalid native pipe Z')
        z_conflict=z_conflict or any(abs(p.z-z)>tol for p in (entity.dxf.start,entity.dxf.end));native_lines.append(entity)
    if z_conflict or row.get('plan_control_match'):
        verified_repeated_plan_z(doc,graph,row,native,*native_lines,tol)
    glyphs=[{'a':(e.dxf.start.x,e.dxf.start.y),'b':(e.dxf.end.x,e.dxf.end.y)} for e in doc.modelspace().query('LINE') if e.dxf.layer=='空调立管、水平支管']
    if match_out_of_plane_symbol(circle,glyphs,tol) or any(min(math.dist(center,g['a']),math.dist(center,g['b']))<=circle['radius']+tol for g in glyphs):raise ValueError('reviewed circle has interface glyph interference')
    for s in segments:
        if s['system']!=circle['system'] and on(center,s['a'],s['b'],tol) is not None:raise ValueError('other system at reviewed circle center')
    return match
