"""Apply known source-backed correspondence rules across every axis edge.

No first-error abort for semantic differences. Native dependency failures stop
the batch, while missing paths and ambiguous candidates become explicit rows.
"""
import collections
import copy
from pathlib import Path

from confirm_crossview_paths import load, sha, encode
from crossview_equipment_branch_inventory import index_graph, service_route
from match_anchored_floor_main_network import match_structure
from match_source_checked_crossview_paths import selected_snapshot

MODE='batch_known_crossview_rule_application_v1'


def rebase_axis_inventory(inventory,old_graph,new_graph,identity_proof):
    """Keep native evidence historical and prove every reused trace is unchanged."""
    aliases=identity_proof['aliases'];inverse={v:k for k,v in aliases.items()}
    old={e['edge_id']:e for e in old_graph['edges']};new={e['edge_id']:e for e in new_graph['edges']}
    if set(old)!=set(new):raise ValueError('identity change cannot add or retire pipes')
    for eid,e in old.items():
        for key in ('system','attribute_paths','path_points','path_length'):
            if e.get(key)!=new[eid].get(key):raise ValueError('native pipe geometry changed during identity rebase')
    rows={r['equipment_id']:r for r in inventory['records']};result=copy.deepcopy(inventory)
    for row in result['records']:
        did=row['equipment_id'];prior=rows.get(inverse.get(did,did))
        if not prior:raise ValueError('native identity lost an equipment record')
        # Current caption remains the same literal source text. Only the old
        # body/service evidence belongs to the permuted body identity.
        row['views']['iso']['services']=copy.deepcopy(prior['views']['iso']['services'])
        for system,proof in row['views']['iso']['services'].items():
            trace=service_route(new_graph,did,system)
            if trace!=proof['trace']:raise ValueError('identity migration altered a source-witnessed pipe route')
            proof['identity_transition']=dict(previous_equipment_id=prior['equipment_id'],current_equipment_id=did,
                native_caption_body_proof=identity_proof,source_geometry_and_services_preserved=True,
                old_proof_graph_hash_is_historical=True,physical_values_assigned=0)
        row['ready_for_mapping_comparison']=all(row['views'][v].get('services',{}).get(s,{}).get('ready_for_mapping_comparison') is True
            for v in ('plan','iso') for s in ('supply','return'))
    result['counts']=dict(equipment=len(result['records']),ready_for_mapping_comparison=sum(r['ready_for_mapping_comparison'] for r in result['records']))
    return result


def discover_floor(graphs,inventory,floor):
    """Reuse strict full-floor matching, else grow only unique two-neighbour Ts."""
    indexes={v:index_graph(g) for v,g in graphs.items()};maps={};branches=[];conflicts=[]
    for row in inventory['records']:
        did=row['equipment_id']
        for system in ('supply','return'):
            views={v:row['views'][v].get('services',{}).get(system,{}) for v in graphs}
            if not all(p.get('ready_for_mapping_comparison') is True for p in views.values()):
                conflicts.append(dict(equipment_id=did,system=system,reason='local_service_not_proven',
                    traces={v:p.get('trace') for v,p in views.items()}));continue
            traces={v:service_route(graphs[v],did,system) for v in graphs}
            if any(traces[v]!=views[v]['trace'] for v in graphs):raise ValueError('native inventory route changed')
            if any(t['status']!='unique_graph_service_to_T' or len(t['edges'])!=1 for t in traces.values()):
                conflicts.append(dict(equipment_id=did,system=system,reason='path_requires_multi_edge_correspondence',traces=traces));continue
            p,a=traces['plan']['tee'],traces['iso']['tee']
            if (p in maps and maps[p]!=a) or (a in maps.values() and maps.get(p)!=a):
                conflicts.append(dict(equipment_id=did,system=system,reason='competing_junction_identity',traces=traces));continue
            maps[p]=a
            branches.append(dict(kind='equipment_branch',equipment_id=did,floor=floor,system=system,
                plan_edges=traces['plan']['edges'],iso_edges=traces['iso']['edges'],
                plan_start=p,plan_end=did,iso_start=a,iso_end=did))
    equipment=[r['equipment_id'] for r in inventory['records'] if r['ready_for_mapping_comparison']]
    full=None
    try:
        full=match_structure(graphs,inventory,floor,equipment);maps=full['node_mapping']
    except ValueError as exc:
        full_failure=str(exc)
    steps=[]
    if full is None:
        for iteration in range(sum(len(g['nodes']) for g in graphs.values())):
            reverse={v:k for k,v in maps.items()};groups={v:collections.defaultdict(list) for v in graphs}
            for view,(nodes,edges,adj) in indexes.items():
                for nid,node in nodes.items():
                    if (node.get('floor')!=floor or node['node_type'] not in ('tee','physical_junction')
                        or node.get('review_required') is True or len(adj[nid])!=3
                        or (nid in maps if view=='plan' else nid in reverse)):continue
                    if len({e['system'] for e in adj[nid]})!=1:continue
                    neighbours=[]
                    for e in adj[nid]:
                        other=e['end_node_id'] if e['start_node_id']==nid else e['start_node_id']
                        label=maps.get(other) if view=='plan' else other if other in reverse else None
                        if label:neighbours.append((label,e['system']))
                    if len(neighbours)>=2:groups[view][tuple(sorted(neighbours))].append(nid)
            new={ps[0]:groups['iso'][sig][0] for sig,ps in groups['plan'].items()
                if len(ps)==1 and len(groups['iso'].get(sig,[]))==1}
            if not new:break
            maps.update(new);steps.append(new)
    mains=[];used=set()
    for eid,e in indexes['plan'][1].items():
        a,b=e['start_node_id'],e['end_node_id']
        if a not in maps or b not in maps:continue
        options=[ee for ee in indexes['iso'][1].values() if ee['system']==e['system']
            and {ee['start_node_id'],ee['end_node_id']}=={maps[a],maps[b]}]
        if len(options)!=1 or options[0]['edge_id'] in used:
            conflicts.append(dict(plan_edge=eid,reason='missing_or_parallel_direct_main',axis_edges=[x['edge_id'] for x in options]));continue
        other=options[0];used.add(other['edge_id'])
        mains.append(dict(kind='same_floor_T_to_T_main',floor=floor,system=e['system'],plan_edges=[eid],iso_edges=[other['edge_id']],
            plan_start=a,plan_end=b,iso_start=maps[a],iso_end=maps[b]))
    records=branches+mains
    for i,row in enumerate(records,1):
        row['mapping_id']=f'BATCH-F{floor}-{i:04d}'
        row.update(status='structural_correspondence_native_path_check_required',human_accepted=False,physical_values_assigned=0)
        for view in graphs:row[view+'_snapshot']=selected_snapshot(graphs[view],row[view+'_edges'])
    return dict(floor=floor,records=records,unresolved=conflicts,junction_mapping=maps,
        full_floor_structure=full,full_floor_unresolved_reason=None if full else full_failure,
        unique_two_neighbour_propagation=steps,labels_used_as_sole_evidence=False)


def evaluate_all_axis_edges(axis,floors,published):
    assignments=collections.defaultdict(list)
    for result in floors.values():
        for row in result['records']:
            for eid in row['iso_edges']:assignments[eid].append(row)
    old={e['edge_id']:e for e in published['edges']};result=[]
    fields=('cross_view_attributes','anchored_floor_main_attributes','plan_segment_attributes',
        'external_feed_plan_attributes','network_named_lower_plan_attributes')
    for edge in axis['edges']:
        eid=edge['edge_id'];rows=assignments.get(eid,[])
        if len(rows)>1:state='conflict_multiple_mapping_writers'
        elif rows:state='rule_matched_native_attribute_application_pending'
        elif any(old.get(eid,{}).get(k) for k in fields):state='previous_partial_scope_requires_current_path_replay'
        elif edge.get('floor_start')!=edge.get('floor_end'):state='axis_vertical_or_mixed_scope_requires_segment_rule'
        else:state='unmatched_local_or_main_detail_path'
        result.append(dict(edge_id=eid,state=state,mapping_ids=[r['mapping_id'] for r in rows],
            source_plan_edges=[p for r in rows for p in r['plan_edges']],system=edge['system'],
            floor_start=edge.get('floor_start'),floor_end=edge.get('floor_end'),
            physical_length_mm=None,human_accepted=False))
    if len(result)!=len(axis['edges']) or len({r['edge_id'] for r in result})!=len(result):raise ValueError('axis batch coverage incomplete')
    return dict(total_edges=len(result),states=dict(collections.Counter(r['state'] for r in result)),records=result)
