"""Retain source-backed edge identities after explicitly audited normalization."""
import collections


def reconcile(graph,prior,witness_handles):
    old={e['edge_id']:e for e in prior.get('edges',[])};used={e['edge_id']for e in graph['edges']if e['edge_id']in old}
    nodes={n['node_id']:n for n in graph['nodes']};mapping={};rows=[];witness_handles=set(witness_handles)
    for e in graph['edges']:
        if e['edge_id']in old or not set(e['source_handles'])&witness_handles:continue
        endpoints={e['start_node_id'],e['end_node_id']};candidates=[]
        for p in old.values():
            if p['edge_id']in used or not p.get('source_handles')or not set(p['source_handles'])<=set(e['source_handles']):continue
            common=endpoints&{p['start_node_id'],p['end_node_id']}
            if not common:continue
            physical=sum(nodes[k]['node_type']=='equipment'for k in common if k in nodes)
            score=(physical,len(common),len(set(p['source_handles'])),p.get('path_length',0))
            candidates.append((score,p['edge_id']))
        if not candidates:continue
        candidates.sort(reverse=True);best=candidates[0]
        if len(candidates)>1 and candidates[1][0]==best[0]:
            rows.append({'new_edge_id':e['edge_id'],'status':'identity_ambiguous_retained_new_id','candidates':[p for _,p in candidates]});continue
        before=e['edge_id'];e['edge_id']=best[1];mapping[before]=best[1];used.add(best[1])
        rows.append({'temporary_edge_id':before,'retained_edge_id':best[1],'status':'retained_previous_source_edge_id','rule':'audited_normalization_source_handle_subset_and_shared_boundary_prefer_physical_equipment'})
    if len({e['edge_id']for e in graph['edges']})!=len(graph['edges']):raise ValueError('Normalized edge identity collision')
    final={e['edge_id']for e in graph['edges']};retired=[]
    for p in old.values():
        if p['edge_id']in final:continue
        candidates=[e['edge_id']for e in graph['edges']if set(p.get('source_handles',[]))and set(p['source_handles'])<=set(e['source_handles'])and set(e['source_handles'])&witness_handles]
        if len(candidates)==1:retired.append({'previous_edge_id':p['edge_id'],'replacement_edge_id':candidates[0],'reason':'source_route_normalized_or_display_stub_trimmed; inspect normalization witness'})
    return {'edge_id_mapping':mapping,'retired_edges':retired,'records':rows,'scope':'Only edges with explicit normalization source witnesses; no coordinate-nearest identity matching'}
