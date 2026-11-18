"""Trace explicitly selected legacy expert nodes to final source-backed graph locations."""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source

def evaluate(doc,graph,issue,context,policy,source_hash,graph_hash,issue_hash,context_hash):
 if any(policy.get(k)!=v for k,v in [('source_sha256',source_hash),('graph_sha256',graph_hash),('issue_sha256',issue_hash),('context_sha256',context_hash)]) or graph.get('metadata',{}).get('source_sha256')!=source_hash or issue['sourceHashes']['main_dxf']!=source_hash:raise ValueError('stale source, graph or expert evidence')
 wanted=issue['issue']['nodes'];cases=policy['cases'];ids=[x['expert_node_id'] for x in cases]
 if not wanted or len(wanted)!=len(set(wanted)) or len(ids)!=len(set(ids)) or set(ids)!=set(wanted):raise ValueError('expert node selection not fully reconciled')
 old={n['node_id']:n for n in context['nodes']};nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']};anchors={a['boundary_id']:a for a in graph.get('boundary_anchors',[])}
 if any(len(x)!=len(y) for x,y in [(old,context['nodes']),(nodes,graph['nodes']),(edges,graph['edges']),(anchors,graph.get('boundary_anchors',[]))]):raise ValueError('duplicate IDs')
 rows=[]
 for spec in cases:
  n=old[spec['expert_node_id']];edge=edges[spec['final_edge_id']];h=spec['source_pipe_handle'];system=n['system'];source=doc.entitydb.get(h)
  if h not in n.get('source_handles',[]) or h not in edge.get('source_handles',[]) or edge.get('system')!=system or not source or source.dxftype()!='LINE' or source not in doc.modelspace():raise ValueError('expert pipe identity mismatch')
  expected_layer={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}.get(system)
  if source.dxf.layer!=expected_layer or min(math.hypot(p.x-n['x'],p.y-n['y']) for p in (source.dxf.start,source.dxf.end))>.05:raise ValueError('expert node not native pipe endpoint')
  if any(math.hypot(x['x']-n['x'],x['y']-n['y'])<=.05 and x.get('system')==system for x in graph['nodes']):raise ValueError('legacy location remains a graph node')
  if not any(math.hypot(p[0]-n['x'],p[1]-n['y'])<=.05 for p in edge.get('path',[])):raise ValueError('legacy pipe endpoint missing from final edge path')
  mode=spec['mode'];out={'expert_node_id':spec['expert_node_id'],'source_pipe_handle':h,'system':system,'final_edge_id':edge['edge_id'],'mode':mode}
  if mode=='expert_non_node_boundary':
   a=anchors[spec['boundary_id']]
   if a.get('kind')!='expert_non_node_source_boundary' or a.get('expert_issue')!=issue['issue']['label'] or a.get('source_pipe_handle')!=h or math.hypot(a['x']-n['x'],a['y']-n['y'])>.05 or a['boundary_id'] not in (edge.get('start_boundary_id'),edge.get('end_boundary_id')):raise ValueError('expert boundary mismatch')
   markers=a.get('source_marker_handles',[])
   if len(markers)!=2 or len(set(markers))!=2 or any(not doc.entitydb.get(k) or doc.entitydb[k].dxftype()!='LINE' or doc.entitydb[k].dxf.layer!='空调平面' for k in markers):raise ValueError('two-bar evidence missing')
   out.update(final_boundary_id=a['boundary_id'],marker_handles=markers,beyond_boundary='unknown')
  elif mode=='circle_rim_is_edge_interior':
   tee=nodes[spec['tee_id']];evidence=tee.get('source_reviewed_circle',{});circle=doc.entitydb.get(spec['circle_handle']);main=doc.entitydb.get(spec['main_handle'])
   if not circle or circle.dxftype()!='CIRCLE' or not main or main.dxftype()!='LINE' or main.dxf.layer!=expected_layer or circle.dxf.layer!=expected_layer or evidence.get('circle_handle')!=spec['circle_handle'] or evidence.get('source_rim')!=[n['x'],n['y']] or tee['node_id'] not in (edge.get('start_node_id'),edge.get('end_node_id')) or tee.get('system')!=system or spec['main_handle'] not in tee.get('source_handles',[]) or h not in tee.get('source_handles',[]):raise ValueError('source circle tee evidence mismatch')
   incident=[e for e in graph['edges'] if tee['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
   main_rays=[e for e in incident if spec['main_handle'] in e.get('source_handles',[])]
   if tee.get('node_type')!='tee' or len(incident)!=3 or any(e.get('system')!=system for e in incident) or len(main_rays)!=2 or edge['edge_id'] not in {e['edge_id'] for e in incident}:raise ValueError('tee incidence is not three independent same-system rays')
   c=circle.ocs().to_wcs(circle.dxf.center);distance=math.hypot(c.x-n['x'],c.y-n['y'])
   x0,y0=main.dxf.start.x,main.dxf.start.y;dx,dy=main.dxf.end.x-x0,main.dxf.end.y-y0;den=dx*dx+dy*dy
   if not den:raise ValueError('degenerate main')
   t=((c.x-x0)*dx+(c.y-y0)*dy)/den;main_distance=math.hypot(c.x-x0-t*dx,c.y-y0-t*dy)
   if abs(distance-circle.dxf.radius)>.05 or math.hypot(tee['x']-c.x,tee['y']-c.y)>.05 or not 0<t<1 or main_distance>.05:raise ValueError('circle/rim geometry mismatch')
   out.update(tee_id=tee['node_id'],circle_handle=spec['circle_handle'],main_handle=spec['main_handle'],xy_rim_radius=distance,source_z_consistent=evidence.get('z_consistent_within_tolerance'),tee_status='technical_source_comparison_not_human_acceptance',physical_length='unknown')
  else:raise ValueError('unsupported reconciliation mode')
  rows.append(out)
 return {'status':'expert_selected_nodes_source_reconciled_not_human_acceptance','source_sha256':source_hash,'graph_sha256':graph_hash,'issue_sha256':issue_hash,'context_sha256':context_hash,'issue_id':issue['issue']['label'],'records':rows,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Checks only explicitly selected expert nodes and pinned source entities.','Circle-rim comparison is XY evidence; differing source Z, physical connection and remote destination remain separately reviewable.']}

def main():
 p=argparse.ArgumentParser()
 for n in ('source','graph','issue','context','policy','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);load=lambda p:json.loads(p.read_text(encoding='utf8'));r=evaluate(doc,load(a.graph),load(a.issue),load(a.context),load(a.policy),proof['source_sha256'],sha(a.graph),sha(a.issue),sha(a.context));r.update(policy_sha256=sha(a.policy),source_preflight=proof['status'])
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'expert_nodes':len(r['records'])}))
if __name__=='__main__':main()
