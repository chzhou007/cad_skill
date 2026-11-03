import pipe_geometry as pg_constants
"""Native flexible-joint flange axes and exploded pump recognition for sheet03."""
from pipe_geometry import *
def flange_axis(entity):
 lines=[]
 for p in entity.virtual_entities():
  if p.dxftype()=='LINE':
   a,b=xy(p.dxf.start),xy(p.dxf.end)
   if dist(a,b)>1 and not any(dist(a,c)<pg_constants.TOL and dist(b,d)<pg_constants.TOL or dist(a,d)<pg_constants.TOL and dist(b,c)<pg_constants.TOL for c,d in lines):lines.append((a,b))
 if len(lines)!=2:return None
 (a,b),(c,d)=lines;v=sub(b,a);w=sub(d,c)
 if abs(cross(v,w))>pg_constants.TOL*dist(a,b)or abs(dist(a,b)-dist(c,d))>pg_constants.TOL:return None
 p=((a[0]+b[0])/2,(a[1]+b[1])/2);q=((c[0]+d[0])/2,(c[1]+d[1])/2)
 if dist(p,q)<1 or abs(dot(sub(q,p),v))>pg_constants.TOL*dist(a,b):return None
 return p,q

def dock_axis(entity,segments):
 axis=flange_axis(entity)
 if not axis:return None,'native_two_flange_signature_not_met'
 p,q=axis;L=dist(p,q);v=sub(q,p);docks=[]
 for a,b in [(p,q),(q,p)]:
  cand=[]
  for s in segments:
   if abs(cross(sub(s['b'],s['a']),v))>pg_constants.TOL*dist(s['a'],s['b']):continue
   for t in [s['a'],s['b']]:
    if dist(t,a)<=L*.12+pg_constants.TOL and abs(cross(sub(t,a),v))<=pg_constants.TOL*L and any(dot(sub(z,t),sub(b,a))<0 for z in [s['a'],s['b']]if dist(z,t)>pg_constants.TOL):
     if not any(dist(t,z)<=pg_constants.TOL for z in cand):cand.append(t)
  if len(cand)!=1:return None,'missing_or_ambiguous_collinear_flange_dock'
  docks.append(cand[0])
 if dist(*docks)<=pg_constants.TOL:return None,'zero_span'
 return docks,'native_parallel_flange_axis_and_two_outward_pipe_docks'

def detect_pump(circle,entities):
 c=xy(circle.dxf.center);r=circle.dxf.radius
 lines=[e for e in entities if e.dxftype()=='LINE' and e.dxf.layer==circle.dxf.layer and all(dist(xy(p),c)<=r*1.05 for p in [e.dxf.start,e.dxf.end])]
 if len(lines)!=3:return None
 lengths=sorted(dist(xy(e.dxf.start),xy(e.dxf.end))for e in lines)
 # Complete inscribed triangle, not one circle or incidental diameter.
 if not(r*1.2<lengths[0]<r*1.6 and r*1.2<lengths[1]<r*1.6 and r*1.8<lengths[2]<r*2.1):return None
 endpoints=[xy(p)for e in lines for p in [e.dxf.start,e.dxf.end]]
 clusters=[]
 for p in endpoints:
  k=next((i for i,q in enumerate(clusters)if dist(p,q)<pg_constants.TOL),None)
  if k is None:clusters.append(p)
 if len(clusters)!=3:return None
 return {'center':c,'radius':r,'source_handles':[circle.dxf.handle]+[e.dxf.handle for e in lines]}
