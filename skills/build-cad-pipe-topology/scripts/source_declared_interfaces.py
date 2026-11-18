"""Classify explicit source-named connection interfaces without creating pipe edges."""
import copy,math

def _distance(p,a,b):
 dx=b[0]-a[0];dy=b[1]-a[1];ll=dx*dx+dy*dy;t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/ll)) if ll else 0
 return math.dist(p,(a[0]+t*dx,a[1]+t*dy))
def _vertices(e):
 if e.dxftype()=='LINE':return [e.ocs().to_wcs(e.dxf.start),e.ocs().to_wcs(e.dxf.end)]
 if e.dxftype()=='LWPOLYLINE' and not e.closed and not any(abs(float(v[4]))>1e-12 for v in e.get_points('xyseb')):return list(e.vertices_in_wcs())
 raise ValueError('Unsupported source leader')
def attach(graph,doc,source_sha256):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256:raise ValueError('Source identity mismatch')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};seen=set();links=[]
 for group in out.get('sourceLabeledEquipmentGroups',[]):
  label=group['label'];eq=nodes.get(group['equipment_id'],{})
  if eq.get('node_type')!='equipment' or group.get('hydraulic_connection_confirmed') is not False:raise ValueError('Invalid source group')
  for system in ('supply','return'):
   s=group['services'][system];n=nodes.get(s['endpoint_node_id'],{});r=n.get('source_annotation_reference',{});a=n.get('source_endpoint_annotation',{});edge=edges.get(s['annotated_target_edge_id'],{});source=doc.entitydb.get(r.get('source_pipe_handle'));leader=doc.entitydb.get(r.get('leader_handle'));note=doc.entitydb.get(r.get('text_handle'));localtext=doc.entitydb.get(a.get('text_handle'));localleader=doc.entitydb.get(a.get('leader_handle'))
   if n.get('node_id') in seen or n.get('boundary_type')!='unresolved_source_terminal' or n.get('system')!=system or r.get('system')!=system or r.get('label')!=label or a.get('text')!=label or r.get('target_edge_id')!=edge.get('edge_id') or edge.get('system')!=system:raise ValueError('Endpoint or target mismatch')
   if not all((source,leader,note,localtext,localleader)) or source.dxftype()!='LINE' or note.dxftype()!='TEXT' or localtext.dxftype()!='TEXT' or note.plain_text()!='接至'+label or localtext.plain_text()!=label:raise ValueError('Source note or geometry mismatch')
   pt=r['point'];v=_vertices(leader);lv=_vertices(localleader);ins=note.ocs().to_wcs(note.dxf.insert);lins=localtext.ocs().to_wcs(localtext.dxf.insert)
   if min(math.dist(pt,(x.x,x.y)) for x in (v[0],v[-1]))>.01 or min(math.dist((ins.x,ins.y),(x.x,x.y)) for x in v)>20:raise ValueError('Target leader changed')
   if min(math.dist((n['x'],n['y']),(x.x,x.y)) for x in (lv[0],lv[-1]))>.01 or min(math.dist((lins.x,lins.y),(x.x,x.y)) for x in lv)>20:raise ValueError('Endpoint leader changed')
   aa=source.ocs().to_wcs(source.dxf.start);bb=source.ocs().to_wcs(source.dxf.end)
   if r['source_pipe_handle'] not in edge.get('source_handles',[]) or _distance(pt,(aa.x,aa.y),(bb.x,bb.y))>.01 or not any(_distance(pt,x,y)<.01 for path in edge.get('attribute_paths',[]) for x,y in zip(path,path[1:])):raise ValueError('Target path no longer matches')
   link={'link_id':'SOURCE-DECLARED-'+label+'-'+system,'label':label,'system':system,'endpoint_node_id':n['node_id'],'equipment_id':group['equipment_id'],'equipment_port_id':s['equipment_port_id'],'target_edge_id':edge['edge_id'],'target_point':pt,'source_note':note.plain_text(),'source_note_handle':r['text_handle'],'local_label_handle':a['text_handle'],'source_leader_handle':r['leader_handle'],'source_pipe_handle':r['source_pipe_handle'],'kind':'source_declared_connection','physical_route_verified':False,'physical_length':None,'hydraulic_edge_created':False}
   n['previous_boundary_type']=n['boundary_type'];n['boundary_type']='source_declared_connection_interface';n['subtype']='source_declared_connection_interface';n['label']=label+' · '+system;n['resolution_state']='source_declared_connection_route_pending';n['source_declared_connection']=copy.deepcopy(link);links.append(link);seen.add(n['node_id'])
 if out['edges']!=graph['edges']:raise ValueError('Physical edges changed')
 out['sourceDeclaredConnections']=links
 return out,{'source_declared_links':len(links),'classified_interfaces':len(seen),'physical_edges_created':0,'unverified_routes':len(links)}
