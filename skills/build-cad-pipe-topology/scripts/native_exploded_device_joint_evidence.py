"""Audit selected direct-modelspace device circle/line/flexible-joint chains."""
import argparse,csv,hashlib,json,math
from pathlib import Path
from native_line_path_evidence import LAYERS,_on
from native_nested_joint_evidence import fingerprint
from source_readability import read_source

def collect(doc,graph,inventory,policy,hashes,tol=.05):
 if isinstance(tol,bool) or not isinstance(tol,(int,float)) or not math.isfinite(tol) or not 0<tol<=.05:raise ValueError('invalid tolerance')
 for key in ('source_sha256','graph_sha256','inventory_sha256'):
  if policy.get(key)!=hashes.get(key):raise ValueError('input hash mismatch: '+key)
 block=doc.blocks.get(policy['joint_block'])
 if block is None or fingerprint(block)!=policy['block_fingerprint_sha256'] or sorted(e.dxftype() for e in block)!=['ARC']*4+['LINE']*2:raise ValueError('joint fingerprint mismatch')
 edges={x['edge_id']:x for x in graph['edges']};nodes={x['node_id']:x for x in graph['nodes']}
 if len(edges)!=len(graph['edges']) or len(nodes)!=len(graph['nodes']):raise ValueError('duplicate graph id')
 specs=policy.get('selections',[])
 if not specs or len({x['joint_handle'] for x in specs})!=len(specs) or len({x['edge_id'] for x in specs})!=len(specs):raise ValueError('invalid selections')
 rows=[]
 for x in specs:
  edge=edges.get(x['edge_id']);owner=x['equipment_id'];system=x['system'];joint=doc.entitydb.get(x['joint_handle']);inner=doc.entitydb.get(x['inner_line']);outer=doc.entitydb.get(x['outer_line']);circle=doc.entitydb.get(x['circle_handle'])
  if system not in LAYERS or not edge or edge.get('system')!=system or edge.get('device_label')!=owner or owner not in nodes or nodes[owner].get('node_type') not in ('equipment','physical_equipment') or owner not in (edge.get('start_node_id'),edge.get('end_node_id')):raise ValueError('equipment or edge mismatch')
  if not joint or joint.dxftype()!='INSERT' or joint not in doc.modelspace() or joint.dxf.name!=policy['joint_block']:raise ValueError('joint mismatch')
  if not all(e and e.dxftype()=='LINE' and e in doc.modelspace() and e.dxf.layer==LAYERS[system] for e in (inner,outer)):raise ValueError('source pipe mismatch')
  if not circle or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):raise ValueError('source circle mismatch or unsupported OCS')
  parts=list(joint.virtual_entities());bars=[e for e in parts if e.dxftype()=='LINE']
  if len(parts)!=6 or len(bars)!=2 or sum(e.dxftype()=='ARC' for e in parts)!=4:raise ValueError('unsupported joint transform')
  contacts=[(v.dxf.start+v.dxf.end)/2 for v in bars]
  def end_near(line,pt):return [v for v in (line.dxf.start,line.dxf.end) if math.dist(tuple(v),tuple(pt))<=tol]
  matches=[(i,j) for i in range(2) for j in range(2) if i!=j and len(end_near(inner,contacts[i]))==1 and len(end_near(outer,contacts[j]))==1]
  if len(matches)!=1:raise ValueError('joint contacts ambiguous')
  outer_contact=contacts[matches[0][1]];inner_contact=contacts[matches[0][0]]
  typed_lines=[v for v in doc.modelspace().query('LINE') if v.dxf.layer in LAYERS.values()]
  for contact,expected in ((inner_contact,inner),(outer_contact,outer)):
   touching=[v.dxf.handle for v in typed_lines if len(end_near(v,contact))>0]
   if touching!=[expected.dxf.handle]:raise ValueError('competing typed source line at joint contact')
  inner_other=[v for v in (inner.dxf.start,inner.dxf.end) if math.dist(tuple(v),tuple(inner_contact))>tol]
  if len(inner_other)!=1 or math.dist(tuple(inner_other[0]),tuple(circle.dxf.center))>tol:raise ValueError('inner source line misses circle center')
  witnesses=[]
  for path in edge.get('attribute_paths',[]):
   for a,b in zip(path,path[1:]):
    if _on((outer.dxf.start.x,outer.dxf.start.y),a,b,tol) and _on((outer.dxf.end.x,outer.dxf.end.y),a,b,tol):witnesses.append([a,b])
  if len(witnesses)!=1:raise ValueError('outer source line not uniquely covered by edge')
  inv=[r for r in inventory if r.get('source_top_handle')==x['joint_handle'] and r.get('assignment_status')=='assigned']
  if len(inv)!=1 or inv[0].get('edge_id')!=x['edge_id'] or inv[0].get('owner_equipment')!=owner or inv[0].get('equipment_type')!='金属软接':raise ValueError('joint inventory mismatch')
  name=inv[0]['device_name'];names=[n for item in edge.get('equipment_inventory',[]) if item.get('equipment_type')=='金属软接' for n in item.get('device_names',[])]
  if names.count(name)!=1:raise ValueError('graph joint inventory mismatch')
  rows.append({'equipment_id':owner,'edge_id':x['edge_id'],'system':system,'joint_handle':x['joint_handle'],'joint_component_name':name,'inner_line_handle':x['inner_line'],'outer_line_handle':x['outer_line'],'circle_handle':x['circle_handle'],'inner_line_endpoints':[list(inner.dxf.start),list(inner.dxf.end)],'outer_line_endpoints':[list(outer.dxf.start),list(outer.dxf.end)],'joint_contacts':[list(inner_contact),list(outer_contact)],'circle_center':list(circle.dxf.center),'circle_radius':circle.dxf.radius,'graph_outer_witness':witnesses[0],'physical_port_verified':False,'physical_length':'unknown','status':'native_chain_geometry_unreviewed'})
 return {'status':'native_exploded_device_joint_geometry_unreviewed','records':rows,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Selected modelspace entities only; other competing geometry requires independent source comparison.','Circle-to-pipe and joint-bar contacts are drawing evidence, not proof of physical equipment port or installed length.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','inventory','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);graph=json.loads(a.graph.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'))
 with a.inventory.open(encoding='utf-8-sig',newline='') as f:inventory=list(csv.DictReader(f))
 hashes={'source_sha256':proof['source_sha256'],'graph_sha256':sha(a.graph),'inventory_sha256':sha(a.inventory)};result=collect(doc,graph,inventory,policy,hashes);result.update(hashes,policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':result['status'],'records':len(result['records'])}))
if __name__=='__main__':main()
