import pipe_geometry as pg_constants
"""Source auxiliary-pipe geometry recovery with auditable native curve handling."""
import math
from pipe_geometry import *
from equipment_assemblies import native_primitives,primitive_distance

def physical_auxiliary_geometry(entities,layer):
 lines=[{'a':xy(e.dxf.start),'b':xy(e.dxf.end),'system':'pending','handle':e.dxf.handle,'source_layer':layer}for e in entities if e.dxf.layer==layer and e.dxftype()=='LINE']
 arcs=[e for e in entities if e.dxf.layer==layer and e.dxftype()=='ARC'];audit=[];quarters=[];jumps=[]
 for e in arcs:
  span=(e.dxf.end_angle-e.dxf.start_angle)%360
  geom={'type':'ARC','center':xy(e.ocs().to_wcs(e.dxf.center)),'radius':e.dxf.radius,'start_angle':e.dxf.start_angle,'end_angle':e.dxf.end_angle,'source_handle':e.dxf.handle}
  if abs(span-90)<.01:
   # True source bends retain native display ARC and an effective physical arc path.
   points=[xy(e.vertices([e.dxf.start_angle+span*i/18]).__iter__().__next__())for i in range(19)]
   for i,(a,b)in enumerate(zip(points,points[1:])):quarters.append({'a':a,'b':b,'system':'pending','handle':e.dxf.handle,'source_layer':layer,'normalization':'source_physical_quarter_bend','source_display_geometry':geom,'source_handles':[e.dxf.handle]})
   # Snap only a unique tiny drafting discrepancy along the native curve tangent.
   for endpoint,ang in [(points[0],e.dxf.start_angle),(points[-1],e.dxf.end_angle)]:
    tangent=(-math.sin(math.radians(ang)),math.cos(math.radians(ang)));candidates=[]
    for li,l in enumerate(lines):
     v=sub(l['b'],l['a']);L=dist(l['a'],l['b'])
     if abs(cross(v,tangent))/max(L,1e-9)>.03:continue
     for side in ['a','b']:
      p=l[side];delta=dist(p,endpoint)
      if pg_constants.TOL<delta<=e.dxf.radius*.25 and abs(cross(sub(p,endpoint),tangent))<=e.dxf.radius*.03:candidates.append((li,side,p))
    # Duplicate source lines can share the same contact; each follows the same native endpoint.
    for li,side,p in candidates:
     lines[li][side]=endpoint;audit.append({'source_handle':lines[li]['handle'],'source_curve_handle':e.dxf.handle,'old_endpoint':p,'new_endpoint':endpoint,'rule':'bounded_source_quarter_bend_tangent_contact','distance':dist(p,endpoint)})
  else:
   jumps.append({'a':xy(e.start_point),'b':xy(e.end_point),'system':'pending','handle':e.dxf.handle,'radius':e.dxf.radius,'span':span,'source_display_geometry':geom})
 return lines+quarters,jumps,audit

def native_inline_gap_candidates(segments,symbols):
 """Bridge two opposite pipe terminals touching an identified inline symbol's actual primitives."""
 ends=open_ends(segments);bridges=[];audit=[]
 for s in symbols:
  if not s.get('bridge_allowed'):continue
  prim=native_primitives(s['entity']);bb=s['bounds'];L=dist(bb[:2],bb[2:]);touch=[(sy,p)for sy,p in ends if point_bbox(p,bb)<=pg_constants.TOL and min((primitive_distance(p,z)for z in prim),default=float('inf'))<=pg_constants.TOL]
  candidates=[]
  for i,(sy,p)in enumerate(touch):
   for sj,q in touch[i+1:]:
    if sy!=sj or not(pg_constants.TOL<dist(p,q)<=L*1.05):continue
    v=sub(q,p);atp=[s for s in segments if s['system']==sy and (dist(p,s['a'])<=pg_constants.TOL or dist(p,s['b'])<=pg_constants.TOL)];atq=[s for s in segments if s['system']==sy and (dist(q,s['a'])<=pg_constants.TOL or dist(q,s['b'])<=pg_constants.TOL)]
    if not atp or not atq:continue
    if any(abs(cross(sub(t['b'],t['a']),v))>pg_constants.TOL*dist(t['a'],t['b'])for t in atp+atq):continue
    if not any(dot(sub(z,p),v)<0 for t in atp for z in [t['a'],t['b']]if dist(z,p)>pg_constants.TOL):continue
    if not any(dot(sub(z,q),v)>0 for t in atq for z in [t['a'],t['b']]if dist(z,q)>pg_constants.TOL):continue
    candidates.append((sy,p,q))
  if len(candidates)==1:
   sy,p,q=candidates[0];bridges.append({'a':p,'b':q,'system':sy,'handle':'INLINE-'+s['handle'],'source_handles':[s['handle']],'normalization':'native_inline_two_primitive_terminal_contacts'});audit.append({'source_handle':s['handle'],'source_block_name':s['block'],'a':p,'b':q,'status':'recovered_native_two_primitive_terminal_contacts','gap_length':dist(p,q)})
  elif len(candidates)>1:audit.append({'source_handle':s['handle'],'status':'pending_ambiguous_inline_terminal_contacts','count':len(candidates)})
 return bridges,audit


def recover_inline_source_spans(segments,symbols,entities,contact_fractions=None):
 """Recover exact opposed source terminals across native inline glyphs.
 Unknown circular glyphs stay unclassified source evidence, never equipment nodes.
 """
 vs,ps,ad=build_network(segments);ends=[vs[v]for(sy,v),ids in ad.items()if sy=='physical'and len(ids)==1];bridges=[];audit=[]
 def opposed(p,q):
  if dist(p,q)<=pg_constants.TOL:return False
  axis=sub(q,p)
  pp=[s for s in segments if min(dist(p,s['a']),dist(p,s['b']))<=pg_constants.TOL];qq=[s for s in segments if min(dist(q,s['a']),dist(q,s['b']))<=pg_constants.TOL]
  return pp and qq and all(abs(cross(sub(s['b'],s['a']),axis))<=pg_constants.TOL*dist(s['a'],s['b'])for s in pp+qq)and any(dot(sub(z,p),axis)<0 for s in pp for z in [s['a'],s['b']]if dist(z,p)>pg_constants.TOL)and any(dot(sub(z,q),axis)>0 for s in qq for z in [s['a'],s['b']]if dist(z,q)>pg_constants.TOL)
 for sym in symbols:
  if not sym.get('bridge_allowed'):continue
  prim=native_primitives(sym['entity']);bb=sym['bounds'];diag=dist(bb[:2],bb[2:]);tol=max(pg_constants.TOL,(contact_fractions or {}).get(sym['block'],.025)*diag);near=[p for p in ends if point_bbox(p,bb)<=tol and min((primitive_distance(p,z)for z in prim),default=float('inf'))<=tol];pairs=[(p,q)for i,p in enumerate(near)for q in near[i+1:]if dist(p,q)<=diag*1.05 and opposed(p,q)]
  if len(pairs)==1:
   p,q=pairs[0];bridges.append({'a':p,'b':q,'system':'physical','source_system':'unclassified_water','handle':'DOCK-'+sym['handle'],'source_handles':[sym['handle']],'normalization':'native_inline_opposed_source_terminals'});audit.append({'source_handle':sym['handle'],'source_block':sym['block'],'a':p,'b':q,'rule':'unique_native_primitive_contact_pair_and_opposed_pipe_axes','status':'recovered','contact_tolerance':tol})
 for circle in entities:
  if circle.dxftype()!='CIRCLE':continue
  c=xy(circle.ocs().to_wcs(circle.dxf.center));r=circle.dxf.radius;ink=[e for e in entities if e.dxftype()=='LINE'and e.dxf.layer==circle.dxf.layer and all(dist(xy(z),c)<=r*1.05 for z in [e.dxf.start,e.dxf.end])and dist(xy(e.dxf.start),xy(e.dxf.end))>r*.2]
  if len(ink)!=2:continue
  v1=sub(xy(ink[0].dxf.end),xy(ink[0].dxf.start));v2=sub(xy(ink[1].dxf.end),xy(ink[1].dxf.start))
  if abs(cross(v1,v2))<.05*dist((0,0),v1)*dist((0,0),v2):continue
  near=[p for p in ends if abs(dist(p,c)-r)<=max(pg_constants.TOL,.02*r)];pairs=[(p,q)for i,p in enumerate(near)for q in near[i+1:]if abs(dist(p,q)-2*r)<=max(pg_constants.TOL,.03*r)and segdist(c,p,q)<=pg_constants.TOL and opposed(p,q)]
  if len(pairs)==1:
   p,q=pairs[0];handles=[circle.dxf.handle]+[e.dxf.handle for e in ink];bridges.append({'a':p,'b':q,'system':'physical','source_system':'unclassified_water','handle':'CIRCLE-GLYPH-'+circle.dxf.handle,'source_handles':handles,'normalization':'source_inline_circle_two_oblique_lines_opposed_terminal_span'});audit.append({'source_handles':handles,'a':p,'b':q,'circle_center':c,'circle_radius':r,'rule':'complete_circle_plus_two_oblique_lines_and_opposed_diameter_pipe_terminals','status':'recovered_semantic_classification_pending','semantic_class':'unknown_inline_source_glyph_not_equipment','native_display_preserved':True})
 return bridges,audit
