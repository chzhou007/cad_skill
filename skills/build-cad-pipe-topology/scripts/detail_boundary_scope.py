"""Source-backed non-node boundary inventory and tentative ordered detail candidates."""
import argparse,hashlib,json,math,statistics
from pathlib import Path
from source_readability import read_source

def analyze(doc,graph,scope,policy,source_hash,graph_hash):
 if graph.get('metadata',{}).get('source_sha256')!=source_hash or any(v.get('source_sha256')!=source_hash or v.get('graph_sha256')!=graph_hash for v in (scope,policy)):raise ValueError('stale source or graph')
 if scope.get('status')!='scoped_coverage_not_mapping' or scope.get('mapping_ready') is not False:raise ValueError('unsupported scope state')
 region=scope['regions']['detail'];anchors=[];system_layers=policy['system_layers'];tol=float(policy['source_endpoint_tolerance']);reference=float(policy['reference_tolerance'])
 if not all(math.isfinite(x) and x>0 for x in (tol,reference)):raise ValueError('invalid tolerances')
 ids=set()
 for a in graph.get('boundary_anchors',[]):
  x,y=a['x'],a['y']
  if not (region['xmin']<=x<=region['xmax'] and region['ymin']<=y<=region['ymax']):continue
  if a.get('kind') not in ('expert_non_node_source_boundary','user_confirmed_non_node_source_boundary'):raise ValueError('unconfirmed boundary')
  if a['boundary_id'] in ids:raise ValueError('duplicate boundary');
  ids.add(a['boundary_id']);system=a['system'];circle=doc.entitydb.get(a.get('source_circle_handle'));line=doc.entitydb.get(a.get('source_pipe_handle'))
  if not circle or not line or circle.dxftype()!='CIRCLE' or line.dxftype()!='LINE' or circle not in doc.modelspace() or line not in doc.modelspace():raise ValueError('missing native modelspace boundary')
  if circle.dxf.layer!=system_layers.get(system) or line.dxf.layer!=system_layers.get(system):raise ValueError('source system mismatch')
  c=circle.ocs().to_wcs(circle.dxf.center);center=(c.x,c.y)
  if math.dist(center,(x,y))>tol or not policy['radius_min']<=circle.dxf.radius<=policy['radius_max']:raise ValueError('circle and boundary mismatch')
  endpoint_distance=min(math.dist(center,(p.x,p.y)) for p in (line.dxf.start,line.dxf.end))
  if endpoint_distance>tol:raise ValueError('pipe endpoint does not witness circle center')
  edges=[e for e in graph['edges'] if a['boundary_id'] in (e.get('start_boundary_id'),e.get('end_boundary_id'))]
  if len(edges)!=1 or edges[0].get('system')!=system or a['source_pipe_handle'] not in edges[0].get('source_handles',[]):raise ValueError('ambiguous boundary edge')
  anchors.append({'boundary_id':a['boundary_id'],'system':system,'center':[x,y],'circle_handle':a['source_circle_handle'],'pipe_handle':a['source_pipe_handle'],'edge_id':edges[0]['edge_id'],'source_endpoint_distance':endpoint_distance,'kind':a['kind']})
 if not anchors:raise ValueError('no supported boundary anchors in region')
 rows=[]
 for system in ('supply','return'):
  upper=sorted([u for u in scope['upper'] if u['system']==system and not u['in_existing_candidate_set']],key=lambda u:u['center'][0]);lower=sorted([a for a in anchors if a['system']==system],key=lambda a:a['center'][0])
  if len(upper)!=len(lower) or not upper:raise ValueError('unequal or empty candidate groups; no ordered proposal')
  vectors=[(u['center'][0]-a['center'][0],u['center'][1]-a['center'][1]) for u,a in zip(upper,lower)];ref=(statistics.median(v[0] for v in vectors),statistics.median(v[1] for v in vectors))
  for u,a,v in zip(upper,lower,vectors):
   residual=math.dist(v,ref); competitors=[b['boundary_id'] for b in lower if math.dist((u['center'][0]-b['center'][0],u['center'][1]-b['center'][1]),ref)<=reference]
   rows.append({'system':system,'upper_glyph':u['node_id'],'detail_boundary':a['boundary_id'],'detail_edge':a['edge_id'],'source_circle_handle':a['circle_handle'],'source_pipe_handle':a['pipe_handle'],'ordered_xy_offset':list(v),'median_reference_xy':list(ref),'offset_residual':residual,'competing_boundaries_within_reference_tolerance':competitors,'status':'ordered_candidate_not_connection' if residual<=reference else 'offset_exception_not_connection'})
 return {'status':'ordered_candidates_not_mapping','source_sha256':source_hash,'graph_sha256':graph_hash,'scope':'only explicit upper and detail regions, graph-represented expert/user-confirmed non-node boundaries','anchors':anchors,'rows':rows,'counts':{'detail_boundaries':len(anchors),'ordered_candidates':len(rows),'offset_exceptions':sum(r['status'].startswith('offset_exception') for r in rows)},'mapping_ready':False,'graph_mutated':False,'human_accepted':False,'limitations':['Order and median translation are derived from these candidate positions and are not independent confirmation.','Non-node boundary remains a boundary, not an equipment port or T node.','No evidence that all source glyphs were extracted or that external details do not exist.']}

def main():
 p=argparse.ArgumentParser()
 for n in ('source','graph','scope','policy','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);r=analyze(doc,json.loads(a.graph.read_text(encoding='utf8')),json.loads(a.scope.read_text(encoding='utf8')),json.loads(a.policy.read_text(encoding='utf8')),proof['source_sha256'],sha(a.graph));r.update(scope_sha256=sha(a.scope),policy_sha256=sha(a.policy),source_text_preflight=proof['status']);
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'counts':r['counts']}))
if __name__=='__main__':main()
