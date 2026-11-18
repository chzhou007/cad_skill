"""Trace a selected same-caption cross-view diagnostic, never a mapping.

Paths describe graph adjacency only and may include unverified connections.
"""
import argparse,collections,hashlib,json
from pathlib import Path
from source_readability import read_source

def _caption(doc,handle,expected):
 e=doc.entitydb.get(handle)
 if not e or e.dxftype() not in ('TEXT','MTEXT') or e not in doc.modelspace() or e.plain_text()!=expected:raise ValueError('caption source mismatch')
 same=[x for x in doc.modelspace() if x.dxftype() in ('TEXT','MTEXT') and x.plain_text()==expected]
 if len(same)!=1:raise ValueError('caption is not unique in modelspace')
 return {'handle':handle,'text':expected,'layer':e.dxf.layer}

def shortest(graph,start,target,system,excluded,max_hops):
 nodes={n['node_id']:n for n in graph['nodes']};adj=collections.defaultdict(list)
 for e in graph['edges']:
  if e['edge_id'] in excluded or e.get('system')!=system:continue
  a,b=e.get('start_node_id'),e.get('end_node_id')
  if a in nodes and b in nodes:adj[a].append((b,e));adj[b].append((a,e))
 dist={start:0};ways={start:[[]]};queue=collections.deque([start])
 while queue:
  n=queue.popleft();d=dist[n]
  if d>=max_hops or (n!=start and n!=target and nodes[n].get('node_type') in ('equipment','virtual_equipment')):continue
  for v,e in sorted(adj[n],key=lambda x:x[1]['edge_id']):
   if v not in dist:dist[v]=d+1;ways[v]=[];queue.append(v)
   if dist[v]==d+1:
    for path in ways[n]:
     if len(ways[v])<3:ways[v].append(path+[e['edge_id']])
 return ways.get(target,[])

def compare(plan_doc,iso_doc,plan_graph,iso_graph,policy):
 items=policy['comparisons'];pn={n['node_id']:n for n in plan_graph['nodes']};an={n['node_id']:n for n in iso_graph['nodes']};ae={e['edge_id']:e for e in iso_graph['edges']};out=[]
 for x in items:
  equipment=x['equipment_id'];p=pn.get(equipment);a=an.get(equipment)
  if not p or not a or p.get('node_type')!='equipment' or a.get('node_type')!='equipment':raise ValueError('equipment missing from either graph')
  if p.get('floor') is None or p.get('floor')!=a.get('floor'):raise ValueError('equipment floor mismatch')
  pc=_caption(plan_doc,x['plan_text_handle'],equipment);ic=_caption(iso_doc,x['iso_text_handle'],equipment)
  degree=sum(equipment in (e.get('start_node_id'),e.get('end_node_id')) for e in plan_graph['edges'])
  source_insert=plan_doc.entitydb.get(p.get('source_handle'))
  if not source_insert or source_insert.dxftype()!='INSERT' or source_insert not in plan_doc.modelspace():raise ValueError('plan equipment source insert mismatch')
  traces=[]
  for request in x['isometric_routes']:
   e=ae.get(request['anchor_edge']);end=request['anchor_endpoint'];system=request['system']
   if not e or e.get('system')!=system or end not in (e.get('start_node_id'),e.get('end_node_id')):raise ValueError('invalid anchor edge endpoint')
   paths=shortest(iso_graph,end,equipment,system,{e['edge_id']},request.get('max_hops',3))
   traces.append({'system':system,'anchor_edge':e['edge_id'],'anchor_endpoint':end,'paths':paths,'status':'unique_graph_path_unverified' if len(paths)==1 else 'no_or_ambiguous_graph_path','connection_modes':[[ae[id].get('connection_mode') for id in path] for path in paths],'edge_statuses':[[{'edge_id':eid,'path_length_complete':ae[eid].get('path_length_complete'),'physical_length_status':ae[eid].get('physical_length_status')} for eid in path] for path in paths]})
  plan_routes=[];pe={e['edge_id']:e for e in plan_graph['edges']}
  for request in x.get('plan_routes',[]):
   start=request['start_node'];system=request['system'];node=pn.get(start);hops=request.get('max_hops',8)
   if not node or node.get('subtype')!='out_of_plane_riser' or node.get('system')!=system or node.get('floor')!=p.get('floor') or system not in ('supply','return') or not isinstance(hops,int) or not 1<=hops<=100:raise ValueError('invalid plan riser route request')
   paths=shortest(plan_graph,start,equipment,system,set(),hops)
   path_notes=[]
   for path in paths:
    path_notes.append([{'edge_id':eid,'path_length_complete':pe[eid].get('path_length_complete'),'confirmed_interface':bool(pe[eid].get('confirmed_equipment_interface')),'connection_mode':pe[eid].get('connection_mode')} for eid in path])
   plan_routes.append({'system':system,'start_node':start,'paths':paths,'edge_statuses':path_notes,'status':'unique_graph_path_unverified' if len(paths)==1 else 'no_or_ambiguous_graph_path'})
  out.append({'equipment_id':equipment,'plan_caption':pc,'isometric_caption':ic,'plan_insert':p['source_handle'],'plan_node_degree':degree,'plan_connection_status':p.get('connection_status'),'plan_routes':plan_routes,'isometric_routes':traces,'status':'crossview_diagnostic_not_mapping'})
 return {'status':'diagnostic_only','comparisons':out,'plan_graph_mutated':False,'isometric_graph_mutated':False,'hil_ready':False,'limitations':['Exact unique source caption is a correspondence lead, not confirmed device identity.','Paths are current graph adjacency; source connections, port identity and graph correctness are unverified.','No cross-view mapping, hydraulic connection or physical length is established.']}

def main():
 p=argparse.ArgumentParser()
 for n in ('plan-source','iso-source','plan-graph','iso-graph','policy','output'):p.add_argument('--'+n,required=True,type=Path)
 a=p.parse_args();pd,pp=read_source(a.plan_source);ad,ap=read_source(a.iso_source);pb=a.plan_graph.read_bytes();ab=a.iso_graph.read_bytes();policy_bytes=a.policy.read_bytes();policy=json.loads(policy_bytes);sha=lambda b:hashlib.sha256(b).hexdigest()
 if policy['plan_source_sha256']!=pp['source_sha256'] or policy['iso_source_sha256']!=ap['source_sha256'] or policy['plan_graph_sha256']!=sha(pb) or policy['iso_graph_sha256']!=sha(ab):raise ValueError('source or graph hash mismatch')
 pg=json.loads(pb);ag=json.loads(ab)
 if pg.get('metadata',{}).get('source_sha256')!=pp['source_sha256']:raise ValueError('plan graph source mismatch')
 r=compare(pd,ad,pg,ag,policy);r.update(plan_source_sha256=pp['source_sha256'],iso_source_sha256=ap['source_sha256'],plan_graph_sha256=sha(pb),iso_graph_sha256=sha(ab),policy_sha256=sha(policy_bytes),script_sha256=sha(Path(__file__).read_bytes()),plan_preflight=pp,iso_preflight=ap)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'comparisons':r['comparisons']},ensure_ascii=False))
if __name__=='__main__':main()
