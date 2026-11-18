"""Check selected split-edge component positions against native INSERT/LINE geometry."""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source

LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}

def projection(point,a,b):
 dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
 if not den:return None
 t=((point[0]-a[0])*dx+(point[1]-a[1])*dy)/den
 return t,math.hypot(point[0]-a[0]-t*dx,point[1]-a[1]-t*dy)

def verify(doc,graph,rebinding,policy,hashes,tol=.05):
 if isinstance(tol,bool) or not isinstance(tol,(float,int)) or not math.isfinite(tol) or not 0<tol<=.1:raise ValueError('invalid tolerance')
 for key in ('source_sha256','graph_sha256','rebinding_sha256'):
  if not hashes.get(key) or policy.get(key)!=hashes[key]:raise ValueError('stale '+key)
 if graph.get('metadata',{}).get('source_sha256')!=hashes['source_sha256'] or rebinding.get('new_graph_sha256')!=hashes['graph_sha256'] or rebinding.get('source_sha256')!=hashes['source_sha256'] or rebinding.get('status')!='component_rebinding_candidates_not_ownership_acceptance' or rebinding.get('graph_mutated') is not False or rebinding.get('human_accepted') is not False:raise ValueError('source or rebinding mismatch')
 rows=rebinding.get('records');items=policy.get('selections');edges={e['edge_id']:e for e in graph['edges']}
 if not isinstance(rows,list) or not isinstance(items,list) or not items or len(edges)!=len(graph['edges']):raise ValueError('invalid input')
 by={x['device_name']:x for x in rows}
 if len(by)!=len(rows) or len({x['device_name'] for x in items})!=len(items):raise ValueError('duplicate component')
 result=[]
 for item in items:
  row=by.get(item['device_name']);handle=item['source_handle'];line_handle=item['source_line_handle'];eid=item['new_edge_id'];edge=edges.get(eid);e=doc.entitydb.get(handle);line=doc.entitydb.get(line_handle)
  if not row or row.get('status')!='split_or_unmatched_edge_requires_review' or row.get('source_handle')!=handle or row.get('new_edge_id')!=eid or not edge or line_handle not in edge.get('source_handles',[]):raise ValueError('selection mismatch')
  system=edge.get('system')
  if system not in LAYERS or not e or e.dxftype()!='INSERT' or e not in doc.modelspace() or e.dxf.name!=item['source_block'] or not line or line.dxftype()!='LINE' or line not in doc.modelspace() or line.dxf.layer!=LAYERS[system]:raise ValueError('native source mismatch')
  point=(e.dxf.insert.x,e.dxf.insert.y);hits=[]
  for x in doc.modelspace().query('LINE'):
   if x.dxf.layer!=LAYERS[system]:continue
   a=(x.dxf.start.x,x.dxf.start.y);b=(x.dxf.end.x,x.dxf.end.y);p=projection(point,a,b)
   if p and 0<p[0]<1 and p[1]<=tol:hits.append(x.dxf.handle)
  if hits!=[line_handle]:raise ValueError('native line placement ambiguous')
  path_hits=[]
  for path in edge.get('attribute_paths',[]):
   for a,b in zip(path,path[1:]):
    p=projection(point,a,b)
    if p and 0<p[0]<1 and p[1]<=tol:path_hits.append(p[1])
  if len(path_hits)!=1:raise ValueError('graph path placement ambiguous')
  result.append({'device_name':row['device_name'],'source_insert':handle,'source_line':line_handle,'edge_id':eid,'system':system,'source_point':list(point),'path_distance':path_hits[0],'status':'unique_native_insert_line_placement_candidate','physical_ownership_verified':False})
 return {'status':'split_component_native_positions_not_ownership_acceptance','source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'rebinding_sha256':hashes['rebinding_sha256'],'records':result,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Selected modelspace INSERT and same-system modelspace LINE only; nested, proxy and other systems are outside this search.','Insertion point placement is not proof of physical component semantics or human acceptance.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','rebinding','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));doc,proof=read_source(a.source)
 r=verify(doc,load(a.graph),load(a.rebinding),load(a.policy),{'source_sha256':proof['source_sha256'],'graph_sha256':sha(a.graph),'rebinding_sha256':sha(a.rebinding)})
 r.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'records':len(r['records'])}))
if __name__=='__main__':main()
