"""Fail closed when a normalized source contact becomes an unmarked tee."""
import json,math
from pathlib import Path

def verified_confirmations(directory,graph,events,source_hash):
 from confirm_normalized_near_tees import verify_output
 directory=Path(directory)
 confirmed=verify_output(directory)
 load=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
 audit=load(directory/'near-tee-confirmation-audit.json')
 if (audit['source_sha256']!=source_hash or load(directory/'graph_with_confirmed_near_tees.json')!=graph
     or load(audit['normalization']).get('near_junction')!=json.loads(json.dumps(events,allow_nan=False))):raise ValueError('confirmed near-tee graph or normalization differs from replay')
 return confirmed

def check(graph,events,source_hash,tolerance=.05,confirmed_directory=None):
 if graph.get('metadata',{}).get('source_sha256')!=source_hash or not isinstance(events,list):raise ValueError('invalid source or normalization audit')
 nodes=graph.get('nodes');edges=graph.get('edges')
 if not isinstance(nodes,list) or not isinstance(edges,list):raise ValueError('invalid graph')
 confirmed=set()
 if graph.get('sourceNearTeeConfirmations') or any(n.get('resolution_state')=='source_contact_reconstructed_user_confirmed' for n in nodes):
  if confirmed_directory is None:raise ValueError('confirmed normalized tees require native replay artifacts')
  confirmed=verified_confirmations(confirmed_directory,graph,events,source_hash)
 checked=[]
 for event in events:
  if event.get('status')!='applied':continue
  branches=event.get('source_handles');mains=event.get('main_source_handles');point=event.get('semantic_endpoint')
  if not isinstance(branches,list) or len(branches)!=1 or not isinstance(mains,list) or len(mains)!=1 or not isinstance(point,(tuple,list)) or len(point)!=2 or not all(isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x) for x in point):raise ValueError('unsupported normalized contact')
  branch,main=branches[0],mains[0];matches=[]
  for node in nodes:
   if node.get('node_type') not in ('tee','physical_junction') or not all(isinstance(node.get(k),(float,int)) for k in ('x','y')) or math.dist(point,(node['x'],node['y']))>tolerance:continue
   inc=[e for e in edges if node.get('node_id') in (e.get('start_node_id'),e.get('end_node_id'))]
   if any(branch in e.get('source_handles',[]) for e in inc) and any(main in e.get('source_handles',[]) for e in inc):matches.append((node,inc))
  if len(matches)>1:raise ValueError('ambiguous normalized tee')
  if not matches:
   checked.append({'branch_handle':branch,'main_handle':main,'status':'no_matching_final_tee_not_verified'});continue
  node,inc=matches[0];ev=node.get('source_near_tee_evidence') or {};ids=sorted(e['edge_id'] for e in inc)
  is_confirmed=node['node_id'] in confirmed
  state='source_contact_reconstructed_user_confirmed' if is_confirmed else 'source_contact_reconstructed_pending_comparison'
  if (len(inc)!=3 or any(e.get('system')!=node.get('system') for e in inc) or node.get('resolution_state')!=state
      or node.get('review_required') is not (not is_confirmed) or ev.get('source_sha256')!=source_hash or ev.get('branch_handle')!=branch or ev.get('main_handle')!=main
      or ev.get('incident_edge_ids')!=ids or ev.get('human_accepted') is not False):raise ValueError('normalized tee missing source-bound pending state')
  checked.append({'node_id':node['node_id'],'branch_handle':branch,'main_handle':main,'incident_edge_ids':ids,'status':'explicit_confirmation_native_replayed' if is_confirmed else 'pending_state_present'})
 if confirmed-{r.get('node_id') for r in checked}:raise ValueError('confirmed tee missing current normalization incidence')
 return {'status':'normalized_near_tee_state_gate_passed_not_acceptance','records':checked,'graph_mutated':False,'hil_ready':False}
