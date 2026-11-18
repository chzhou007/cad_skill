"""Qualify a local DN conflict after complete native extraction.

This consumes checked local results; it does not verify CAD, choose a DN or
accept topology. Unrelated source-provider gaps do not block a proved scope.
"""
import math


def qualify(graph, floor_result, edge_ids):
    ids=list(edge_ids)
    if not ids or len(set(ids))!=len(ids):raise ValueError('empty or repeated review edge')
    edges={e['edge_id']:e for e in graph['edges']}
    rows={r['edge_id']:r for r in floor_result['records']}
    if len(edges)!=len(graph['edges']) or len(rows)!=len(floor_result['records']):raise ValueError('duplicate source edge')
    gaps=set(floor_result['source_T_exceptions']);barriers=set(floor_result['annotation_barriers'])
    used=set(ids);nodes=set();blockers=[];systems=set()
    for eid in ids:
        if eid not in edges or eid not in rows:raise ValueError('review edge missing from checked source')
        row=rows[eid];system=row['system'];systems.add(system)
        if row['status']!='conflict' or row['nominal_mm'] is not None or row.get('human_accepted') is not False:raise ValueError('review requires an unaccepted unresolved DN conflict')
        values={r['nominal_mm'] for r in row['lineage']}
        if len(values)<2 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<=0 for v in values):raise ValueError('conflict lacks distinct positive source values')
        for lineage in row['lineage']:
            if not lineage['evidence']:raise ValueError('conflict lacks native witnesses')
            for witness in lineage['evidence']:
                path=witness['edge_path']
                if not witness['evidence_id'].startswith('source:') or not path or path[-1]!=eid:raise ValueError('conflict lineage does not end at its reviewed edge')
                for pe in path:
                    if pe not in edges or edges[pe]['system']!=system:raise ValueError('lineage edge missing or cross-system')
                    used.add(pe)
                for transfer in witness.get('transfers',[]):
                    left,right=transfer['from_edge'],transfer['to_edge'];node=transfer['node_id']
                    if left not in path or right not in path:raise ValueError('transfer outside witnessed path')
                    if any(node not in (edges[e]['start_node_id'],edges[e]['end_node_id']) for e in (left,right)):raise ValueError('transfer lacks source edge incidence')
                    nodes.add(node)
    if len(systems)!=1:raise ValueError('one review group cannot combine supply and return')
    for eid in used:
        edge=edges[eid]
        for end in ('start','end'):
            node=edge[end+'_node_id']
            if node is None:
                boundary=edge.get(end+'_boundary_id');meaning=edge.get('endpoint_semantics',{}).get(end,{})
                if not boundary or meaning.get('kind')!='source_boundary' or meaning.get('id')!=boundary:
                    raise ValueError('missing endpoint without explicit non-node boundary evidence')
            else:nodes.add(node)
    if used&barriers:blockers.append(dict(kind='annotation_barriers_in_scope',edge_ids=sorted(used&barriers)))
    if nodes&gaps:blockers.append(dict(kind='unproved_source_T_in_scope',node_ids=sorted(nodes&gaps)))
    return dict(review_enabled=not blockers,technical_blockers=blockers,
        checked_edge_ids=sorted(used),checked_node_ids=sorted(nodes),
        unrelated_source_T_gaps=sorted(gaps-nodes),source_native_replay_performed=False,
        topology_or_DN_changed=False,human_accepted=False,whole_graph_hil_ready=False)
