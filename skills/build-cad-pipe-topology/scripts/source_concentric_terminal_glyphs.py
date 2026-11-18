"""Retain source concentric terminal graphics without inferring an interface."""
import collections,copy,math

def reconcile(graph,evidence,source_sha256,graph_sha256,doc,tolerance=.5):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256 or evidence.get('source_sha256')!=source_sha256 or evidence.get('graph_sha256')!=graph_sha256:raise ValueError('Stale source or graph evidence')
 rows=evidence.get('records',[])
 if not rows or len(rows)!=evidence.get('assemblies_examined') or not 0<tolerance<=.5:raise ValueError('Incomplete or uncalibrated concentric inventory')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};adj=collections.Counter(n for e in out['edges'] for n in (e['start_node_id'],e['end_node_id']))
 glyphs=out.setdefault('sourceTerminalGlyphs',[]);used={h for x in glyphs for h in x.get('source_handles',[])};ids={x['id'] for x in glyphs};seen=set();lines=collections.defaultdict(list)
 for line in doc.modelspace().query('LINE'):lines[line.dxf.layer].append(line)
 for r in rows:
  node=nodes.get(r.get('node_id'));edge=edges.get(r.get('edge_id'));rings=r.get('rings',[]);center=r.get('center',[])
  if not node or node.get('node_type')!='virtual_equipment' or node.get('boundary_type')!='unresolved_source_terminal' or node.get('source_terminal_glyph_ids') or adj[node['node_id']]!=1 or not edge or node['node_id'] not in (edge['start_node_id'],edge['end_node_id']) or edge['system']!=r.get('system') or str(node['floor'])!=str(r.get('floor')):raise ValueError('Terminal graph ownership changed')
  if len(center)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in center) or len(rings)!=2:raise ValueError('Invalid native concentric witness')
  handles=[x.get('handle') for x in rings];circles=[doc.entitydb.get(h) for h in handles]
  if len(set(handles))!=2 or any(h in used for h in handles) or any(c is None or not c.is_alive or c.dxftype()!='CIRCLE' or c.dxf.owner!=doc.modelspace().block_record_handle for c in circles):raise ValueError('Conflicting or missing source circles')
  layer=circles[0].dxf.layer
  if any(c.dxf.layer!=layer or math.dist((c.dxf.center.x,c.dxf.center.y),center)>tolerance or abs(c.dxf.radius-ring['radius'])>1e-6 for c,ring in zip(circles,rings)) or abs(circles[0].dxf.radius-circles[1].dxf.radius)<tolerance:raise ValueError('Concentric source shape changed')
  matching=[]
  for line in lines[layer]:
   for side,p in [('start',line.dxf.start),('end',line.dxf.end)]:
    dist=math.hypot(p.x-center[0],p.y-center[1])
    if any(abs(dist-c.dxf.radius)<=tolerance for c in circles):matching.append((line.dxf.handle,side,p.x,p.y))
  if len(matching)!=1 or len(r.get('native_contacts',[]))!=1:raise ValueError('Competing native circle contacts')
  line,side,x,y=matching[0];witness=r['native_contacts'][0]
  if line!=witness.get('line_handle') or side!=witness.get('side') or line not in edge.get('source_handles',[]) or math.dist((x,y),(node['x'],node['y']))>tolerance:raise ValueError('Native line or terminal witness changed')
  gid='CONCENTRIC-'+node['node_id']
  if gid in ids or node['node_id'] in seen:raise ValueError('Duplicate terminal source ownership')
  item={'id':gid,'kind':'native_concentric_circle_candidate','source_handles':handles,'node_id':node['node_id'],'edge_id':edge['edge_id'],'floor':node['floor'],'system':edge['system'],'remote_continuation_confirmed':False}
  node['source_terminal_glyph_ids']=[gid];node['source_concentric_candidate']={'source_circle_handles':handles,'source_line_handle':line,'center':list(center),'radii':[c.dxf.radius for c in circles],'source_sha256':source_sha256,'source_graph_sha256':graph_sha256,'status':'native_shape_recorded_semantics_pending'}
  glyphs.append(item);used.update(handles);ids.add(gid);seen.add(node['node_id'])
 out['metadata']['hil_ready']=False;out['metadata']['stage_status']='concentric_terminal_meaning_pending'
 return out,{'glyphs_added':len(seen),'native_circles_preserved':2*len(seen),'edges_unchanged':out['edges']==graph['edges'],'nodes_added':0,'edges_added':0,'scope':'Local source graphics only; engineering type, vertical direction and remote hydraulic connectivity remain pending.'}
