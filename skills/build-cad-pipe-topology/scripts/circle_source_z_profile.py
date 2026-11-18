"""Audit contact Z and complete native LINE endpoint Z for circle candidates."""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source

def profile(doc,graph,screen,source_hash,graph_hash):
 if (graph.get('metadata',{}).get('source_sha256')!=source_hash or screen.get('source_sha256')!=source_hash or screen.get('graph_sha256')!=graph_hash or screen.get('status')!='source_shape_comparison_not_connectivity' or screen.get('graph_mutated') is not False or screen.get('hil_ready') is not False):raise ValueError('stale circle screen')
 tol=screen.get('z_tolerance')
 if isinstance(tol,bool) or not isinstance(tol,(int,float)) or not math.isfinite(tol) or tol<=0:raise ValueError('invalid Z tolerance')
 rows=[];seen=set()
 for c in screen.get('candidates',[]):
  key=(c.get('circle_handle'),c.get('line_system'))
  if not all(key) or key in seen:raise ValueError('duplicate or invalid candidate')
  seen.add(key);circle=doc.entitydb.get(key[0]);main=doc.entitydb.get(c.get('main_handle'));branch=doc.entitydb.get(c.get('branch_handle'))
  if any(e is None or e not in doc.modelspace() for e in (circle,main,branch)) or [e.dxftype() for e in (circle,main,branch)]!=['CIRCLE','LINE','LINE']:raise ValueError('missing native entities')
  if tuple(circle.dxf.extrusion)!=(0.,0.,1.) or circle.dxf.layer!=c.get('circle_layer') or abs(circle.dxf.radius-c.get('radius',-1))>.05 or math.dist((circle.dxf.center.x,circle.dxf.center.y),c['center'])>.05:raise ValueError('native circle mismatch')
  from source_circle_rim_tee_screen import LAYERS
  if LAYERS.get(main.dxf.layer)!=key[1] or LAYERS.get(branch.dxf.layer)!=key[1]:raise ValueError('native line system mismatch')
  p=c['center'];a,b=main.dxf.start,main.dxf.end;dx=b.x-a.x;dy=b.y-a.y;den=dx*dx+dy*dy
  if den<=.05**2:raise ValueError('degenerate main')
  t=((p[0]-a.x)*dx+(p[1]-a.y)*dy)/den;mz=a.z+t*(b.z-a.z);ends=[branch.dxf.start,branch.dxf.end];rim=c['branch_rim'];nearest=min(ends,key=lambda v:math.dist((v.x,v.y),rim));rz=nearest.z;z=circle.dxf.center.z;allz=[a.z,b.z,*[v.z for v in ends],z]
  if not all(math.isfinite(v) for v in allz+[mz,rz]) or math.dist((nearest.x,nearest.y),rim)>.05 or abs(mz-c['main_z_at_center'])>1e-6 or abs(rz-c['branch_z_at_rim'])>1e-6 or abs(z-c['circle_z'])>1e-6:raise ValueError('native contact differs from screen')
  contact=abs(mz-z)<=tol and abs(rz-z)<=tol;whole=all(abs(v-z)<=tol for v in allz)
  if contact is not c.get('z_consistent_within_tolerance'):raise ValueError('contact status mismatch')
  rows.append({'circle_handle':key[0],'line_system':key[1],'circle_z':z,'main_z_at_center':mz,'branch_z_at_rim':rz,'main_endpoint_z':[a.z,b.z],'branch_endpoint_z':[v.z for v in ends],'contact_z_consistent':contact,'all_line_endpoints_match_circle_z':whole,'status':'all_endpoints_match' if whole else 'line_endpoint_z_differs_uninterpreted','source_connection_status':c['status']})
 return {'status':'circle_z_profile_not_elevation_or_connectivity','source_sha256':source_hash,'graph_sha256':graph_hash,'records':rows,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Z at circle contacts and Z at both ends of each native LINE are distinct checks.','Different source Z does not establish physical elevation, separate pipes or disconnection.','Only native lines in the supplied radius-scoped screen are covered.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','screen','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args();doc,proof=read_source(a.source);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();g=json.loads(a.graph.read_text(encoding='utf8'));s=json.loads(a.screen.read_text(encoding='utf8'));r=profile(doc,g,s,proof['source_sha256'],sha(a.graph));r.update(screen_sha256=sha(a.screen),script_sha256=sha(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'records':len(r['records']),'different_endpoint_z':sum(x['status']!='all_endpoints_match' for x in r['records'])}))
if __name__=='__main__':main()
