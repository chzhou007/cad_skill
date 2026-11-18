"""Apply a hash-pinned, expert-calibrated two-port joint repair in isolation.

This is an opt-in post-build operation; it never edits the input or confirms HIL.
"""
from pathlib import Path
from collections import Counter
import argparse,copy,csv,hashlib,json,math
from source_readability import read_source

def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def fingerprint(block):
 a=[]
 for e in block:
  if e.dxftype()=='SPLINE':a.append({'type':'SPLINE','degree':e.dxf.degree,'knots':list(e.knots),'control_points':[list(x) for x in e.control_points]})
  elif e.dxftype()=='POINT':a.append({'type':'POINT','p':list(e.dxf.location)})
  elif e.dxftype()=='LINE':a.append({'type':'LINE','a':list(e.dxf.start),'b':list(e.dxf.end)})
  else:raise ValueError('unsupported block geometry')
 return hashlib.sha256(json.dumps(a,ensure_ascii=False,sort_keys=True).encode('utf8')).hexdigest()

def _ray(e,n,tol):
 p=e.get('path_points') or e.get('path');q=[n['x'],n['y']]
 if e['end_node_id']==n['node_id']:p=list(reversed(p))
 elif e['start_node_id']!=n['node_id']:raise ValueError('nonincident node')
 if math.dist(q,p[0])>tol:raise ValueError('edge endpoint mismatch')
 for x in p[1:]:
  d=math.dist(q,x)
  if d>tol:return [(x[i]-q[i])/d for i in (0,1)]
 raise ValueError('missing edge ray')

def repair(graph,devices,doc,policy):
 g=copy.deepcopy(graph);devices=copy.deepcopy(devices);nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']}
 if policy.get('confirmation_basis')=='source_geometry_calibrated' and g.get('expertFlexibleJointRepair'):raise ValueError('existing flexible-joint repair requires explicit history reconciliation')
 if len(nodes)!=len(g['nodes']) or len(edges)!=len(g['edges']):raise ValueError('duplicate graph IDs')
 handles=policy['instance_handles'];block=policy['block_name'];tol=float(policy['contact_tolerance']);angle_tol=float(policy['angle_tolerance_degrees'])
 if not handles or len(handles)!=len(set(handles)) or not 0<tol<=1 or not 0<angle_tol<=2:raise ValueError('invalid explicit scope or tolerances')
 if block not in doc.blocks or fingerprint(doc.blocks[block])!=policy['block_fingerprint_sha256']:raise ValueError('block fingerprint mismatch')
 mapping={};steps=[];new=[]
 def resolve(eid):
  seen=set()
  while eid in mapping:
   if eid in seen:raise ValueError('cyclic mapping')
   seen.add(eid);eid=mapping[eid]
  return eid
 for h in handles:
  ins=doc.entitydb.get(h)
  if ins is None or ins.dxftype()!='INSERT' or ins.dxf.name!=block or ins.dxf.owner!=doc.modelspace().block_record_handle:raise ValueError('incorrect native insert '+h)
  glyph=list(ins.virtual_entities());pts=[p.dxf.location for p in glyph if p.dxftype()=='POINT']
  if len(pts)!=2:raise ValueError('expected two transformed points')
  ends=[]
  for p in pts:
   hit=[n for n in nodes.values() if math.dist((n['x'],n['y']),(p.x,p.y))<=tol]
   if len(hit)!=1 or hit[0].get('subtype')!='unresolved_source_terminal':raise ValueError('ambiguous endpoint '+h)
   n=hit[0];adj=[e for e in edges.values() if n['node_id'] in (e['start_node_id'],e['end_node_id'])]
   if len(adj)!=1:raise ValueError('endpoint is not degree one')
   ends.append((n,adj[0]))
  (u,eu),(v,ev)=ends
  if policy.get('confirmation_basis')=='source_geometry_calibrated':
   bars=[x for x in glyph if x.dxftype()=='LINE']
   if sorted(x.dxftype() for x in glyph)!=['LINE','LINE','POINT','POINT','SPLINE'] or len(bars)!=2:raise ValueError('unexpected native flexible-joint glyph')
   mids=[(x.dxf.start+x.dxf.end)/2 for x in bars]
   if any(sum(math.dist(pt,mid)<=tol for mid in mids)!=1 for pt in pts):raise ValueError('joint bar and point mismatch')
   layer={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}
   for pt,(node,edge) in zip(pts,ends):
    matches=[x for x in doc.modelspace().query('LINE') if x.dxf.layer==layer.get(edge['system']) and min(math.dist(pt,x.dxf.start),math.dist(pt,x.dxf.end))<=tol]
    if len(matches)!=1 or matches[0].dxf.handle not in edge.get('source_handles',[]):raise ValueError('joint contact source line missing or ambiguous')
   if any(d.get('source_handle')==h or d.get('source_top_handle')==h for d in devices):raise ValueError('joint already in component inventory')
  if eu['edge_id']==ev['edge_id'] or eu['system']!=ev['system'] or eu['system'] not in policy['allowed_systems'] or u['floor']!=v['floor']:raise ValueError('mixed system, floor or cycle')
  axis=[v['x']-u['x'],v['y']-u['y']];span=math.hypot(*axis)
  if span<=tol:raise ValueError('degenerate joint')
  axis=[x/span for x in axis];ru,rv=_ray(eu,u,tol),_ray(ev,v,tol)
  dot=lambda a,b:sum(x*y for x,y in zip(a,b))
  if dot(ru,axis)>-math.cos(math.radians(angle_tol)) or dot(rv,axis)<math.cos(math.radians(angle_tol)):raise ValueError('nonaligned contact rays')
  # Prefer retaining an equipment-branch ID; otherwise preserve the longer edge.
  def score(e,n):
   outside=e['end_node_id'] if e['start_node_id']==n['node_id'] else e['start_node_id']
   return (nodes[outside]['node_type']=='equipment',e['path_length'],e['edge_id'])
  anchor,other=(eu,ev) if score(eu,u)>=score(ev,v) else (ev,eu);nu,nv=(u,v) if anchor is eu else (v,u)
  a=anchor['end_node_id'] if anchor['start_node_id']==nu['node_id'] else anchor['start_node_id'];b=other['end_node_id'] if other['start_node_id']==nv['node_id'] else other['start_node_id']
  if a==b:raise ValueError('self-loop')
  def orient(e,start):
   p=e.get('path_points') or e['path'];return list(p if e['start_node_id']==start else reversed(p))
  merged=copy.deepcopy(anchor);path=orient(anchor,a)+orient(other,nv['node_id'])
  merged.update(start_node_id=a,end_node_id=b,path=path,path_points=path,attribute_paths=copy.deepcopy(anchor['attribute_paths']+other['attribute_paths']),source_handles=sorted(set(anchor['source_handles']+other['source_handles'])),path_length=anchor['path_length']+other['path_length'],path_length_complete=False,path_length_scope='source_drawn_pipe_only_flexible_joint_interior_unknown',connection_mode=('source_geometry_calibrated_native_flexible_joint_unreviewed' if policy.get('confirmation_basis')=='source_geometry_calibrated' else 'expert_confirmed_native_flexible_joint'))
  risers=copy.deepcopy(anchor.get('source_riser_interfaces',[])+other.get('source_riser_interfaces',[]))
  if risers:
   merged['source_riser_interfaces']=risers
   merged['path_length_scope']='source_drawn_pipe_only_flexible_joint_and_riser_lengths_unknown'
  riser_connections=copy.deepcopy(anchor.get('source_expert_riser_connections',[])+other.get('source_expert_riser_connections',[]))
  if riser_connections:
   merged['source_expert_riser_connections']=riser_connections
   merged['path_length_scope']='source_drawn_pipe_only_flexible_joint_and_riser_lengths_unknown'
  name=policy['device_id_prefix']+h
  if any(d['device_name']==name for d in devices+new):raise ValueError('device identity collision')
  merged['equipment_names']=anchor.get('equipment_names',[])+other.get('equipment_names',[])+[name];cnt=Counter(anchor.get('equipment_counts',{}));cnt.update(other.get('equipment_counts',{}));cnt['flexible_joint']+=1;merged['equipment_counts']=dict(cnt)
  merged['source_flexible_joints']=copy.deepcopy(anchor.get('source_flexible_joints',[])+other.get('source_flexible_joints',[]))+[{'source_handle':h,'source_block':block,'source_contact_points':[[u['x'],u['y']],[v['x'],v['y']]],'source_graphic_span':span,'physical_length':'unknown','parameter_status':'unknown_not_zero','expert_feedback':policy['expert_evidence']}]
  if policy.get('confirmation_basis')=='source_geometry_calibrated':merged['source_flexible_joints'][-1].update(confirmation_basis='source_geometry_calibrated',human_accepted=False)
  for side,nid,e in [('start',a,anchor),('end',b,other)]:
   merged.pop(side+'_port_id',None);old='start' if e['start_node_id']==nid else 'end'
   if e.get(old+'_port_id'):merged[side+'_port_id']=e[old+'_port_id']
  merged['edge_type']='tee_to_virtual_equipment' if any(nodes[i]['node_type']=='virtual_equipment' for i in (a,b)) else 'tee_to_equipment' if any(nodes[i]['node_type']=='equipment' for i in (a,b)) else 'tee_to_tee'
  del edges[other['edge_id']];edges[anchor['edge_id']]=merged;mapping[other['edge_id']]=anchor['edge_id'];del nodes[u['node_id']];del nodes[v['node_id']]
  new.append({'device_name':name,'equipment_type':'flexible_joint','type_code':policy.get('type_code','FLEX'),'x':str(ins.dxf.insert.x),'y':str(ins.dxf.insert.y),'source_kind':'block_reference','source_block_name':block,'source_handle':h,'edge_id':anchor['edge_id'],'edge_distance':'0','assignment_status':'assigned'})
  steps.append({'source_handle':h,'old_nodes':[u['node_id'],v['node_id']],'system':eu['system'],'retained_edge':anchor['edge_id'],'source_graphic_span':span})
 for d in devices+new:d['edge_id']=resolve(d['edge_id'])
 for glyph in g.get('sourceTerminalGlyphs',[]):
  glyph['edge_id']=resolve(glyph['edge_id'])
  if glyph['node_id'] not in nodes or glyph['edge_id'] not in edges or glyph['node_id'] not in (edges[glyph['edge_id']]['start_node_id'],edges[glyph['edge_id']]['end_node_id']):raise ValueError('terminal glyph ownership lost during joint merge')
 for e in edges.values():
  assigned=[d for d in devices+new if d['edge_id']==e['edge_id']]
  if Counter(d['equipment_type'] for d in assigned)!=Counter(e.get('equipment_counts',{})) or Counter(d['device_name'] for d in assigned)!=Counter(e.get('equipment_names',[])):raise ValueError('instance conservation failed')
 g['nodes']=list(nodes.values());g['edges']=list(edges.values());g.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False)
 g['expertFlexibleJointRepair']={'expert_evidence':policy['expert_evidence'],'steps':steps,'edge_id_mapping':{k:resolve(v) for k,v in mapping.items()}}
 if policy.get('confirmation_basis')=='source_geometry_calibrated':g['expertFlexibleJointRepair'].update(confirmation_basis='source_geometry_calibrated',human_accepted=False)
 return g,devices+new,g['expertFlexibleJointRepair']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--graph',type=Path,required=True);ap.add_argument('--devices',type=Path,required=True);ap.add_argument('--policy',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 p=json.loads(a.policy.read_text(encoding='utf8'));doc,proof=read_source(a.source)
 if proof['source_sha256']!=p['source_sha256'] or sha(a.graph)!=p['graph_sha256'] or sha(a.devices)!=p['devices_sha256']:raise ValueError('input hash mismatch')
 graph=json.loads(a.graph.read_text(encoding='utf8'))
 with a.devices.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;devices=list(r)
 g,rows,audit=repair(graph,devices,doc,p)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 fields=list(dict.fromkeys(fields+[k for row in rows for k in row]))
 with (a.output/'assigned_edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
 (a.output/'repair-audit.json').write_text(json.dumps({'source_sha256':proof['source_sha256'],'graph_sha256':sha(a.graph),'steps':audit['steps'],'edge_id_mapping':audit['edge_id_mapping'],'human_review':'unreviewed'},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'instances':len(audit['steps']),'nodes':len(g['nodes']),'edges':len(g['edges'])}))
if __name__=='__main__':main()
