"""Screen native circle-rim branches near, but not on, same-system mains."""
import argparse,collections,hashlib,json,math
from pathlib import Path
from native_equipment_body import point_segment_distance
from native_line_path_evidence import _on
from cad_ceiling_native_rules import match_out_of_plane_symbol
from source_circle_rim_tee_screen import LAYERS
from source_readability import read_source

def scan(doc,graph,policy,source_hash,graph_hash,tol=.05):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('stale source or graph')
 radius=policy.get('circle_radius');limit=policy.get('max_main_offset')
 if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (radius,limit)) or radius<=0 or limit<=tol:raise ValueError('invalid scan scope')
 edges=graph['edges'];nodes=graph['nodes'];lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS];glyphs=[{'handle':e.dxf.handle,'a':(e.dxf.start.x,e.dxf.start.y),'b':(e.dxf.end.x,e.dxf.end.y)} for e in doc.modelspace().query('LINE') if e.dxf.layer=='空调立管、水平支管'];rows=[];ambiguous=[]
 for circle in doc.modelspace().query('CIRCLE'):
  if circle.dxf.layer not in LAYERS or abs(circle.dxf.radius-radius)>tol or tuple(circle.dxf.extrusion)!=(0.,0.,1.):continue
  p=(circle.dxf.center.x,circle.dxf.center.y)
  if match_out_of_plane_symbol({'center':p,'radius':radius},glyphs,tol):continue
  for layer,system in LAYERS.items():
   mains=[];branches=[]
   for e in lines:
    if e.dxf.layer!=layer:continue
    a=(e.dxf.start.x,e.dxf.start.y);b=(e.dxf.end.x,e.dxf.end.y);da,db=math.dist(p,a),math.dist(p,b);offset=point_segment_distance(p,a,b)
    if tol<offset<=limit and min(da,db)>radius+limit:mains.append((e,offset))
    near,far=(a,b) if da<db else (b,a)
    if abs(min(da,db)-radius)<=tol and _on(near,far,p,tol):branches.append((e,near))
   if not mains or not branches:continue
   if len(mains)!=1 or len(branches)!=1:
    ambiguous.append({'circle_handle':circle.dxf.handle,'system':system,'main_handles':[x[0].dxf.handle for x in mains],'branch_handles':[x[0].dxf.handle for x in branches]});continue
   main,offset=mains[0];branch,rim=branches[0];u=(main.dxf.end.x-main.dxf.start.x,main.dxf.end.y-main.dxf.start.y);v=(branch.dxf.end.x-branch.dxf.start.x,branch.dxf.end.y-branch.dxf.start.y);den=math.hypot(*u)*math.hypot(*v)
   if not den or abs(u[0]*v[1]-u[1]*v[0])/den<.17:continue
   me=[e['edge_id'] for e in edges if e.get('system')==system and main.dxf.handle in e.get('source_handles',[]) and any(point_segment_distance(p,a,b)<=limit for path in e.get('attribute_paths',[]) for a,b in zip(path,path[1:]))]
   be=[e['edge_id'] for e in edges if e.get('system')==system and branch.dxf.handle in e.get('source_handles',[]) and any(math.dist(rim,x)<=tol for path in e.get('attribute_paths',[]) for x in (path[0],path[-1]))]
   terminals=[n['node_id'] for n in nodes if n.get('node_type')=='virtual_equipment' and n.get('system')==system and math.dist((n.get('x',float('inf')),n.get('y',float('inf'))),rim)<=tol]
   rows.append({'circle_handle':circle.dxf.handle,'circle_layer':circle.dxf.layer,'line_system':system,'center':list(p),'radius':radius,'main_handle':main.dxf.handle,'branch_handle':branch.dxf.handle,'branch_rim':list(rim),'main_offset_drawing_units':offset,'main_graph_edges':sorted(me),'branch_graph_edges':sorted(be),'rim_virtual_nodes':sorted(terminals),'status':'near_main_not_connection_confirmation'})
 return {'status':'near_offset_circle_candidates_only','source_sha256':source_hash,'graph_sha256':graph_hash,'circle_radius':radius,'max_main_offset':limit,'candidates':rows,'ambiguous_native_geometry':ambiguous,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Scoped modelspace LINE/CIRCLE and known terminal glyphs only; other geometries and transforms may be omitted.','Nearness, same system and a radius-matched branch do not establish a tee, a physical elevation or an equipment connection.','Z differences are not interpreted; source review and classification of competing crossings are required.']}
def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();g=json.loads(a.graph.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'));r=scan(doc,g,policy,proof['source_sha256'],sha(a.graph));r.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'candidates':len(r['candidates']),'ambiguous':len(r['ambiguous_native_geometry'])}))
if __name__=='__main__':main()
