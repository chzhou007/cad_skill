"""Audited source geometry normalization shared by drawing-family adapters."""
import math
import pipe_geometry as pg
from straight_crossovers import recover_straight_crossovers

def exclude_paired_bar_display_tails(segments,doc,config):
 if not config:return list(segments),[]
 bars=[e for e in doc.modelspace().query('LINE')if e.dxf.layer in config['bar_layers']];removed=set();audit=[]
 for i,s in enumerate(segments):
  length=pg.dist(s['a'],s['b'])
  if not pg.TOL<length<=config['maximum_length']:continue
  for tip,base in [(s['a'],s['b']),(s['b'],s['a'])]:
   if any(j!=i and t['system']==s['system']and pg.on(tip,t['a'],t['b'])for j,t in enumerate(segments)):continue
   rays=set()
   for j,t in enumerate(segments):
    if j==i or t['system']!=s['system']or not pg.on(base,t['a'],t['b']):continue
    for q in [t['a'],t['b']]:
     if pg.dist(base,q)>pg.TOL:rays.add(tuple(round(v/pg.dist(base,q),5)for v in pg.sub(q,base)))
   if len(rays)!=2:continue
   u=pg.sub(tip,base);found=[]
   for e in bars:
    a=tuple(e.dxf.start)[:2];b=tuple(e.dxf.end)[:2];v=pg.sub(b,a);width=pg.dist(a,b);c=((a[0]+b[0])/2,(a[1]+b[1])/2);delta=pg.sub(c,tip);along=pg.dot(delta,u)/length
    if .2*length<=width<=3*length and abs(pg.dot(u,v))<=.001*length*width and abs(pg.cross(delta,u))/length<=pg.TOL and -pg.TOL<=along<=length:found.append((along,e.dxf.handle))
   if len(found)==2 and min(abs(t[0])for t in found)<=pg.TOL and abs(found[0][0]-found[1][0])>pg.TOL:
    removed.add(i);audit.append(dict(source_handles=s.get('source_handles',[s['handle']]),bar_handles=[t[1]for t in found],base=base,tip=tip,rule='profile_verified_paired_bar_dead_display_tail',status='display_excluded'));break
 return [s for i,s in enumerate(segments)if i not in removed],audit

def snap_near_junction_endpoints(segments,config):
 """Extend a dangling tail only along its own axis to a unique same-class main."""
 if not config:return list(segments),[]
 result=[dict(s)for s in segments];audit=[]
 def cls(s):
  service=s.get('source_system',s['system'])
  if service in [None,'pending','unclassified_water']and s.get('source_layer')in config.get('verified_unknown_service_layers',[]):return ('source_layer_group',s['source_layer'])
  return service
 for i,s in enumerate(result):
  if cls(s)in [None,'pending','unclassified_water']or s.get('crossing_connectivity'):continue
  length=pg.dist(s['a'],s['b']);limit=min(config.get('discovery_maximum_gap',config['maximum_gap']),length*config['maximum_ratio'])
  if length<=pg.TOL or limit<=pg.TOL:continue
  for end,other in [('a','b'),('b','a')]:
   tip=s[end]
   if any(j!=i and t['system']==s['system']and pg.on(tip,t['a'],t['b'])for j,t in enumerate(result)):continue
   u=pg.sub(tip,s[other]);probe=(tip[0]+u[0]/length*limit,tip[1]+u[1]/length*limit);inner=(tip[0]-u[0]/length*limit,tip[1]-u[1]/length*limit);hits=[]
   for j,t in enumerate(result):
    if j==i or cls(t)!=cls(s)or t.get('crossing_connectivity'):continue
    v=pg.sub(t['b'],t['a'])
    if abs(pg.cross(u,v))<math.sin(math.radians(config.get('minimum_angle_degrees',20)))*length*pg.dist(t['a'],t['b']):continue
    p=pg.intersection(inner,probe,t['a'],t['b'])
    if not p or min(pg.dist(p,t['a']),pg.dist(p,t['b']))<=pg.TOL:continue
    if any(pg.on(q,tip,p)for q in config.get('protected_points',[])):continue
    hits.append((p,t))
   if len(hits)!=1:continue
   if pg.dist(tip,hits[0][0])>config['maximum_gap']:
    audit.append(dict(source_handles=s.get('source_handles',[s['handle']]),main_source_handles=hits[0][1].get('source_handles',[hits[0][1]['handle']]),original_endpoint=tip,candidate_endpoint=hits[0][0],gap_length=pg.dist(tip,hits[0][0]),status='pending',reason='Outside source-profile verified junction contact precision; graph and equipment bindings unchanged'));continue
   p,t=hits[0];s[end]=p;audit.append(dict(source_handles=s.get('source_handles',[s['handle']]),main_source_handles=t.get('source_handles',[t['handle']]),original_endpoint=tip,semantic_endpoint=p,added_length=pg.dist(tip,p),action='extend'if pg.dot(pg.sub(p,tip),u)>0 else'trim',rule='unique_same_class_axial_tail_contact_to_main_interior',status='applied'))
 return result,audit

def trim_elbow_overshoots(segments,config):
 if not config:return list(segments),[]
 result=[dict(s)for s in segments];audit=[]
 for i,s in enumerate(result):
  for endpoint,other in [('a','b'),('b','a')]:
   tip=s[endpoint];length=pg.dist(s['a'],s['b'])
   if any(j!=i and t['system']==s['system']and pg.on(tip,t['a'],t['b'])for j,t in enumerate(result)):continue
   candidates=[]
   for j,t in enumerate(result):
    if j==i or t['system']!=s['system']:continue
    for p,z in [(t['a'],t['b']),(t['b'],t['a'])]:
     stub=pg.dist(tip,p)
     if not pg.TOL<stub<=config['maximum_length']or stub/length>config['maximum_ratio']or not pg.on(p,s['a'],s['b']):continue
     v=pg.sub(z,p);u=pg.sub(s[other],p)
     if abs(pg.cross(u,v))<math.sin(math.radians(config['minimum_angle_degrees']))*pg.dist(p,z)*pg.dist(s[other],p):continue
     if any(k not in [i,j]and r['system']==s['system']and pg.on(p,r['a'],r['b'])for k,r in enumerate(result)):continue
     if any(k!=i and r['system']==s['system']and(any(pg.on(q,p,tip)and pg.dist(q,p)>pg.TOL for q in [r['a'],r['b']])or pg.intersection(p,tip,r['a'],r['b'])is not None)for k,r in enumerate(result)):continue
     if any(pg.on(q,p,tip)for q in config.get('protected_points',[])):continue
     candidates.append(p)
   uniq={tuple(round(v,6)for v in p):p for p in candidates}
   if len(uniq)==1:
    p=next(iter(uniq.values()));audit.append({'source_handles':s.get('source_handles',[s['handle']]),'source_handle_scope':s.get('source_handle_scope','native_entity'),'original_endpoint':tip,'semantic_endpoint':p,'removed_length':pg.dist(tip,p),'rule':'dangling_micro_overshoot_at_two_ray_elbow','status':'applied'});s[endpoint]=p
 return result,audit

def normalize_segments(segments,symbols,config):
 cleaned,trims=trim_elbow_overshoots(segments,config.get('elbow_overshoot'))
 bridges,crossovers=recover_straight_crossovers(cleaned,symbols,config.get('straight_crossovers'))
 return cleaned+bridges,{'elbow_overshoots':trims,'crossovers':crossovers,'relative_elevation':'unknown'}
