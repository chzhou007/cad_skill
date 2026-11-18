"""Inventory radius-scoped source circle/main/rim contacts before expert review.

This is geometric comparison only. It never modifies topology, assigns a
system from a circle, or asserts hydraulic connectivity.
"""
import argparse,collections,hashlib,json,math
from pathlib import Path
from source_readability import read_source
from native_line_path_evidence import _on
from cad_ceiling_native_rules import match_out_of_plane_symbol
LAYERS={'空调冷冻水供水':'supply','空调冷冻水回水':'return'}

def scan(doc,graph,policy,source_hash,graph_hash,tol=.05):
 if graph.get('metadata',{}).get('source_sha256')!=source_hash or policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash:raise ValueError('source or graph mismatch')
 radius=policy.get('circle_radius');ztol=policy.get('z_tolerance')
 if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in (radius,ztol,tol)):raise ValueError('invalid screen tolerance')
 nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
 if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate graph IDs')
 lines=[x for x in doc.modelspace().query('LINE') if x.dxf.layer in LAYERS];glyphs=[{'handle':x.dxf.handle,'a':(x.dxf.start.x,x.dxf.start.y),'b':(x.dxf.end.x,x.dxf.end.y)} for x in doc.modelspace().query('LINE') if x.dxf.layer=='空调立管、水平支管']
 results=[];suppressed=[];ambiguous=[];unsupported=[]
 for circle in doc.modelspace().query('CIRCLE'):
  if circle.dxf.layer not in LAYERS or abs(circle.dxf.radius-radius)>tol:continue
  if tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):unsupported.append(circle.dxf.handle);continue
  p=(circle.dxf.center.x,circle.dxf.center.y);cz=circle.dxf.center.z
  if not all(math.isfinite(x) for x in (*p,cz)):raise ValueError('invalid native circle position')
  native={'center':p,'radius':circle.dxf.radius}
  if match_out_of_plane_symbol(native,glyphs,tol):suppressed.append(circle.dxf.handle);continue
  mains=[];branches=[]
  for line in lines:
   a=(line.dxf.start.x,line.dxf.start.y);b=(line.dxf.end.x,line.dxf.end.y);da=math.dist(p,a);db=math.dist(p,b)
   if _on(p,a,b,tol) and min(da,db)>radius+tol:mains.append(line)
   nearest,other=(a,b) if da<db else (b,a)
   if abs(min(da,db)-radius)<=tol and _on(nearest,other,p,tol):branches.append((line,nearest))
  for layer,system in LAYERS.items():
   ms=[x for x in mains if x.dxf.layer==layer];bs=[x for x in branches if x[0].dxf.layer==layer]
   if not ms or not bs:continue
   if len(ms)!=1 or len(bs)!=1:ambiguous.append({'circle_handle':circle.dxf.handle,'system':system,'main_handles':[x.dxf.handle for x in ms],'branch_handles':[x[0].dxf.handle for x in bs],'status':'ambiguous_native_lines'});continue
   main=ms[0];branch,rim=bs[0]
   if not all(math.isfinite(q) for entity in (main,branch) for point in (entity.dxf.start,entity.dxf.end) for q in (point.x,point.y,point.z)):raise ValueError('invalid native line coordinates')
   u=(main.dxf.end.x-main.dxf.start.x,main.dxf.end.y-main.dxf.start.y);v=(branch.dxf.end.x-branch.dxf.start.x,branch.dxf.end.y-branch.dxf.start.y);norm=math.hypot(*u)*math.hypot(*v)
   if not norm or abs(u[0]*v[1]-u[1]*v[0])/norm<.17:continue
   t=((p[0]-main.dxf.start.x)*u[0]+(p[1]-main.dxf.start.y)*u[1])/(u[0]*u[0]+u[1]*u[1]);mz=main.dxf.start.z+t*(main.dxf.end.z-main.dxf.start.z);bp=branch.dxf.start if math.dist(rim,(branch.dxf.start.x,branch.dxf.start.y))<=tol else branch.dxf.end
   main_edges=[e['edge_id'] for e in edges.values() if e.get('system')==system and main.dxf.handle in e.get('source_handles',[]) and any(_on(p,a,b,tol) for path in e.get('attribute_paths',[]) for a,b in zip(path,path[1:]))];branch_edges=[e['edge_id'] for e in edges.values() if e.get('system')==system and branch.dxf.handle in e.get('source_handles',[]) and any(math.dist(rim,v)<=tol for path in e.get('attribute_paths',[]) for v in (path[0],path[-1]))]
   branch_containing_rim=[e['edge_id'] for e in edges.values() if e.get('system')==system and branch.dxf.handle in e.get('source_handles',[]) and any(_on(rim,a,b,tol) for path in e.get('attribute_paths',[]) for a,b in zip(path,path[1:]))]
   center_nodes=[n['node_id'] for n in nodes.values() if n.get('node_type') in ('tee','physical_junction') and n.get('system')==system and math.dist((n.get('x',float('inf')),n.get('y',float('inf'))),p)<=tol];rim_nodes=[n['node_id'] for n in nodes.values() if n.get('node_type')=='virtual_equipment' and n.get('system')==system and math.dist((n.get('x',float('inf')),n.get('y',float('inf'))),rim)<=tol]
   def incident(eid,nid):return nid in (edges[eid].get('start_node_id'),edges[eid].get('end_node_id'))
   # A normalized branch may start at the circle center while the native
   # rim lies inside its path, notably a user-confirmed non-node boundary.
   # Require both center incidence and a graph path containing the rim; this
   # is evidence of the existing graph only, not proof of the source meaning.
   centered_branch=[eid for eid in branch_containing_rim if any(math.dist(p,v)<=tol for path in edges[eid].get('attribute_paths',[]) for v in (path[0],path[-1]))]
   graph_branches=set(branch_edges)|set(centered_branch)
   already=any(len([eid for eid in main_edges if incident(eid,nid)])==2 and len([eid for eid in graph_branches if incident(eid,nid)])==1 and len([e for e in edges.values() if nid in (e.get('start_node_id'),e.get('end_node_id'))])==3 and all(e.get('system')==system for e in edges.values() if nid in (e.get('start_node_id'),e.get('end_node_id'))) for nid in center_nodes)
   boundary=[x['boundary_id'] for x in graph.get('boundary_anchors',[]) if circle.dxf.handle in x.get('source_marker_handles',[])]
   results.append({'circle_handle':circle.dxf.handle,'circle_layer':circle.dxf.layer,'circle_system':LAYERS[circle.dxf.layer],'line_system':system,'circle_layer_matches_lines':LAYERS[circle.dxf.layer]==system,'center':list(p),'radius':circle.dxf.radius,'main_handle':main.dxf.handle,'branch_handle':branch.dxf.handle,'branch_rim':list(rim),'main_z_at_center':mz,'branch_z_at_rim':bp.z,'circle_z':cz,'z_consistent_within_tolerance':abs(cz-mz)<=ztol and abs(bp.z-mz)<=ztol,'main_graph_edges':sorted(main_edges),'branch_graph_edges':sorted(branch_edges),'branch_containing_rim_edges':sorted(branch_containing_rim),'center_graph_tees':sorted(center_nodes),'rim_virtual_nodes':sorted(rim_nodes),'protected_boundaries':sorted(boundary),'status':'existing_graph_connection_unreviewed' if already else 'source_shape_graph_connection_not_established'})
 results.sort(key=lambda x:(x['circle_handle'],x['line_system']))
 return {'status':'source_shape_comparison_not_connectivity','source_sha256':source_hash,'graph_sha256':graph_hash,'circle_radius':radius,'z_tolerance':ztol,'candidates':results,'ambiguous_native_geometry':ambiguous,'out_of_plane_glyph_suppressed':suppressed,'unsupported_circle_transforms':unsupported,'graph_mutated':False,'hil_ready':False,'limitations':['Modelspace LINE and CIRCLE plus recognized glyph LINE only; other blocks, proxy objects and drawing symbols are excluded.','Z disagreement is retained, not interpreted as an elevation or separate pipe.','Same-layer, nearby shape, or a candidate is not proof of a T junction, system override or remote equipment.','Experts may explicitly classify circles as non-node boundaries; no shape can override their source-specific decision.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args();doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();r=scan(doc,json.loads(gb),json.loads(pb),proof['source_sha256'],sha(gb));r.update(policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'candidates':len(r['candidates']),'ambiguous':len(r['ambiguous_native_geometry']),'status':r['status']}))
if __name__=='__main__':main()
