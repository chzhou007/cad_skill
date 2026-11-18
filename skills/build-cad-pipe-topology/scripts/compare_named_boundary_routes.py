"""Compare scoped, named same-system boundary paths; never establishes a mapping."""
import argparse,hashlib,json
from pathlib import Path
from crossview_route_diagnostics import shortest

def compare(plan,axis,screen,axis_evidence,policy,plan_hash,axis_hash,plan_source,axis_source):
 if (policy.get('plan_graph_sha256')!=plan_hash or policy.get('axis_graph_sha256')!=axis_hash or policy.get('plan_source_sha256')!=plan_source or policy.get('axis_source_sha256')!=axis_source or plan.get('metadata',{}).get('source_sha256')!=plan_source):raise ValueError('stale source or graph')
 if screen.get('status')!='scoped_leader_candidates_not_binding' or screen.get('graph_sha256')!=plan_hash or screen.get('source_sha256')!=plan_source or screen.get('mapping_ready') is not False:raise ValueError('plan leader evidence mismatch')
 if axis_evidence.get('status')!='source_geometry_witnesses_crossview_not_accepted' or axis_evidence.get('axis_graph_sha256')!=axis_hash or axis_evidence.get('axis_source_sha256')!=axis_source or axis_evidence.get('mapping_ready') is not False:raise ValueError('axis leader evidence mismatch')
 ps={r['node_id']:r for r in screen['selections']};ar={r['axis']['port_id']:r for r in axis_evidence['pairs']};pn={n['node_id']:n for n in plan['nodes']};an={n['node_id']:n for n in axis['nodes']};pe={e['edge_id']:e for e in plan['edges']};ae={e['edge_id']:e for e in axis['edges']};rows=[]
 for item in policy['comparisons']:
  system=item['system'];ends=item['ends']
  if system not in ('supply','return') or len(ends)!=2:raise ValueError('invalid system or ends')
  pnids=[];axis_edges=[];axis_inner=[];labels=[];shared=None
  for spec in ends:
   nid=spec['plan_node'];portid=spec['axis_port'];p=ps.get(nid);a=ar.get(portid)
   if not p or not a or p['label']['original_text']!=a['source_label']['original_text'] or p['system']!=system or a['axis']['edge_id']!=spec['axis_edge']:raise ValueError('label or evidence mismatch')
   node=pn.get(nid);edge=ae.get(spec['axis_edge']);v=an.get(spec['axis_node'])
   if not node or node.get('system')!=system or node.get('boundary_type')!='unresolved_source_terminal' or not edge or edge.get('system')!=system or not v or v.get('node_type')!='virtual_equipment' or spec['axis_node'] not in (edge.get('start_node_id'),edge.get('end_node_id')):raise ValueError('graph endpoint mismatch')
   port=next((z for z in v.get('ports',[]) if z.get('port_id')==portid and z.get('system')==system),None)
   if not port or portid not in (edge.get('start_port_id'),edge.get('end_port_id')):raise ValueError('axis port mismatch')
   if shared is None:shared=spec['axis_node']
   elif shared!=spec['axis_node']:raise ValueError('axis boundaries differ')
   pnids.append(nid);axis_edges.append(spec['axis_edge']);axis_inner.append(edge['end_node_id'] if edge['start_node_id']==shared else edge['start_node_id']);labels.append(p['label']['original_text'])
  if len(set(pnids))!=2 or len(set(axis_edges))!=2 or len(set(axis_inner))!=2:raise ValueError('duplicate endpoints')
  pp=shortest(plan,pnids[0],pnids[1],system,set(),100);ap=shortest(axis,axis_inner[0],axis_inner[1],system,set(axis_edges),100)
  def notes(paths,edges):
   return [[{'edge_id':eid,'connection_mode':edges[eid].get('connection_mode'),'path_length_complete':edges[eid].get('path_length_complete'),'source_handles':edges[eid].get('source_handles',[])} for eid in path] for path in paths]
  rows.append({'system':system,'labels':labels,'plan_boundary_nodes':pnids,'plan_shortest_paths':pp,'plan_edge_evidence':notes(pp,pe),'axis_boundary_node':shared,'axis_anchor_edges':axis_edges,'axis_inner_nodes':axis_inner,'axis_shortest_paths_excluding_anchor_edges':ap,'axis_edge_evidence':notes(ap,ae),'status':'graph_adjacency_diagnostic_not_physical_loop'})
 return {'status':'boundary_path_comparison_not_mapping','comparisons':rows,'plan_graph_mutated':False,'axis_graph_mutated':False,'mapping_ready':False,'hil_ready':False,'limitations':['One or more shortest graph paths do not establish unique physical route or prove connectivity.','Virtual equipment stops path traversal; axis anchor edges are excluded so the shared virtual node cannot join ports.','Pending contacts, source gaps and plan topology remain unverified; no cross-view identity, diameter inheritance or physical length is established.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('plan-graph','axis-graph','plan-screen','axis-evidence','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));policy=load(a.policy)
 for key,path in [('plan_screen_sha256',a.plan_screen),('axis_evidence_sha256',a.axis_evidence)]:
  if policy.get(key)!=sha(path):raise ValueError('evidence hash mismatch')
 result=compare(load(a.plan_graph),load(a.axis_graph),load(a.plan_screen),load(a.axis_evidence),policy,sha(a.plan_graph),sha(a.axis_graph),policy['plan_source_sha256'],policy['axis_source_sha256']);result.update(plan_graph_sha256=sha(a.plan_graph),axis_graph_sha256=sha(a.axis_graph),plan_source_sha256=policy['plan_source_sha256'],axis_source_sha256=policy['axis_source_sha256'],policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':result['status'],'systems':len(result['comparisons'])}))
if __name__=='__main__':main()
