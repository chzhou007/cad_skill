"""Bind selected graph segments to uniquely covering native LINE witnesses.

Source geometry evidence only: no connection, diameter or physical length
claims are made, and the graph is never modified.
"""
import argparse,hashlib,json,math
from pathlib import Path
LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}
def _on(p,a,b,tol):
 dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
 if den==0:return False
 u=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den;foot=(a[0]+u*dx,a[1]+u*dy)
 return -tol/math.sqrt(den)<=u<=1+tol/math.sqrt(den) and math.dist(p,foot)<=tol

def collect(doc,graph,policy,source_hash,graph_hash,tol=.05):
 if not math.isfinite(tol) or tol<=0:raise ValueError('invalid tolerance')
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash:raise ValueError('source or graph hash mismatch')
 edges={e['edge_id']:e for e in graph['edges']};selections=policy['selections']
 if len(edges)!=len(graph['edges']):raise ValueError('duplicate graph edge')
 if not selections or len({x['edge_id'] for x in selections})!=len(selections):raise ValueError('duplicate or empty edge selections')
 result=[]
 for choice in selections:
  e=edges.get(choice['edge_id']);paths=e.get('attribute_paths') if e else None
  if not e or e.get('system') not in LAYERS or e.get('connection_mode')!='continuous_original_cad_pipe' or not isinstance(paths,list) or len(paths)!=1 or len(paths[0])<2:raise ValueError('unsupported graph edge')
  points=paths[0];handles=choice['line_handles']
  if len(handles)!=len(points)-1 or len(set(handles))!=len(handles):raise ValueError('source handle count mismatch')
  segments=[]
  for idx,(a,b,h) in enumerate(zip(points,points[1:],handles)):
   if len(a)!=2 or len(b)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in a+b) or math.dist(a,b)<=tol:raise ValueError('invalid graph segment')
   hits=[]
   for line in doc.modelspace().query('LINE'):
    if line.dxf.layer!=LAYERS[e['system']]:continue
    p=(line.dxf.start.x,line.dxf.start.y);q=(line.dxf.end.x,line.dxf.end.y)
    if _on(a,p,q,tol) and _on(b,p,q,tol):hits.append(line.dxf.handle)
   if hits!=[h]:raise ValueError('native source line missing or ambiguous for '+e['edge_id'])
   line=doc.entitydb[h];segments.append({'segment_index':idx,'source_handle':h,'source_layer':line.dxf.layer,'graph_start':a,'graph_end':b,'source_start':[line.dxf.start.x,line.dxf.start.y],'source_end':[line.dxf.end.x,line.dxf.end.y]})
  result.append({'edge_id':e['edge_id'],'system':e['system'],'segments':segments,'status':'source_line_geometry_witness_only'})
 return {'status':'geometry_evidence_unreviewed','source_sha256':source_hash,'graph_sha256':graph_hash,'edges':result,'graph_mutated':False,'hil_ready':False,'limitations':['Selected modelspace LINEs on configured service layers only; nested blocks, polylines and proxy content are outside this evidence.','Collinear geometric coverage does not prove connectivity at crossings, physical direction, diameter assignment or physical length.','This is not full source coverage or an accepted topology.']}

def main():
 p=argparse.ArgumentParser()
 for key in ('source','graph','policy','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();from source_readability import read_source
 doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();r=collect(doc,json.loads(gb),json.loads(pb),proof['source_sha256'],hashlib.sha256(gb).hexdigest());r.update(policy_sha256=hashlib.sha256(pb).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'edges':len(r['edges']),'segments':sum(len(x['segments']) for x in r['edges'])}))
if __name__=='__main__':main()
