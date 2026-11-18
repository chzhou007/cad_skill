"""Reconstruct same-system circles with user or technical-source evidence.

Input source, prior graph, screen and component table are hash-pinned. Default
mode requires user confirmation. The source-review mode independently checks
native geometry and hashed comparisons and never claims human confirmation.
"""
import argparse, collections, copy, csv, hashlib, json, math
from pathlib import Path
from edge_endpoint_semantics import reconcile
from source_readability import read_source

TOL=.05
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dist(a,b):return math.dist(a,b)
def pos(path,p,tol=TOL):
    hits=[];offset=0
    for a,b in zip(path,path[1:]):
        dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
        if length<=tol:raise ValueError('zero path segment')
        t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(length*length)
        if -tol/length<=t<=1+tol/length:
            t=max(0,min(1,t));q=[a[0]+t*dx,a[1]+t*dy]
            if dist(q,p)<=tol:hits.append(offset+t*length)
        offset+=length
    unique=[]
    for h in hits:
        if not any(abs(h-x)<=tol for x in unique):unique.append(h)
    if len(unique)!=1:raise ValueError('point not uniquely on path')
    return unique[0]
def point_at(path,x):
    offset=0
    for a,b in zip(path,path[1:]):
        length=dist(a,b)
        if x<=offset+length+TOL:
            t=max(0,min(1,(x-offset)/length));return [a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])]
        offset+=length
    raise ValueError('position outside path')
def slice_path(path,lo,hi):
    out=[point_at(path,lo)];s=0
    for a,b in zip(path,path[1:]):
        s+=dist(a,b)
        if lo+TOL<s<hi-TOL:out.append(list(b))
    out.append(point_at(path,hi));return out
def segments_for_interval(path,paths,lo,hi):
    result=[]
    for piece in paths:
        for a,b in zip(piece,piece[1:]):
            sa,sb=pos(path,a),pos(path,b)
            low,high=max(lo,min(sa,sb)),min(hi,max(sa,sb))
            if high-low>TOL:
                p,q=point_at(path,low),point_at(path,high)
                result.append([p,q] if sa<sb else [q,p])
    return result
def overlap(a,b,c,d):
    dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
    if length<TOL:return 0
    ux,uy=dx/length,dy/length
    if max(abs((p[0]-a[0])*uy-(p[1]-a[1])*ux) for p in (c,d))>TOL:return 0
    t=[(p[0]-a[0])*ux+(p[1]-a[1])*uy for p in (c,d)]
    return max(0,min(length,max(t))-max(0,min(t)))
def assign_sources(doc,handles,pieces):
    result=[]
    for h in handles:
        line=doc.entitydb.get(h)
        if not line or line.dxftype()!='LINE':raise ValueError('main source is not a native LINE')
        a=[line.dxf.start.x,line.dxf.start.y];b=[line.dxf.end.x,line.dxf.end.y]
        if any(overlap(a,b,p,q)>TOL for path in pieces for p,q in zip(path,path[1:])):result.append(h)
    if not result:raise ValueError('split main has no native source line')
    return result
def apply(doc,graph,rows,screen,policy,source_hash,graph_hash,screen_hash,source_review_policy=None):
    technical=source_review_policy is not None
    calibrated=not technical and policy.get('confirmation',{}).get('confirmed_by')=='technical_calibration'
    current_screen=not technical and policy.get('screen_basis')=='current_graph'
    if current_screen:
        evidence=policy.get('review_evidence',{})
        image=Path(evidence.get('image',''))
        manifest_path=Path(evidence.get('manifest',''))
        if not image.is_file() or not manifest_path.is_file() or sha(image)!=evidence.get('image_sha256') or sha(manifest_path)!=evidence.get('manifest_sha256'):
            raise ValueError('current-screen user review evidence missing or changed')
        manifest=json.loads(manifest_path.read_text(encoding='utf8'))
        if manifest.get('source_sha256')!=source_hash or manifest.get('graph_sha256')!=graph_hash:
            raise ValueError('current-screen review evidence is bound to another source or graph')
        selected=set(policy.get('circle_handles',[]))
        reviewed=set(evidence.get('shown_circle_handles',[]))
        native={c['circle_handle'] for p in manifest.get('pairs',[]) for c in p.get('connections',[])}
        if not selected or selected!=reviewed or not selected.issubset(native):
            raise ValueError('user review does not cover selected circles')
    if (policy.get('source_sha256')!=source_hash or policy.get('input_graph_sha256')!=graph_hash or
        policy.get('screen_sha256')!=screen_hash or screen.get('source_sha256')!=source_hash or
        graph.get('metadata',{}).get('source_sha256')!=source_hash or
        screen.get('graph_sha256')!=(graph_hash if technical or current_screen else graph.get('confirmedEquipmentInterfaceRepair',{}).get('input_graph_sha256'))):
        raise ValueError('source, graph or screen identity mismatch')
    confirm=policy.get('confirmation',{})
    expert=not technical and confirm.get('confirmed_by')=='expert'
    if not technical and (confirm.get('confirmed_by') not in ('user','expert','technical_calibration') or not confirm.get('answer') or not confirm.get('question')):raise ValueError('missing explicit confirmation')
    if calibrated:
        if not current_screen or confirm.get('human_accepted') is not False:raise ValueError('calibration must remain unaccepted')
        v=policy.get('calibration_evidence',{});paths=[Path(v.get(k,'')) for k in ('screen','review','policy')]
        if any(not p.is_file() for p in paths) or any(sha(p)!=v.get(k) for p,k in zip(paths,('screen_sha256','review_sha256','policy_sha256'))):raise ValueError('calibration evidence missing or changed')
        from calibrate_duplicate_circle_screen import prepare
        original,review,calibration=[json.loads(p.read_text(encoding='utf8')) for p in paths]
        regenerated=prepare(doc,graph,original,review,calibration,source_hash,graph_hash,sha(paths[0]),sha(paths[1]))
        if regenerated!=screen or set(policy.get('circle_handles',[]))!={c['circle_handle'] for c in regenerated['candidates']}:raise ValueError('calibration screen or selection changed')
    if expert:
        evidence=policy.get('expert_issue_evidence',{});issue_path=Path(evidence.get('issue',''))
        if not current_screen or not issue_path.is_file() or sha(issue_path)!=evidence.get('issue_sha256'):raise ValueError('expert issue evidence missing or changed')
        issue=json.loads(issue_path.read_text(encoding='utf8'));mark=issue.get('issue',{})
        if issue.get('sourceHashes',{}).get('main_dxf')!=source_hash or mark.get('id')!=evidence.get('issue_id') or mark.get('note')!=confirm.get('answer'):raise ValueError('expert issue identity or note mismatch')
        bounds=mark.get('sourceBounds',[])
        if len(bounds)!=4 or bounds[2]<=0 or bounds[3]<=0:raise ValueError('expert issue has no valid source bounds')
        selected=set(policy.get('circle_handles',[]));by_circle={c['circle_handle']:c for c in screen.get('candidates',[])}
        if not selected.issubset(by_circle):raise ValueError('expert selection absent from screen')
        for h in selected:
            c=by_circle[h];ids=c.get('coincident_native_main_handles',[])
            if len(ids)<2 or c.get('physical_main_identity')!='unresolved' or not set(c.get('main_graph_edges',[])+c.get('branch_graph_edges',[])).issubset(set(mark.get('edges',[]))) or not set(c.get('rim_virtual_nodes',[])).issubset(set(mark.get('nodes',[]))):raise ValueError('expert issue scope mismatch')
            from duplicate_native_main_diagnostics import same_line
            natives=[doc.entitydb.get(x) for x in ids];center=c.get('center',[])
            if len(center)!=2 or not(bounds[0]<=center[0]<=bounds[0]+bounds[2] and bounds[1]<=center[1]<=bounds[1]+bounds[3]) or any(e is None or e not in doc.modelspace() for e in natives) or any(not same_line(natives[0],e,TOL) for e in natives[1:]) or c.get('main_handle') not in ids:raise ValueError('expert coincident source evidence invalid')
    selected=policy.get('circle_handles')
    if not isinstance(selected,list) or not selected or len(set(selected))!=len(selected):raise ValueError('invalid circle selection')
    if technical:
        from source_reviewed_circle_connections import load_review,candidate
        from source_circle_rim_tee_screen import LAYERS
        review=load_review(source_review_policy,source_hash)
        if set(review)!=set(selected):raise ValueError('technical review scope differs from selected circles')
        segments=[{'handle':e.dxf.handle,'system':LAYERS.get(e.dxf.layer),'a':(e.dxf.start.x,e.dxf.start.y),'b':(e.dxf.end.x,e.dxf.end.y)} for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS or e.dxf.layer=='空调立管、水平支管']
        for handle in selected:
            entity=doc.entitydb.get(handle)
            if entity is None or entity.dxftype()!='CIRCLE':raise ValueError('reviewed native circle missing')
            circle={'handle':handle,'system':LAYERS.get(entity.dxf.layer),'center':(entity.dxf.center.x,entity.dxf.center.y),'radius':entity.dxf.radius}
            if candidate(doc,circle,segments,review,graph=graph) is None:raise ValueError('reviewed native contact unsupported')
        confirm={'review_kind':'technical_native_source_comparison','review_manifest':source_review_policy['review_manifest'],'review_sha256':source_review_policy['review_sha256'],'human_accepted':False}
    prefix='SOURCE' if technical else 'EXPERT' if expert else 'CALIBRATED' if calibrated else 'USER'
    edge_evidence_key='source_reviewed_circle_connection' if technical else 'source_expert_circle_connection' if expert else 'source_calibrated_duplicate_connection' if calibrated else 'source_user_circle_connection'
    g=copy.deepcopy(graph);rows=copy.deepcopy(rows);nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']}
    if len(nodes)!=len(g['nodes']) or len(edges)!=len(g['edges']):raise ValueError('duplicate IDs')
    candidates={};
    for c in screen['candidates']:
        if c['circle_handle'] in candidates:raise ValueError('duplicate screen circle')
        candidates[c['circle_handle']]=c
    grouped=collections.defaultdict(list);records=[]
    for h in selected:
        c=candidates[h];main_ids=c['main_graph_edges'];branch_ids=c['branch_graph_edges'];terminals=c['rim_virtual_nodes']
        if c['status']!='source_shape_graph_connection_not_established' or len(main_ids)!=1 or len(branch_ids)!=1 or len(terminals)!=1 or c['protected_boundaries']:raise ValueError('ambiguous or protected candidate')
        main=edges[main_ids[0]];branch=edges[branch_ids[0]];terminal=nodes[terminals[0]];system=c['line_system']
        if main['system']!=system or branch['system']!=system or terminal.get('system')!=system or terminal.get('subtype')!='unresolved_source_terminal':raise ValueError('system or terminal mismatch')
        if sum(terminal['node_id'] in (e.get('start_node_id'),e.get('end_node_id')) for e in edges.values())!=1:raise ValueError('terminal is not unique')
        if c['main_handle'] not in main['source_handles'] or c['branch_handle'] not in branch['source_handles']:raise ValueError('source handle mismatch')
        circle=doc.entitydb.get(h);line=doc.entitydb.get(c['branch_handle']);native_main=doc.entitydb.get(c['main_handle'])
        if not circle or circle.dxftype()!='CIRCLE' or not line or line.dxftype()!='LINE' or not native_main or native_main.dxftype()!='LINE':raise ValueError('source circle or pipe missing')
        if circle.dxf.layer!=c['circle_layer'] or abs(circle.dxf.radius-c['radius'])>TOL or dist((circle.dxf.center.x,circle.dxf.center.y),c['center'])>TOL:raise ValueError('native circle mismatch')
        p=[terminal['x'],terminal['y']];center=c['center']
        if dist(p,c['branch_rim'])>TOL or abs(dist(p,center)-c['radius'])>TOL:raise ValueError('native rim mismatch')
        if min(dist(p,(v.x,v.y)) for v in (line.dxf.start,line.dxf.end))>TOL:raise ValueError('branch line does not end at rim')
        s=pos(main['path'],center)
        if s<=TOL or s>=sum(dist(a,b) for a,b in zip(main['path'],main['path'][1:]))-TOL:raise ValueError('circle outside main interior')
        if len([point for point in branch['path'] if dist(point,[terminal['x'],terminal['y']])<=TOL])!=1:raise ValueError('branch endpoint mismatch')
        grouped[main['edge_id']].append((s,c,terminal['node_id'],branch['edge_id']))
    pending_connections=[]
    for main_id,items in grouped.items():
        items.sort(key=lambda x:x[0]);main=edges.pop(main_id);path=main['path'];total=sum(dist(a,b) for a,b in zip(path,path[1:]));cuts=[0]+[x[0] for x in items]+[total]
        if any(k.startswith('diameter_') or k in ('pipe_diameter','source_segment_dimensions','physical_length','physical_length_mm') for k in main):
            raise ValueError('split main has diameter or physical-length attributes requiring explicit remapping')
        if any(b-a<=TOL for a,b in zip(cuts,cuts[1:])):raise ValueError('overlapping cuts')
        tees=['T-'+prefix+'-'+x[1]['circle_handle'] for x in items];new_ids=[main_id]+['E-'+prefix+'-'+x[1]['circle_handle'] for x in items]
        if any(n in nodes for n in tees) or any(e in edges for e in new_ids):raise ValueError('new ID collision')
        child_ends=[main['start_node_id']]+tees+[main['end_node_id']];children=[]
        for i,(lo,hi) in enumerate(zip(cuts,cuts[1:])):
            e=copy.deepcopy(main);e['edge_id']=new_ids[i];e['start_node_id']=child_ends[i];e['end_node_id']=child_ends[i+1]
            if i:e.pop('start_port_id',None)
            if i<len(new_ids)-1:e.pop('end_port_id',None)
            e['path']=slice_path(path,lo,hi);e['path_points']=copy.deepcopy(e['path']);e['attribute_paths']=segments_for_interval(path,main['attribute_paths'],lo,hi)
            if not e['attribute_paths']:raise ValueError('split main lacks source paths')
            e['path_length']=sum(dist(p,q) for piece in e['attribute_paths'] for p,q in zip(piece,piece[1:]));e['source_handles']=assign_sources(doc,main['source_handles'],e['attribute_paths'])
            e['source_flexible_joints']=[f for f in main.get('source_flexible_joints',[]) if all(lo-TOL<=pos(path,p)<=hi+TOL for p in f['source_contact_points'])]
            if not e['source_flexible_joints']:
                e.pop('source_flexible_joints',None);e.pop('connection_mode',None)
            e['equipment_names']=[];e['equipment_counts']={};e['split_source_edge']={'edge_id':main_id,'source_graph_sha256':graph_hash,'interval_native_units':[lo,hi]};children.append(e)
        if set(h for e in children for h in e['source_handles'])!=set(main['source_handles']):raise ValueError('split lost source handles')
        if abs(sum(e['path_length'] for e in children)-main['path_length'])>TOL:raise ValueError('split lost source length')
        original_flex=[f['source_handle'] for f in main.get('source_flexible_joints',[])]
        if collections.Counter(f['source_handle'] for e in children for f in e.get('source_flexible_joints',[]))!=collections.Counter(original_flex):raise ValueError('split lost or duplicated flexible joint')
        for row in rows:
            if row.get('edge_id')!=main_id:continue
            s=pos(path,[float(row['x']),float(row['y'])],tol=5.0)
            slots=[i for i,(lo,hi) in enumerate(zip(cuts,cuts[1:])) if lo+TOL<s<hi-TOL]
            if len(slots)!=1:raise ValueError('component is ambiguous at cut')
            e=children[slots[0]];row['edge_id']=e['edge_id'];e['equipment_names'].append(row['device_name']);typ=row['equipment_type'];e['equipment_counts'][typ]=e['equipment_counts'].get(typ,0)+1
        if collections.Counter(d for e in children for d in e['equipment_names'])!=collections.Counter(main.get('equipment_names',[])):raise ValueError('component conservation failed')
        for e in children:edges[e['edge_id']]=e
        for (_,c,terminal_id,branch_id),tee in zip(items,tees):
            pending_connections.append((c,terminal_id,branch_id,tee,main_id,new_ids))
    # A branch can itself be a main cut by other selected circles. Resolve its
    # unique descendant only after every main has been split, then reattach.
    for c,terminal_id,branch_id,tee,main_id,new_ids in pending_connections:
            candidates=[e for e in edges.values() if (e['edge_id']==branch_id or e.get('split_source_edge',{}).get('edge_id')==branch_id) and terminal_id in (e['start_node_id'],e['end_node_id']) and c['branch_handle'] in e['source_handles'] and e['system']==c['line_system']]
            if len(candidates)!=1:raise ValueError('branch descendant missing or ambiguous after main splitting')
            old=nodes.pop(terminal_id);branch=candidates[0];side='start' if branch['start_node_id']==terminal_id else 'end' if branch['end_node_id']==terminal_id else None
            if side is None:raise ValueError('branch no longer reaches terminal')
            center=list(c['center']);branch[side+'_node_id']=tee;branch.pop(side+'_port_id',None)
            branch['path']=([center]+branch['path']) if side=='start' else (branch['path']+[center]);branch['path_points']=copy.deepcopy(branch['path'])
            previous_connection=copy.deepcopy(branch.get(edge_evidence_key))
            branch[edge_evidence_key]={('source_comparison' if technical else 'confirmation'):confirm,'circle_handle':c['circle_handle'],'circle_layer':c['circle_layer'],'line_system':c['line_system'],'circle_layer_matches_lines':c['circle_layer_matches_lines'],'z_consistent_within_tolerance':c['z_consistent_within_tolerance'],'circle_z':c['circle_z'],'main_z_at_center':c['main_z_at_center'],'branch_z_at_rim':c['branch_z_at_rim'],'source_rim':c['branch_rim'],'center':center,'source_graph_sha256':graph_hash,'screen_sha256':screen_hash,'graphic_radius_is_physical_length':False,'physical_length':'unknown'}
            if expert:
                branch[edge_evidence_key].update(expert_issue_evidence=copy.deepcopy(policy['expert_issue_evidence']),coincident_native_main_handles=copy.deepcopy(c['coincident_native_main_handles']),physical_main_identity='unresolved')
            if calibrated:
                branch[edge_evidence_key].update(expert_control_circle=c['expert_control_circle'],coincident_native_main_handles=copy.deepcopy(c['coincident_native_main_handles']),physical_main_identity='unresolved',human_accepted=False)
            if technical and review[c['circle_handle']].get('confirmed_plan_control'):
                branch[edge_evidence_key]['confirmed_plan_control']=copy.deepcopy(review[c['circle_handle']]['confirmed_plan_control'])
                if review[c['circle_handle']].get('plan_control_match'):
                    branch[edge_evidence_key]['plan_control_match']=review[c['circle_handle']]['plan_control_match']
            if previous_connection:branch[edge_evidence_key]['previous_connection']=previous_connection
            branch['path_length_complete']=False;branch['path_length_scope']='source_drawn_pipe_only_'+('source_reviewed' if technical else 'expert_confirmed' if expert else 'technical_calibrated' if calibrated else 'user_confirmed')+'_circle_and_equipment_length_unknown'
            nodes[tee]={'node_id':tee,'node_type':'tee','subtype':'physical_tee','floor':old['floor'],'system':c['line_system'],'x':center[0],'y':center[1],'label':tee,'source_handles':[c['circle_handle'],c['main_handle'],c['branch_handle']],('source_reviewed_circle' if technical else 'expert_confirmed_circle' if expert else 'calibrated_duplicate_circle' if calibrated else 'user_confirmed_circle'):branch[edge_evidence_key]}
            records.append({'circle_handle':c['circle_handle'],'retired_terminal':terminal_id,'tee':tee,'branch_edge':branch['edge_id'],'main_source_edge':main_id,'main_child_edges':new_ids,'system':c['line_system']})
    g['nodes']=list(nodes.values());g['edges']=list(edges.values());removed={r['retired_terminal'] for r in records}
    g['virtual_equipment_ports']=[p for p in g.get('virtual_equipment_ports',[]) if p.get('virtual_equipment_id') not in removed]
    g,changes=reconcile(g)
    for r in records:
        incident=[e for e in g['edges'] if r['tee'] in (e.get('start_node_id'),e.get('end_node_id'))]
        if len(incident)!=3 or any(e['system']!=r['system'] for e in incident):raise ValueError('rebuilt tee invariant failed')
    repair_key='sourceReviewedCircleJunctionRepair' if technical else 'expertConfirmedCircleJunctionRepair' if expert else 'sourceCalibratedDuplicateCircleRepair' if calibrated else 'userConfirmedCircleJunctionRepair'
    g[repair_key]={'records':records,('source_comparison' if technical else 'confirmation'):confirm,'source_sha256':source_hash,'input_graph_sha256':graph_hash,'screen_sha256':screen_hash,'supply_return_independent':True,'physical_length':'unknown'}
    if graph.get(repair_key):g[repair_key]['previous_repair']=copy.deepcopy(graph[repair_key])
    g['preHilComparison']={'status':'pending','previous_comparison':copy.deepcopy(graph.get('preHilComparison')),'reason':('source-reviewed' if technical else 'expert-confirmed' if expert else 'technically calibrated' if calibrated else 'user-confirmed')+' source circle junctions require fresh source comparison and graph-bound reviews'}
    g['metadata'].update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_semantic_change')
    return g,rows,{'records':records,'endpoint_changes':changes,'hil_ready':False}

def main():
    p=argparse.ArgumentParser()
    for n in ('source','graph','devices','screen','policy','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('output exists')
    doc,proof=read_source(a.source);graph=json.loads(a.graph.read_text(encoding='utf8'));screen=json.loads(a.screen.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'))
    if policy.get('devices_sha256')!=sha(a.devices):raise ValueError('component table identity mismatch')
    with a.devices.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    out,rows,audit=apply(doc,graph,rows,screen,policy,proof['source_sha256'],sha(a.graph),sha(a.screen));a.output.mkdir(parents=True)
    target=a.output/'graph_with_confirmed_circle_junctions.json';target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    with (a.output/'assigned_edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    audit.update(source_sha256=proof['source_sha256'],input_graph_sha256=sha(a.graph),screen_sha256=sha(a.screen),policy_sha256=sha(a.policy),input_devices_sha256=sha(a.devices),output_graph_sha256=sha(target),script_sha256=sha(__file__))
    (a.output/'confirmed-circle-junction-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'junctions':len(audit['records']),'output_sha256':sha(target)}))
if __name__=='__main__':main()
