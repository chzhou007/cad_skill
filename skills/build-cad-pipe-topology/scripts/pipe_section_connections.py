"""Connect source-calibrated pipe section circles; preserve native paths and IDs."""
import copy,collections,math

def distance(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
def point(n):return [n['x'],n['y']]
def oriented(edge,start):return edge['path_points']if edge['start_node_id']==start else edge['path_points'][::-1]
def opposite(edge,nid):return edge['end_node_id']if edge['start_node_id']==nid else edge['start_node_id']
def first_ray(path,tol):
    for q in path[1:]:
        length=distance(path[0],q)
        if length>tol:return [(q[i]-path[0][i])/length for i in (0,1)],length
    return [0,0],0
def remap_id(value,mapping):
    visited=set()
    while value in mapping and value not in visited:visited.add(value);value=mapping[value]
    return value

def apply_to_doc(doc,graph,profile,prior=None):
    circles=[]
    for e in doc.modelspace().query('CIRCLE'):
        if tuple(e.dxf.extrusion)!=(0.,0.,1.):continue
        c=e.ocs().to_wcs(e.dxf.center)
        circles.append({'handle':e.dxf.handle,'layer':e.dxf.layer,'x':c.x,'y':c.y,'r':e.dxf.radius})
    layers={}
    for e in graph['edges']:
        parts=[doc.entitydb.get(h)for h in e.get('source_handles',[])]
        layers[e['edge_id']]=[p.dxf.layer for p in parts]if all(p is not None for p in parts)else['_unresolved_native_handle']
    result,audit=reconnect(graph,circles,layers,profile)
    # Reconstructed edge signatures are compared AFTER section continuity.
    # Raw temporary endpoints must not cause stable final IDs to drift.
    def signature(e):return tuple(sorted([e['start_node_id'],e['end_node_id']])),tuple(sorted(set(e['source_handles'])))
    previous={signature(e):e['edge_id']for e in(prior or {}).get('edges',[])}
    renames={e['edge_id']:previous[signature(e)]for e in result['edges']if signature(e)in previous}
    wanted=[renames.get(e['edge_id'],e['edge_id'])for e in result['edges']]
    if len(set(wanted))!=len(wanted):raise ValueError('Stable edge reconciliation collision')
    for e in result['edges']:e['edge_id']=renames.get(e['edge_id'],e['edge_id'])
    for c in audit['connections']:
        if c.get('retained_edge_id'):c['retained_edge_id']=renames.get(c['retained_edge_id'],c['retained_edge_id'])
    for record in audit['retired_nodes'].values():record['edge_id']=renames.get(record['edge_id'],record['edge_id'])
    audit['stable_edge_reconciliation']=renames
    audit['edge_id_mapping']={k:renames.get(v,v)for k,v in audit['edge_id_mapping'].items()}
    return result,audit

def reconnect(graph,circles,edge_source_layers,profile):
    if not profile.get('calibration_evidence')or not profile.get('readability_verified'):
        raise ValueError('Readable native source calibration is required before pipe section trials')
    g=copy.deepcopy(graph);nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']}
    layers={k:set(v)for k,v in edge_source_layers.items()};tol=profile['contact_tolerance'];audit=[];edge_map={};retired_nodes={}
    eligible=[c for c in circles if c['layer']in profile['pipe_layers']and any(abs(c['r']-r)<=tol for r in profile['radii'])]
    for circle in eligible:
        center=[circle['x'],circle['y']];radius=circle['r'];adj=collections.defaultdict(list)
        for e in edges.values():
            for nid in[e['start_node_id'],e['end_node_id']]:adj[nid].append(e)
        center_nodes=[];rim_nodes=[];excluded_contacts=[]
        for n in nodes.values():
            if len(adj[n['node_id']])!=1:continue
            e=adj[n['node_id']][0];delta=distance(point(n),center)
            if delta>radius+tol:continue
            if layers.get(e['edge_id'])!={circle['layer']}:
                if delta<=tol or abs(delta-radius)<=tol:excluded_contacts.append(n['node_id'])
                continue
            if n.get('node_type')!='virtual_equipment':continue
            if delta<=tol:center_nodes.append(n)
            elif abs(delta-radius)<=tol:rim_nodes.append(n)
        if not center_nodes or not rim_nodes:continue
        row={'circle_handle':circle['handle'],'source_layer':circle['layer'],'radius':radius,'excluded_other_layer_contacts':excluded_contacts,'status':'pending'}
        if len(center_nodes)!=1 or len(rim_nodes)!=1:
            audit.append(dict(row,reason='competing same-source contacts'));continue
        u,v=center_nodes[0],rim_nodes[0];eu,ev=adj[u['node_id']][0],adj[v['node_id']][0]
        if eu is ev or eu['system']!=ev['system']or u.get('floor')!=v.get('floor'):
            audit.append(dict(row,reason='same edge, conflicting service or floor'));continue
        if u.get('interface_destination')or v.get('interface_destination'):
            audit.append(dict(row,reason='explicit interface identity protected'));continue
        pu,pv=oriented(eu,u['node_id']),oriented(ev,v['node_id']);ru,lu=first_ray(pu,tol);rv,lv=first_ray(pv,tol)
        radial=[(point(v)[i]-center[i])/radius for i in (0,1)]
        if lu<=radius+tol or sum(radial[i]*rv[i]for i in (0,1))<.999:
            audit.append(dict(row,reason='no external main witness or rim tail points into circle'));continue
        angle=math.degrees(math.acos(max(-1,min(1,sum(ru[i]*rv[i]for i in(0,1))))))
        if not any(abs(angle-a)<=profile['angle_tolerance_degrees']for a in profile['angles_degrees']):
            audit.append(dict(row,reason='uncalibrated contact angle'));continue
        dn={e.get('diameter_nominal_mm')for e in[eu,ev]}-{None}
        if len(dn)>1:audit.append(dict(row,reason='diameter conflict'));continue
        anchor,other=(eu,ev)if eu['path_length']>=ev['path_length']else(ev,eu)
        nu,nv=(u,v)if anchor is eu else(v,u)
        a,b=opposite(anchor,nu['node_id']),opposite(other,nv['node_id'])
        if a==b:audit.append(dict(row,reason='self-loop requires explicit schema support'));continue
        merged=copy.deepcopy(anchor);p1=oriented(anchor,a);p2=oriented(other,nv['node_id']);path=p1+p2
        merged.update(start_node_id=a,end_node_id=b,path_points=path,
                      attribute_paths=copy.deepcopy(anchor['attribute_paths']+other['attribute_paths']),
                      source_handles=sorted(set(anchor['source_handles']+other['source_handles'])),
                      source_systems=sorted(set(anchor.get('source_systems',[])+other.get('source_systems',[]))),
                      path_length=sum(distance(x,y)for x,y in zip(path,path[1:])),
                      connection_mode='source_calibrated_pipe_section_continuity',
                      path_length_is_physical=False,
                      source_connector_handles=sorted(set(anchor.get('source_connector_handles',[])+other.get('source_connector_handles',[])+[circle['handle']])))
        merged['source_path_length']=anchor.get('source_path_length',anchor['path_length'])+other.get('source_path_length',other['path_length'])
        merged['semantic_bridge_drawing_length']=anchor.get('semantic_bridge_drawing_length',0)+other.get('semantic_bridge_drawing_length',0)+distance(point(u),point(v))
        merged['length_scope']='Projected source route plus explicit section connector; neither section radius nor terminal strokes certify installed length'
        merged['normalizations']=sorted(set(anchor.get('normalizations',[])+other.get('normalizations',[])+['native_pipe_section_circle']))
        if not merged.get('diameter_nominal_mm')and other.get('diameter_nominal_mm'):
            for k in['pipe_diameter','diameter_nominal_mm','diameter_text','diameter_status']:
                if k in other:merged[k]=copy.deepcopy(other[k])
        inv=collections.defaultdict(list)
        for e in[anchor,other]:
            for item in e.get('equipment_inventory',[]):inv[item['equipment_type']]+=item['device_names']
        merged['equipment_inventory']=[{'equipment_type':k,'count':len(names),'device_names':names}for k,names in inv.items()]
        for key,nid in [('start_port_id',a),('end_port_id',b)]:
            merged.pop(key,None)
            if nodes[nid].get('node_type')=='virtual_equipment':
                if len(nodes[nid].get('ports',[]))!=1:raise ValueError('Ambiguous retained virtual port')
                merged[key]=nodes[nid]['ports'][0]['port_id']
        merged['floor_start']=nodes[a]['floor'];merged['floor_end']=nodes[b]['floor']
        merged['edge_type']='tee_to_virtual_equipment'if any(nodes[n]['node_type']=='virtual_equipment'for n in[a,b])else'tee_to_tee'
        # A short native terminal tail is preserved in attribute_paths; it is not
        # silently erased or certified as installed pipe length.
        rim_outer=opposite(ev,v['node_id'])
        if ev['path_length']<=profile['short_tail_max_length']and nodes[rim_outer]['node_type']=='virtual_equipment':
            n=nodes[rim_outer]
            if n['node_id']not in [u['node_id'],v['node_id']]and not n.get('interface_destination'):
                n.update(boundary_type='source_pipe_section_terminal',subtype='native_pipe_section_interface',
                         label='管道圆截面接口（远端待关联）',interface_kind_zh='原图管道圆截面与端线接口',
                         resolution_state='local_continuity_proven_remote_identity_pending',review_queue='identity_completion',
                         relative_elevation='unverified')
                n.setdefault('source_connector_handles',[]).append(circle['handle'])
        edge_map[other['edge_id']]=anchor['edge_id'];layers[anchor['edge_id']]|=layers[other['edge_id']]
        for n in[u,v]:retired_nodes[n['node_id']]={'reason':'source pipe section connector is an edge interior','edge_id':anchor['edge_id']};del nodes[n['node_id']]
        edges[anchor['edge_id']]=merged;del edges[other['edge_id']]
        audit.append(dict(row,status='applied',reason='unique same-layer center/rim incidence with external main and radial tail',
                          source_node_ids=[u['node_id'],v['node_id']],source_edge_ids=[eu['edge_id'],ev['edge_id']],
                          retained_edge_id=anchor['edge_id'],retired_edge_id=other['edge_id'],contact_angle=angle,
                          source_paths_preserved=True,relative_elevation='unverified'))
    g['nodes']=list(nodes.values());g['edges']=list(edges.values())
    final_map={k:remap_id(v,edge_map)for k,v in edge_map.items()}
    for row in audit:
        if row['status']=='applied':row['retained_edge_id']=remap_id(row['retained_edge_id'],edge_map)
    for v in retired_nodes.values():v['edge_id']=remap_id(v['edge_id'],edge_map)
    g.setdefault('metadata',{})['pipe_section_reconstruction']={'applied':sum(r['status']=='applied'for r in audit),'profile':profile['id'],'relative_elevation':'unverified','fabricated_equipment':0}
    return g,{'connections':audit,'edge_id_mapping':final_map,'retired_nodes':retired_nodes,'calibration_evidence':profile['calibration_evidence']}
