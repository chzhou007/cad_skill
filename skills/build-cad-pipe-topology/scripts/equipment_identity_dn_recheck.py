"""Prepare a DN policy for re-evaluation after an equipment-only node addition."""
import copy,hashlib,json

def prepare(prior,updated,policy_bytes,source_hash,old_graph_hash,new_graph_hash):
 before={n['node_id']:n for n in prior['nodes']};after={n['node_id']:n for n in updated['nodes']}
 if len(before)!=len(prior['nodes']) or len(after)!=len(updated['nodes']) or prior['edges']!=updated['edges'] or any(after.get(k)!=v for k,v in before.items()):raise ValueError('cannot recheck DN after changes to existing topology')
 added=[n for k,n in after.items() if k not in before]
 if any(n.get('node_type')!='equipment' or n.get('connection_status')!='ports_unresolved' for n in added):raise ValueError('new nodes are not unresolved equipment')
 policy=json.loads(policy_bytes)
 if policy.get('graph_sha256')!=old_graph_hash or policy.get('source_sha256')!=source_hash:raise ValueError('original DN policy not bound to identity input')
 result=copy.deepcopy(policy);result['graph_sha256']=new_graph_hash;result['rechecked_from_policy_sha256']=hashlib.sha256(policy_bytes).hexdigest();result['prior_graph_sha256']=old_graph_hash
 return result
