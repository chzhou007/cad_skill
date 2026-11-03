"""Derive a scoped hydraulic graph without changing the source/audit graph."""
import copy,json,csv,argparse,math,hashlib
from pathlib import Path

def derive(graph,instances,policy):
 g=copy.deepcopy(graph);original=copy.deepcopy(graph);nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']};retired={};excluded=[];pumps=[];collapsed=[];boundaries=[]
 omit_nodes={k for k,n in nodes.items()if n.get('subtype')in policy.get('excluded_equipment_types',[])or k in policy.get('excluded_equipment_tags',[])or n.get('source_block')in policy.get('excluded_equipment_blocks',[])}
 omit_handles=set(policy.get('excluded_source_handles',[]));omit_systems=set(policy.get('excluded_systems',[]))
 physical_equipment={k for k,n in nodes.items()if n['node_type']=='equipment'}
 if omit_nodes & physical_equipment:raise ValueError('Physical equipment cannot be excluded from the hydraulic model: '+','.join(sorted(omit_nodes & physical_equipment)))
 for eid,e in list(edges.items()):
  if e['start_node_id']in omit_nodes or e['end_node_id']in omit_nodes or e['system']in omit_systems or set(e.get('source_handles',[]))&omit_handles or eid in policy.get('excluded_edge_ids',[]):
   if {e['start_node_id'],e['end_node_id']} & physical_equipment:raise ValueError('Physical equipment connection cannot be discarded: '+eid)
   excluded.append(dict(edge_id=eid,source_handles=e.get('source_handles',[]),reason='explicit_expert_calculation_scope',system=e['system']));del edges[eid]
 def merge(nid,is_pump=False):
  es=[e for e in edges.values()if nid in [e['start_node_id'],e['end_node_id']]]
  if len(es)!=2 or es[0]['system']!=es[1]['system']:return False
  es.sort(key=lambda e:e['edge_id']);a,b=es;u=a['end_node_id']if a['start_node_id']==nid else a['start_node_id'];v=b['end_node_id']if b['start_node_id']==nid else b['start_node_id']
  if u==v:return False
  pa=a['path_points']if a['start_node_id']==u else list(reversed(a['path_points']));pb=b['path_points']if b['start_node_id']==nid else list(reversed(b['path_points']));path=pa+pb[1:]if math.dist(pa[-1],pb[0])<1e-6 else pa+pb
  e=copy.deepcopy(a);e.update(start_node_id=u,end_node_id=v,path_points=path,path_length=sum(math.dist(p,q)for p,q in zip(path,path[1:])),attribute_paths=a.get('attribute_paths',[a['path_points']])+b.get('attribute_paths',[b['path_points']]),source_handles=sorted(set(a.get('source_handles',[])+b.get('source_handles',[]))),source_edge_ids=list(dict.fromkeys(a.get('source_edge_ids',[a['edge_id']])+b.get('source_edge_ids',[b['edge_id']]))),edge_type='calculation_adjacent_nodes')
  e.pop('start_port_id',None);e.pop('end_port_id',None)
  for dest,source,nkey in [('start_port_id',a,u),('end_port_id',b,v)]:
   p=source.get('start_port_id'if source['start_node_id']==nkey else'end_port_id')
   if p:e[dest]=p
  del edges[b['edge_id']];edges[a['edge_id']]=e;retired[b['edge_id']]=a['edge_id'];del nodes[nid]
  collapsed.append(dict(source_node_id=nid,edge_id=a['edge_id']))
  if is_pump:pumps.append(dict(equipment=copy.deepcopy(original_node[nid]),source_edges=[a['edge_id'],b['edge_id']],edge_id=a['edge_id']))
  return True
 original_node=copy.deepcopy(nodes)
 for nid in list(nodes):
  if nodes[nid].get('subtype')in policy.get('inline_equipment_types',['Water Pump']):merge(nid,True)
 changed=True
 while changed:
  changed=False
  for nid in list(nodes):
   if nodes[nid]['node_type']in ['tee','physical_junction']and merge(nid):changed=True
 def current(eid):
  while eid in retired:eid=retired[eid]
  return eid
 active={k for e in edges.values()for k in [e['start_node_id'],e['end_node_id']]};nodes={k:n for k,n in nodes.items()if k in active or n['node_type']=='equipment'};kept=[];excluded_instances=[]
 for d in instances:
  r=copy.deepcopy(d);eid=current(r['edge_id'])
  if eid in edges:r['edge_id']=eid;r['related_edge_ids']=[current(x)for x in (json.loads(r['related_edge_ids'])if isinstance(r.get('related_edge_ids'),str)and r['related_edge_ids']else r.get('related_edge_ids',[]))if current(x)in edges];kept.append(r)
  else:excluded_instances.append(r)
 for i,p in enumerate(pumps):
  n=p['equipment'];eid=current(p['edge_id']);p['edge_id']=eid;edges[eid].setdefault('inline_equipment',[]).append(n)
  kept.append(dict(device_name=n['node_id'],equipment_type='Water Pump',edge_id=eid,assignment_status='assigned',source_kind='source_inline_equipment',source_block_name=n.get('source_block',''),source_top_handle=n.get('source_handle')or(n.get('source_handles')or[''])[0],source_handles=n.get('display_source_handles')or n.get('source_handles',[]),x=n['x'],y=n['y'],assignment_x=n['x'],assignment_y=n['y'],edge_distance=0,profile_candidates=n.get('profile_candidates',[]),normalization='source_equipment_collapsed_to_edge_attribute'))
 for nid,n in list(nodes.items()):
  if n['node_type']not in ['tee','physical_junction']:continue
  incident={e['system']for e in edges.values()if nid in [e['start_node_id'],e['end_node_id']]};n['incident_systems']=sorted(incident)
  if len(incident)==1:n['source_noted_system']=n.get('system');n['system']=next(iter(incident));n['mixed_source_contact']=False;n['system_review_required']=False
  elif len(incident)>1:n['mixed_source_contact']=True;n['system_review_required']=True
  adj=[e for e in edges.values()if nid in [e['start_node_id'],e['end_node_id']]]
  if len(adj)!=3:
   new='CB-'+nid;n.update(source_node_id=nid,node_id=new,node_type='virtual_equipment',subtype='calculation_service_boundary',boundary_type='unresolved_source_terminal',review_required=True,label=new,ports=[])
   for e in adj:
    pid=new+'-'+e['edge_id'];key='start'if e['start_node_id']==nid else'end';e[key+'_node_id']=new;e[key+'_port_id']=pid;n['ports'].append(dict(port_id=pid,x=n['x'],y=n['y'],system=e['system'],status='unverified_logical_boundary',physical_port_verified=False))
   del nodes[nid];nodes[new]=n;boundaries.append(dict(source_node_id=nid,node_id=new,reason='Calculation scope or unresolved service boundary; not a physical T'))
 equipment_coverage=[]
 for nid,n in nodes.items():
  if n['node_type']!='equipment':continue
  n['hydraulic_model']={'included':True,'resistance_status':'parameter_required','assumed_zero_resistance':False,'solver_ready':False}
  source_adj=[e['edge_id']for e in original['edges']if nid in[e['start_node_id'],e['end_node_id']]]
  live_adj=[e['edge_id']for e in edges.values()if nid in[e['start_node_id'],e['end_node_id']]]
  equipment_coverage.append(dict(node_id=nid,representation='equipment_node',source_edges=source_adj,active_edges=live_adj,connection_status='source_connections_retained'if live_adj else'source_ports_unresolved',resistance_status='parameter_required'))
 for p in pumps:
  equipment_coverage.append(dict(node_id=p['equipment']['node_id'],representation='inline_equipment',edge_id=p['edge_id'],resistance_status='pump_curve_required'))
  for n in edges[p['edge_id']].get('inline_equipment',[]):n['hydraulic_model']={'included':True,'resistance_status':'pump_curve_required','assumed_zero_resistance':False,'solver_ready':False}
 represented={r['node_id']for r in equipment_coverage}
 if physical_equipment-represented:raise ValueError('Physical equipment lost from calculation model')
 g['hydraulicEquipmentCoverage']=equipment_coverage
 g['hydraulicReadiness']={'solver_ready':False,'reason':'Equipment resistance parameters and source service classifications require verification; no zero resistance assumed'}
 g['nodes']=list(nodes.values());g['edges']=list(edges.values());g['technicalPending']=[dict(id='CALCULATION-SCOPE',reason='Derived connectivity only. Physical equipment and source-supported connections retained. Measurement-only simplifications remain audited; resistance parameters, service conflicts and flow directions are not solver-certified.')];g['calculationScope']=dict(policy=policy,source_nodes=len(original['nodes']),source_edges=len(original['edges']),source_graph_retained=True);g['junctionValidation']={'new_unexplained_degree_exceptions':[]};g['sourceTaggedHeadCoverage']=[dict(r,status='calculation_scope_context_only')for r in g.get('sourceTaggedHeadCoverage',[])]
 return g,kept,dict(excluded_edges=excluded,excluded_instances=excluded_instances,retired_edges={k:current(k)for k in retired},collapsed_nodes=[dict(r,edge_id=current(r['edge_id']))for r in collapsed],boundary_nodes=boundaries,inline_equipment=pumps,source_instances=len(instances),active_instances=len(kept),conservation=len(instances)==len(kept)-len(pumps)+len(excluded_instances))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--graph',type=Path,required=True);p.add_argument('--devices',type=Path,required=True);p.add_argument('--policy',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();policy=json.loads(a.policy.read_text(encoding='utf8'))
 if policy.get('input_graph_sha256')and hashlib.sha256(a.graph.read_bytes()).hexdigest()!=policy['input_graph_sha256']:raise ValueError('Calculation scope belongs to another input graph; rebind expert source scope')
 g=json.loads(a.graph.read_text(encoding='utf8'));rows=list(csv.DictReader(a.devices.open(encoding='utf-8-sig')));rows=[r for r in rows if r.get('assignment_status')=='assigned'];g,rows,audit=derive(g,rows,policy);a.output.mkdir(parents=True,exist_ok=False)
 for name,obj in [('graph_with_edges.json',g),('calculation_scope_audit.json',audit)]: (a.output/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with(a.output/'edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(list,dict))else v for k,v in r.items()}for r in rows)
if __name__=='__main__':main()
