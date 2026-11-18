"""Audit explicit source spline-joint contacts; never change topology or ownership."""
import argparse,csv,hashlib,json,math
from pathlib import Path
from native_line_path_evidence import LAYERS,_on
from source_readability import read_source

def audit(doc,graph,inventory,policy,hashes,tol=.05):
 for key in ('source_sha256','graph_sha256','inventory_sha256'):
  if policy.get(key)!=hashes.get(key):raise ValueError('input hash mismatch')
 if not 0<tol<=.05:raise ValueError('invalid tolerance')
 edges={e['edge_id']:e for e in graph['edges']};rows={r['device_name']:r for r in inventory};selection=policy['components']
 if len(edges)!=len(graph['edges']) or len(rows)!=len(inventory) or not selection or len(selection)!=len(set(selection)):raise ValueError('duplicate or empty selection')
 layer_system={v:k for k,v in LAYERS.items()};lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in layer_system];out=[]
 for name in selection:
  row=rows.get(name);edge=edges.get(row.get('edge_id')) if row else None;handle=row.get('source_top_handle') if row else None;joint=doc.entitydb.get(handle) if handle else None
  if not row or not edge or row.get('equipment_type')!='金属软接' or row.get('assignment_status')!='assigned' or row.get('source_block_name')!=policy['block_name'] or not joint or joint.dxftype()!='INSERT' or joint not in doc.modelspace() or joint.dxf.name!=policy['block_name']:raise ValueError('source/component binding mismatch')
  ins=joint.ocs().to_wcs(joint.dxf.insert)
  if math.dist((float(row['x']),float(row['y'])),(ins.x,ins.y))>tol:raise ValueError('component position mismatch')
  geometry=list(joint.virtual_entities());bars=[e for e in geometry if e.dxftype()=='LINE'];points=[e for e in geometry if e.dxftype()=='POINT']
  if sorted(e.dxftype() for e in geometry)!=['LINE','LINE','POINT','POINT','SPLINE']:raise ValueError('unsupported joint geometry')
  mid=[(e.dxf.start+e.dxf.end)/2 for e in bars]
  if math.dist(mid[0],mid[1])<=tol or any(sum(math.dist(p.dxf.location,m)<=tol for p in points)!=1 for m in mid):raise ValueError('joint midpoint markers mismatch')
  contacts=[]
  for point in mid:
   found=[]
   for line in lines:
    a,b=line.dxf.start,line.dxf.end
    if abs(a.z-point.z)>tol or abs(b.z-point.z)>tol or not _on(tuple(point)[:2],tuple(a)[:2],tuple(b)[:2],tol):continue
    witnesses=[e['edge_id'] for e in graph['edges'] if e.get('system')==layer_system[line.dxf.layer] and any(_on(tuple(point)[:2],u,v,tol) for path in e.get('attribute_paths',[]) for u,v in zip(path,path[1:]))]
    found.append({'source_handle':line.dxf.handle,'system':layer_system[line.dxf.layer],'assigned_edge_witnessed':edge['edge_id'] in witnesses,'graph_witness_edges':sorted(witnesses),'contact_at_endpoint':min(math.dist(point,a),math.dist(point,b))<=tol})
   contacts.append({'point':list(point),'lines':found})
  if all(len(c['lines'])==1 for c in contacts):
   systems={c['lines'][0]['system'] for c in contacts}
   if len(systems)>1:status='opposite_system_source_conflict'
   elif edge.get('system') not in systems:status='assigned_system_mismatch'
   elif all(c['lines'][0]['assigned_edge_witnessed'] for c in contacts):status='same_system_assigned_edge_contact_witnessed'
   else:status='assigned_edge_not_witnessed_on_both_contacts'
  else:status='ambiguous_or_missing_native_pipe'
  out.append({'device_name':name,'source_handle':handle,'edge_id':edge['edge_id'],'assigned_system':edge.get('system'),'contacts':contacts,'status':status,'human_accepted':False})
 return {'status':'source_geometry_audit_not_connectivity_proof','records':out,'source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'inventory_sha256':hashes['inventory_sha256'],'graph_mutated':False,'hil_ready':False,'limitations':['Contact geometry and assigned-edge witnesses do not prove physical connectivity, installed length or human acceptance.','Only same-system modelspace LINEs are inspected; other source entities are not excluded.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','inventory','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 with a.inventory.open(encoding='utf-8-sig',newline='') as f:inv=list(csv.DictReader(f))
 res=audit(doc,json.loads(a.graph.read_text(encoding='utf8')),inv,json.loads(a.policy.read_text(encoding='utf8')),{k:sha(getattr(a,k[:-7] if k!='inventory_sha256' else 'inventory')) for k in ('source_sha256','graph_sha256','inventory_sha256')});res.update(policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(res,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'records':len(res['records']),'witnessed':sum(x['status']=='same_system_assigned_edge_contact_witnessed' for x in res['records'])}))
if __name__=='__main__':main()
