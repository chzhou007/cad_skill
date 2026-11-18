"""Derive a scoped hydraulic graph without changing the source/audit graph."""
import copy,json,csv,argparse,math,hashlib
from pathlib import Path

def merged_length(a,b,display_gap):
 """Sum witnessed source lengths, never a synthetic display connector."""
 def value(edge):
  v=edge.get('source_path_length')
  if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0:
   safe_scopes={'source_drawn_pipe_only_symbol_interior_excluded',
                'source_drawn_pipe_only_section_connector_length_unknown',
                'source_drawn_pipe_only_overlay_continuation_unknown',
                'sum_of_source_edge_lengths_no_display_connector'}
   v=edge.get('path_length') if edge.get('path_length_complete') is True or edge.get('path_length_scope') in safe_scopes else None
  return v if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0 else None
 vals=[value(a),value(b)]
 complete=all(e.get('path_length_complete') is True for e in (a,b)) and display_gap<=1e-6 and all(v is not None for v in vals)
 evidence=[]
 for edge,v in zip((a,b),vals):
  existing=edge.get('calculation_source_length_evidence')
  if existing:evidence.extend(copy.deepcopy(existing))
  else:evidence.append({'edge_id':edge['edge_id'],'recorded_source_length':v,'path_length_complete':edge.get('path_length_complete'),
                        'path_length_scope':edge.get('path_length_scope')})
 return (sum(vals) if all(v is not None for v in vals) else None),complete,evidence

def merged_inventory(a,b):
 """Conserve per-type named components across a degree-two contraction."""
 groups={}
 for edge in (a,b):
  for item in edge.get('equipment_inventory',[]):
   names=item.get('device_names');typ=item.get('equipment_type')
   if not typ or not isinstance(names,list) or item.get('count')!=len(names):raise ValueError('Invalid edge component inventory')
   groups.setdefault(typ,[]).extend(names)
 if len([n for names in groups.values() for n in names])!=len({n for names in groups.values() for n in names}):raise ValueError('Duplicate edge component identity')
 return [{'equipment_type':typ,'count':len(names),'device_names':names} for typ,names in sorted(groups.items())]

def source_supported_equipment_attachment(graph, edge, node_id, covered_source):
 """Accept only source-bound logical ownership; never establish a physical port."""
 a=edge.get('source_block_equipment_attachment');b=graph.get('sourceBlockEquipmentAttachment');x=edge.get('source_device_extension')
 if not all(isinstance(v,dict) for v in (a,b,x)):return False
 nodes=[n for n in graph['nodes'] if n.get('node_id')==node_id]
 if len(nodes)!=1:return False
 expected={'start_node_id':edge.get('start_node_id'),'end_node_id':edge.get('end_node_id'),'system':edge.get('system'),'attribute_paths':edge.get('attribute_paths'),'equipment_xy':[nodes[0].get('x'),nodes[0].get('y')]}
 if a.get('source_edge_snapshot')!=expected:return False
 side='start' if edge.get('start_node_id')==node_id else 'end' if edge.get('end_node_id')==node_id else None
 mappings=b.get('mappings');matches=[m for m in mappings if isinstance(m,dict) and m.get('edge_id')==edge.get('edge_id') and m.get('equipment_id')==node_id and m.get('system')==edge.get('system') and m.get('source_insert_handle')==a.get('source_insert_handle') and m.get('source_circle_handle')==a.get('source_circle_handle')] if isinstance(mappings,list) else []
 return bool(side and a.get('status')=='source_supported_logical_attachment_not_human_accepted' and b.get('status')=='source_supported_logical_attachments_not_human_accepted' and covered_source and a.get('source_sha256')==b.get('source_sha256')==x.get('source_sha256')==covered_source and a.get('input_graph_sha256') and a.get('input_graph_sha256')==b.get('input_graph_sha256') and a.get('evidence_sha256') and a.get('evidence_sha256')==b.get('evidence_sha256') and a.get('equipment_id')==node_id and a.get('interface_side')==side and edge.get('source_insert_handle')==a.get('source_insert_handle') and x.get('source_circle_chain')==[a.get('source_insert_handle'),a.get('source_circle_handle')] and isinstance(a.get('source_joint_chain'),list) and a.get('source_joint_chain')==x.get('source_joint_chain') and x.get('status')=='source_drawn_line_with_joint_evidence_unreviewed' and x.get('physical_port_verified') is False and x.get('physical_length')=='unknown' and a.get('physical_port_verified') is False and a.get('physical_length')=='unknown' and a.get('human_accepted') is False and b.get('physical_ports_verified') is False and b.get('physical_lengths_known') is False and b.get('human_accepted') is False and edge.get('physical_length')=='unknown' and edge.get('path_length_complete') is False and len(matches)==1)

def require_witnessed_equipment_connections(graph):
 """Do not promote an unwitnessed drawing connector into a hydraulic port."""
 nodes={n['node_id']:n for n in graph['nodes']};source_hash=graph.get('metadata',{}).get('source_sha256');coverage_sources=set()
 for e in graph['edges']:
  coverage=e.get('source_path_coverage')
  if coverage is None:continue
  equipment=[nodes.get(e.get(side+'_node_id')) for side in ('start','end')]
  equipment=[n for n in equipment if n and n.get('node_type')=='equipment']
  if not equipment:continue
  paths=e.get('attribute_paths');indices=coverage.get('unverified_segment_indices') if isinstance(coverage,dict) else None
  covered_source=coverage.get('source_sha256') if isinstance(coverage,dict) else None
  if (not isinstance(paths,list) or len(paths)!=1 or len(paths[0])<2 or not isinstance(indices,list) or not indices or any(isinstance(i,bool) or not isinstance(i,int) or i<0 or i>=len(paths[0])-1 for i in indices) or len(set(indices))!=len(indices) or not isinstance(covered_source,str) or not covered_source or (source_hash and covered_source!=source_hash)):raise ValueError('Invalid equipment source path coverage: '+e['edge_id'])
  coverage_sources.add(covered_source)
  if len(coverage_sources)>1:raise ValueError('Mixed source path coverage')
  for n in equipment:
   xy=[n.get('x'),n.get('y')]
   if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in xy):raise ValueError('Invalid equipment coordinates: '+n['node_id'])
   path=paths[0];touches=(0 in indices and math.dist(xy,path[0])<=.05) or (len(path)-2 in indices and math.dist(xy,path[-1])<=.05)
   reaches=min(math.dist(xy,path[0]),math.dist(xy,path[-1]))<=.05
   if not touches and reaches:continue
   c=e.get('confirmed_equipment_interface');confirmation=c.get('confirmation',{}) if isinstance(c,dict) else {}
   side='start' if e.get('start_node_id')==n['node_id'] else 'end'
   repair=graph.get('confirmedEquipmentInterfaceRepair');bound=False
   while isinstance(repair,dict):
    original=c.get('original_interface',{}) if isinstance(c,dict) else {}
    bound=bound or (repair.get('source_sha256')==covered_source and repair.get('confirmation')==confirmation and any(m.get('edge_id')==e['edge_id'] and m.get('equipment_id')==n['node_id'] and m.get('system')==e.get('system') and m.get('retired_node_id')==original.get('node_id') for m in repair.get('mappings',[])))
    repair=repair.get('previous_repair')
   confirmed=(bound and isinstance(c,dict) and c.get('source_sha256')==covered_source and c.get('interface_side')==side and c.get('physical_port_verified') is False and c.get('interface_to_equipment_length_known') is False and confirmation.get('confirmed_by')=='user' and bool(confirmation.get('question')) and bool(confirmation.get('answer')))
   if not confirmed and not source_supported_equipment_attachment(graph,e,n['node_id'],covered_source):raise ValueError('Unwitnessed equipment connection blocks hydraulic graph: '+e['edge_id'])

def derive(graph,instances,policy):
 for key in ('sourceInlineSystemConflicts','sourceCircleCrossoverConflicts'):
  conflicts=graph.get(key,[])
  if not isinstance(conflicts,list) or any(not isinstance(x,dict) for x in conflicts):raise ValueError('Invalid source conflict record: '+key)
  if conflicts:raise ValueError('Unresolved source conflict blocks hydraulic graph: '+key)
 detail=graph.get('sourceDetailComparison')
 if detail is not None:
  raise ValueError('Source main/detail alternative is present: resolve its equipment and boundary mapping before deriving a hydraulic graph')
 require_witnessed_equipment_connections(graph)
 pending_edges=[e.get('edge_id','?') for e in graph.get('edges',[]) if isinstance(e.get('source_expert_circle_link'),dict) and e['source_expert_circle_link'].get('similar_location_inferred') is True]
 pending_records=[r.get('created_tee','?') for r in graph.get('expertLeftCircleRepairs',[]) if isinstance(r,dict) and r.get('similar_location_inferred') is True]
 if pending_edges or pending_records:
  raise ValueError('Inferred similar-circle connection requires source reconciliation before deriving a hydraulic graph: '+','.join(sorted(set(pending_edges+pending_records))))
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
  length,complete,length_evidence=merged_length(a,b,math.dist(pa[-1],pb[0]))
  e=copy.deepcopy(a);e.update(start_node_id=u,end_node_id=v,path_points=path,path_length=length,path_length_complete=complete,
   path_length_scope='sum_of_source_edge_lengths_no_display_connector',calculation_source_length_evidence=length_evidence,
   attribute_paths=a.get('attribute_paths',[a['path_points']])+b.get('attribute_paths',[b['path_points']]),source_handles=sorted(set(a.get('source_handles',[])+b.get('source_handles',[]))),source_edge_ids=list(dict.fromkeys(a.get('source_edge_ids',[a['edge_id']])+b.get('source_edge_ids',[b['edge_id']]))),edge_type='calculation_adjacent_nodes',equipment_inventory=merged_inventory(a,b))
  # A contracted edge is not the original evidence-bearing edge. Keep its
  # attachment as source-edge provenance rather than misbinding its ID/side.
  attachments=[]
  for old in (a,b):
   attachments.extend(copy.deepcopy(old.get('calculation_source_equipment_attachments',[])))
   if old.get('source_block_equipment_attachment'):
    attachments.append({'source_edge_id':old['edge_id'],'evidence':copy.deepcopy(old['source_block_equipment_attachment'])})
  e.pop('source_block_equipment_attachment',None)
  if attachments:e['calculation_source_equipment_attachments']=attachments
  else:e.pop('calculation_source_equipment_attachments',None)
  # The merged graph's length summarizes both sources; inherited single-edge
  # length metadata would otherwise be mistaken for the new edge's scope.
  for key in ('source_path_length','length_scope','length_scope_before_graphic_separation','path_length_before_graphic_separation'):
   e.pop(key,None)
  for key in ('source_symbol_connectors','source_overlay_connectors'):
   combined=copy.deepcopy(a.get(key,[]))+copy.deepcopy(b.get(key,[]))
   if combined:e[key]=combined
   else:e.pop(key,None)
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
 g.setdefault('metadata',{}).update(hil_ready=False,review_status='unreviewed')
 g['nodes']=list(nodes.values());g['edges']=list(edges.values());g['technicalPending']=copy.deepcopy(original.get('technicalPending',[]))+[dict(id='CALCULATION-SCOPE',reason='Derived connectivity only. Physical equipment and source-supported connections retained. Measurement-only simplifications remain audited; resistance parameters, service conflicts and flow directions are not solver-certified.')];g['calculationScope']=dict(policy=policy,source_nodes=len(original['nodes']),source_edges=len(original['edges']),source_graph_retained=True);g['junctionValidation']={'new_unexplained_degree_exceptions':[]};g['sourceTaggedHeadCoverage']=[dict(r,status='calculation_scope_context_only')for r in g.get('sourceTaggedHeadCoverage',[])]
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
