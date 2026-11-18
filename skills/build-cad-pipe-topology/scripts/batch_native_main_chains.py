"""Correspond unique native main chains between already proved junctions.

Existing direct writers remain intact. Discovery uses unused paths; acceptance
rechecks the complete native LINE corridor, so removing used edges cannot make
a loop or parallel route appear unique. Intermediate branch identities and
one-to-many metric allocation remain separate evidence requirements.
"""
import collections
from crossview_equipment_branch_inventory import index_graph,native_tee
from match_source_checked_crossview_paths import native_main_corridor,bridge_main_path,selected_snapshot
from batch_native_path_coverage import collect as coverage
from native_line_path_evidence import _on

MODE='source_checked_known_junction_main_chain_batch_v1'
TYPES={'tee','physical_junction'}


def straight_corridor(graph,start,end,system,floor):
    """Select native path geometry on the straight interval, retaining parallels.

    Native LINE coverage and every T are checked separately before acceptance.
    This is an explicit drawing corridor, not a choice of shortest ring route.
    """
    nodes,edges,_=index_graph(graph);a=[nodes[start]['x'],nodes[start]['y']];b=[nodes[end]['x'],nodes[end]['y']]
    if a==b:raise ValueError('straight corridor anchors collapse')
    selected=[]
    for edge in edges.values():
        ends=[edge['start_node_id'],edge['end_node_id']];paths=edge.get('attribute_paths',[])
        if edge['system']!=system or not paths or any(not p for p in paths):continue
        if any(n not in nodes or nodes[n].get('floor')!=floor or nodes[n]['node_type'] not in TYPES for n in ends):continue
        if all(_on(point,a,b,.05) for path in paths for point in path):selected.append(edge)
    return dict(nodes=graph['nodes'],edges=selected),dict(scope='source_witnessed_straight_LINE_union_corridor',
        anchor_points=[a,b],source_path_edges=[e['edge_id'] for e in selected],other_ring_routes_not_asserted_unique=True)


def discover_chains(graph,floor,mapped,used):
    nodes,edges,adj=index_graph(graph);net=collections.defaultdict(list)
    for eid,e in edges.items():
        a,b=e['start_node_id'],e['end_node_id'];system=e['system']
        if eid in used or system not in ('supply','return') or a==b or any(n not in nodes for n in (a,b)):continue
        if any(nodes[n].get('floor')!=floor or nodes[n]['node_type'] not in TYPES for n in (a,b)):continue
        if any(len(adj[n])!=3 or nodes[n].get('review_required') is True or {x['system'] for x in adj[n]}!={system} for n in (a,b)):continue
        net[a].append((b,eid,system));net[b].append((a,eid,system))
    paths={};seen=set()
    for start in sorted(mapped):
        for other,eid,system in net[start]:
            ids=[eid];visited=[start,other];current=other
            while current not in mapped and len(net[current])==2:
                options=[x for x in net[current] if x[0]!=visited[-2]]
                if len(options)!=1 or options[0][0] in visited or options[0][2]!=system:break
                nxt,edge,_=options[0];visited.append(nxt);ids.append(edge);current=nxt
            if current not in mapped or current==start:continue
            signature=tuple(sorted(ids))
            if signature in seen:continue
            seen.add(signature);key=(system,frozenset((mapped[start],mapped[current])))
            paths.setdefault(key,[]).append(dict(start=start,end=current,nodes=visited,edges=ids))
    return paths


def discover(graphs,parent,floor):
    maps=parent['junction_mapping']
    if len(set(maps.values()))!=len(maps):raise ValueError('current known junctions collapse')
    if type(floor) is not int or set(graphs)!={'plan','iso'}:raise ValueError('explicit two-view integer floor required')
    used={v:[eid for row in parent['records'] for eid in row[v+'_edges']] for v in graphs}
    if any(len(ids)!=len(set(ids)) for ids in used.values()):raise ValueError('parent path writer repeated')
    paths={v:discover_chains(g,floor,maps if v=='plan' else {x:x for x in maps.values()},set(used[v])) for v,g in graphs.items()}
    candidates=[];pending=[]
    for (system,endpoints),plan in sorted(paths['plan'].items(),key=lambda x:(x[0][0],sorted(x[0][1]))):
        axis=paths['iso'].get((system,endpoints),[])
        if len(plan)!=len(axis) or len(plan)!=1:
            pending.append(dict(system=system,plan=plan,iso=axis,reason='missing_or_parallel_anchor_chain'));continue
        p,a=plan[0],axis[0]
        if maps[p['start']]!=a['start']:a=dict(a,start=a['end'],end=a['start'],nodes=list(reversed(a['nodes'])),edges=list(reversed(a['edges'])))
        if maps[p['end']]!=a['end']:raise ValueError('chain orientation differs from independent parent anchors')
        if len(p['edges'])==len(a['edges'])==1:
            pending.append(dict(system=system,plan=p,iso=a,reason='direct_main_belongs_to_existing_direct_rule'));continue
        row=dict(kind='native_main_chain_between_independent_junctions',floor=floor,system=system,
            plan_edges=p['edges'],iso_edges=a['edges'],plan_start=p['start'],plan_end=p['end'],iso_start=a['start'],iso_end=a['end'],
            plan_nodes=p['nodes'],iso_nodes=a['nodes'],internal_node_identities_assigned=False,
            per_axis_edge_metric_allocation_known=False,shortest_or_nearest_path_used=False,human_accepted=False)
        for view in graphs:row[view+'_snapshot']=selected_snapshot(graphs[view],row[view+'_edges'])
        candidates.append(row)
    return candidates,pending


def source_check(docs,graphs,row,hashes):
    proofs={}
    for view,graph in graphs.items():
        nodes,edges,adj=index_graph(graph);start,end=row[view+'_start'],row[view+'_end'];system=row['system']
        try:
            route=bridge_main_path(graph,start,end,system,row['floor'])
            evidence=dict(scope='unique_bridge_route_in_complete_same_floor_same_service_graph',shortest_path_used=False)
        except ValueError:
            try:corridor,evidence=native_main_corridor(docs[view],graph,dict(start=start,end=end),system,row['floor'])
            except ValueError:corridor,evidence=straight_corridor(graph,start,end,system,row['floor'])
            route=bridge_main_path(corridor,start,end,system,row['floor'])
        if route['edges']!=row[view+'_edges'] or route['nodes']!=row[view+'_nodes']:raise ValueError('complete native corridor route differs from residual discovery')
        junctions={nid:native_tee(docs[view],graph,nid,hashes[view]['source_sha256'],hashes[view]['graph_sha256']) for nid in route['nodes']}
        path=coverage(docs[view],graph,route['edges'],hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
        if any(s['status']!='single_source_line_covers' for e in path['edges'] for s in e['segments']):raise ValueError('chain path lacks unique native LINE coverage')
        proofs[view]=dict(corridor=evidence,route=route,junctions=junctions,path_coverage=path,
            offcorridor_branch_correspondence='not_asserted')
    if len(proofs['plan']['route']['nodes'])!=len(proofs['iso']['route']['nodes']):
        # Different detail may be meaningful, but this inherited mode requires
        # equal independently witnessed branch counts before pairing the route.
        raise ValueError('internal native branch counts differ; explicit segmentation evidence required')
    return proofs


def apply(docs,graphs,parent,floor,hashes):
    candidates,pending=discover(graphs,parent,floor);accepted=[];evidence={};seen={v:set() for v in graphs}
    for index,row in enumerate(candidates,1):
        try:proof=source_check(docs,graphs,row,hashes)
        except ValueError as exc:
            pending.append(dict(candidate=row,reason='native_chain_evidence_incomplete',detail=str(exc)));continue
        for view in graphs:
            if seen[view].intersection(row[view+'_edges']):raise ValueError('new chain writers overlap')
            seen[view].update(row[view+'_edges'])
        row=dict(row,mapping_id=f'CHAIN-F{floor}-{index:04d}',status='native_path_correspondence_attribute_allocation_pending')
        evidence[row['mapping_id']]=proof;accepted.append(row)
    return dict(mode=MODE,floor=floor,records=accepted,native_evidence=evidence,pending=pending,
        graph_mutated=False,previous_writers_replaced=0,physical_values_assigned=0,human_accepted=False,hil_ready=False)
