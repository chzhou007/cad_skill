"""Record calibrated tangent-circle source geometry without connecting systems."""
import collections,copy,math

def attach(graph,evidence,doc,source_sha256,graph_sha256,tolerance=.1):
 if not 0<tolerance<=.1 or graph.get('metadata',{}).get('source_sha256')!=source_sha256 or evidence.get('source_sha256')!=source_sha256 or evidence.get('graph_sha256')!=graph_sha256:raise ValueError('Stale source, graph or tolerance')
 records=evidence.get('records',[])
 if not records or len(records)!=evidence.get('summary',{}).get('pairs'):raise ValueError('Incomplete pair inventory')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};adj=collections.Counter(n for e in out['edges'] for n in (e['start_node_id'],e['end_node_id']));glyphs=out.setdefault('sourceTerminalGlyphs',[]);used={h for g in glyphs for h in g.get('source_handles',[])};ids={g['id'] for g in glyphs};seen=set();pairs=[]
 source_layers={doc.entitydb[v['circle']].dxf.layer for row in records for v in (row['supply'],row['return']) if doc.entitydb.get(v.get('circle')) is not None}
 source_lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in source_layers]
 for i,r in enumerate(records):
  item=[]
  for system in ('supply','return'):
   v=r.get(system,{});n=nodes.get(v.get('node_id'));e=edges.get(v.get('edge_id'));c=doc.entitydb.get(v.get('circle'));hits=v.get('line_hits_at_center',[])
   if not n or not e or n.get('node_type')!='virtual_equipment' or n.get('boundary_type')!='unresolved_source_terminal' or n.get('source_terminal_glyph_ids') or adj[n['node_id']]!=1 or n['node_id'] not in (e['start_node_id'],e['end_node_id']) or e.get('system')!=system or n.get('system')!=system:raise ValueError('Graph terminal ownership or system changed')
   if c is None or c.dxftype()!='CIRCLE' or c.dxf.owner!=doc.modelspace().block_record_handle or c.dxf.handle in used:raise ValueError('Missing, reused or nested source circle')
   center=c.ocs().to_wcs(c.dxf.center)
   if len(v.get('center',[]))!=2 or math.dist((center.x,center.y),v['center'])>tolerance or math.dist((n['x'],n['y']),(center.x,center.y))>tolerance:raise ValueError('Source circle center or node changed')
   if len(hits)!=1 or hits[0]['handle'] not in e.get('source_handles',[]) or hits[0].get('center_location')!='endpoint':raise ValueError('Missing unique incident line witness')
   line=doc.entitydb.get(hits[0]['handle'])
   if line is None or line.dxftype()!='LINE' or line.dxf.layer!=c.dxf.layer or min(math.hypot(p.x-center.x,p.y-center.y) for p in (line.dxf.start,line.dxf.end))>tolerance:raise ValueError('Native endpoint or layer changed')
   incident=[]
   for candidate in source_lines:
    a,b=candidate.dxf.start,candidate.dxf.end;dx,dy=b.x-a.x,b.y-a.y;den=dx*dx+dy*dy
    if not den:continue
    t=max(0,min(1,((center.x-a.x)*dx+(center.y-a.y)*dy)/den))
    if math.hypot(center.x-a.x-t*dx,center.y-a.y-t*dy)<=tolerance:incident.append(candidate.dxf.handle)
   if incident!=[line.dxf.handle]:raise ValueError('Competing native line contacts')
   gid='TANGENT-CIRCLE-'+c.dxf.handle
   if gid in ids or n['node_id'] in seen:raise ValueError('Duplicate glyph or terminal')
   item.append((n,e,c,center,gid));used.add(c.dxf.handle);ids.add(gid);seen.add(n['node_id'])
  u,v=item;distance=math.hypot(u[3].x-v[3].x,u[3].y-v[3].y)
  if u[0]['floor']!=v[0]['floor'] or abs(distance-u[2].dxf.radius-v[2].dxf.radius)>tolerance or abs(distance-r['circle_tangent_distance'])>tolerance:raise ValueError('Circle pair geometry or floor changed')
  pair_id='TANGENT-PAIR-'+u[2].dxf.handle+'-'+v[2].dxf.handle
  for current,other in ((u,v),(v,u)):
   n,e,c,center,gid=current
   n['source_terminal_glyph_ids']=[gid];n['source_tangent_circle_candidate']={'pair_id':pair_id,'source_circle_handle':c.dxf.handle,'source_line_handle':r[current[1]['system']]['line_hits_at_center'][0]['handle'],'paired_circle_handle':other[2].dxf.handle,'paired_node_id':other[0]['node_id'],'source_sha256':source_sha256,'source_graph_sha256':graph_sha256,'status':'source_shape_only_no_hydraulic_connection'}
   glyphs.append({'id':gid,'kind':'native_tangent_circle_candidate','source_handles':[c.dxf.handle],'node_id':n['node_id'],'edge_id':e['edge_id'],'floor':n['floor'],'system':e['system'],'remote_continuation_confirmed':False})
  pairs.append({'id':pair_id,'supply_node_id':u[0]['node_id'],'return_node_id':v[0]['node_id'],'source_circle_handles':[u[2].dxf.handle,v[2].dxf.handle],'status':'source_shape_only_no_hydraulic_connection'})
 out['sourceTangentCircleCandidates']=pairs;out['metadata']['hil_ready']=False
 return out,{'pairs':len(pairs),'source_glyphs':len(seen),'edges_unchanged':out['edges']==graph['edges'],'physical_connections_added':0,'remote_continuations_confirmed':0}
