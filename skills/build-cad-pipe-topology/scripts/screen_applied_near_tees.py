"""Keep source-normalized near-tee connections visible as unreviewed dependencies."""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source

LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}

def screen(doc,graph,audit,policy,hashes,tol=.05):
 for k in ('source_sha256','graph_sha256','normalization_sha256'):
  if not hashes.get(k) or policy.get(k)!=hashes[k]:raise ValueError('stale '+k)
 if graph.get('metadata',{}).get('source_sha256')!=hashes['source_sha256']:raise ValueError('graph source mismatch')
 items=policy.get('selections');events=audit.get('near_junction');nodes=graph.get('nodes');edges=graph.get('edges')
 if not isinstance(items,list) or not items or not isinstance(events,list) or not isinstance(nodes,list) or not isinstance(edges,list):raise ValueError('invalid screen inputs')
 if len({x['branch_handle'] for x in items})!=len(items):raise ValueError('duplicate source branch')
 out=[]
 for spec in items:
  bh,mh,system=spec['branch_handle'],spec['main_handle'],spec['system'];node_id=spec['node_id']
  if system not in LAYERS:raise ValueError('unknown system')
  hits=[x for x in events if x.get('source_handles')==[bh] and x.get('main_source_handles')==[mh] and x.get('status')=='applied' and x.get('action')=='trim']
  if len(hits)!=1:raise ValueError('normalization event mismatch')
  event=hits[0];raw=event['original_endpoint'];point=event['semantic_endpoint'];dist=math.dist(raw,point)
  if not .05<dist<=1 or abs(dist-event.get('removed_length',-1))>.001 or event.get('physical_length')!='unknown':raise ValueError('invalid normalization geometry')
  branch=doc.entitydb.get(bh);main=doc.entitydb.get(mh)
  if any(not e or e.dxftype()!='LINE' or e not in doc.modelspace() or e.dxf.layer!=LAYERS[system] for e in (branch,main)):raise ValueError('source line mismatch')
  ends=[(x.x,x.y) for x in (branch.dxf.start,branch.dxf.end)]
  if sum(math.dist(raw,x)<=tol for x in ends)!=1:raise ValueError('source endpoint mismatch')
  a,b=main.dxf.start,main.dxf.end;dx=b.x-a.x;dy=b.y-a.y;den=dx*dx+dy*dy
  if not den:raise ValueError('degenerate source main')
  t=((point[0]-a.x)*dx+(point[1]-a.y)*dy)/den
  if not 0<t<1 or math.hypot(point[0]-a.x-t*dx,point[1]-a.y-t*dy)>tol:raise ValueError('main source geometry mismatch')
  selected=[n for n in nodes if n.get('node_id')==node_id]
  if len(selected)!=1 or selected[0].get('node_type')!='tee' or math.dist(point,(selected[0]['x'],selected[0]['y']))>tol:raise ValueError('graph node mismatch')
  incident=[e for e in edges if node_id in (e.get('start_node_id'),e.get('end_node_id'))]
  if len(incident)!=3 or any(e.get('system')!=system for e in incident) or sum(bh in e.get('source_handles',[]) for e in incident)!=1 or sum(mh in e.get('source_handles',[]) for e in incident)!=2:raise ValueError('graph incidence mismatch')
  out.append({'node_id':node_id,'system':system,'branch_handle':bh,'main_handle':mh,'incident_edge_ids':sorted(e['edge_id'] for e in incident),'normalization_distance':dist,'status':'source_normalized_tee_not_human_accepted'})
 return {'status':'applied_near_tees_pending_review','source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'normalization_sha256':hashes['normalization_sha256'],'records':out,'graph_mutated':False,'human_accepted':False,'hil_ready':False}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','normalization','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));doc,proof=read_source(a.source)
 result=screen(doc,load(a.graph),load(a.normalization),load(a.policy),{'source_sha256':proof['source_sha256'],'graph_sha256':sha(a.graph),'normalization_sha256':sha(a.normalization)});result.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'records':len(result['records'])}))
if __name__=='__main__':main()
