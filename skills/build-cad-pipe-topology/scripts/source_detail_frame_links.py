"""Validate source-drawn four-corner dashed links between two drawing regions.

The frame describes graphical correspondence only, not individual pipe identity.
"""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source


def screen(doc,glyphs,policy,hashes,tol=.1):
 for key in ('source_sha256','graph_sha256','glyphs_sha256'):
  if policy.get(key)!=hashes.get(key):raise ValueError('input hash mismatch: '+key)
 if glyphs.get('source_sha256')!=hashes['source_sha256'] or glyphs.get('graph_sha256')!=hashes['graph_sha256'] or glyphs.get('graph_mutated') is not False:raise ValueError('glyph evidence binding mismatch')
 if not 0<tol<=.1:raise ValueError('invalid tolerance')
 selected=set();frames=[]
 for spec in policy['frames']:
  hs=spec['line_handles']
  if len(hs)!=4 or len(set(hs))!=4 or selected.intersection(hs):raise ValueError('invalid frame line scope')
  selected.update(hs);upper=[];lower=[];deltas=[]
  for h in hs:
   e=doc.entitydb.get(h)
   if not e or e.dxftype()!='LINE' or e.dxf.owner!=doc.modelspace().block_record_handle or e.dxf.layer!=policy['annotation_layer'] or e.dxf.get('linetype','BYLAYER').upper() not in policy['allowed_linetypes']:raise ValueError('invalid frame source line')
   a,b=e.dxf.start,e.dxf.end
   if abs(a.z)>tol or abs(b.z)>tol or abs(a.y-b.y)<=tol:raise ValueError('unsupported frame line geometry')
   u,l=(a,b) if a.y>b.y else (b,a);upper.append((u.x,u.y));lower.append((l.x,l.y));deltas.append((u.x-l.x,u.y-l.y))
  delta=deltas[0]
  if any(math.dist(delta,d)>tol for d in deltas):raise ValueError('frame translations differ')
  def bounds(points):
   xs=sorted(set(round(x,2) for x,y in points));ys=sorted(set(round(y,2) for x,y in points))
   if len(xs)!=2 or len(ys)!=2 or len({(round(x,2),round(y,2)) for x,y in points})!=4:raise ValueError('frame endpoints are not four corners')
   return [xs[0],ys[0],xs[1],ys[1]]
  ub,lb=bounds(upper),bounds(lower)
  if abs((ub[2]-ub[0])-(lb[2]-lb[0]))>tol or abs((ub[3]-ub[1])-(lb[3]-lb[1]))>tol:raise ValueError('frame extents differ')
  frames.append({'frame_id':spec['frame_id'],'source_handles':hs,'upper_bounds':ub,'lower_bounds':lb,'source_line_offset':[delta[0],delta[1]],'kind':'source_dashed_annotation_frame_not_pipe'})
 def inside(point,box):return box[0]-tol<=point[0]<=box[2]+tol and box[1]-tol<=point[1]<=box[3]+tol
 rows=[]
 for row in glyphs['rows']:
  u=row['upper']['center'];l=row['detail']['center'];hits=[f['frame_id'] for f in frames if inside(u,f['upper_bounds']) and inside(l,f['lower_bounds'])]
  rows.append({'system':row['system'],'rank':row['rank'],'upper_edge':row['upper_edge'],'detail_edge':row['detail_edge'],'shared_frame_candidates':hits,'status':'source_frame_context_not_individual_mapping'})
 return {'status':'source_dashed_frame_context_not_mapping','source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'glyphs_sha256':hashes['glyphs_sha256'],
         'frames':frames,'candidate_rows':rows,'graph_mutated':False,'mapping_ready':False,'human_accepted':False,'hil_ready':False,
         'limitations':['Dashed frame is graphical regional evidence, not a physical pipe or proof of individual element correspondence.',
                        'Only explicitly selected modelspace annotation LINEs and prior candidate centers were inspected.']}


def main():
 p=argparse.ArgumentParser()
 for name in ('source','graph','glyphs','policy','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);policy=json.loads(a.policy.read_text(encoding='utf8'))
 hashes={key+'_sha256':sha(getattr(a,key)) for key in ('source','graph','glyphs')};g=json.loads(a.graph.read_text(encoding='utf8'))
 if g.get('metadata',{}).get('source_sha256')!=hashes['source_sha256']:raise ValueError('graph source mismatch')
 result=screen(doc,json.loads(a.glyphs.read_text(encoding='utf8')),policy,hashes);result.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'frames':len(result['frames']),'rows':len(result['candidate_rows']),'mapping_ready':False}))
if __name__=='__main__':main()
