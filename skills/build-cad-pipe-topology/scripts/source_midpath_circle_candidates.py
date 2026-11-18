"""Retain audited source circles on existing pipe edges without inferring branches."""
import copy, math

def attach(graph,evidence,source_sha256,graph_sha256,source_doc):
 if graph.get('metadata',{}).get('source_sha256')!=source_sha256 or evidence.get('source_sha256')!=source_sha256 or evidence.get('graph_sha256')!=graph_sha256:raise ValueError('Stale source or graph witness')
 rows=evidence.get('records',[])
 if len(rows)!=evidence.get('circles_examined') or not rows:raise ValueError('Incomplete circle witness')
 out=copy.deepcopy(graph);edges={e['edge_id']:e for e in out['edges']};nodes={n['node_id']:n for n in out['nodes']};seen_circles=set();seen_edges=set()
 for row in rows:
  edge=edges.get(row.get('edge_id'));tower=nodes.get(row.get('tower_id'));h=row.get('circle_handle');line=row.get('closest_line_handle')
  if not edge or edge.get('system')!='cooling_return' or not tower or tower.get('node_type')!='equipment' or tower.get('source_internal_path_candidate',{}).get('edge_id')!=edge['edge_id'] or line not in edge.get('source_handles',[]):raise ValueError('Source path or ownership candidate changed')
  if not h or h in seen_circles or edge['edge_id'] in seen_edges or edge.get('source_midpath_symbol_candidates'):raise ValueError('Duplicate source circle or edge')
  center=row.get('center');radius=row.get('radius');fraction=row.get('fraction');distance=row.get('center_distance')
  if not isinstance(center,(tuple,list)) or len(center)!=2 or not all(isinstance(v,(float,int)) and math.isfinite(v) for v in center) or not isinstance(radius,(int,float)) or not math.isfinite(radius) or radius<=0 or not isinstance(fraction,(int,float)) or not 0<fraction<1 or not isinstance(distance,(int,float)) or not 0<=distance<=.5:raise ValueError('Invalid circle geometry witness')
  circle=source_doc.entitydb.get(h);native_line=source_doc.entitydb.get(line)
  if not circle or not native_line or not circle.is_alive or not native_line.is_alive or circle.dxftype()!='CIRCLE' or native_line.dxftype()!='LINE':raise ValueError('Native circle or line missing')
  if circle.dxf.owner!=source_doc.modelspace().block_record_handle or native_line.dxf.owner!=source_doc.modelspace().block_record_handle or circle.dxf.layer!='HVAC-D-CWR' or native_line.dxf.layer!=circle.dxf.layer:raise ValueError('Native ownership or layer changed')
  if math.dist((circle.dxf.center.x,circle.dxf.center.y),center)>1e-7 or abs(circle.dxf.radius-radius)>1e-7:raise ValueError('Native circle geometry changed')
  a=native_line.dxf.start;b=native_line.dxf.end;dx=b.x-a.x;dy=b.y-a.y;length_sq=dx*dx+dy*dy
  if not length_sq:raise ValueError('Native line has zero length')
  actual_fraction=((center[0]-a.x)*dx+(center[1]-a.y)*dy)/length_sq
  if not 0<actual_fraction<1 or abs(actual_fraction-fraction)>1e-7:raise ValueError('Native line projection changed')
  actual_distance=math.dist(center,(a.x+actual_fraction*dx,a.y+actual_fraction*dy))
  if actual_distance>.5 or abs(actual_distance-distance)>1e-6:raise ValueError('Native line contact changed')
  edge['source_midpath_symbol_candidates']=[{'source_circle_handle':h,'source_line_handle':line,'center':list(center),'radius':radius,'source_sha256':source_sha256,'source_graph_sha256':graph_sha256,'status':'circle_on_pipe_interpretation_pending','symbol_type':'unclassified','tower_candidate_id':tower['node_id'],'scope':'Native circle centered on existing pipe; no vertical branch, direction, or connectivity inferred.'}]
  seen_circles.add(h);seen_edges.add(edge['edge_id'])
 out['metadata']['hil_ready']=False
 out['metadata']['stage_status']='midpath_circle_source_semantics_pending'
 out.setdefault('technicalPending',[]).append({'id':'ROOF-CWR-MIDPATH-CIRCLES','kind':'algorithm_interpretation','reason':'Native circles centered on existing return paths require symbol and potential vertical-interface reconciliation.'})
 return out,{'circle_candidates':len(seen_circles),'edges_annotated':len(seen_edges),'nodes_unchanged':out['nodes']==graph['nodes'],'new_nodes':0,'new_edges':0,'source_sha256':source_sha256,'source_graph_sha256':graph_sha256}
