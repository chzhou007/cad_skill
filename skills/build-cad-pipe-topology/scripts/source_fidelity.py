"""Complete source display groups without changing hydraulic equipment boundaries."""
from ezdxf import bbox
import pipe_geometry as pg
from instrumentation import source_gauges,gauge_connector_handles

def pump_display_family(doc,node):
 """Verified pump body + short radial lead + complete attached rectangular contour.
 A nearby rectangle alone is never attached. Multiple candidates stay ambiguous.
 """
 circle=doc.entitydb[node['source_handle']];c=pg.xy(circle.dxf.center);r=circle.dxf.radius;tol=max(pg.TOL,.03*r);matches=[]
 for shape in doc.modelspace().query('LWPOLYLINE'):
  if not shape.closed or len(shape)!=4 or any(abs(v[4])>1e-9 for v in shape.get_points()):continue
  pts=[tuple(p[:2])for p in shape.get_points()];sides=list(zip(pts,pts[1:]+pts[:1]));lens=[pg.dist(a,b)for a,b in sides]
  if min(lens)<.4*r or max(lens)>2.5*r or not 1.2<max(lens)/min(lens)<3:continue
  if any(abs(pg.dot(pg.sub(b,a),pg.sub(d,b)))>.02*pg.dist(a,b)*pg.dist(b,d)for a,b,d in zip(pts,pts[1:]+pts[:1],pts[2:]+pts[:2])):continue
  center=(sum(p[0]for p in pts)/4,sum(p[1]for p in pts)/4)
  if not 1.2*r<pg.dist(c,center)<4*r:continue
  for a,b in sides:
   if pg.dist(a,b)>min(lens)*1.02:continue
   mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
   for line in doc.modelspace().query('LINE'):
    u,v=pg.xy(line.dxf.start),pg.xy(line.dxf.end)
    for tip,tail in [(u,v),(v,u)]:
     if pg.dist(tip,mid)>tol or abs(pg.dist(tail,c)-r)>tol or not .1*r<pg.dist(u,v)<r:continue
     if abs(pg.cross(pg.sub(tip,c),pg.sub(tail,c)))/pg.dist(tip,c)>tol:continue
     if pg.dist(tip,c)<=pg.dist(tail,c):continue
     matches.append([shape.dxf.handle,line.dxf.handle])
 matches=sorted({tuple(m)for m in matches})
 return {'node_id':node['node_id'],'rule':'complete_pump_body_unique_radial_lead_to_short_side_midpoint_of_closed_rectangle','status':'complete_native_display_family'if len(matches)==1 else 'pending_ambiguous_display_family'if matches else 'body_only_no_proven_attached_family','candidates':[list(m)for m in matches],'source_handles':sorted(set(node['source_handles'])|set(matches[0]if len(matches)==1 else []))}

def equipment_display(doc,nodes):
 audit=[]
 for n in nodes:
  if n['node_type']!='equipment':continue
  handles=n['source_handles'];row={'node_id':n['node_id'],'status':'native_body','source_handles':handles}
  if n['source_block']=='exploded_pump_triangle_circle':row=pump_display_family(doc,n)
  elif n.get('package_boundary'):
   bb=n['source_bounds'];handles=[]
   for e in doc.modelspace():
    if e.dxftype()in ['TEXT','MTEXT','DIMENSION','HATCH']:continue
    eb=bbox.extents([e])
    if eb.has_data and eb.extmin.x>=bb[0]-pg.TOL and eb.extmin.y>=bb[1]-pg.TOL and eb.extmax.x<=bb[2]+pg.TOL and eb.extmax.y<=bb[3]+pg.TOL:handles.append(e.dxf.handle)
   row={'node_id':n['node_id'],'status':'native_verified_package_enclosure','source_handles':sorted(handles)}
  n['display_source_handles']=row['source_handles'];n['display_source_status']=row['status'];audit.append(row)
 return audit

def assembly_fidelity(doc,groups,symbols):
 byhandle={s['handle']:s for s in symbols};gauges=source_gauges(doc);bycircle={q['entity'].dxf.handle:q for q in gauges};rows=[]
 for a in groups:
  required=set(a['source_handles']);members=[]
  for h in a['component_handles']:
   s=byhandle[h];hs=s.get('source_handles',[h]);required.update(hs);members.append({'member':h,'required_source_handles':hs})
  if a['source_kind']=='source_measurement_assembly':
   q=bycircle[a['id'].removeprefix('INSTR-')]
   for h in gauges:
    if h['kind']=='DPIT'and pg.dist(h['center'],q['center'])<=4*q['radius']:required.update(gauge_connector_handles(doc,q,h))
  missing=sorted(required-set(a['source_handles']));rows.append({'id':a['id'],'members':members,'required_source_handles':sorted(required),'exported_source_handles':a['source_handles'],'missing_source_handles':missing,'status':'FAIL'if missing else 'PASS'})
 return rows
