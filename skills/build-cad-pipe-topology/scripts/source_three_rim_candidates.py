"""Identify native three-rim pipe candidates, without changing connectivity."""
import collections,math

def with_prior_floor(nodes,prior_nodes,position_tolerance=1e-6):
    """Use a source-backed prior floor only for the same unchanged native node."""
    previous={n['node_id']:n for n in prior_nodes};result=[]
    for node in nodes:
        candidate=dict(node);old=previous.get(node['node_id'])
        if old and old.get('floor_semantics') and math.dist((old['x'],old['y']),(node['x'],node['y']))<=position_tolerance:
            candidate['floor']=old['floor']
        result.append(candidate)
    return result

def identify_in_doc(doc,graph,profile):
    if not profile.get('readability_verified') or not profile.get('calibration_evidence'):
        raise ValueError('Readable source calibration required for three-rim candidate inventory')
    tolerance=profile['contact_tolerance'];layers=set(profile['pipe_layers']);radii=profile['radii']
    circles=[]
    for e in doc.modelspace().query('CIRCLE'):
        if tuple(e.dxf.extrusion)!=(0.,0.,1.) or e.dxf.layer not in layers or not any(abs(e.dxf.radius-r)<=tolerance for r in radii):continue
        c=e.ocs().to_wcs(e.dxf.center)
        circles.append({'handle':e.dxf.handle,'x':c.x,'y':c.y,'r':e.dxf.radius,'layer':e.dxf.layer})
    edge_layers={}
    for e in graph['edges']:
        parts=[doc.entitydb.get(h)for h in e.get('source_handles',[])]
        edge_layers[e['edge_id']]=[p.dxf.layer for p in parts] if parts and all(p is not None for p in parts) else ['_unresolved_native_handle']
    return identify(graph,circles,edge_layers,tolerance,profile.get('angle_tolerance_degrees',2))

def identify(graph,circles,edge_layers,tolerance=.1,angle_tolerance=2):
    if tolerance<=0 or angle_tolerance<=0:raise ValueError('Invalid source calibration')
    nodes={n['node_id']:n for n in graph['nodes']};adj=collections.defaultdict(list)
    for e in graph['edges']:
        for node_id in (e['start_node_id'],e['end_node_id']):adj[node_id].append(e)
    rows=[]
    for circle in circles:
        c=(circle['x'],circle['y']);r=circle['r'];contacts=[];excluded=[]
        if r<=tolerance:continue
        for n in graph['nodes']:
            nid=n['node_id'];distance=math.dist((n['x'],n['y']),c)
            if abs(distance-r)>tolerance or len(adj[nid])!=1:continue
            edge=adj[nid][0]
            if set(edge_layers.get(edge['edge_id'],[]))!={circle['layer']}:
                excluded.append(nid);continue
            if n['node_type']!='virtual_equipment' or n.get('interface_destination'):continue
            path=edge['path_points'] if edge['start_node_id']==nid else list(reversed(edge['path_points']))
            if len(path)<2 or math.dist(path[0],(n['x'],n['y']))>tolerance:continue
            radial=((n['x']-c[0])/distance,(n['y']-c[1])/distance)
            other=next((p for p in path[1:] if math.dist(p,path[0])>tolerance),None)
            if other is None:continue
            length=math.dist(other,path[0]);ray=((other[0]-path[0][0])/length,(other[1]-path[0][1])/length)
            if sum(a*b for a,b in zip(radial,ray))<math.cos(math.radians(angle_tolerance)):continue
            contacts.append({'node_id':nid,'edge_id':edge['edge_id'],'system':edge['system'],'floor':n['floor'],'radial':radial})
        if len(contacts)!=3 or len({p['edge_id'] for p in contacts})!=3:continue
        if len({p['system'] for p in contacts})!=1 or len({str(p['floor'])for p in contacts})!=1:continue
        angles=sorted(math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(p['radial'],q['radial'])))))) for i,p in enumerate(contacts)for q in contacts[i+1:])
        if any(abs(x-y)>angle_tolerance for x,y in zip(angles,(90,90,180))):continue
        rows.append({'circle_handle':circle['handle'],'circle_layer':circle['layer'],'radius':r,'center':list(c),'contacts':contacts,'angles_degrees':angles,'excluded_other_layer_nodes':sorted(set(excluded)),
                     'status':'algorithm_candidate_not_connected','reason':'Three distinct same-layer outward source rays touch one circle; interior semantics require independent confirmation.'})
    return rows
