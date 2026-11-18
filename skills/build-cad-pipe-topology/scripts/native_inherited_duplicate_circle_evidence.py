"""Read inherited expert/calibrated rim contacts with coincident native mains.

This is a read-only source witness. The caller must independently replay the
topology owner before using the witness for correspondence. Native duplicate
source entities remain ambiguous physical identities; no pipe is fabricated
between a rim and centre, and no human confirmation transfers to a calibration.
"""
import math
from pathlib import Path
from confirm_crossview_paths import load,sha
from native_line_path_evidence import LAYERS,_on
from duplicate_native_main_diagnostics import same_line
from calibrate_duplicate_circle_screen import signature,equal_signature
from source_reviewed_circle_branch_evidence import repair_root,recorded_z


def _issue(binding,source_hash,point,branch_id=None,answer=None):
    path=Path(binding.get('issue',''))
    if not path.is_file() or sha(path)!=binding.get('issue_sha256'):raise ValueError('historical expert issue changed')
    document=load(path);issue=document.get('issue',{});bounds=issue.get('sourceBounds',[])
    if (document.get('sourceHashes',{}).get('main_dxf')!=source_hash or issue.get('id')!=binding.get('issue_id')
        or not issue.get('note') or answer is not None and issue['note']!=answer or len(bounds)!=4
        or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in bounds) or min(bounds[2:])<=0
        or not(bounds[0]<=point[0]<=bounds[0]+bounds[2] and bounds[1]<=point[1]<=bounds[1]+bounds[3])
        or branch_id is not None and branch_id not in issue.get('edges',[])):raise ValueError('expert issue does not cover this source contact')
    return dict(path=str(path.resolve()),sha256=sha(path),issue_id=issue['id'],note=issue['note'])


def _contact(doc,graph,node,branch,meta,mains):
    system=node['system'];point=[node['x'],node['y']];circle=doc.entitydb.get(meta.get('circle_handle'));handle=meta.get('branch_pipe_handle')
    if handle is None:
        candidates=[h for h in branch.get('source_handles',[]) if doc.entitydb.get(h) is not None and doc.entitydb[h].dxftype()=='LINE'
            and min(math.dist(list(p)[:2],meta.get('source_rim',[])) for p in (doc.entitydb[h].dxf.start,doc.entitydb[h].dxf.end))<=.05]
        if len(candidates)!=1:raise ValueError('inherited native branch identity ambiguous')
        handle=candidates[0]
    native=doc.entitydb.get(handle);rim=meta.get('source_rim',meta.get('branch_rim'))
    if (not circle or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or tuple(circle.dxf.extrusion)!=(0.,0.,1.)
        or not native or native.dxftype()!='LINE' or native not in doc.modelspace() or handle not in branch.get('source_handles',[])
        or circle.dxf.layer!=LAYERS[system] or native.dxf.layer!=LAYERS[system] or not math.isfinite(circle.dxf.radius) or circle.dxf.radius<=0
        or not isinstance(rim,list) or len(rim)!=2 or math.dist(point,list(circle.dxf.center)[:2])>.05
        or math.dist(point,meta.get('center',[]))>.05 or abs(math.dist(point,rim)-circle.dxf.radius)>.05
        or min(math.dist(list(p)[:2],rim) for p in (native.dxf.start,native.dxf.end))>.05):raise ValueError('inherited circle native geometry differs')
    lines=[doc.entitydb.get(h) for h in mains]
    if (len(lines)<2 or len(set(mains))!=len(mains) or any(e is None or e not in doc.modelspace() or e.dxftype()!='LINE' or e.dxf.layer!=LAYERS[system] for e in lines)
        or any(not same_line(lines[0],e,.05) for e in lines[1:])
        or not _on(point,list(lines[0].dxf.start)[:2],list(lines[0].dxf.end)[:2],.05)):
        raise ValueError('inherited coincident native main family changed')
    z=recorded_z(doc,meta,circle,dict(handle=mains[0]),dict(handle=handle),rim)
    if max(abs(z['circle_z']-z[k]) for k in ('main_z_at_center','branch_z_at_rim'))>.05:raise ValueError('inherited circle native Z is inconsistent')
    opposite=[e.dxf.handle for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS.values() and e.dxf.layer!=LAYERS[system]
        and _on(point,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05)]
    if opposite:raise ValueError('opposite system crosses inherited circle centre')
    return circle,native,rim,z


def _rays(doc,node,incident,branch,mains,circle,native,rim):
    point=[node['x'],node['y']];rays=[];directions=[]
    for edge in incident:
        target=rim if edge is branch else point;touch=[]
        for path in edge.get('attribute_paths',[]):
            for a,b in zip(path,path[1:]):
                if math.dist(a,target)<=.05 and math.dist(b,target)>.05:touch.append((a,b))
                elif math.dist(b,target)<=.05 and math.dist(a,target)>.05:touch.append((b,a))
        if len(touch)!=1:raise ValueError('inherited graph ray missing or ambiguous')
        a,b=touch[0];hits=[e.dxf.handle for e in doc.modelspace().query('LINE') if e.dxf.layer==LAYERS[node['system']]
            and _on(a,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05) and _on(b,list(e.dxf.start)[:2],list(e.dxf.end)[:2],.05)]
        if edge is branch:
            if hits!=[native.dxf.handle]:raise ValueError('inherited rim ray lacks one native branch')
            source=dict(scope='inherited_expert_or_calibrated_circle_rim',source_branch_line_handle=native.dxf.handle,
                source_main_line_handles=mains,circle_handle=circle.dxf.handle,branch_rim=rim,physical_connector_length=None)
        else:
            canonical=set(hits)&set(edge.get('source_handles',[]))
            if set(hits)!=set(mains) or len(canonical)!=1:raise ValueError('inherited main ray source family or canonical graph owner differs')
            source=dict(source_line_handle=next(iter(canonical)),coincident_native_main_handles=mains,physical_main_identity='unresolved')
        length=math.dist(a,b);direction=[(b[i]-a[i])/length for i in (0,1)]
        if any(sum(x*y for x,y in zip(direction,v))>math.cos(math.radians(.1)) for v in directions):raise ValueError('inherited circle rays coincide')
        directions.append(direction);rays.append(dict(source,edge_id=edge['edge_id'],graph_segment=[a,b],direction=direction))
    return rays


def collect(doc,graph,node_id,source_hash,graph_hash,policy=None):
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']};node=nodes[node_id]
    incident=[e for e in graph['edges'] if node_id in (e.get('start_node_id'),e.get('end_node_id'))];point=[node['x'],node['y']]
    if (graph.get('metadata',{}).get('source_sha256')!=source_hash or len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges'])
        or node.get('node_type') not in ('tee','physical_junction') or node.get('review_required') is True or node.get('system') not in LAYERS
        or isinstance(node.get('floor'),bool) or not isinstance(node.get('floor'),int)
        or len(incident)!=3 or {e.get('system') for e in incident}!={node['system']}):raise ValueError('inherited circle incidence or source differs')
    expert=node.get('expert_confirmed_circle');calibrated=node.get('calibrated_duplicate_circle');external=(policy or {}).get('external_cases',{}).get(node_id)
    if sum(bool(x) for x in (expert,calibrated,external))!=1:raise ValueError('one inherited source contract required')
    control=None;issue=None
    if expert or calibrated:
        meta=expert or calibrated;key='expertConfirmedCircleJunctionRepair' if expert else 'sourceCalibratedDuplicateCircleRepair'
        confirmation=meta.get('confirmation',{});expected='expert' if expert else 'technical_calibration'
        if confirmation.get('confirmed_by')!=expected or meta.get('physical_main_identity')!='unresolved':raise ValueError('inherited confirmation basis differs')
        root=repair_root(graph,key,node_id,meta.get('circle_handle'),'confirmation',confirmation,source_hash)
        record=next(r for r in root['records'] if r.get('tee')==node_id and r.get('circle_handle')==meta['circle_handle'])
        branch=edges[record['branch_edge']];mains=meta.get('coincident_native_main_handles',[])
        if (branch not in incident or record['system']!=node['system'] or meta.get('source_graph_sha256')!=root.get('input_graph_sha256')
            or meta.get('screen_sha256')!=root.get('screen_sha256') or meta.get('graphic_radius_is_physical_length') is not False
            or meta.get('physical_length')!='unknown' or meta.get('line_system')!=node['system']):raise ValueError('inherited repair record differs')
        if expert:issue=_issue(meta.get('expert_issue_evidence',{}),source_hash,point,branch['edge_id'],confirmation.get('answer'))
        else:
            if meta.get('human_accepted') is not False or confirmation.get('human_accepted') is not False:raise ValueError('technical calibration inherited human acceptance')
            controls=[n for n in graph['nodes'] if n.get('expert_confirmed_circle',{}).get('circle_handle')==meta.get('expert_control_circle')]
            if len(controls)!=1:raise ValueError('inherited expert control missing or duplicated')
            control=controls[0]
    else:
        candidates=[e for e in incident if e.get('source_circle_connection')]
        if len(candidates)!=1:raise ValueError('external legacy circle branch missing or ambiguous')
        branch=candidates[0];meta=branch['source_circle_connection'];control=nodes.get(external.get('control_node_id'))
        issue=_issue(external,source_hash,point)
        if load(external['issue'])['issue'].get('label')!=meta.get('expert_issue') or meta.get('physical_length')!='unknown':raise ValueError('legacy circle expert label differs')
        if not control or not control.get('expert_confirmed_circle'):raise ValueError('external legacy circle lacks an expert shape control')
        mains=control['expert_confirmed_circle'].get('coincident_native_main_handles',[])
        if meta.get('main_pipe_handle') not in mains:raise ValueError('legacy circle canonical main differs')
    circle,native,rim,z=_contact(doc,graph,node,branch,meta,mains)
    if external and abs(meta.get('graphic_radius_not_physical_length',-1)-circle.dxf.radius)>.05:raise ValueError('legacy graphic-radius exclusion differs')
    control_proof=None
    if control is not None:
        control_proof=collect(doc,graph,control['node_id'],source_hash,graph_hash)
        cm=control['expert_confirmed_circle'];cb=edges[next(r for r in graph['expertConfirmedCircleJunctionRepair']['records'] if r['tee']==control['node_id'])['branch_edge']]
        cc=doc.entitydb[cm['circle_handle']]
        if (control['system']!=node['system'] or control.get('floor')!=node['floor'] or set(mains)!=set(cm['coincident_native_main_handles']) or abs(circle.dxf.radius-cc.dxf.radius)>.05
            or abs(circle.dxf.center.z-cc.dxf.center.z)>.05
            or not equal_signature(signature(doc,circle.dxf.center,branch['source_handles']),signature(doc,cc.dxf.center,cb['source_handles']))):
            raise ValueError('complete native branch signature differs from inherited expert control')
    rays=_rays(doc,node,incident,branch,mains,circle,native,rim)
    return dict(status='native_inherited_duplicate_circle_ray_evidence_replayed',source_sha256=source_hash,graph_sha256=graph_hash,
        junctions=[dict(node_id=node_id,system=node['system'],position=point,source_rays=rays,status='inherited_logical_circle_contact_source_replayed')],
        evidence_basis='historical_expert_issue' if expert else 'native_full_branch_calibration_against_historical_expert_control',
        expert_issue=issue,control_evidence=control_proof,native_Z=z,physical_main_identity_resolved=False,
        graph_mutated=False,physical_ports_verified=False,human_accepted=False,hil_ready=False)


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in (Path(__file__).name,
        'duplicate_native_main_diagnostics.py','calibrate_duplicate_circle_screen.py','source_reviewed_circle_branch_evidence.py','native_line_path_evidence.py')}
