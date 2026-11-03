"""Restore one broken source pipe across a proven independent pipe, with bounded scale."""
import statistics
import pipe_geometry as pg
import math

def recover_straight_crossovers(segments,symbols,calibration,discovery_audit=None):
 if not calibration:return [],[]
 ds=[pg.dist(s['bounds'][:2],s['bounds'][2:])for s in symbols if s['block']in calibration.get('blocks',[])]
 limit=calibration.get('maximum_gap_native_units')
 if limit is None:
  if not ds:return [],[]
  limit=statistics.median(ds)*float(calibration['maximum_gap_symbol_diagonals'])
 minimum_sine=math.sin(math.radians(calibration.get('minimum_crossing_angle_degrees',20)))
 def cls(s):return s.get('source_system',s['system'])
 def group(s):
  service=cls(s)
  if service in [None,'unclassified_water','pending']and s.get('source_layer')in calibration.get('verified_unknown_service_layers',[]):return ('verified_source_layer',s['source_layer'])
  return service
 def record(p,q,sp,sq):
  row={'a':p,'b':q,'source_handles':sorted(set(hs(sp)+hs(sq))),'source_layers':[sp.get('source_layer'),sq.get('source_layer')],'source_services':[cls(sp),cls(sq)],'status':'pending','reason':'candidate_discovered_before_service_filter'}
  if discovery_audit is not None:discovery_audit.append(row)
  return row
 def hs(s):return s.get('source_handles',[s['handle']])
 def parallel(u,v):return abs(pg.cross(u,v))<=pg.TOL*max(pg.dist((0,0),u),pg.dist((0,0),v))
 def opposed_tail_alignment(p,q,u,v):
  axis=pg.sub(q,p);gap=pg.dist(p,q);lu=pg.dist((0,0),u);lv=pg.dist((0,0),v)
  if not lu or not lv:return None
  offsets=[abs(pg.cross(axis,u))/lu,abs(pg.cross(axis,v))/lv]
  if parallel(u,axis)and parallel(v,axis):return {'kind':'strict_collinear','tail_offsets':offsets}
  # Optional source-profile drafting precision. Do not relax global incidence,
  # occupied-span checks, crossing witnesses or native equipment contacts.
  bound=calibration.get('maximum_tail_offset_native_units')
  angle=calibration.get('maximum_tail_angle_degrees')
  if bound is None or angle is None:return None
  sine=math.sin(math.radians(float(angle)))
  if max(offsets)>float(bound)or max(offsets)/gap>sine:return None
  if abs(pg.cross(u,v))/(lu*lv)>sine:return None
  return {'kind':'profile_bounded_drafting_offset','tail_offsets':offsets,'maximum_tail_offset':bound,'maximum_tail_angle_degrees':angle}
 ends=[(p,o,s)for s in segments for p,o in [(s['a'],s['b']),(s['b'],s['a'])]];matches={};discovered_by_key={}
 for i,(p,op,sp)in enumerate(ends):
  for q,oq,sq in ends[i+1:]:
   length=pg.dist(p,q)
   if not pg.TOL<length<=limit:continue
   axis=pg.sub(q,p);u=pg.sub(op,p);v=pg.sub(oq,q)
   if pg.dot(u,axis)>=0 or pg.dot(v,axis)<=0:continue
   alignment=opposed_tail_alignment(p,q,u,v)
   if alignment is None:continue
   row=record(p,q,sp,sq)
   if alignment['kind']=='profile_bounded_drafting_offset':row['tail_alignment']=alignment
   occupied=False
   for s in segments:
    w=pg.sub(s['b'],s['a'])
    if not parallel(w,axis)or pg.segdist(s['a'],p,q)>pg.TOL and pg.segdist(s['b'],p,q)>pg.TOL:continue
    t0=pg.dot(pg.sub(s['a'],p),axis)/length;t1=pg.dot(pg.sub(s['b'],p),axis)/length
    if min(length,max(t0,t1))-max(0,min(t0,t1))>pg.TOL:occupied=True;break
   if occupied:row['reason']='span_already_occupied';continue
   if calibration.get('exclude_symbol_bounds'):
    from instrumentation import box_contact
    if any(box_contact(p,q,s['bounds'],tol=pg.TOL)for s in symbols):row['reason']='native_symbol_interference';continue
   crossings=[]
   def add(point,witnesses,kind):
    if not any(pg.dist(point,c['crossing'])<=pg.TOL for c in crossings):crossings.append({'crossing':point,'crossed_handle':witnesses[0]['handle'],'crossed_handles':sorted({h for s in witnesses for h in hs(s)}),'crossed_source_system':cls(witnesses[0]),'crossing_evidence':kind})
   for s in segments:
    w=pg.sub(s['b'],s['a'])
    if abs(pg.cross(axis,w))<minimum_sine*length*pg.dist(s['a'],s['b']):continue
    hit=pg.intersection(p,q,s['a'],s['b'])
    if hit:add(hit,[s],'native_pipe_interior')
   for s in segments:
    for tip,tail in [(s['a'],s['b']),(s['b'],s['a'])]:
     if not pg.on(tip,p,q)or min(pg.dist(tip,p),pg.dist(tip,q))<=pg.TOL:continue
     ray=pg.sub(tail,tip)
     if abs(pg.cross(axis,ray))<minimum_sine*length*pg.dist(tip,tail):continue
     for t in segments:
      if cls(t)!=cls(s):continue
      for a,b in [(t['a'],t['b']),(t['b'],t['a'])]:
       other=pg.sub(b,tip)
       if pg.dist(a,tip)<=pg.TOL and pg.dot(ray,other)<0 and parallel(ray,other):add(tip,[s,t],'opposite_collinear_native_pipe_rays')
   row['crossings']=crossings
   if len(crossings)!=1:row['reason']='no_independent_crossed_pipe'if not crossings else'multiple_independent_crossings';continue
   if group(sp)!=group(sq):row['reason']='conflicting_source_groups';continue
   if group(sp)in [None,'unclassified_water','pending']:row['reason']='source_group_not_verified_despite_crossing_evidence';continue
   row['reason']='qualified_unique_source_group_and_crossing'
   key=tuple(sorted([tuple(round(v,5)for v in p),tuple(round(v,5)for v in q)]));matches[key]=(p,q,sp,sq,crossings);discovered_by_key[key]=row
 spans=[];audit=[];rows=list(matches.values())
 for p,q,sp,sq,crossings in rows:
  key=tuple(sorted([tuple(round(v,5)for v in p),tuple(round(v,5)for v in q)]));row=discovered_by_key[key]
  if sum(any(pg.dist(a,b)<=pg.TOL for a in [p,q]for b in [x,y])for x,y,*_ in rows)!=1:row['reason']='ambiguous_terminal_pairing';continue
  row.update(status='applied',reason='unique_source_group_opposed_tails_independent_crossed_pipe')
  handles=sorted(set(hs(sp)+hs(sq)));handle='CROSS-GAP-'+handles[0]
  spans.append({'a':p,'b':q,'system':sp['system'],'source_system':cls(sp),'handle':handle,'source_handles':handles,'normalization':'source_straight_crossover_gap','crossings':crossings,'crossing_connectivity':'independent_pipes_no_junction','relative_elevation':'unknown'})
  audit.append({'a':p,'b':q,'source_handles':handles,'gap_length':pg.dist(p,q),'maximum_gap':limit,'calibration_blocks':calibration.get('blocks',[]),'crossings':crossings,'status':'normalized','crossing_connectivity':'independent_pipes_no_junction','relative_elevation':'unknown'})
  if 'tail_alignment'in row:audit[-1]['tail_alignment']=row['tail_alignment']
 for span,row in zip(spans,audit):
  sp=next(s for s in segments if set(hs(s))&set(row['source_handles'])and s.get('source_layer')in calibration.get('verified_unknown_service_layers',[]))if span['source_system']in [None,'unclassified_water','pending']else None
  if sp is not None:
   span['source_layer']=sp['source_layer'];row['source_group_evidence']={'kind':'verified_source_layer','source_layer':sp['source_layer'],'hydraulic_service':'unclassified','rule':'physical_source_group_does_not_require_hydraulic_service_assignment'}
 return spans,audit

def recover_straight_crossovers_legacy(segments,symbols,calibration):
 if not calibration:return [],[]
 ds=[pg.dist(s['bounds'][:2],s['bounds'][2:])for s in symbols if s['block']in calibration['blocks']]
 if not ds:return [],[]
 limit=statistics.median(ds)*float(calibration['maximum_gap_symbol_diagonals']);vs,ps,adj=pg.build_network(segments);ends=[(v,vs[v],ps[ids[0]])for (sy,v),ids in adj.items()if sy=='physical'and len(ids)==1];matches=[]
 def source_class(piece):return {s.get('source_system')for s in segments if set(s.get('source_handles',[s['handle']]))&set(piece['source_handles'])}-{None,'unclassified_water'}
 for i,(vi,p,pi)in enumerate(ends):
  for vj,q,pj in ends[i+1:]:
   gap=pg.dist(p,q)
   if not pg.TOL<gap<=limit or source_class(pi)!=source_class(pj)or len(source_class(pi))!=1:continue
   axis=pg.sub(q,p);tails=[(pi,p,-1),(pj,q,1)];ok=True
   for piece,terminal,sign in tails:
    other=vs[next(v for v in piece['vertices']if pg.dist(vs[v],terminal)>pg.TOL)]
    if abs(pg.cross(pg.sub(other,terminal),axis))>pg.TOL*gap or pg.dot(pg.sub(other,terminal),axis)*sign<=0:ok=False
   if not ok:continue
   crossings=[]
   for s in segments:
    hit=pg.intersection(p,q,s['a'],s['b'])
    if hit and not any(pg.dist(hit,x['crossing'])<=pg.TOL for x in crossings):crossings.append({'crossing':hit,'crossed_handle':s['handle'],'crossed_source_system':s.get('source_system')})
   if len(crossings)!=1:continue
   matches.append((p,q,pi,pj,crossings))
 spans=[];audit=[]
 for p,q,pi,pj,crossings in matches:
  if sum(any(pg.dist(z,t)<=pg.TOL for z in [p,q]for t in [u,v])for u,v,*_ in matches)!=1:continue
  hs=sorted(set(pi['source_handles']+pj['source_handles']));sy=next(iter(source_class(pi)));h='CROSS-GAP-'+hs[0]
  spans.append({'a':p,'b':q,'system':'physical','source_system':sy,'handle':h,'source_handles':hs,'normalization':'source_straight_crossover_gap','crossing_connectivity':'independent_pipes_no_junction','relative_elevation':'unknown'})
  audit.append({'a':p,'b':q,'source_handles':hs,'gap_length':pg.dist(p,q),'maximum_gap':limit,'calibration_blocks':calibration['blocks'],'crossings':crossings,'status':'normalized','crossing_connectivity':'independent_pipes_no_junction','relative_elevation':'unknown'})
 return spans,audit
