"""Source-backed edge attributes; annotation geometry never changes connectivity."""
import math,re,collections
import pipe_geometry as pg
from ezdxf import bbox

def source_texts(doc,source_id,source_hash):
 out=[]
 for e in doc.modelspace():
  if e.dxftype()not in ('TEXT','MTEXT'):continue
  text=e.plain_text();p=e.ocs().to_wcs(e.dxf.insert)if e.dxftype()=='TEXT'else e.dxf.insert
  h=float(e.dxf.height if e.dxftype()=='TEXT'else e.dxf.char_height)
  out.append(dict(id=source_id+':'+e.dxf.handle,source_id=source_id,source_sha256=source_hash,handle=e.dxf.handle,layer=e.dxf.layer,text=text,position=[p.x,p.y],height=h,rotation=float(e.dxf.get('rotation',0)),entity_type=e.dxftype()))
 return out

def annotation_legs(doc,layers):
 result=[]
 for e in doc.modelspace().query('LWPOLYLINE'):
  if e.dxf.layer not in layers or e.closed or len(e)!=3 or any(abs(p[4])>1e-9 for p in e.get_points()):continue
  a,b,c=[pg.xy(v)for v in e.vertices_in_wcs()];u=pg.sub(b,a);v=pg.sub(c,b);lu=pg.dist(a,b);lv=pg.dist(b,c)
  if min(lu,lv)<=pg.TOL or abs(pg.dot(u,v))>.002*lu*lv:continue
  result.append(dict(handle=e.dxf.handle,a=a,b=b,c=c,u=u,v=v,lu=lu,lv=lv,layer=e.dxf.layer))
 return result

def contact(a,b,c,d):
 u=pg.sub(b,a);v=pg.sub(d,c);den=pg.cross(u,v)
 if abs(den)<1e-9:return None
 t=pg.cross(pg.sub(c,a),v)/den;s=pg.cross(pg.sub(c,a),u)/den
 if -1e-7<=t<=1+1e-7 and -1e-7<=s<=1+1e-7:return (a[0]+t*u[0],a[1]+t*u[1])

def point_edges(point,handles,edges,service=None):
 return [e['edge_id']for e in edges if (not service or e['system']==service)and set(handles)&set(e['source_handles'])and any(pg.on(point,a,b)for path in e['attribute_paths']for a,b in zip(path,path[1:]))]

def recognize_f_leaders(doc,texts,segments,edges,layers):
 legs=annotation_legs(doc,layers);rows=[];used=set();frames=[]
 dn=[t for t in texts if re.fullmatch(r'DN\s*\d+(?:\.\d+)?(?:\([^)]*\))?',t['text'],re.I)and t['layer']in layers]
 for low in legs:
  candidates=[hi for hi in legs if hi is not low and hi['layer']==low['layer']and pg.dist(hi['a'],low['b'])<=pg.TOL and pg.dot(low['u'],hi['u'])>0 and abs(pg.cross(low['u'],hi['u']))<=pg.TOL*max(low['lu'],hi['lu'])and pg.dot(low['v'],hi['v'])>0 and pg.dist(low['v'],hi['v'])<=pg.TOL]
  if len(candidates)!=1:continue
  hi=candidates[0];frames.append((low,hi,[hi['b'],low['a']],'straight_spine'))
 # A folded stem uses one native straight stroke for the lower bar and
 # outgoing tail. Its upper L must meet the stroke interior, and both bar
 # ends must align. The tail may turn 90 degrees; order follows the spine.
 for e in doc.modelspace().query('LWPOLYLINE'):
  if e.dxf.layer not in layers or e.closed or len(e)!=2:continue
  a,b=[pg.xy(v)for v in e.vertices_in_wcs()]
  for hi in legs:
   if hi['layer']!=e.dxf.layer or not pg.on(hi['a'],a,b)or min(pg.dist(hi['a'],a),pg.dist(hi['a'],b))<=pg.TOL:continue
   for end,tail in [(a,b),(b,a)]:
    v=pg.sub(end,hi['a'])
    if pg.dist(v,hi['v'])>pg.TOL or pg.dot(pg.sub(tail,hi['a']),hi['v'])>=0:continue
    low=dict(hi,handle=e.dxf.handle,a=tail,b=hi['a'],c=end)
    frames.append((low,hi,[hi['b'],hi['a'],tail],'bent_spine'))
 for low,hi,spine,family in frames:
  key=tuple(sorted([low['handle'],hi['handle']]))
  if key in used:continue
  used.add(key);axis=(hi['u'][0]/hi['lu'],hi['u'][1]/hi['lu']);arm=(hi['v'][0]/hi['lv'],hi['v'][1]/hi['lv']);bound=[]
  for leg in [hi,low]:
   matches=[]
   for t in dn:
    delta=pg.sub(t['position'],leg['b']);along=pg.dot(delta,arm);above=pg.dot(delta,axis);angle=math.radians(t['rotation']);baseline=(math.cos(angle),math.sin(angle))
    if -.1*t['height']<=above<=1.5*t['height']and -.2*t['height']<=along<=leg['lv']and abs(pg.cross(baseline,arm))<.02:matches.append(t)
   bound.append(matches)
  row=dict(id='F-'+key[0],family=family,leader_handles=list(key),stem=spine,bar_points=[hi['b'],low['b']],texts=[m[0]for m in bound if len(m)==1],status='pending',bindings=[])
  rows.append(row)
  if any(len(m)!=1 for m in bound)or bound[0][0]['id']==bound[1][0]['id']:row['reason']='missing_or_ambiguous_bar_text';continue
  crosses=[]
  walked=0
  for start,end in zip(spine,spine[1:]):
   sv=pg.sub(end,start);sl=pg.dist(start,end)
   for s in segments:
    p=contact(start,end,s['a'],s['b'])
    if p is None:continue
    v=pg.sub(s['b'],s['a']);length=pg.dist(s['a'],s['b'])
    if not length or abs(pg.cross(sv,v))/(sl*length)<.2:continue
    handles=s.get('source_handles',[s['handle']]);service=s.get('source_system',s['system']);edgeids=point_edges(p,handles,edges,service)
    if not edgeids:continue
    previous=next((c for c in crosses if pg.dist(c['point'],p)<=pg.TOL and c['system']==service),None)
    if previous:previous['source_pipe_handles']=sorted(set(previous['source_pipe_handles']+handles));previous['edge_ids']=sorted(set(previous['edge_ids']+edgeids))
    else:crosses.append(dict(point=list(p),system=service,source_pipe_handles=list(handles),edge_ids=edgeids,order_distance=walked+pg.dist(start,p)))
   walked+=sl
  crosses.sort(key=lambda c:c['order_distance']);row['pipe_crossings']=crosses
  if len(crosses)!=2:row['reason']='expected_two_unique_pipe_crossings';continue
  if any(len(c['edge_ids'])!=1 for c in crosses):row['reason']='crossing_on_ambiguous_edge_junction';continue
  for i,c in enumerate(crosses):row['bindings'].append(dict(c,text=bound[i][0],nominal_mm=float(re.search(r'[0-9.]+',bound[i][0]['text']).group()),order=i+1,rule='F_bar_order_from_stem_cap_to_tip_matches_pipe_crossing_order'))
  row.update(status='assigned',reason='two_qualified_bars_two_native_texts_two_ordered_source_pipe_crossings')
 return rows

def direct_diameters(texts,edges,excluded_ids,layers):
 assigned=[];pending=[]
 for t in texts:
  if t['id']in excluded_ids or t['layer']not in layers or not re.fullmatch(r'DN\s*\d+(?:\.\d+)?(?:\([^)]*\))?',t['text'],re.I):continue
  angle=math.radians(t['rotation']);u=(math.cos(angle),math.sin(angle));p=t['position'];candidates=[]
  for e in edges:
   for path in e['attribute_paths']:
    for a,b in zip(path,path[1:]):
     v=pg.sub(b,a);length=pg.dist(a,b)
     if not length or abs(pg.cross(u,v))/length>math.sin(math.radians(2)):continue
     along=pg.dot(pg.sub(p,a),v)/(length*length)
     if not 0<along<1:continue
     foot=(a[0]+along*v[0],a[1]+along*v[1]);delta=pg.sub(p,foot);distance=pg.dist(p,foot)
     if distance<=2*t['height']:candidates.append((distance,e['edge_id'],foot))
  best={}
  for c in candidates:
   if c[1]not in best or c[0]<best[c[1]][0]:best[c[1]]=c
  values=sorted(best.values());row=dict(text=t,status='pending',candidate_edge_ids=[v[1]for v in values])
  if values and (len(values)==1 or values[1][0]-values[0][0]>.5*t['height']):
   row.update(status='assigned',edge_id=values[0][1],point=values[0][2],nominal_mm=float(re.search(r'[0-9.]+',t['text']).group()),rule='single_text_axial_projection_unique_parallel_source_edge_within_two_text_heights');assigned.append(row)
  else:pending.append(row)
 return assigned,pending

def floor_bands(doc,texts,layers,region_bounds):
 labels=[t for t in texts if t['layer']in layers and re.fullmatch(r'(?:[1-9]\d*F|[一二三四五六七八九十]+层|机房层|屋面层?)',t['text'])];groups=collections.defaultdict(list)
 for e in doc.modelspace().query('LWPOLYLINE'):
  if e.dxf.layer not in layers or len(e)!=2:continue
  a,b=[pg.xy(v)for v in e.vertices_in_wcs()]
  if abs(a[1]-b[1])>pg.TOL or abs(a[0]-b[0])<10000:continue
  xmin,xmax=sorted([a[0],b[0]]);y=a[1]
  matches=[t for t in labels if abs(t['position'][0]-xmin)<t['height']and 0<=t['position'][1]-y<=t['height']]
  if len(matches)!=1:continue
  t=matches[0];groups[(round(xmin,3),round(xmax,3))].append(dict(source_floor=t['text'],text=t,line_handle=e.dxf.handle,y=y,xmin=xmin,xmax=xmax))
 result=[]
 for group in groups.values():
  group.sort(key=lambda r:r['y'])
  for i,r in enumerate(group):
   candidates=[b[3]for b in region_bounds if b[0]<=r['xmin']<=b[2]and b[1]<=r['y']<=b[3]]
   ceiling=min(candidates)if candidates else r['y']+(group[-1]['y']-group[-2]['y']if len(group)>1 else 6000)
   r['ymax']=min(group[i+1]['y'],ceiling)if i+1<len(group)else ceiling
   r['floor_name_zh']=str(int(r['source_floor'][:-1]))+'层'if re.fullmatch(r'\d+F',r['source_floor'])else r['source_floor'];result.append(r)
 # A drawing can stack a two-level panel below a six-level panel within
 # the same frame. Its last floor band must stop at the next actual floor
 # baseline, even when that baseline has a slightly different x extent.
 for r in result:
  mid=(r['xmin']+r['xmax'])/2
  higher=[q['y']for q in result if q['y']>r['y']+pg.TOL and q['xmin']<=mid<=q['xmax']]
  if higher:r['ymax']=min(r['ymax'],min(higher))
 return result

def path_band_intervals(path,band):
 # Strictly positive overlap, so a floor boundary alone never labels two floors.
 box=[band['xmin'],band['y'],band['xmax'],band['ymax']];out=[]
 for a,b in zip(path,path[1:]):
  lo,hi=0.,1.
  for axis in [0,1]:
   delta=b[axis]-a[axis]
   if abs(delta)<1e-12:
    if not box[axis]<=a[axis]<box[axis+2]:hi=-1;break
   else:
    p,q=(box[axis]-a[axis])/delta,(box[axis+2]-a[axis])/delta
    if p>q:p,q=q,p
    lo=max(lo,p);hi=min(hi,q)
  if hi-lo>1e-7:out.append([[a[k]+lo*(b[k]-a[k])for k in [0,1]],[a[k]+hi*(b[k]-a[k])for k in [0,1]]])
 return out
