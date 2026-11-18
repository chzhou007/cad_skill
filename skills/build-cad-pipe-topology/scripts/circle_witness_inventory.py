"""Read-only circle/arc/ellipse witness inventory; no hydraulic decisions."""
import collections,math
from ezdxf.disassemble import recursive_decompose

def scan(doc,points,tolerance=.5):
 if tolerance<=0:raise ValueError('positive tolerance required')
 rows=[{'id':p['id'],'point':list(p['point']),'hits':[]} for p in points];stats=collections.Counter();errors=[]
 def visit(e,root,scope):
  typ=e.dxftype();stats[scope+'_'+typ]+=1
  if typ=='ELLIPSE':
   c=e.dxf.center;major=e.dxf.major_axis;a=math.hypot(major.x,major.y);b=a*e.dxf.ratio
   if a<=0 or b<=0:return
   for row in rows:
    dx,dy=row['point'][0]-c.x,row['point'][1]-c.y;u=(dx*major.x+dy*major.y)/a;v=(-dx*major.y+dy*major.x)/a;metric=math.hypot(u/a,v/b);rel='center' if math.hypot(dx,dy)<=tolerance else 'ellipse_boundary_candidate' if abs(metric-1)*min(a,b)<=tolerance else None
    if rel:row['hits'].append({'root_handle':root,'type':typ,'layer':e.dxf.layer,'center':[c.x,c.y],'major_axis':[major.x,major.y],'ratio':e.dxf.ratio,'start_param':e.dxf.start_param,'end_param':e.dxf.end_param,'relationship':rel,'scope':scope,'note':'2D candidate; parameter range and extrusion not certified'})
   return
  if typ not in ('CIRCLE','ARC'):return
  c=e.dxf.center;r=e.dxf.radius
  for row in rows:
   x,y=row['point'];dist=math.hypot(x-c.x,y-c.y);rel='center' if dist<=tolerance else 'rim' if abs(dist-r)<=tolerance else None
   if not rel:continue
   hit={'root_handle':root,'entity_handle':e.dxf.get('handle','') or '', 'type':typ,'layer':e.dxf.layer,'center':[c.x,c.y],'radius':r,'relationship':rel,'scope':scope}
   if typ=='ARC':
    start=e.dxf.start_angle%360;end=e.dxf.end_angle%360;span=(end-start)%360;angle=math.degrees(math.atan2(y-c.y,x-c.x))%360;hit.update(start_angle=start,end_angle=end,arc_span_degrees=span,point_on_arc=(rel=='rim' and (angle-start)%360<=span+0.05))
   row['hits'].append(hit)
 for entity in doc.modelspace():
  typ=entity.dxftype();handle=entity.dxf.handle
  try:
   if typ in ('CIRCLE','ARC','ELLIPSE'):visit(entity,handle,'modelspace')
   elif typ=='LWPOLYLINE':
    for e in entity.virtual_entities():visit(e,handle,'polyline_segment')
   elif typ=='INSERT':
    for e in recursive_decompose([entity]):
     if e.dxftype()=='LWPOLYLINE':
      for v in e.virtual_entities():visit(v,handle,'nested_polyline_segment')
     else:visit(e,handle,'nested_insert')
  except Exception as ex:errors.append({'handle':handle,'type':typ,'error':type(ex).__name__+': '+str(ex)[:200]})
 return {'records':rows,'visit_counts':dict(stats),'exceptions':errors,'unclassified_modelspace':dict(collections.Counter(e.dxftype() for e in doc.modelspace() if e.dxftype() in ('SPLINE','ACAD_PROXY_ENTITY'))),'scope':'Read-only geometry candidates; unsupported source forms remain unclassified; no connections inferred.'}
