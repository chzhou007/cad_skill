"""Read-only same-system, small-overshoot endpoint crossing inventory."""
import argparse,collections,hashlib,json,math
from pathlib import Path
from source_readability import read_source

def screen(doc,graph,policy,source_hash,graph_hash):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('source or graph mismatch')
 limit=float(policy['maximum_overshoot']);minimum=float(policy['minimum_overshoot']);node_tol=float(policy['node_tolerance']);z_tol=float(policy['z_tolerance']);angle=float(policy['minimum_sine_angle']);layers=policy['source_layer_systems']
 if not (0<=minimum<limit<=1 and 0<node_tol<=1 and 0<z_tol<=1 and .5<=angle<=1) or set(layers.values())!={'supply','return'}:raise ValueError('invalid screening bounds')
 nodes={n['node_id']:n for n in graph['nodes']};edges=graph['edges'];refs=collections.defaultdict(list)
 if len(nodes)!=len(graph['nodes']) or len({e['edge_id'] for e in edges})!=len(edges):raise ValueError('duplicate graph IDs')
 for e in edges:
  for h in e.get('source_handles',[]):refs[h].append(e)
 lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in layers and e.dxf.handle in refs];rows=[]
 for line in lines:
  a,b=line.dxf.start,line.dxf.end;dx,dy=b.x-a.x,b.y-a.y;length=math.hypot(dx,dy)
  if length<10:continue
  for endpoint in (a,b):
   matches={n['node_id']:n for e in refs[line.dxf.handle] for n in (nodes.get(e.get('start_node_id')),nodes.get(e.get('end_node_id'))) if n and n.get('subtype')=='unresolved_source_terminal' and n.get('system')==layers[line.dxf.layer] and math.hypot(n['x']-endpoint.x,n['y']-endpoint.y)<=node_tol}
   if not matches:continue
   for main in lines:
    if main is line or main.dxf.layer!=line.dxf.layer:continue
    c,z=main.dxf.start,main.dxf.end;mx,my=z.x-c.x,z.y-c.y;den=dx*my-dy*mx;mlen=math.hypot(mx,my)
    if mlen<10 or abs(den)/(length*mlen)<angle:continue
    t=((c.x-a.x)*my-(c.y-a.y)*mx)/den;u=((c.x-a.x)*dy-(c.y-a.y)*dx)/den
    if not(0<t<1 and .000001<u<.999999):continue
    q=(a.x+t*dx,a.y+t*dy);dist=math.hypot(q[0]-endpoint.x,q[1]-endpoint.y);z_branch=a.z+t*(b.z-a.z);z_main=c.z+u*(z.z-c.z)
    if not(minimum<dist<=limit and abs(z_branch-z_main)<=z_tol):continue
    for node in matches.values():
     branch_edges=sorted({e['edge_id'] for e in refs[line.dxf.handle] if node['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))});main_edges=sorted({e['edge_id'] for e in refs[main.dxf.handle] if e.get('system')==node['system']})
     if not branch_edges or not main_edges:continue
     rows.append({'source_branch_handle':line.dxf.handle,'source_main_handle':main.dxf.handle,'system':node['system'],'endpoint_node_id':node['node_id'],'branch_edge_ids':branch_edges,'main_edge_ids':main_edges,'endpoint':[endpoint.x,endpoint.y,endpoint.z],'crossing':[q[0],q[1]],'overshoot_native_units':dist,'source_z_difference':z_branch-z_main,'status':'near_endpoint_crossing_candidate_not_connection'})
 rows.sort(key=lambda r:(r['source_branch_handle'],r['source_main_handle'],r['endpoint_node_id']))
 return {'status':'source_near_endpoint_crossings_not_connections','source_sha256':source_hash,'graph_sha256':graph_hash,'counts':{'graph_referenced_typed_modelspace_lines':len(lines),'candidates':len(rows)},'candidates':rows,'graph_mutated':False,'hil_ready':False,'limitations':['Search is restricted to typed modelspace LINEs referenced by the graph and unresolved terminal nodes; unextracted lines, other entities and drawing conventions are excluded.','Small overshoot, matching system and close Z do not prove a tee; source symbols, nearby topology and expert evidence still matter.','No graph, component, length or review status is changed.']}

def main():
 p=argparse.ArgumentParser()
 for n in ('source','graph','policy','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);r=screen(doc,json.loads(a.graph.read_text(encoding='utf8')),json.loads(a.policy.read_text(encoding='utf8')),proof['source_sha256'],sha(a.graph));r.update(policy_sha256=sha(a.policy),source_preflight=proof['status'])
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'counts':r['counts']}))
if __name__=='__main__':main()
