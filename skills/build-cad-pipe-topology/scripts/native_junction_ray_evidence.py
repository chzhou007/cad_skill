"""Verify source LINE rays at explicitly selected graph T junctions.

Geometric evidence only; symbols, other entity types, physical 3D connection,
flow and human review remain independently unresolved.
"""
import argparse,hashlib,json,math
from pathlib import Path
from ezdxf.disassemble import recursive_decompose
from source_readability import read_source
from native_line_path_evidence import _on,LAYERS

def collect(doc,graph,policy,source_hash,graph_hash,tol=.05):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash:raise ValueError('source or graph hash mismatch')
 nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']};selected=policy.get('junctions',[])
 if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']) or not selected or len({x['node_id'] for x in selected})!=len(selected):raise ValueError('invalid graph or duplicate selections')
 model_lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS.values()];rows=[]
 for item in selected:
  nid=item['node_id'];node=nodes.get(nid);expected=item['edge_witnesses'];incident=[e for e in edges.values() if nid in (e.get('start_node_id'),e.get('end_node_id'))]
  if not node or node.get('node_type') not in ('tee','physical_junction') or len(incident)!=3 or set(expected)!={e['edge_id'] for e in incident}:raise ValueError('junction or incident edge mismatch')
  systems={e.get('system') for e in incident}
  if len(systems)!=1 or not systems <= set(LAYERS):raise ValueError('mixed or unknown system')
  system=next(iter(systems));p=(node['x'],node['y']);rays=[];directions=[]
  for e in incident:
   touching=[]
   for path in e.get('attribute_paths',[]):
    for a,b in zip(path,path[1:]):
     if math.dist(a,p)<=tol and math.dist(b,p)>tol:touching.append((a,b))
     elif math.dist(b,p)<=tol and math.dist(a,p)>tol:touching.append((b,a))
   if len(touching)!=1:raise ValueError('ambiguous or missing graph ray')
   at,other=touching[0];dx,dy=other[0]-p[0],other[1]-p[1];length=math.hypot(dx,dy);v=(dx/length,dy/length)
   if any(v[0]*u[0]+v[1]*u[1]>math.cos(math.radians(.1)) for u in directions):raise ValueError('coincident graph rays')
   directions.append(v);hits=[];witness=expected[e['edge_id']]
   if isinstance(witness,str):
    for line in model_lines:
     if line.dxf.layer!=LAYERS[system]:continue
     a=(line.dxf.start.x,line.dxf.start.y);b=(line.dxf.end.x,line.dxf.end.y)
     if _on(at,a,b,tol) and _on(other,a,b,tol):hits.append(line.dxf.handle)
    if hits!=[witness]:raise ValueError('ray source line ambiguous or changed')
    rays.append({'edge_id':e['edge_id'],'source_line_handle':hits[0],'graph_segment':[at,other],'direction':list(v)})
   elif isinstance(witness,dict) and set(witness)=={'scope','insert_handle'} and witness['scope']=='decomposed_selected_insert':
    h=witness['insert_handle'];insert=doc.entitydb.get(h)
    if not insert or insert.dxftype()!='INSERT' or insert not in doc.modelspace() or e.get('source_insert_handle')!=h:raise ValueError('selected ray insert mismatch')
    for line in recursive_decompose([insert]):
     if line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[system]:continue
     a=(line.dxf.start.x,line.dxf.start.y);b=(line.dxf.end.x,line.dxf.end.y)
     if _on(at,a,b,tol) and _on(other,a,b,tol):hits.append({'start':list(a),'end':list(b),'layer':line.dxf.layer})
    if len(hits)!=1:raise ValueError('nested ray source line ambiguous or changed')
    rays.append({'edge_id':e['edge_id'],'source_insert_handle':h,'scope':'decomposed_selected_insert','source_line_geometry':hits[0],'graph_segment':[at,other],'direction':list(v)})
   else:raise ValueError('invalid ray witness specification')
  native=[]
  for line in model_lines:
   a=(line.dxf.start.x,line.dxf.start.y);b=(line.dxf.end.x,line.dxf.end.y)
   if _on(p,a,b,tol):native.append({'handle':line.dxf.handle,'layer':line.dxf.layer,'contact':'endpoint' if min(math.dist(p,a),math.dist(p,b))<=tol else 'interior'})
  same={x['handle'] for x in native if x['layer']==LAYERS[system]};other=[x for x in native if x['layer']!=LAYERS[system]]
  if same!={r['source_line_handle'] for r in rays if 'source_line_handle' in r}:raise ValueError('unaccounted same-system source line at junction')
  rows.append({'node_id':nid,'system':system,'position':list(p),'source_rays':rays,'native_line_contacts':native,'opposite_system_contacts':other,'status':'native_line_ray_evidence_not_accepted'})
 return {'status':'native_ray_evidence_unreviewed','source_sha256':source_hash,'graph_sha256':graph_hash,'junctions':rows,'graph_mutated':False,'hil_ready':False,'limitations':['Only modelspace LINE entities and LINE descendants of explicitly selected device INSERTs on configured supply/return layers are checked; other nested blocks, curves and proxies are not covered.','Source rays and endpoint/interior geometry do not alone prove 3D hydraulic connectivity or absence of symbol overrides.','Opposite-system geometric contacts, if any, are recorded but never connected.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();sha=lambda x:hashlib.sha256(x).hexdigest();r=collect(doc,json.loads(gb),json.loads(pb),proof['source_sha256'],sha(gb));r.update(policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'junctions':len(r['junctions'])}))
if __name__=='__main__':main()
