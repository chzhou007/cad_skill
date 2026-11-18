"""Screen offset circle contacts for selected modelspace device-side joint chains."""
import argparse,csv,hashlib,json,math
from pathlib import Path
from native_line_path_evidence import LAYERS,_on
from native_nested_joint_evidence import fingerprint
from source_readability import read_source

def collect(doc,graph,inventory,policy,hashes,tol=.05):
 for key in ('source_sha256','graph_sha256','inventory_sha256'):
  if policy.get(key)!=hashes.get(key):raise ValueError('input hash mismatch: '+key)
 ratio=policy.get('max_radius_ratio')
 if isinstance(ratio,bool) or not isinstance(ratio,(int,float)) or not 0<ratio<=.2 or not 0<tol<=.05:raise ValueError('invalid offset bounds')
 block=doc.blocks.get(policy['joint_block'])
 if block is None or fingerprint(block)!=policy['block_fingerprint_sha256'] or sorted(e.dxftype() for e in block)!=['ARC']*4+['LINE']*2:raise ValueError('joint fingerprint mismatch')
 edges={x['edge_id']:x for x in graph['edges']};nodes={x['node_id']:x for x in graph['nodes']}
 if len(edges)!=len(graph['edges']) or len(nodes)!=len(graph['nodes']):raise ValueError('duplicate graph ids')
 specs=policy.get('selections',[])
 if not specs or len({x['joint_handle'] for x in specs})!=len(specs) or len({x['edge_id'] for x in specs})!=len(specs):raise ValueError('invalid selections')
 typed=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS.values()];circles=list(doc.modelspace().query('CIRCLE'));rows=[]
 for x in specs:
  edge=edges.get(x['edge_id']);owner=x['equipment_id'];system=x['system'];joint=doc.entitydb.get(x['joint_handle']);inner=doc.entitydb.get(x['inner_line']);outer=doc.entitydb.get(x['outer_line'])
  if system not in LAYERS or not edge or edge.get('system')!=system or edge.get('device_label')!=owner or owner not in nodes or nodes[owner].get('node_type') not in ('equipment','physical_equipment') or owner not in (edge.get('start_node_id'),edge.get('end_node_id')):raise ValueError('equipment or edge mismatch')
  if not joint or joint.dxftype()!='INSERT' or joint not in doc.modelspace() or joint.dxf.name!=policy['joint_block']:raise ValueError('joint mismatch')
  if not all(e and e.dxftype()=='LINE' and e in doc.modelspace() and e.dxf.layer==LAYERS[system] for e in (inner,outer)):raise ValueError('source pipe mismatch')
  parts=list(joint.virtual_entities());bars=[e for e in parts if e.dxftype()=='LINE']
  if len(parts)!=6 or len(bars)!=2 or sum(e.dxftype()=='ARC' for e in parts)!=4:raise ValueError('unsupported joint transform')
  contacts=[(v.dxf.start+v.dxf.end)/2 for v in bars]
  def near(line,pt):return [v for v in (line.dxf.start,line.dxf.end) if math.dist(tuple(v),tuple(pt))<=tol]
  pairs=[(i,j) for i in range(2) for j in range(2) if i!=j and len(near(inner,contacts[i]))==1 and len(near(outer,contacts[j]))==1]
  if len(pairs)!=1:raise ValueError('ambiguous joint contacts')
  ic,oc=contacts[pairs[0][0]],contacts[pairs[0][1]]
  for contact,expected in ((ic,inner),(oc,outer)):
   if [v.dxf.handle for v in typed if near(v,contact)]!=[expected.dxf.handle]:raise ValueError('competing typed line at joint')
  remaining=[v for v in (inner.dxf.start,inner.dxf.end) if math.dist(tuple(v),tuple(ic))>tol]
  if len(remaining)!=1:raise ValueError('ambiguous inner endpoint')
  point=remaining[0];matches=[]
  for c in circles:
   if tuple(c.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.) or not math.isfinite(c.dxf.radius) or c.dxf.radius<=0:continue
   dist=math.hypot(point.x-c.dxf.center.x,point.y-c.dxf.center.y)
   if tol<dist<=ratio*c.dxf.radius and abs(point.z-c.dxf.center.z)<=tol:matches.append({'circle_handle':c.dxf.handle,'layer':c.dxf.layer,'center':list(c.dxf.center),'radius':c.dxf.radius,'offset':dist,'offset_radius_ratio':dist/c.dxf.radius})
  witnesses=[]
  for path in edge.get('attribute_paths',[]):
   for a,b in zip(path,path[1:]):
    if _on((outer.dxf.start.x,outer.dxf.start.y),a,b,tol) and _on((outer.dxf.end.x,outer.dxf.end.y),a,b,tol):witnesses.append([a,b])
  if len(witnesses)!=1:raise ValueError('outer source line not uniquely covered')
  inv=[r for r in inventory if r.get('source_top_handle')==x['joint_handle'] and r.get('assignment_status')=='assigned']
  if len(inv)!=1 or inv[0].get('edge_id')!=x['edge_id'] or inv[0].get('owner_equipment')!=owner or inv[0].get('equipment_type')!='金属软接':raise ValueError('joint inventory mismatch')
  name=inv[0]['device_name'];names=[n for item in edge.get('equipment_inventory',[]) if item.get('equipment_type')=='金属软接' for n in item.get('device_names',[])]
  if names.count(name)!=1:raise ValueError('graph joint inventory mismatch')
  rows.append({'equipment_id':owner,'edge_id':x['edge_id'],'system':system,'joint_handle':x['joint_handle'],'inner_line_handle':x['inner_line'],'outer_line_handle':x['outer_line'],'inner_endpoint':list(point),'candidates':matches,'status':'unique_offset_candidate_not_connection' if len(matches)==1 else 'ambiguous_or_no_candidate','physical_port_verified':False,'physical_length':'unknown'})
 return {'status':'exploded_offset_circle_candidates_only','records':rows,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Only selected modelspace chains and circles with default OCS are scanned.','An endpoint inside a source circle is not proof of device ownership, connectivity or physical length.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','inventory','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);graph=json.loads(a.graph.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'))
 with a.inventory.open(encoding='utf-8-sig',newline='') as f:inventory=list(csv.DictReader(f))
 hashes={'source_sha256':proof['source_sha256'],'graph_sha256':sha(a.graph),'inventory_sha256':sha(a.inventory)};r=collect(doc,graph,inventory,policy,hashes);r.update(hashes,policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':r['status'],'records':len(r['records']),'unique':sum(x['status']=='unique_offset_candidate_not_connection' for x in r['records'])}))
if __name__=='__main__':main()
