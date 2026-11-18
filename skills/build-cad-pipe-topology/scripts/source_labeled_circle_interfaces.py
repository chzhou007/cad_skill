"""Classify paired interfaces linked by native notes and same-service circle marks."""
import copy,math

def verts(e):
 if e.dxftype()=='LINE':return [e.ocs().to_wcs(e.dxf.start),e.ocs().to_wcs(e.dxf.end)]
 if e.dxftype()=='LWPOLYLINE' and not e.closed and not any(abs(float(v[4]))>1e-12 for v in e.get_points('xyseb')):return list(e.vertices_in_wcs())
 raise ValueError('Unsupported annotation leader')
def attach(graph,doc,source_sha256,records):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256:raise ValueError('Source identity mismatch')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges=out['edges'];seen=set();links=[]
 for r in records:
  n=nodes.get(r['local_node_id'],{});m=nodes.get(r['target_node_id'],{});t=doc.entitydb.get(r['local_text_handle']);nt=doc.entitydb.get(r['target_note_handle']);lead=doc.entitydb.get(r['local_leader_handle']);remote=doc.entitydb.get(r['target_leader_handle']);circle=doc.entitydb.get(r['circle_handle']);system=r['system'];label=r['label']
  if any(x.get('boundary_type')!='unresolved_source_terminal' or x.get('system')!=system or x.get('node_id') in seen for x in (n,m)) or n.get('floor')!=m.get('floor'):raise ValueError('Endpoint, floor or service mismatch')
  if not all((t,nt,lead,remote,circle)) or t.dxftype()!='TEXT' or nt.dxftype()!='TEXT' or circle.dxftype()!='CIRCLE' or t.plain_text()!=label or nt.plain_text()!='接至'+label:raise ValueError('Source text or circle mismatch')
  model=doc.modelspace().block_record_handle
  if any(x.dxf.owner!=model for x in (t,nt,lead,remote,circle)):raise ValueError('Source not in modelspace')
  a=verts(lead);b=verts(remote);tp=t.ocs().to_wcs(t.dxf.insert);np=nt.ocs().to_wcs(nt.dxf.insert);center=circle.ocs().to_wcs(circle.dxf.center);xy=(n['x'],n['y']);target=(m['x'],m['y'])
  localtol=float(r.get('local_text_anchor_tolerance',20));centertol=float(r.get('target_center_tolerance',.01))
  if localtol>50 or centertol>20 or min(localtol,centertol)<0 or ((localtol>20 or centertol>.01) and not r.get('local_calibration_evidence')):raise ValueError('Missing or excessive local calibration')
  if min(math.dist(xy,(v.x,v.y)) for v in (a[0],a[-1]))>.01 or min(math.dist((tp.x,tp.y),(v.x,v.y)) for v in a)>localtol:raise ValueError('Local leader does not prove label')
  if min(math.dist((center.x,center.y),(v.x,v.y)) for v in (b[0],b[-1]))>centertol or min(math.dist((np.x,np.y),(v.x,v.y)) for v in b)>20:raise ValueError('Target leader does not prove circle')
  tip=min((b[0],b[-1]),key=lambda v:math.dist((center.x,center.y),(v.x,v.y)))
  nearby=[x for x in doc.modelspace().query('CIRCLE') if x.dxf.layer==circle.dxf.layer and math.dist((x.dxf.center.x,x.dxf.center.y),(tip.x,tip.y))<=centertol]
  if len(nearby)!=1 or nearby[0].dxf.handle!=circle.dxf.handle:raise ValueError('Target circle is not unique')
  if abs(math.dist(target,(center.x,center.y))-circle.dxf.radius)>.01:raise ValueError('Target does not touch circle rim')
  rim=[x['node_id'] for x in out['nodes'] if abs(math.dist((x['x'],x['y']),(center.x,center.y))-circle.dxf.radius)<.01]
  if rim!=[m['node_id']]:raise ValueError('Circle rim target is not unique')
  for node in (n,m):
   inc=[e for e in edges if node['node_id'] in (e['start_node_id'],e['end_node_id'])]
   if len(inc)!=1 or inc[0]['system']!=system:raise ValueError('Ambiguous endpoint graph edge')
   pipehits=[]
   for h in inc[0].get('source_handles',[]):
    e=doc.entitydb.get(h)
    if e and e.dxftype()=='LINE' and e.dxf.layer==circle.dxf.layer:
     p=e.ocs().to_wcs(e.dxf.start);q=e.ocs().to_wcs(e.dxf.end)
     if min(math.dist((node['x'],node['y']),(v.x,v.y)) for v in (p,q))<.01:pipehits.append(h)
   if len(pipehits)!=1:raise ValueError('No unique same-layer source pipe endpoint')
  link={'link_id':'SOURCE-DECLARED-'+label+'-'+system,'label':label,'system':system,'endpoint_node_id':n['node_id'],'target_node_id':m['node_id'],'source_note':nt.plain_text(),'source_note_handle':r['target_note_handle'],'local_label_handle':r['local_text_handle'],'source_leader_handle':r['target_leader_handle'],'local_leader_handle':r['local_leader_handle'],'target_circle_handle':r['circle_handle'],'target_circle_center':[center.x,center.y],'target_circle_radius':circle.dxf.radius,'target_leader_center_offset':math.dist((center.x,center.y),(tip.x,tip.y)),'local_text_anchor_offset':min(math.dist((tp.x,tp.y),(v.x,v.y)) for v in a),'local_calibration_evidence':r.get('local_calibration_evidence'),'kind':'source_declared_connection','physical_route_verified':False,'physical_length':None,'hydraulic_edge_created':False}
  for role,node in [('local',n),('target',m)]:
   node['previous_boundary_type']=node['boundary_type'];node['boundary_type']='source_declared_connection_interface';node['subtype']='source_declared_connection_interface';node['label']=label+' · '+system;node['resolution_state']='source_declared_connection_route_pending';node['source_declared_connection']=copy.deepcopy(link);node['source_declared_connection']['interface_role']=role;seen.add(node['node_id'])
  links.append(link)
 if out['edges']!=graph['edges']:raise ValueError('Physical edges changed')
 out.setdefault('sourceDeclaredConnections',[]).extend(links)
 return out,{'classified_interfaces':len(seen),'new_source_declared_links':len(links),'physical_edges_created':0,'unverified_routes':len(links)}
