"""Compare explicitly selected same-drawing branch motifs; never repair topology."""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source

def compare(doc,graph,policy,source_hash,graph_hash):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('stale graph or source')
 layers=policy['system_layers'];nodes=graph['nodes'];rows=[];radius=policy.get('graph_node_radius');groups=policy.get('groups')
 if not isinstance(radius,(int,float)) or isinstance(radius,bool) or not math.isfinite(radius) or not 0<=radius<=10 or not isinstance(groups,list) or len(groups)<2:raise ValueError('invalid motif scope')
 refs={h for e in graph['edges'] for h in e.get('source_handles',[])}
 for group in groups:
  s=doc.entitydb.get(group['supply_handle']);r=doc.entitydb.get(group['return_handle']);sm=doc.entitydb.get(group['supply_main']);rm=doc.entitydb.get(group['return_main'])
  if any(x is None or x.dxftype()!='LINE' or x.dxf.owner!=doc.modelspace().block_record_handle for x in (s,r,sm,rm)):raise ValueError('native line missing')
  if any(x.dxf.handle not in refs for x in (s,r,sm,rm)):raise ValueError('line not referenced by current graph')
  if s.dxf.layer!=layers['supply'] or sm.dxf.layer!=layers['supply'] or r.dxf.layer!=layers['return'] or rm.dxf.layer!=layers['return']:raise ValueError('system layer mismatch')
  def calc(line,main,system):
   a,b=line.dxf.start,line.dxf.end;m,z=main.dxf.start,main.dxf.end;dx=z.x-m.x;dy=z.y-m.y;den=dx*dx+dy*dy
   if den<=0:raise ValueError('zero main')
   candidates=[]
   for endpoint in (a,b):
    u=((endpoint.x-m.x)*dx+(endpoint.y-m.y)*dy)/den
    if not 0<u<1:continue
    xy=(m.x+u*dx,m.y+u*dy);candidates.append((math.dist((endpoint.x,endpoint.y),xy),endpoint,xy))
   if not candidates:raise ValueError('branch misses main extent')
   gap,end,projection=min(candidates,key=lambda x:x[0]);near=[{'node_id':n['node_id'],'type':n.get('node_type'),'boundary_type':n.get('boundary_type'),'distance_to_projection':math.dist((n['x'],n['y']),projection)} for n in nodes if n.get('system')==system and math.dist((n['x'],n['y']),projection)<=radius]
   return {'source_handle':line.dxf.handle,'main_handle':main.dxf.handle,'a':[a.x,a.y,a.z],'b':[b.x,b.y,b.z],'length_2d':math.dist((a.x,a.y),(b.x,b.y)),'endpoint_to_main_distance':gap,'endpoint':[end.x,end.y,end.z],'main_projection':list(projection),'nearby_graph_nodes':near}
  rows.append({'id':group['id'],'supply':calc(s,sm,'supply'),'return':calc(r,rm,'return')})
 if len(rows)<2 or len({r['id'] for r in rows})!=len(rows):raise ValueError('invalid motif groups')
 return {'status':'native_motif_comparison_not_connection_proof','source_sha256':source_hash,'graph_sha256':graph_hash,'groups':rows,'graph_mutated':False,'hil_ready':False,'limitations':['Only explicitly selected modelspace LINEs and graph nodes are compared; block/proxy and unrelated geometry remain outside scope.','Equal branch lengths or offsets are clues, not proof of connectivity, physical fitting or engineering acceptance.','Supply and return remain separate systems.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);result=compare(doc,json.loads(a.graph.read_text(encoding='utf8')),json.loads(a.policy.read_text(encoding='utf8')),proof['source_sha256'],sha(a.graph));result.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'groups':len(result['groups'])}))
if __name__=='__main__':main()
