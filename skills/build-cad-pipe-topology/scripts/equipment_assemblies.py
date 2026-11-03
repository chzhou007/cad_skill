import pipe_geometry as pg_constants
"""Reusable profile-driven native equipment-assembly recognition.
No block-name or tag-prefix whitelist; native bounds are candidate gates, not ports.
"""
import math,collections
from ezdxf import bbox
from pipe_geometry import xy,dist,point_bbox,segdist

def native_primitives(insert,depth=0):
 result=[]
 for e in insert.virtual_entities():
  typ=e.dxftype()
  if typ=='INSERT'and depth<12:result.extend(native_primitives(e,depth+1))
  else:result.append(e)
 return result

def world_line_segments(entity):
 typ=entity.dxftype()
 if typ=='LINE':return[(xy(entity.dxf.start),xy(entity.dxf.end))]
 if typ=='LWPOLYLINE':
  pts=[xy(p)for p in entity.vertices_in_wcs()];pairs=list(zip(pts,pts[1:]))
  if entity.closed:pairs.append((pts[-1],pts[0]))
  return pairs
 return[]

def primitive_distance(point,entity):
 typ=entity.dxftype()
 if typ in ['LINE','LWPOLYLINE']:return min((segdist(point,a,b)for a,b in world_line_segments(entity)),default=float('inf'))
 if typ=='ARC':
  c=xy(entity.ocs().to_wcs(entity.dxf.center));angle=math.degrees(math.atan2(point[1]-c[1],point[0]-c[0]));span=(entity.dxf.end_angle-entity.dxf.start_angle)%360
  radial=abs(dist(point,c)-entity.dxf.radius)if (angle-entity.dxf.start_angle)%360<=span+1e-8 else float('inf')
  return min(radial,dist(point,xy(entity.start_point)),dist(point,xy(entity.end_point)))
 if typ in ['ELLIPSE','SPLINE']:
  from ezdxf.path import make_path
  pts=[xy(p)for p in make_path(entity).flattening(max(pg_constants.TOL*.1,.001))]
  return min((segdist(point,a,b)for a,b in zip(pts,pts[1:])),default=float('inf'))
 if typ=='CIRCLE':
  c=xy(entity.ocs().to_wcs(entity.dxf.center));return abs(dist(point,c)-entity.dxf.radius)
 return float('inf')

def profile_native_assemblies(doc,bindings,profiles,inline_block_names,already_owned_handles=(),minimum_primitives=6,native_rules=()):
 """Return unique profile-backed whole equipment candidates and exhaustive tag audit.
 Candidate gating is relative to explicit tag size and complete native geometry.
 A candidate is never connected until source pipe terminals touch native primitives.
 """
 byprofile={p['profile_id']:p for p in profiles};candidates=[];audits=[]
 for e in doc.modelspace().query('INSERT'):
  if e.dxf.name in inline_block_names or e.dxf.handle in already_owned_handles:continue
  prim=native_primitives(e);counts=collections.Counter(p.dxftype()for p in prim)
  if sum(counts.values())<minimum_primitives or counts['LINE']+counts['LWPOLYLINE']<4:continue
  if not any(counts[t]for t in ['CIRCLE','ARC','ELLIPSE','HATCH','SOLID']):continue
  b=bbox.extents([e])
  if not b.has_data:continue
  candidates.append({'entity':e,'primitives':prim,'counts':dict(counts),'bounds':[b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y]})
 results=[]
 for binding in bindings:
  profiles_here=[byprofile[k]for k in binding.get('profile_candidates',[])if k in byprofile]
  native_rules_here=[r for r in native_rules if __import__('re').fullmatch(r['tag_regex'],binding['equipment_tag'])]
  tag_entity=doc.entitydb.get(binding['source_handle']);height=float(tag_entity.dxf.get('height',0))if tag_entity else 0
  audit={'equipment_tag':binding['equipment_tag'],'source_tag_handle':binding['source_handle'],'profile_candidates':binding.get('profile_candidates',[]),'candidate_handles':[],'rule':'explicit_profile_plus_scale_bounded_unique_native_assembly','rejected_candidates':[],'status':'pending_no_source_profile'if not(profiles_here or native_rules_here)else 'pending_no_unique_native_assembly'}
  eligible=[]
  if (profiles_here or native_rules_here) and height>0:
   p=(binding['x'],binding['y'])
   for c in candidates:
    if native_rules_here and not profiles_here and not any(c['entity'].dxf.name==r['source_block']for r in native_rules_here):continue
    bb=c['bounds'];diag=dist(bb[:2],bb[2:]);gap=point_bbox(p,bb)
    # Exclude drawing frames and tiny inline graphics without absolute CAD coordinates.
    if not(3*height<=diag<=40*height):continue
    matched_rules=[r for r in native_rules_here if r['source_block']==c['entity'].dxf.name]
    limit=min(4*height,.35*diag)
    if matched_rules:
     limit=max([limit]+[min(float(r.get('maximum_tag_gap_text_heights',4))*height,float(r.get('maximum_tag_gap_body_diagonals',.35))*diag)for r in matched_rules])
    if gap>limit:
     audit['rejected_candidates'].append({'source_handle':c['entity'].dxf.handle,'source_block':c['entity'].dxf.name,'tag_gap':gap,'candidate_limit':limit,'reason':'outside_profile_bounded_tag_gap'})
     continue
    eligible.append(c);audit['candidate_handles'].append(c['entity'].dxf.handle)
  if len(eligible)==1:
   c=eligible[0];package_rules=[r for r in native_rules_here if r.get('port_policy')=='verified_closed_enclosure' and r['source_block']==c['entity'].dxf.name]
   frames=[z for z in c['primitives']if z.dxftype()=='LWPOLYLINE'and z.closed and len(z)==4 and not any(abs(v[4])>1e-10 for v in z.get_points())]
   package_verified=bool(package_rules and any(max(abs(v-w)for v,w in zip([bbox.extents([z]).extmin.x,bbox.extents([z]).extmin.y,bbox.extents([z]).extmax.x,bbox.extents([z]).extmax.y],c['bounds']))<=pg_constants.TOL for z in frames))
   c['package_boundary_verified']=package_verified
   audit['package_boundary_verified']=package_verified
   audit['status']='recognized_whole_native_assembly_unreviewed';audit.update(source_block=c['entity'].dxf.name,bounds=c['bounds'],primitive_counts=c['counts'])
   results.append(dict(c,binding=binding,profile_labels=[p['label']for p in profiles_here],audit=audit))
  elif len(eligible)>1:audit['status']='pending_ambiguous_native_assemblies'
  audits.append(audit)
 # One source assembly cannot be silently claimed by two different equipment tags.
 counts=collections.Counter(r['entity'].dxf.handle for r in results)
 for r in list(results):
  if counts[r['entity'].dxf.handle]>1:r['audit']['status']='pending_multiple_tags_claim_same_assembly';results.remove(r)
 return results,audits



def material_contour_candidates(doc,materials,segments,rules):
 """Recognize material-scheduled physical equipment from explicit tags/captions,
 a complete closed native contour and source pipe terminals at that contour.
 A room/frame or tag alone is never sufficient. Inline material rows remain attributes.
 """
 import re
 found=[];audit=[]
 for rule in rules:
  profiles=[p for p in materials if re.search(rule['material_name_regex'],p.get('source_name',''))];texts=[]
  for text in doc.modelspace():
   if text.dxftype()not in ['TEXT','MTEXT']:continue
   value=text.plain_text()if text.dxftype()=='MTEXT'else text.dxf.text
   if re.fullmatch(rule['tag_regex'],value.strip()):texts.append((text,value.strip()))
  for ordinal,(text,value)in enumerate(sorted(texts,key=lambda q:(-q[0].dxf.insert.y,q[0].dxf.insert.x)),1):
   h=float(text.dxf.height if text.dxftype()=='TEXT'else text.dxf.char_height);tag=value if rule.get('preserve_tag',True)else rule['generated_id_prefix']+str(ordinal).zfill(3);candidates=[]
   if profiles:
    for shape in doc.modelspace().query('LWPOLYLINE'):
     if not shape.closed or len(shape)<4 or any(abs(z[4])>1e-10 for z in shape.get_points()):continue
     bb0=bbox.extents([shape]);bb=[bb0.extmin.x,bb0.extmin.y,bb0.extmax.x,bb0.extmax.y];diagonal=dist(bb[:2],bb[2:])
     # Some native vendor packages place their source tag/caption just outside
     # the dashed enclosure. Opt-in bounded label gaps retain the same complete
     # enclosure, schedule, caption/note and pipe-contact requirements.
     tag_gap=h*float(rule.get('maximum_tag_gap_text_heights',0))
     if not(3*h<=diagonal<=40*h)or point_bbox(xy(text.dxf.insert),bb)>max(pg_constants.TOL,tag_gap):continue
     package=rule.get('geometry_family')=='vendor_package_enclosure'
     if package:
      if 'DASH'not in shape.dxf.get('linetype','').upper():continue
      label_gap=h*float(rule.get('maximum_label_gap_text_heights',0))
      notes=[t for t in doc.modelspace().query('TEXT')if re.search(rule['vendor_note_regex'],t.dxf.text)and point_bbox(xy(t.dxf.insert),bb)<=max(pg_constants.TOL,label_gap)]
      captions=[t for t in doc.modelspace().query('TEXT')if re.fullmatch(rule['caption_regex'],t.dxf.text.strip())and point_bbox(xy(t.dxf.insert),bb)<=max(pg_constants.TOL,label_gap)]
      if not notes or not captions:continue
     contacts=[]
     for seg in segments:
      if package:
       for point in contour_boundary_crossings(seg['a'],seg['b'],bb):
        if not any(dist(point,p)<=pg_constants.TOL for p in contacts):contacts.append(point)
       continue
      for point,other in [(seg['a'],seg['b']),(seg['b'],seg['a'])]:
       if point_bbox(point,bb)<=pg_constants.TOL and point_bbox(other,bb)>pg_constants.TOL and primitive_distance(point,shape)<=pg_constants.TOL:
        if not any(dist(point,p)<=pg_constants.TOL for p in contacts):contacts.append(point)
     if len(contacts)>=rule.get('minimum_source_ports',2):candidates.append({'entity':shape,'bounds':bb,'contacts':contacts,'package_boundary':package,'source_package_note_handles':[n.dxf.handle for n in notes]if package else []})
   row={'equipment_id':tag,'source_tag_handle':text.dxf.handle,'source_text':value,'material_profile_candidates':[p['profile_id']for p in profiles],'native_contour_candidates':[c['entity'].dxf.handle for c in candidates],'rule':'material_equipment_name_and_explicit_tag_or_caption_plus_closed_native_contour_and_pipe_ports','status':'recognized_material_equipment_contour_unreviewed'if len(candidates)==1 else 'pending_material_equipment_geometry'}
   if len(candidates)==1:
    c=candidates[0];binding={'equipment_tag':tag,'source_handle':text.dxf.handle,'x':text.dxf.insert.x,'y':text.dxf.insert.y,'profile_candidates':row['material_profile_candidates'],'reference_origin':'material_schedule'};found.append(dict(c,binding=binding,label=rule['label'],audit=row))
   audit.append(row)
 return found,audit


def contour_boundary_crossings(a,b,bb):
 hits=[];dx=b[0]-a[0];dy=b[1]-a[1]
 for x in [bb[0],bb[2]]:
  if abs(dx)>1e-10:
   t=(x-a[0])/dx;y=a[1]+t*dy
   if -1e-9<=t<=1+1e-9 and bb[1]-pg_constants.TOL<=y<=bb[3]+pg_constants.TOL:hits.append((x,y))
 for y in [bb[1],bb[3]]:
  if abs(dy)>1e-10:
   t=(y-a[1])/dy;x=a[0]+t*dx
   if -1e-9<=t<=1+1e-9 and bb[0]-pg_constants.TOL<=x<=bb[2]+pg_constants.TOL and not any(dist((x,y),p)<=pg_constants.TOL for p in hits):hits.append((x,y))
 return hits

def collapse_package_source_geometry(segments,packages,preserve_through_systems=None):
 result=list(segments);audit=[]
 for package in packages:
  if not package.get('package_boundary'):continue
  bb=package['bounds'];changed=[]
  for seg in result:
   allowed=(preserve_through_systems or{}).get(package.get('label'),[])
   crossings=contour_boundary_crossings(seg['a'],seg['b'],bb)
   if seg.get('source_system',seg['system'])in allowed and len(crossings)==2 and all(point_bbox(p,bb)>pg_constants.TOL for p in [seg['a'],seg['b']]):
    changed.append(seg);audit.append({'equipment_id':package['binding']['equipment_tag'],'source_handles':seg.get('source_handles',[seg['handle']]),'a':seg['a'],'b':seg['b'],'rule':'source_profile_verified_external_through_main_preserved'});continue
   pts=[seg['a']]+contour_boundary_crossings(seg['a'],seg['b'],bb)+[seg['b']];pts.sort(key=lambda p:dist(seg['a'],p));unique=[]
   for p in pts:
    if not unique or dist(p,unique[-1])>pg_constants.TOL:unique.append(p)
   for a,b in zip(unique,unique[1:]):
    if dist(a,b)<=pg_constants.TOL:continue
    mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
    if bb[0]+pg_constants.TOL<mid[0]<bb[2]-pg_constants.TOL and bb[1]+pg_constants.TOL<mid[1]<bb[3]-pg_constants.TOL:audit.append({'equipment_id':package['binding']['equipment_tag'],'source_handles':seg.get('source_handles',[seg['handle']]),'a':a,'b':b,'rule':'inside_explicit_vendor_equipment_package; retained as internal source evidence'})
    else:changed.append(dict(seg,a=a,b=b))
  result=changed
 return result,audit


def snap_native_equipment_terminals(doc,segments,rules):
 """Calibrated axial endpoint correction to a verified native equipment contour.
 Requires a complete configured block, an outward pipe, and one unique nearby
 native straight primitive contact. Never connects two arbitrary nearby pipes.
 """
 result=[dict(s)for s in segments];audit=[]
 for seg in result:
  for side,other_side in [('a','b'),('b','a')]:
   p,q=seg[side],seg[other_side];choices=[]
   for rule in rules:
    for en in doc.modelspace().query('INSERT'):
     if en.dxf.name!=rule['source_block']:continue
     extent=bbox.extents([en]);bb=[extent.extmin.x,extent.extmin.y,extent.extmax.x,extent.extmax.y]
     limit=min(float(rule['maximum_gap']),float(rule['maximum_body_diagonal_ratio'])*dist(bb[:2],bb[2:]))
     if point_bbox(p,bb)>limit:continue
     if point_bbox(q,bb)<=limit and not rule.get('allow_multisegment_source_exit',False):continue
     # Contact is on the source pipe axis; bound both undershoot and overshoot.
     length=dist(p,q)
     if length<=limit:continue
     u=((q[0]-p[0])/length,(q[1]-p[1])/length)
     a=(p[0]-u[0]*limit,p[1]-u[1]*limit);b=(p[0]+u[0]*limit,p[1]+u[1]*limit)
     for primitive in native_primitives(en):
      if primitive.dxftype()=='CIRCLE'and rule.get('allow_native_circle_contacts',False):
       center=xy(primitive.ocs().to_wcs(primitive.dxf.center));radius=primitive.dxf.radius;v=(p[0]-center[0],p[1]-center[1]);projection=v[0]*u[0]+v[1]*u[1];discriminant=projection*projection-(v[0]*v[0]+v[1]*v[1]-radius*radius)
       if discriminant>=0:
        for t in [-projection-math.sqrt(discriminant),-projection+math.sqrt(discriminant)]:
         hit=(p[0]+u[0]*t,p[1]+u[1]*t)
         if abs(t)<=limit and not any(dist(hit,z[0])<=pg_constants.TOL for z in choices):choices.append((hit,en.dxf.handle,limit,list(bb)))
      for c,d in world_line_segments(primitive):
       from pipe_geometry import intersection
       hit=intersection(a,b,c,d)
       if hit is None:continue
       # pipe_geometry intersection returns a point
       if dist(p,hit)<=limit and not any(dist(hit,z[0])<=pg_constants.TOL for z in choices):choices.append((hit,en.dxf.handle,limit,list(bb)))
   if len(choices)==1 and dist(p,choices[0][0])>pg_constants.TOL:
    hit,handle,limit,bb=choices[0]
    if point_bbox(q,bb)<=limit:
     # Follow only a unique source continuation; a branch or internal loop cannot prove an external port.
     previous=seg;current=q;visited={id(seg)};exits=False
     for _ in range(len(result)):
      if point_bbox(current,bb)>limit:exits=True;break
      nexts=[z for z in result if id(z)not in visited and min(dist(current,z['a']),dist(current,z['b']))<=pg_constants.TOL]
      if len(nexts)!=1:break
      previous=nexts[0];visited.add(id(previous));current=previous['b']if dist(current,previous['a'])<=pg_constants.TOL else previous['a']
     if not exits:continue
    seg[side]=hit;audit.append({'source_handle':seg['handle'],'equipment_source_handle':handle,'old_endpoint':p,'new_endpoint':hit,'distance':dist(p,hit),'limit':limit,'rule':'unique_scale_bounded_axial_native_equipment_primitive_contact'})
 return result,audit
