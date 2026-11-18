"""Identify source-backed terminal crossbars for comparison, never change topology."""
import collections,copy,math

def identify(graph,doc,profile):
    if not profile.get('source_sha256') or graph.get('metadata',{}).get('source_sha256')!=profile['source_sha256']:
        raise ValueError('Crossbar profile does not match graph source')
    if not profile.get('source_layers') or not profile.get('calibration_evidence'):
        raise ValueError('Crossbar geometry needs explicit local calibration')
    target=float(profile['native_length']); tol=float(profile.get('tolerance',.1)); nodes={n['node_id']:n for n in graph['nodes']};adj=collections.defaultdict(list)
    for edge in graph['edges']:
        for nid in (edge['start_node_id'],edge['end_node_id']):adj[nid].append(edge)
    result=[]
    for tee in graph['nodes']:
        if tee.get('node_type')!='tee' or len(adj[tee['node_id']])!=3:continue
        pair=collections.defaultdict(list)
        for e in adj[tee['node_id']]:
            other=e['end_node_id'] if e['start_node_id']==tee['node_id'] else e['start_node_id'];n=nodes.get(other)
            if not n or n.get('node_type')!='virtual_equipment' or len(adj[other])!=1 or len(e.get('source_handles',[]))!=1:continue
            if n.get('source_terminal_glyph_ids') or n.get('interface_destination'):continue
            pair[e['source_handles'][0]].append((e,n))
        for handle,parts in pair.items():
            if len(parts)!=2:continue
            source=doc.entitydb.get(handle)
            if source is None or source.dxftype()!='LINE' or source.dxf.layer not in profile['source_layers']:continue
            a=source.ocs().to_wcs(source.dxf.start);b=source.ocs().to_wcs(source.dxf.end);u=(b.x-a.x,b.y-a.y);length=math.hypot(*u);mid=((a.x+b.x)/2,(a.y+b.y)/2)
            if abs(length-target)>tol or math.dist(mid,(tee['x'],tee['y']))>tol:continue
            if min(math.dist((a.x,a.y),(parts[0][1]['x'],parts[0][1]['y']))+math.dist((b.x,b.y),(parts[1][1]['x'],parts[1][1]['y'])),math.dist((a.x,a.y),(parts[1][1]['x'],parts[1][1]['y']))+math.dist((b.x,b.y),(parts[0][1]['x'],parts[0][1]['y'])))>2*tol:continue
            third=[e for e in adj[tee['node_id']] if e not in (parts[0][0],parts[1][0])]
            if len(third)!=1:continue
            if len({e['system'] for e,_ in parts})!=1:continue
            mixed=any(e['system']!=third[0]['system'] for e,_ in parts)
            if mixed and (not profile.get('include_mixed_source_candidates') or not tee.get('mixed_source_contact') or not tee.get('system_review_required')):continue
            witnesses=[]
            for h in third[0].get('source_handles',[]):
                entity=doc.entitydb.get(h)
                if entity is None or entity.dxftype()!='LINE':continue
                if (not mixed and entity.dxf.layer!=source.dxf.layer) or (mixed and (entity.dxf.layer==source.dxf.layer or entity.dxf.layer not in profile.get('mixed_source_layers',[]))):continue
                p=entity.ocs().to_wcs(entity.dxf.start);q=entity.ocs().to_wcs(entity.dxf.end);v=(q.x-p.x,q.y-p.y);vl=math.hypot(*v)
                if vl and min(math.dist(mid,(p.x,p.y)),math.dist(mid,(q.x,q.y)))<=tol and abs(u[0]*v[0]+u[1]*v[1])/(length*vl)<=profile.get('maximum_abs_cosine',.01):witnesses.append((h,entity.dxf.layer))
            if len(witnesses)!=1:continue
            result.append({'source_line_handle':handle,'branch_line_handle':witnesses[0][0],'source_layer':source.dxf.layer,'branch_source_layer':witnesses[0][1],'tee_id':tee['node_id'],
                           'terminal_node_ids':sorted(n['node_id'] for _,n in parts),'edge_ids':sorted(e['edge_id'] for e,_ in parts),
                           'systems':sorted(set([third[0]['system']]+[e['system'] for e,_ in parts])),'mixed_source_contact':mixed,'status':'mixed_source_shape_role_pending' if mixed else 'source_shape_role_pending','hydraulic_change':False,
                           'scope':'Single native crossbar geometry only; not a blind flange, cap, T, or deletion conclusion.'})
    return result

def attach(graph,doc,profile):
    """Group source candidates on existing nodes; preserve all physical edges."""
    candidates=identify(graph,doc,profile);out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};used=set();groups=[]
    for c in candidates:
        members=[c['tee_id']]+c['terminal_node_ids']
        if len(set(members))!=3 or used.intersection(members):raise ValueError('Overlapping crossbar candidate ownership')
        used.update(members)
        group={'group_id':'SRC-CROSSBAR-'+c['source_line_handle'],'source_line_handle':c['source_line_handle'],
               'branch_line_handle':c['branch_line_handle'],'source_layer':c['source_layer'],'branch_source_layer':c['branch_source_layer'],
               'tee_id':c['tee_id'],'terminal_node_ids':c['terminal_node_ids'],'edge_ids':c['edge_ids'],'systems':c['systems'],
               'mixed_source_contact':c['mixed_source_contact'],'status':c['status'],'hydraulic_change':False,
               'scope':'Native graphical candidate only; physical role and any remote continuation remain unresolved.'}
        for nid in members:
            if 'source_crossbar_candidate' in nodes[nid]:raise ValueError('Crossbar candidate already attached')
            nodes[nid]['source_crossbar_candidate']=copy.deepcopy(group)
        groups.append(group)
    if out['edges']!=graph['edges']:raise ValueError('Crossbar grouping cannot change edges')
    out['sourceCrossbarCandidates']=groups
    return out,{'groups':len(groups),'nodes':len(used),'mixed_source_groups':sum(g['mixed_source_contact'] for g in groups),
                'edges_unchanged':True,'hydraulic_change':False}
