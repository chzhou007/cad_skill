"""Rebind a policy only when its exact referenced topology scope is unchanged.

This never migrates changed/split edge IDs or copies acceptance. Downstream
source-reading stages must still rerun to produce current evidence.
"""
import argparse,copy,hashlib,json
from pathlib import Path

def rebase(before,after,policy,before_hash,after_hash):
    source=policy.get('source_sha256')
    if not source or any(g.get('metadata',{}).get('source_sha256')!=source for g in (before,after)) or policy.get('graph_sha256')!=before_hash:raise ValueError('policy/source/graph identity mismatch')
    edges=set(policy.get('edges',[]));nodes=set(policy.get('junctions',[]));junction_nodes=set(nodes)
    for key in ('selections','seeds','dimensions'):
        edges.update(r['edge_id'] for r in policy.get(key,[]))
    for row in policy.get('junction_witnesses',[]):
        nodes.add(row['node_id']);junction_nodes.add(row['node_id']);edges.update(row['edge_witnesses'])
    if not edges:raise ValueError('no explicit supported attribute scope')
    old_e={e['edge_id']:e for e in before['edges']};new_e={e['edge_id']:e for e in after['edges']}
    old_n={n['node_id']:n for n in before['nodes']};new_n={n['node_id']:n for n in after['nodes']}
    for graph,es,ns in ((before,old_e,old_n),(after,new_e,new_n)):
        if len(es)!=len(graph['edges']) or len(ns)!=len(graph['nodes']):raise ValueError('duplicate graph IDs')
    keys=('system','start_node_id','end_node_id','start_port_id','end_port_id','source_handles','attribute_paths','path','path_points','path_length','start_floor','end_floor','equipment_names','equipment_counts')
    for eid in edges:
        if eid not in old_e or eid not in new_e or any(old_e[eid].get(k)!=new_e[eid].get(k) for k in keys):raise ValueError('changed policy edge scope: '+eid)
        nodes.update((old_e[eid]['start_node_id'],old_e[eid]['end_node_id']))
    nkeys=('node_type','subtype','system','x','y','floor','source_handle','source_handles','ports')
    for nid in nodes:
        if nid not in old_n or nid not in new_n or any(old_n[nid].get(k)!=new_n[nid].get(k) for k in nkeys):raise ValueError('changed policy node scope: '+nid)
    for nid in junction_nodes:
        incident=lambda es:sorted((e['edge_id'],e['system'],e['start_node_id'],e['end_node_id'],e.get('source_handles',[])) for e in es.values() if nid in (e['start_node_id'],e['end_node_id']))
        if incident(old_e)!=incident(new_e):raise ValueError('changed inheritance junction incidence: '+nid)
    output=copy.deepcopy(policy);output['graph_sha256']=after_hash
    audit={'status':'unchanged_scoped_topology_rebound_requires_source_reexecution','source_sha256':source,'old_graph_sha256':before_hash,'new_graph_sha256':after_hash,'edge_ids':sorted(edges),'node_ids':sorted(nodes),'human_acceptance_inherited':False}
    return output,audit

def main():
 p=argparse.ArgumentParser()
 for k in ('before','after','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();read=lambda x:json.loads(x.read_text(encoding='utf8'));sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
 policy,audit=rebase(read(a.before),read(a.after),read(a.policy),sha(a.before),sha(a.after))
 with a.output.open('x',encoding='utf8') as f:json.dump(policy,f,ensure_ascii=False,indent=2);f.write('\n')
 a.output.with_suffix('.audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
