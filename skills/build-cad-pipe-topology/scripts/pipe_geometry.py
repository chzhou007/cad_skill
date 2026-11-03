"""Shared source-contact geometry. Crossover chords continue one pipe without joining the crossed pipe.
No elevation or flow inference. Public API retains the project adapter compatibility functions.
"""
__version__="1.0.0"
import math,collections
TOL=0.5

def set_tolerance(value):
 global TOL
 value=float(value)
 if not math.isfinite(value)or value<=0:raise ValueError('Tolerance must be finite and positive')
 TOL=value

def xy(p):return (float(p[0]),float(p[1]))
def dist(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
def dot(a,b):return a[0]*b[0]+a[1]*b[1]
def sub(a,b):return(a[0]-b[0],a[1]-b[1])
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def on(p,a,b,tol=None):
 tol=TOL if tol is None else tol
 v=sub(b,a); l=dot(v,v)
 if l==0:return dist(p,a)<=tol
 t=dot(sub(p,a),v)/l
 return -tol/math.sqrt(l)<=t<=1+tol/math.sqrt(l) and abs(cross(sub(p,a),v))/math.sqrt(l)<=tol

def segdist(p,a,b):
 v=sub(b,a);l=dot(v,v)
 t=max(0,min(1,dot(sub(p,a),v)/l)) if l else 0
 return dist(p,(a[0]+t*v[0],a[1]+t*v[1]))
def intersection(a,b,c,d):
 v=sub(b,a);w=sub(d,c);den=cross(v,w)
 if abs(den)<1e-8:return None
 t=cross(sub(c,a),w)/den;u=cross(sub(c,a),v)/den
 if 1e-7<t<1-1e-7 and 1e-7<u<1-1e-7:return(a[0]+t*v[0],a[1]+t*v[1])
def point_bbox(p,b):return math.hypot(max(b[0]-p[0],0,p[0]-b[2]),max(b[1]-p[1],0,p[1]-b[3]))
def build_network(segments):
 # Cut only at existing same-system pipe endpoints: pure crossings never join.
 vertices=[]
 def key(p):
  for i,v in enumerate(vertices):
   if dist(v,p)<=TOL:return i
  vertices.append(p);return len(vertices)-1
 endpoints=[(s['system'],p)for s in segments for p in [s['a'],s['b']]]
 adjacency=collections.defaultdict(list);pieces=[]
 for s in segments:
  protected=s.get('normalization')=='semicircular_crossover_chord' or s.get('crossing_connectivity')=='independent_pipes_no_junction'
  pts=[s['a'],s['b']] if protected else [p for sy,p in endpoints if sy==s['system'] and on(p,s['a'],s['b'])]
  pts.sort(key=lambda p:dist(s['a'],p));ids=[]
  for p in pts:
   k=key(p)
   if not ids or ids[-1]!=k:ids.append(k)
  for u,v in zip(ids,ids[1:]):
   if u==v:continue
   # deduplicate exact superposed physical rays, retaining source coverage.
   existing=next((j for j in adjacency[(s['system'],u)]if set(pieces[j]['vertices'])=={u,v}),None)
   if existing is not None:
    pieces[existing]['source_handles'].extend(s.get('source_handles',[s['handle']]))
    continue
   j=len(pieces);pieces.append({'vertices':(u,v),'system':s['system'],'source_handles':list(s.get('source_handles',[s['handle']])),'normalization':s.get('normalization')})
   adjacency[(s['system'],u)].append(j);adjacency[(s['system'],v)].append(j)
 return vertices,pieces,adjacency

def open_ends(segments):
 vs,ps,ad=build_network(segments)
 return[(sy,vs[v])for(sy,v),inds in ad.items()if len(inds)==1]

def normalize_arc(a,b,segments):
 """Normalize a verified local jump. `b` is pipe evidence, never arbitrary symbol ink.
 A composed crossing may consist of two native LINEs meeting at the crossing.
 The owning semantic chord is protected from unrelated endpoint splitting.
 """
 sy=a['system'];p=xy(a['a']);q=xy(a['b']);v=sub(q,p);L=dist(p,q)
 if not(0<L<=a['radius']*2.01)or abs(a['span']-180)>0.1:return None,'not_semicircular'
 for t,other in [(p,q),(q,p)]:
  candidates=[s for s in segments if s['system']==sy and any(dist(t,e)<=TOL for e in [s['a'],s['b']]) and abs(cross(sub(s['b'],s['a']),v))<=TOL*dist(s['a'],s['b'])]
  candidates=[s for s in candidates if any(dist(t,e)>TOL and dot(sub(e,t),sub(other,t))<0 for e in [s['a'],s['b']])]
  if not candidates:return None,'no_collinear_outward_pipe_at_both_arc_ends'
 hits=[]
 for seg in b:
  hit=intersection(p,q,seg['a'],seg['b'])
  if hit:hits.append({'crossing':hit,'crossed_system':seg['system'],'crossed_handle':seg['handle'],'crossing_evidence':'native_pipe_interior'})
 # A drafting split at the crossing is still a continuous crossed pipe when
 # two opposite same-system source rays support it; one terminal alone is not.
 for seg in b:
  for t in [seg['a'],seg['b']]:
   if not on(t,p,q)or min(dist(t,p),dist(t,q))<=TOL:continue
   rays=[]
   for other in b:
    if other['system']!=seg['system']:continue
    for u,z in [(other['a'],other['b']),(other['b'],other['a'])]:
     if dist(u,t)<=TOL and dist(z,t)>TOL and abs(cross(sub(z,t),v))>TOL*L:rays.append((sub(z,t),other['handle']))
   for i,(r,h)in enumerate(rays):
    for r2,h2 in rays[i+1:]:
     if dot(r,r2)<0 and abs(cross(r,r2))<=TOL*max(dist((0,0),r),dist((0,0),r2)):
      if not any(dist(t,x['crossing'])<=TOL and x['crossed_system']==seg['system']for x in hits):hits.append({'crossing':xy(t),'crossed_system':seg['system'],'crossed_handle':h,'crossed_handles':sorted({h,h2}),'crossing_evidence':'opposite_collinear_native_pipe_rays'})
 if not hits:return None,'no_crossed_pipe'
 return {'a':p,'b':q,'system':sy,'handle':a['handle'],'source_handles':[a.get('source_entity_handle',a['handle'])],'normalization':'semicircular_crossover_chord','crossings':hits,'source_display_geometry':a.get('source_display_geometry'),'crossing_connectivity':'independent_pipes_no_junction','relative_elevation':'unknown'},'normalized'

def curve_candidates(entity,system):
 """ARC and LWPOLYLINE bulge candidates in WCS; retain parent provenance.
 Arbitrary SPLINEs and ordinary bends stay unsupported/pending, never flattened.
 """
 typ=entity.dxftype();handle=entity.dxf.handle
 if typ=='ARC':parts=[(None,entity)]
 elif typ in ('LWPOLYLINE','POLYLINE'):parts=[(i,e)for i,e in enumerate(entity.virtual_entities())if e.dxftype()=='ARC']
 else:return []
 result=[]
 for index,e in parts:
  result.append({'a':xy(e.start_point),'b':xy(e.end_point),'system':system,'handle':handle if index is None else str(handle)+':'+str(index),'source_entity_handle':handle,'radius':float(e.dxf.radius),'span':(e.dxf.end_angle-e.dxf.start_angle)%360,'source_display_geometry':{'type':typ,'source_handle':handle,'segment_index':index,'center':xy(e.dxf.center),'radius':float(e.dxf.radius),'start_angle':float(e.dxf.start_angle),'end_angle':float(e.dxf.end_angle)}})
 return result

def heal_symbols(segments,symbols):
 audits=[];changed=list(segments)
 for s in symbols:
  if not s.get('bridge_allowed'):continue
  ends=open_ends(changed);bb=s['bounds'];maxsize=max(bb[2]-bb[0],bb[3]-bb[1]);cand=[]
  if maxsize<=0:continue
  for i,(sy,p)in enumerate(ends):
   if point_bbox(p,bb)>maxsize*.12+TOL:continue
   for sj,q in ends[i+1:]:
    if sy!=sj or not(TOL<dist(p,q)<=maxsize*1.3):continue
    if point_bbox(q,bb)>maxsize*.12+TOL:continue
    if not on(xy(s['insert']),p,q,maxsize*.15+TOL):continue
    v=sub(q,p)
    atp=[t for t in changed if t['system']==sy and (dist(p,t['a'])<=TOL or dist(p,t['b'])<=TOL)]
    atq=[t for t in changed if t['system']==sy and (dist(q,t['a'])<=TOL or dist(q,t['b'])<=TOL)]
    if not atp or not atq:continue
    if any(abs(cross(sub(t['b'],t['a']),v))/max(dist(t['a'],t['b'])*dist(p,q),1e-9)>1e-5 for t in atp+atq):continue
    cand.append((sy,p,q))
  if len(cand)==1:
   sy,p,q=cand[0];h='SYMBOL-'+s['handle'];changed.append({'a':p,'b':q,'system':sy,'handle':h,'source_handles':[s['handle']],'normalization':'verified_native_symbol_gap'})
   audits.append({'source_handle':s['handle'],'source_block_name':s['block'],'a':p,'b':q,'system':sy,'gap_length':dist(p,q),'status':'healed_unique_collinear_terminal_pair'})
  elif len(cand)>1:audits.append({'source_handle':s['handle'],'status':'ambiguous_symbol_terminal_pairs','candidate_count':len(cand)})
 return changed,audits
