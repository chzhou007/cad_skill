"""Complete native prototype matching across all model-space drafting layers.

Only straight primitive families are supported. Every transformed segment must
have a unique source witness; partial entities and overlapping INSERTs fail.
"""
import math,collections
from ezdxf import bbox
import pipe_geometry as pg
from instrumentation import source_gauges,gauge_connector_handles
from equipment_assemblies import world_line_segments

def recover_exploded_templates(doc,block_names,existing,duplicate_tolerant_blocks=()):
 source=[]
 for e in doc.modelspace():
  if e.dxftype()not in ['LINE','LWPOLYLINE']:continue
  if e.dxftype()=='LWPOLYLINE'and any(abs(p[4])>1e-10 for p in e.get_points()):continue
  for a,b in world_line_segments(e):
   if pg.dist(a,b)>pg.TOL:source.append((e,a,b))
 cell=max(pg.TOL*2,.001);index=collections.defaultdict(list)
 def key(p):return tuple(round(v/cell)for v in p)
 for i,(e,a,b)in enumerate(source):
  index[key(a)].append(i);index[key(b)].append(i)
 def witnesses(a,b):
  k=key(a);ids=set()
  for dx in [-1,0,1]:
   for dy in [-1,0,1]:ids.update(index[(k[0]+dx,k[1]+dy)])
  return [i for i in ids for _,c,d in [source[i]]if min(max(pg.dist(a,c),pg.dist(b,d)),max(pg.dist(a,d),pg.dist(b,c)))<=pg.TOL]
 result=[];used=set();gauges=source_gauges(doc)
 for name in block_names:
  if name not in doc.blocks:continue
  entities=[e for e in doc.blocks[name]if e.dxftype()not in ['TEXT','MTEXT','ATTDEF','ATTRIB']]
  if any(e.dxftype()not in ['LINE','LWPOLYLINE']or(e.dxftype()=='LWPOLYLINE'and any(abs(p[4])>1e-10 for p in e.get_points()))for e in entities):continue
  template=[p for e in entities for p in world_line_segments(e)]
  if len(template)<5:continue
  ta,tb=max(template,key=lambda ab:pg.dist(*ab));tu=pg.sub(tb,ta);tl=pg.dist(ta,tb)
  for seed,(en,sa,sb)in enumerate(source):
   if en.dxf.handle in used:continue
   for a,b in [(sa,sb),(sb,sa)]:
    scale=pg.dist(a,b)/tl
    if not .01<=scale<=10000:continue
    u=pg.sub(b,a);length=pg.dist(a,b)
    for mirror in [-1,1]:
     def transform(p):
      v=pg.sub(p,ta);x=pg.dot(v,tu)/tl*scale;y=pg.cross(tu,v)/tl*scale*mirror
      return(a[0]+(x*u[0]-y*u[1])/length,a[1]+(x*u[1]+y*u[0])/length)
     groups=[]
     for c,d in template:
      group=next((g for g in groups if min(max(pg.dist(c,g[0][0]),pg.dist(d,g[0][1])),max(pg.dist(c,g[0][1]),pg.dist(d,g[0][0])))<=pg.TOL),None)if name in duplicate_tolerant_blocks else None
      if group is None:groups.append([(c,d)])
      else:group.append((c,d))
     matches=[witnesses(transform(g[0][0]),transform(g[0][1]))for g in groups]
     if any(len(m)!=len(g)for m,g in zip(matches,groups)):continue
     ids={i for m in matches for i in m}
     if len(ids)!=len(template):continue
     hs={source[i][0].dxf.handle for i in ids}
     if hs&used:continue
     # A polyline is indivisible; never steal a few strokes from a larger shape.
     if any(sum(source[i][0].dxf.handle==h for i in ids)!=sum(e.dxf.handle==h for e,_,_ in source)for h in hs):continue
     points=[p for i in ids for p in source[i][1:]];bb=[min(p[0]for p in points),min(p[1]for p in points),max(p[0]for p in points),max(p[1]for p in points)]
     if any(pg.point_bbox(((s['bounds'][0]+s['bounds'][2])/2,(s['bounds'][1]+s['bounds'][3])/2),bb)<=pg.TOL for s in existing):continue
     head=None;extra=[]
     if name=='传感器':
      bodies=[doc.entitydb[h]for h in hs if doc.entitydb[h].dxftype()=='LWPOLYLINE'and doc.entitydb[h].closed]
      if len(bodies)!=1:continue
      body=bodies[0];bodybox=bbox.extents([body]);bodybb=[bodybox.extmin.x,bodybox.extmin.y,bodybox.extmax.x,bodybox.extmax.y];candidates=[]
      for q in gauges:
       c,r=q['center'],q['radius']
       if pg.point_bbox(c,bodybb)>3*pg.dist(bodybb[:2],bodybb[2:]):continue
       for line in doc.modelspace().query('LINE'):
        if line.dxf.handle in hs:continue
        l,m=pg.xy(line.dxf.start),pg.xy(line.dxf.end);le=pg.dist(l,m)
        if le<=pg.TOL:continue
        for p,t in [(l,m),(m,l)]:
         onbody=pg.point_bbox(p,bodybb)<=pg.TOL and any(pg.segdist(p,x,y)<=pg.TOL for x,y in world_line_segments(body))
         if onbody and abs(pg.dist(t,c)-r)<=pg.TOL and abs(pg.cross(pg.sub(c,t),pg.sub(t,p)))/le<=pg.TOL:candidates.append((q,line.dxf.handle))
      unique={q['entity'].dxf.handle for q,h in candidates}
      if len(unique)!=1:continue
      head=candidates[0][0];extra=sorted({h for q,h in candidates}|set(head['handles']))
     handles=sorted(hs|set(extra));primary=min(hs)
     item={'handle':primary,'source_handles':handles,'block':name,'bounds':bb,'insert':((bb[0]+bb[2])/2,(bb[1]+bb[3])/2),'entity':None,'bridge_allowed':False,'source_kind':'exploded_complete_native_template','recognition_rule':'all_native_prototype_segments_similarity_matched','prototype_segment_count':len(template)}
     if name.startswith('PROFILE_NATIVE_'):
      origin=transform((0,0));ex=transform((1,0));ey=transform((0,1));item['prototype_transform']={'origin':origin,'xaxis':pg.sub(ex,origin),'yaxis':pg.sub(ey,origin)}
     if head:item['head_evidence']={'source_sensor_handle':primary,'source_handles':handles,'candidate_head_handles':[head['entity'].dxf.handle],'status':'complete_tagged_head','source_head_handle':head['entity'].dxf.handle,'source_head_tag':head['tag'],'leader_handles':extra,'native_block_lead':False}
     result.append(item);used.update(hs)
 return result
