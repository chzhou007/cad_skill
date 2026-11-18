"""Reconcile existing pending-main evidence after source-backed edge splits."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
from source_pending_main_continuity import attach
from source_readability import read_source

def validate_references(graph):
 nodes=graph['nodes'];edges=graph['edges'];checked=[]
 if len({n['node_id'] for n in nodes})!=len(nodes) or len({e['edge_id'] for e in edges})!=len(edges):raise ValueError('duplicate graph IDs')
 for n in nodes:
  ev=n.get('source_main_continuation')
  if ev is None:continue
  incident=[e for e in edges if n['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))];main=ev.get('main_source_handle');mains=[e for e in incident if main in e.get('source_handles',[])];branch=[e for e in incident if e['edge_id']==ev.get('branch_edge_id')]
  if n.get('resolution_state')!='source_main_continuation_branch_pending' or ev.get('branch_connectivity')!='pending' or ev.get('circle_semantics')!='pending' or len(incident)!=3 or len(mains)!=2 or sorted(e['edge_id'] for e in mains)!=sorted(ev.get('main_edge_ids',[])) or len(branch)!=1 or branch[0] in mains or any(e.get('system')!=n.get('system') for e in incident) or ev.get('branch_source_handle') not in branch[0].get('source_handles',[]):raise ValueError('stale pending main continuity references: '+n['node_id'])
  checked.append(n['node_id'])
 return checked

def reconcile(graph,doc,pending,policy,hashes):
 for k in ('source_sha256','graph_sha256','pending_sha256','devices_sha256'):
  if policy.get(k)!=hashes.get(k):raise ValueError('input hash mismatch: '+k)
 names=policy.get('node_ids',[]);nodes={n['node_id']:n for n in graph['nodes']}
 if not names or len(set(names))!=len(names) or any(n not in nodes for n in names):raise ValueError('invalid selected nodes')
 old={}
 for nid in names:
  n=nodes[nid];e=n.get('source_main_continuation')
  if n.get('resolution_state')!='source_main_continuation_branch_pending' or not isinstance(e,dict) or e.get('source_sha256')!=hashes['source_sha256'] or e.get('branch_connectivity')!='pending' or e.get('circle_semantics')!='pending':raise ValueError('missing prior source evidence')
  old[nid]=copy.deepcopy(e)
 working=copy.deepcopy(graph)
 for n in working['nodes']:
  if n['node_id'] in old:n.pop('source_main_continuation');n.pop('resolution_state')
 selected=[]
 for item in pending:
  hits=[nid for nid in names if item.get('system')==nodes[nid].get('system') and abs(item.get('x')-nodes[nid]['x'])<=.05 and abs(item.get('y')-nodes[nid]['y'])<=.05]
  if len(hits)>1:raise ValueError('ambiguous pending item')
  if hits:selected.append(item)
 if len(selected)!=len(names):raise ValueError('pending item scope mismatch')
 result,records=attach(working,doc,selected,hashes['source_sha256']);updated={x['node_id']:x for x in records}
 if set(updated)!=set(names):raise ValueError('recomputed scope mismatch')
 changes=[]
 for nid in names:
  n=next(x for x in result['nodes'] if x['node_id']==nid);previous=old[nid];current=n['source_main_continuation']
  for key in ('main_source_handle','branch_source_handle','circle_handles','source_point','branch_connectivity','circle_semantics'):
   if previous.get(key)!=current.get(key):raise ValueError('source evidence changed: '+key)
  n.setdefault('source_main_continuation_history',[]).append({'evidence':previous,'status':'historical_before_edge_split','input_graph_sha256':hashes['graph_sha256']})
  changes.append({'node_id':nid,'previous_main_edges':previous['main_edge_ids'],'current_main_edges':current['main_edge_ids'],'previous_branch_edge':previous['branch_edge_id'],'current_branch_edge':current['branch_edge_id']})
 result['mainContinuityReferenceReconciliation']={'source_sha256':hashes['source_sha256'],'input_graph_sha256':hashes['graph_sha256'],'changes':changes,'status':'source_rechecked_branch_still_pending','hil_ready':False}
 validate_references(result)
 return result,changes

def main():
 p=argparse.ArgumentParser()
 for x in ('source','graph','pending','devices','policy','output'):p.add_argument('--'+x,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source);g,changes=reconcile(json.loads(a.graph.read_text(encoding='utf8')),doc,json.loads(a.pending.read_text(encoding='utf8')),json.loads(a.policy.read_text(encoding='utf8')),{k:sha(getattr(a,{'source_sha256':'source','graph_sha256':'graph','pending_sha256':'pending','devices_sha256':'devices'}[k])) for k in ('source_sha256','graph_sha256','pending_sha256','devices_sha256')});a.output.mkdir(parents=True,exist_ok=False);target=a.output/'graph_with_main_continuity.json';target.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv');report={'source_sha256':proof['source_sha256'],'input_graph_sha256':sha(a.graph),'output_graph_sha256':sha(target),'pending_sha256':sha(a.pending),'devices_sha256':sha(a.devices),'policy_sha256':sha(a.policy),'changes':changes,'hil_ready':False};(a.output/'main-continuity-reconciliation-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'reconciled':len(changes),'hil_ready':False}))
if __name__=='__main__':main()
