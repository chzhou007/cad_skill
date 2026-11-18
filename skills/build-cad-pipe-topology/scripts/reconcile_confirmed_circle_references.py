"""Reconcile recorded three-rim candidates and a graph-bound terminal inventory.

Other sidecars and graph references remain an explicit blocking responsibility.
"""
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path


def reconcile(graph, inventory, *, graph_sha256, inventory_sha256):
    out=copy.deepcopy(graph);inv=copy.deepcopy(inventory)
    repair=out.get('confirmedCircleJunctions')
    if not isinstance(repair,dict) or not repair.get('retired_nodes'):
        raise ValueError('Missing confirmed circle repair')
    retired=repair['retired_nodes']; source=repair['source_sha256']
    if inv.get('source_sha256')!=source or inv.get('graph_sha256')!=repair['input_graph_sha256']:
        raise ValueError('Inventory is not bound to the original source and graph')
    nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']}
    if len(nodes)!=len(out['nodes']) or len(edges)!=len(out['edges']) or set(retired)&nodes.keys():
        raise ValueError('Invalid current node or edge identities')
    rewires=repair.get('rewired_edge_ends',[])
    if len(rewires)!=len(retired) or {r['old_node_id'] for r in rewires}!=set(retired):
        raise ValueError('Repair endpoint audit incomplete')
    by_circle={}
    for r in rewires:
        nid=r['old_node_id'];tid=retired[nid];edge=edges.get(r['edge_id']);side=r['side'];node=nodes.get(tid)
        if side not in ('start','end') or not edge or not node or r['new_node_id']!=tid or edge[side+'_node_id']!=tid or node.get('source_circle_handle')!=r['circle_handle'] or edge.get('system')!=node.get('system'):
            raise ValueError('Repair endpoint audit does not match current graph')
        by_circle.setdefault(r['circle_handle'],set()).add(nid)
    candidates=out.get('sourceThreeRimCandidates')
    if not isinstance(candidates,list) or out.get('sourceThreeRimCandidateHistory') is not None:
        raise ValueError('Missing or already archived three-rim candidates')
    matched=[];remaining=[];seen=set()
    for candidate in candidates:
        circle=candidate.get('circle_handle')
        if circle not in by_circle:
            remaining.append(candidate);continue
        contacts=candidate.get('contacts',[])
        if circle in seen or len(contacts)!=3 or {c['node_id'] for c in contacts}!=by_circle[circle]:
            raise ValueError('Circle candidate membership changed')
        seen.add(circle);matched.append(candidate)
    if seen!=set(by_circle):raise ValueError('Missing confirmed circle candidate')
    out['sourceThreeRimCandidateHistory']={'status':'retired_after_user_confirmation',
        'source_graph_sha256':repair['input_graph_sha256'],'records':matched}
    if remaining:out['sourceThreeRimCandidates']=remaining
    else:
        out.pop('sourceThreeRimCandidates')
        families=[f for f in out.get('preHilComparison',{}).get('families',[]) if f.get('id')=='three-rim-source-semantics']
        if len(families)==1 and set(families[0].get('source_handles',[]))==set(by_circle):
            out['technicalPending']=[r for r in out.get('technicalPending',[]) if r.get('id')!='THREE-RIM-SOURCE-SEMANTICS']
            families[0].update(status='resolved',disposition='Explicitly confirmed same-service circle contacts reconstructed; overall reference reconciliation remains pending.')
    records=inv.get('records')
    if not isinstance(records,list):raise ValueError('Missing terminal inventory records')
    removed=[r for r in records if r.get('node_id') in retired]
    keep=[r for r in records if r.get('node_id') not in retired]
    if len(removed)!=len(retired) or {r['node_id'] for r in removed}!=set(retired) or any(r.get('family')!='circle_rim' for r in removed):
        raise ValueError('Terminal inventory does not match retired circle endpoints')
    old_edges={r['old_node_id']:r['edge_id'] for r in rewires}
    if any(r.get('edge_id')!=old_edges[r['node_id']] for r in removed):
        raise ValueError('Retired terminal inventory edge differs from repair audit')
    if any(r.get('node_id') not in nodes or (r.get('edge_id') and (r['edge_id'] not in edges or r['node_id'] not in (edges[r['edge_id']]['start_node_id'],edges[r['edge_id']]['end_node_id']))) for r in keep):
        raise ValueError('Retained terminal record has stale graph reference')
    inv.update(records=keep,remaining_unclassified_nodes=len(keep),family_counts=dict(Counter(r['family'] for r in keep)),
        scope='Remaining terminal roles; remote identity and other source ambiguities remain unconfirmed.')
    inv['retired_record_archive']={'source_inventory_sha256':inventory_sha256,'records':removed,'retired_to_junction':retired}
    out['metadata'].update(hil_ready=False,graph_complete=False,stage_status='circle_candidates_and_terminal_inventory_reconciled_other_references_pending')
    summary={'input_repaired_graph_sha256':graph_sha256,'input_inventory_sha256':inventory_sha256,'source_sha256':source,
             'archived_circle_candidates':len(matched),'unresolved_circle_candidates':len(remaining),
             'archived_terminal_records':len(removed),'remaining_terminal_records':len(keep),
             'family_counts':inv['family_counts'],'hil_ready':False,
             'scope':'Candidate and terminal inventory only; other sidecars and graph references remain pending.'}
    return out,inv,summary


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('graph','inventory','output-dir'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    if a.output_dir.exists():parser.error('output directory already exists')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
    graph,inv,summary=reconcile(read(a.graph),read(a.inventory),graph_sha256=digest(a.graph),inventory_sha256=digest(a.inventory))
    encoded=(json.dumps(graph,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    graph_hash=hashlib.sha256(encoded).hexdigest();inv['graph_sha256']=graph_hash;summary['output_graph_sha256']=graph_hash
    a.output_dir.mkdir(parents=True)
    (a.output_dir/'graph_with_edges.json').write_bytes(encoded)
    for name,obj in [('remaining-terminal-source-inventory.json',inv),('reconciliation-audit.json',summary)]:
        (a.output_dir/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))

if __name__=='__main__':main()
