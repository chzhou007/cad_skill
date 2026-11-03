"""Source-proven measurement assemblies; capillaries never merge hydraulic pipes."""
import re,math
from ezdxf import bbox
import pipe_geometry as pg
from equipment_assemblies import native_primitives

def bounds(e):
 b=bbox.extents([e]);return [b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y]if b.has_data else None

def box_contact(a,b,bb,tol=None):
 # Inclusive segment/box clipping: a pipe on a symbol's boundary is a contact.
 tol=pg.TOL if tol is None else tol;lo,hi=0.,1.
 for k in [0,1]:
  delta=b[k]-a[k];mn=bb[k]-tol;mx=bb[k+2]+tol
  if abs(delta)<1e-12:
   if not mn<=a[k]<=mx:return False
  else:
   t0,t1=sorted([(mn-a[k])/delta,(mx-a[k])/delta]);lo=max(lo,t0);hi=min(hi,t1)
   if lo>hi:return False
 return True

def source_gauges(doc):
 found=[];m=list(doc.modelspace())
 for text in m:
  if text.dxftype()not in ['TEXT','MTEXT']:continue
  value=(text.plain_text()if text.dxftype()=='MTEXT'else text.dxf.text).strip()
  if not re.fullmatch(r'(?:DPS|DPIT|TIT|PIT|FIT|SFIT)(?:-[A-Za-z0-9]+)?',value):continue
  bb=bounds(text)
  if not bb:continue
  p=((bb[0]+bb[2])/2,(bb[1]+bb[3])/2)
  circles=[c for c in m if c.dxftype()=='CIRCLE'and c.dxf.layer==text.dxf.layer and pg.dist(p,pg.xy(c.dxf.center))<=c.dxf.radius*.8]
  if len(circles)!=1:continue
  c=circles[0];center=pg.xy(c.dxf.center);radius=c.dxf.radius;hs=[c.dxf.handle,text.dxf.handle]
  for line in m:
   if line.dxftype()!='LINE' or line.dxf.layer!=c.dxf.layer:continue
   a,b=pg.xy(line.dxf.start),pg.xy(line.dxf.end);mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
   if all(abs(pg.dist(p,center)-radius)<=max(pg.TOL,.02*radius)for p in [a,b])and pg.dist(mid,center)<=.02*radius and 1.9*radius<pg.dist(a,b)<2.05*radius:hs.append(line.dxf.handle)
  found.append({'entity':c,'text_entity':text,'kind':value.split('-')[0],'tag':value,'center':center,'radius':radius,'handles':hs})
 return found

def measurement_assemblies(doc,segments,symbols,config):
 """Fold only complete local DPS capillary loops with two proven main taps.
 A separate panel signature retains its real two risers and never joins them.
 """
 gauges=source_gauges(doc);groups=[];removed=set();consumed=set();m=list(doc.modelspace())
 main=[s for s in segments if s.get('source_layer')in config.get('hydraulic_main_layers',[])];cap_layers=config.get('capillary_layers',[])
 for gauge in gauges:
  if gauge['kind']!='DPS':continue
  c,r=gauge['center'],gauge['radius'];near=[s for s in segments if s.get('source_layer')in cap_layers and all(pg.dist(p,c)<=r*9 for p in [s['a'],s['b']])]
  if not near:continue
  # Drafting layers can be shared by main pipe and measuring capillary. Start
  # at the two real DPS boundary tails and follow native ends/valves, so nearby
  # disconnected pump/main strokes cannot contaminate the loop signature.
  candidate_handles=set()
  if set(config.get('hydraulic_main_layers',[]))&set(cap_layers):
   connected={i for i,s in enumerate(near)if any(abs(pg.dist(p,c)-r)<=pg.TOL for p in [s['a'],s['b']])}
   changed=True
   while changed:
    changed=False
    for j,s in enumerate(near):
     if j in connected:continue
     if any(any(pg.dist(p,q)<=pg.TOL or any(pg.point_bbox(p,z['bounds'])<=r*.12 and pg.point_bbox(q,z['bounds'])<=r*.12 for z in symbols)for p in [s['a'],s['b']]for q in [near[i]['a'],near[i]['b']])for i in connected):connected.add(j);changed=True
   candidates=near;near=[s for i,s in enumerate(candidates)if i in connected]
   candidate_handles={s['handle']for s in candidates}
  main_witnesses=[s for s in main if s['handle']not in candidate_handles]
  taps=[]
  for s in near:
   for p in [s['a'],s['b']]:
    if any(pg.on(p,t['a'],t['b'])for t in main_witnesses)and not any(pg.dist(p,z)<=pg.TOL for z in taps):taps.append(p)
  # Two source main taps plus a DPS body contacted by two distinct capillary tails.
  body_contacts=[p for s in near for p in [s['a'],s['b']]if abs(pg.dist(p,c)-r)<=pg.TOL]
  if len(taps)!=2 or len(body_contacts)!=2:continue
  handles={s['handle']for s in near};xs=[p[0]for s in near for p in [s['a'],s['b']]];ys=[p[1]for s in near for p in [s['a'],s['b']]];bb=[min(xs)-r*.15,min(ys)-r*.15,max(xs)+r*.15,max(ys)+r*.15]
  native=[sym for sym in symbols if pg.point_bbox(((sym['bounds'][0]+sym['bounds'][2])/2,(sym['bounds'][1]+sym['bounds'][3])/2),bb)<=pg.TOL and any(box_contact(s['a'],s['b'],sym['bounds'])for s in near)]
  # Each disconnected capillary gap must be bridged by a native valve or the DPS circle.
  ends=[p for s in near for p in [s['a'],s['b']]if not any(pg.dist(p,z)<=pg.TOL for z in taps)and abs(pg.dist(p,c)-r)>pg.TOL and sum(min(pg.dist(p,t['a']),pg.dist(p,t['b']))<=pg.TOL for t in near)==1]
  def crossed_gap(p):
   for q in ends:
    if not pg.TOL<pg.dist(p,q)<=r:continue
    if not any(pg.intersection(p,q,s['a'],s['b'])is not None for s in main):continue
    axis=pg.sub(q,p);tails=[s for s in near if min(pg.dist(p,s['a']),pg.dist(p,s['b']),pg.dist(q,s['a']),pg.dist(q,s['b']))<=pg.TOL]
    if len(tails)==2 and all(abs(pg.cross(pg.sub(s['b'],s['a']),axis))<=pg.TOL*pg.dist(s['a'],s['b'])for s in tails):return True
   return False
  if any(not any(pg.point_bbox(p,sym['bounds'])<=r*.12 for sym in native)and not crossed_gap(p)for p in ends):continue
  gauge_neighbors=[q for q in gauges if q['kind']=='DPIT'and pg.dist(q['center'],c)<=r*4]
  hs=handles|set(gauge['handles'])|{h for sym in native for h in sym.get('source_handles',[sym['handle']])}
  for q in gauge_neighbors:hs.update(q['handles'])
  for q in gauge_neighbors:hs.update(gauge_connector_handles(doc,gauge,q))
  groups.append({'id':'INSTR-'+gauge['entity'].dxf.handle,'label':'Differential Pressure Assembly','source_kind':'source_measurement_assembly','source_handles':sorted(hs),'native_capillary_handles':sorted(handles),'component_handles':[sym['handle']for sym in native],'attachment_points':taps,'display_center':c,'hydraulic_connection':False,'rule':'complete_DPS_circle_and_tag_two_main_taps_two_body_contacts_all_gaps_at_native_valves'})
  removed.update(handles);consumed.update(sym['handle']for sym in native)
 # Full native panel: closed source enclosure, >=2 DPS and >=2 DPIT inside,
 # two typed risers terminate inside. No caption/table-only equipment inference.
 for shape in doc.modelspace().query('LWPOLYLINE'):
  if not shape.closed or len(shape)!=4:continue
  bb=bounds(shape);inside=[q for q in gauges if pg.point_bbox(q['center'],bb)<=pg.TOL]
  if sum(q['kind']=='DPS'for q in inside)<2 or sum(q['kind']=='DPIT'for q in inside)<2:continue
  rr=max(q['radius']for q in inside)
  if pg.dist(bb[:2],bb[2:])>rr*30:continue
  taps=[]
  for s in main:
   for p in [s['a'],s['b']]:
    if pg.point_bbox(p,bb)<=pg.TOL and not any(pg.dist(p,z)<=pg.TOL for z in taps):taps.append(p)
  if len(taps)!=2:continue
  hs=[]
  for e in m:
   eb=bounds(e)
   if eb and eb[0]>=bb[0]-pg.TOL and eb[1]>=bb[1]-pg.TOL and eb[2]<=bb[2]+pg.TOL and eb[3]<=bb[3]+pg.TOL:hs.append(e.dxf.handle)
  members=[sym['handle']for sym in symbols if set(sym.get('source_handles',[sym['handle']]))<=set(hs)];consumed.update(members)
  groups.append({'id':'INSTR-PANEL-'+shape.dxf.handle,'label':'Differential Pressure Panel','source_kind':'source_measurement_panel','source_handles':sorted(hs),'native_capillary_handles':[],'component_handles':members,'attachment_points':taps,'display_center':((bb[0]+bb[2])/2,(bb[1]+bb[3])/2),'hydraulic_connection':False,'rule':'closed_native_panel_two_DPS_two_DPIT_two_independent_typed_riser_terminals'})
 kept=[s for s in segments if not set(s.get('source_handles',[s['handle']]))&removed and not(s.get('normalization')and set(s.get('source_handles',[]))&consumed)]
 return kept,groups,consumed

def gauge_connector_handles(doc,left,right):
 """A native straight stroke joining the facing boundaries of two source circles.
 Cross-layer drawing is allowed only with both exact geometric end contacts.
 """
 c,d=left['center'],right['center'];length=pg.dist(c,d);r,s=left['radius'],right['radius']
 if length<=r+s:return []
 axis=((d[0]-c[0])/length,(d[1]-c[1])/length)
 p=(c[0]+axis[0]*r,c[1]+axis[1]*r);q=(d[0]-axis[0]*s,d[1]-axis[1]*s);tol=max(pg.TOL,.02*min(r,s))
 return [e.dxf.handle for e in doc.modelspace().query('LINE')if any(pg.dist(a,p)<=tol and pg.dist(b,q)<=tol for a,b in [(pg.xy(e.dxf.start),pg.xy(e.dxf.end)),(pg.xy(e.dxf.end),pg.xy(e.dxf.start))])]

def exploded_bowties(doc,layers):
 """Complete four-stroke bowtie, not a single crossed pair or rectangle."""
 lines=[e for e in doc.modelspace().query('LINE')if e.dxf.layer in layers];byend={};result=[]
 def key(p):return(round(p[0]/pg.TOL),round(p[1]/pg.TOL))
 for i,e in enumerate(lines):
  for p in [pg.xy(e.dxf.start),pg.xy(e.dxf.end)]:byend.setdefault((e.dxf.layer,key(p)),[]).append(i)
 visited=set()
 for i,e in enumerate(lines):
  if i in visited:continue
  todo=[i];ids=set()
  while todo:
   j=todo.pop()
   if j in ids:continue
   ids.add(j);t=lines[j]
   for p in [pg.xy(t.dxf.start),pg.xy(t.dxf.end)]:todo += [k for k in byend[(t.dxf.layer,key(p))]if k not in ids]
  visited.update(ids)
  if len(ids)!=4:continue
  es=[lines[j]for j in sorted(ids)];pts=[(pg.xy(e.dxf.start),pg.xy(e.dxf.end))for e in es];endkeys={key(p)for ab in pts for p in ab}
  if len(endkeys)!=4 or any(sum(key(p)==k for ab in pts for p in ab)!=2 for k in endkeys):continue
  crossed=[(a,b)for k,a in enumerate(pts)for b in pts[k+1:]if pg.intersection(*a,*b)is not None]
  if len(crossed)!=1:continue
  diag1,diag2=crossed[0];others=[ab for ab in pts if ab not in [diag1,diag2]];u=pg.sub(others[0][1],others[0][0]);v=pg.sub(others[1][1],others[1][0]);l1=pg.dist(*others[0]);l2=pg.dist(*others[1])
  if l1<=pg.TOL*4 or abs(l1-l2)>.03*max(l1,l2)or abs(pg.cross(u,v))>.03*l1*l2:continue
  allp=[p for ab in pts for p in ab];bb=[min(p[0]for p in allp),min(p[1]for p in allp),max(p[0]for p in allp),max(p[1]for p in allp)];span=pg.dist(((others[0][0][0]+others[0][1][0])/2,(others[0][0][1]+others[0][1][1])/2),((others[1][0][0]+others[1][1][0])/2,(others[1][0][1]+others[1][1][1])/2))
  if not .5< span/l1 <2:continue
  hs=sorted(e.dxf.handle for e in es);result.append({'handle':hs[0],'source_handles':hs,'block':'EXPLODED_ISOLATION_VALVE','bounds':bb,'insert':((bb[0]+bb[2])/2,(bb[1]+bb[3])/2),'bridge_allowed':False,'source_kind':'exploded_complete_bowtie','semantic_status':'valve_subtype_pending','entity':None})
 return result

def symbol_pipe_contacts(symbol,edges,doc,extension_blocks=(),anchor_rules=()):
 """Prefer actual source primitive terminal contacts to a bounding box guess."""
 prim=native_primitives(symbol['entity'])if symbol.get('entity')is not None else [doc.entitydb[h]for h in symbol.get('source_handles',[])];anchors=[]
 for pe in prim:
  if pe.dxftype()=='LINE':anchors += [pg.xy(pe.dxf.start),pg.xy(pe.dxf.end)]
 direct={e['edge_id']for e in edges if any(any(pg.segdist(p,a,b)<=pg.TOL for a,b in zip(e['path_points'],e['path_points'][1:]))for p in anchors)}
 if direct:return [e for e in edges if e['edge_id']in direct],'native_primitive_endpoint_on_pipe'
 if anchor_rules:
  from native_inline_anchors import anchor_contacts
  anchored=anchor_contacts(symbol,edges,doc,anchor_rules)
  if anchored is not None:return anchored,'verified_complete_native_prototype_anchor_on_source_pipe'
 if symbol['block']in extension_blocks:
  bb=symbol['bounds'];diag=pg.dist(bb[:2],bb[2:]);extension=[]
  for line in list(doc.modelspace().query('LINE'))+[pe for pe in prim if pe.dxftype()=='LINE']:
   body=symbol.get('entity')or doc.entitydb[symbol['handle']]
   if line.dxf.handle is not None and line.dxf.layer!=body.dxf.layer:continue
   a,b=pg.xy(line.dxf.start),pg.xy(line.dxf.end)
   if not (pg.point_bbox(a,bb)<=pg.TOL or pg.point_bbox(b,bb)<=pg.TOL):continue
   if pg.dist(a,b)>diag*.75:continue
   for p in [a,b]:
    for e in edges:
     for u,v in zip(e['path_points'],e['path_points'][1:]):
      if pg.segdist(p,u,v)>max(pg.TOL,.05*diag):continue
      axis=pg.sub(b,a);pipe=pg.sub(v,u)
      if abs(pg.dot(axis,pipe))<=.1*pg.dist(a,b)*pg.dist(u,v):extension.append(e['edge_id'])
  if len(set(extension))==1:return [e for e in edges if e['edge_id']in extension],'native_sensor_extension_leader_bounded_axis_contact'
 return [e for e in edges if any(box_contact(a,b,symbol['bounds'])for a,b in zip(e['path_points'],e['path_points'][1:]))],'inclusive_source_bounds_contact'

def instrument_head_match(symbol,doc,gauges):
 """Match a tagged head through actual sensor strokes, regardless of insert mirroring.
 Native block leads and combined diameter/leader strokes are both source evidence.
 Multiple paths to the same head are one match; multiple distinct heads stay pending.
 """
 if symbol.get('head_evidence'):return dict(symbol['head_evidence'])
 hs=set(symbol.get('source_handles',[symbol['handle']]));audit={'source_sensor_handle':symbol['handle'],'source_handles':sorted(hs),'candidate_head_handles':[],'status':'not_sensor'}
 if symbol['block']!='传感器' or symbol.get('entity')is None:return audit
 bb=symbol['bounds'];diag=pg.dist(bb[:2],bb[2:]);prim=native_primitives(symbol['entity']);native=[e for e in prim if e.dxftype()=='LINE'];matches={}
 for q in gauges:
  c,r=q['center'],q['radius'];tol=max(pg.TOL,.02*r)
  if q['entity'].dxf.layer!=symbol['entity'].dxf.layer or pg.point_bbox(c,bb)>3*diag:continue
  for line in native+list(doc.modelspace().query('LINE')):
   internal=line in native
   if not internal and line.dxf.layer!=symbol['entity'].dxf.layer:continue
   a,b=pg.xy(line.dxf.start),pg.xy(line.dxf.end);length=pg.dist(a,b)
   if length<=pg.TOL or length>diag+2.05*r:continue
   # The line must contact the source sensor body/lead, not merely pass near it.
   body_contact=any(pg.point_bbox(p,bb)<=pg.TOL for p in [a,b])
   aligned=any(abs(pg.cross(pg.sub(b,a),pg.sub(e.dxf.end,e.dxf.start)))<=.02*length*pg.dist(pg.xy(e.dxf.start),pg.xy(e.dxf.end)) for e in native)
   if not body_contact or not aligned:continue
   # A real end reaches the circle or its interior; the shaft follows a radius.
   if min(pg.dist(a,c),pg.dist(b,c))>r+tol or pg.segdist(c,a,b)>r+tol:continue
   if abs(pg.cross(pg.sub(c,a),pg.sub(b,a)))/length>tol:continue
   record=matches.setdefault(q['entity'].dxf.handle,{'gauge':q,'leader_handles':set(),'native_block_lead':False})
   if internal:record['native_block_lead']=True
   else:record['leader_handles'].add(line.dxf.handle)
 audit['candidate_head_handles']=sorted(matches)
 audit['status']='complete_tagged_head'if len(matches)==1 else 'pending_ambiguous_heads'if matches else 'pending_no_proven_head'
 if len(matches)==1:
  record=next(iter(matches.values()));q=record['gauge'];hs.update(q['handles']);hs.update(record['leader_handles']);audit.update(source_head_handle=q['entity'].dxf.handle,source_head_tag=q['tag'],leader_handles=sorted(record['leader_handles']),native_block_lead=record['native_block_lead'])
 if not matches:
  nearby=[]
  for q in gauges:
   c,r=q['center'],q['radius']
   if q['entity'].dxf.layer!=symbol['entity'].dxf.layer or pg.point_bbox(c,bb)>1.5*diag:continue
   if not any(abs(pg.cross(pg.sub(c,pg.xy(e.dxf.start)),pg.sub(e.dxf.end,e.dxf.start)))/pg.dist(pg.xy(e.dxf.start),pg.xy(e.dxf.end))<=.05*diag for e in native):continue
   nearby.append({'source_head_handle':q['entity'].dxf.handle,'source_tag':q['tag'],'source_center':c,'body_to_circle_clearance':max(0,pg.point_bbox(c,bb)-r),'status':'nearby_source_head_only_not_assigned_without_native_leader'})
  audit['nearby_unassigned_heads']=nearby
 audit['source_handles']=sorted(hs);return audit

def symbol_display_handles(symbol,doc,gauges):
 return instrument_head_match(symbol,doc,gauges)['source_handles']

def source_reference_regions(doc,source_names):
 """A source legend title plus a dense cluster of explicit known legend captions."""
 regions=[];texts=[e for e in doc.modelspace()if e.dxftype()=='TEXT']
 for title in texts:
  if title.dxf.text.strip()not in ['图例','LEGEND','Legend']:continue
  h=title.dxf.height;x,y=pg.xy(title.dxf.insert);bb=[x-15*h,y-24*h,x+15*h,y+2*h];captions=[t for t in texts if pg.point_bbox(pg.xy(t.dxf.insert),bb)<=pg.TOL and t.dxf.text.strip()in source_names]
  if len({t.dxf.text.strip()for t in captions})<6:continue
  regions.append({'bounds':bb,'source_title_handle':title.dxf.handle,'source_caption_handles':[t.dxf.handle for t in captions],'rule':'explicit_legend_title_and_at_least_six_known_source_symbol_captions_scale_bounded_region'})
 return regions
