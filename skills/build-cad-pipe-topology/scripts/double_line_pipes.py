"""Conservative straight double-wall candidates; no equipment or graph connections inferred."""
import math

def discover_straight_centerlines(walls,config):
 if not config:raise ValueError('Source-calibrated double-wall limits required')
 tol=config['tolerance'];lo=config['minimum_width'];hi=config['maximum_width'];span=config['minimum_overlap'];ratio=config['minimum_overlap_ratio'];records=[]
 for i,s in enumerate(walls):
  a,b=s['a'],s['b'];length=math.dist(a,b)
  if length<span:continue
  u=((b[0]-a[0])/length,(b[1]-a[1])/length)
  if u[0]<-tol/length or(abs(u[0])<=tol/length and u[1]<0):u=(-u[0],-u[1])
  records.append(dict(i=i,s=s,a=a,b=b,u=u,length=length))
 candidates=[]
 for ii,r in enumerate(records):
  u=r['u'];n=(-u[1],u[0]);dot=lambda p,v:p[0]*v[0]+p[1]*v[1];ar=sorted([dot(r['a'],u),dot(r['b'],u)]);offset=dot(r['a'],n)
  for q in records[ii+1:]:
   if r['s']['group']!=q['s']['group']:continue
   if max(abs(dot(q[k],n)-dot(q['a'],n))for k in ['a','b'])>tol:continue
   qo=dot(q['a'],n);width=abs(qo-offset)
   if not lo<=width<=hi:continue
   br=sorted([dot(q['a'],u),dot(q['b'],u)]);left,right=max(ar[0],br[0]),min(ar[1],br[1]);overlap=right-left
   if overlap<span or overlap/min(r['length'],q['length'])<ratio:continue
   # A third parallel wall inside the proposed pipe prevents a unique interpretation.
   interior=False
   for z in records:
    if z['i']in[r['i'],q['i']]or z['s']['group']!=r['s']['group']:continue
    zo=dot(z['a'],n)
    if not min(offset,qo)+tol<zo<max(offset,qo)-tol:continue
    if abs(dot(z['b'],n)-zo)>tol:continue
    zr=sorted([dot(z['a'],u),dot(z['b'],u)])
    if min(right,zr[1])-max(left,zr[0])>=span:interior=True;break
   mid=(offset+qo)/2;candidates.append(dict(wall_indices=[r['i'],q['i']],source_chains=[r['s']['source_chain'],q['s']['source_chain']],group=r['s']['group'],width=width,a=[left*u[0]+mid*n[0],left*u[1]+mid*n[1]],b=[right*u[0]+mid*n[0],right*u[1]+mid*n[1]],status='pending_intermediate_wall'if interior else'candidate',reason='Straight paired walls only; no junction, equipment port, bend or fitting connection asserted'))
 counts={}
 for c in candidates:
  if c['status']=='candidate':
   for i in c['wall_indices']:counts[i]=counts.get(i,0)+1
 for c in candidates:
  if c['status']=='candidate'and any(counts[i]!=1 for i in c['wall_indices']):c['status']='pending_multiple_wall_pairings'
 return candidates
