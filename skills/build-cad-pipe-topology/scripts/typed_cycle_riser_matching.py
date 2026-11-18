"""Use native riser roles inside an independently anchored simple cycle.

Only unique riser attachments become new identities. Unequal terminal chains
remain bounded path differences; positional or ordinal identity is not inferred.
"""
from collections import defaultdict
from crossview_equipment_branch_inventory import index_graph
TYPES={'tee','physical_junction'}

def cycle_index(graph,cycle,floor,system):
    nodes,edges,full=index_graph(graph);cn=set(cycle['cycle_nodes']);ce=set(cycle['cycle_edges']);adj=defaultdict(list)
    if len(cn)!=len(cycle['cycle_nodes'])or len(ce)!=len(cycle['cycle_edges'])or len(cn)!=len(ce)or len(cn)<3:raise ValueError('simple cycle inventory required')
    for eid in ce:
        e=edges[eid];a,b=e['start_node_id'],e['end_node_id']
        if a==b or not {a,b}<=cn or e['system']!=system:raise ValueError('cycle edge identity differs')
        adj[a].append((b,eid));adj[b].append((a,eid))
    for n in cn:
        row=nodes[n]
        if row['node_type']not in TYPES or row.get('floor')!=floor or row.get('review_required')is True or len(full[n])!=3 or len(adj[n])!=2 or {e['system']for e in full[n]}!={system}:raise ValueError('cycle node is not a same-system qualified T')
    seen={next(iter(cn))};q=list(seen)
    for n in q:
        for b,_ in adj[n]:
            if b not in seen:seen.add(b);q.append(b)
    if seen!=cn:raise ValueError('cycle is disconnected')
    return nodes,edges,full,adj

def attachments(graph,cycle,floor,system,view,routing):
    nodes,edges,full,adj=cycle_index(graph,cycle,floor,system);ce=set(cycle['cycle_edges']);out=[]
    for n in sorted(cycle['cycle_nodes']):
        branch=[e for e in full[n]if e['edge_id']not in ce]
        if len(branch)!=1:raise ValueError('cycle branch is not unique')
        edge=branch[0];peer=edge['end_node_id']if edge['start_node_id']==n else edge['start_node_id'];row=nodes[peer]
        if view=='plan':
            if row.get('node_type')!='virtual_equipment'or row.get('subtype')!='out_of_plane_riser'or row.get('floor')!=floor or row.get('system')!=system or len(full[peer])!=1:continue
            out.append(dict(main_node=n,interface_node=peer,branch_edge=edge['edge_id'],role='native_plan_out_of_plane_riser'))
        else:
            if row.get('node_type')not in TYPES or row.get('floor')!=floor or row.get('review_required')is True or len(full[peer])!=3:continue
            vertical=[e for e in full[peer]if e['edge_id']!=edge['edge_id']];witnesses=[]
            for e in vertical:
                other=e['end_node_id']if e['start_node_id']==peer else e['start_node_id'];dest=nodes[other];route=routing.get(e['edge_id'],{})
                if e['system']!=system or dest.get('node_type')not in TYPES or dest.get('review_required')is True or not isinstance(dest.get('floor'),int)or dest['floor']==floor or route.get('classification')!='mixed_horizontal_vertical'or route.get('vertical_segments',0)<1:break
                witnesses.append(dict(edge_id=e['edge_id'],other_node=other,other_floor=dest['floor'],classification=route['classification'],vertical_segments=route['vertical_segments']))
            if len(witnesses)!=2 or not min(w['other_floor']for w in witnesses)<floor<max(w['other_floor']for w in witnesses):continue
            branch_route=routing.get(edge['edge_id'],{})
            if branch_route.get('classification')!='horizontal_only':continue
            out.append(dict(main_node=n,interface_node=peer,branch_edge=edge['edge_id'],role='native_axis_two_sided_interfloor_riser',vertical_witnesses=sorted(witnesses,key=lambda w:w['other_floor'])))
    return out

def arcs(graph,cycle,mapping,floor,system):
    _,_,_,adj=cycle_index(graph,cycle,floor,system);known=set(cycle['cycle_nodes'])&mapping.keys();result={}
    for start in sorted(known):
        for peer,eid in sorted(adj[start]):
            ordered=[start,peer];ids=[eid];previous=start;current=peer
            while current not in known:
                options=[(b,e)for b,e in adj[current]if b!=previous]
                if len(options)!=1:raise ValueError('cycle arc is not unique')
                nxt,edge=options[0]
                if nxt in ordered:raise ValueError('arc failed to reach next known anchor')
                ordered.append(nxt);ids.append(edge);previous,current=current,nxt
            a,b=mapping[start],mapping[current]
            if a>b:ordered.reverse();ids.reverse();a,b=b,a
            key=(a,b)
            row=dict(endpoint_identities=[a,b],nodes=ordered,edges=ids,internal_node_count=len(ordered)-2)
            if key not in result:result[key]=[]
            if not any(r['edges']==ids for r in result[key]):result[key].append(row)
    return result

def discover(graphs,mapping,floor,groups,routing):
    if set(graphs)!={'plan','iso'}or type(floor)is not int or len(mapping)!=len(set(mapping.values())):raise ValueError('independent two-view anchors required')
    pairs={};ports=[];routes=[];pending=[];evidence=[]
    for group in groups:
        system=group['system'];plan,axis=group['plan'],group['iso']
        known={p:mapping[p]for p in plan['cycle_nodes']if p in mapping}
        if len(known)<2 or not set(known.values())<=set(axis['cycle_nodes']):raise ValueError('cycle lacks its independently qualified gate anchors')
        pr=attachments(graphs['plan'],plan,floor,system,'plan',routing);ar=attachments(graphs['iso'],axis,floor,system,'iso',routing)
        if len(pr)!=1 or len(ar)!=1:
            pending.append(dict(system=system,reason='riser_role_missing_or_ambiguous',plan_candidates=pr,axis_candidates=ar));continue
        p,a=pr[0],ar[0];pn,an=p['main_node'],a['main_node']
        if pn in mapping or an in mapping.values()or pn in pairs or an in pairs.values():raise ValueError('riser attachment competes with a known identity')
        pairs[pn]=an;ports.append(dict(plan_node=p['interface_node'],axis_node=a['interface_node'],floor=floor,system=system,domain='scoped_riser_interface_to_axis_junction',plan_branch=p['branch_edge'],axis_branch=a['branch_edge']))
        evidence.append(dict(floor=floor,system=system,known_gate_mapping=known,plan=p,iso=a))
        pm=dict(known,**{pn:an});am={n:n for n in pm.values()};pa=arcs(graphs['plan'],plan,pm,floor,system);aa=arcs(graphs['iso'],axis,am,floor,system)
        for key,candidates in pa.items():
            options=aa.get(key,[])
            if len(candidates)!=1 or len(options)!=1:
                pending.append(dict(system=system,reason='cycle_arc_alternatives_not_unique',endpoint_identities=list(key)));continue
            pp,ap=candidates[0],options[0]
            if max(len(pp['edges']),len(ap['edges']))<=1:continue
            routes.append(dict(floor=floor,system=system,kind='bounded_cycle_route_not_individual_edge_mapping',plan=pp,iso=ap,
                interior_counts_equal=pp['internal_node_count']==ap['internal_node_count'],individual_node_identities_assigned=False,individual_edge_attributes_assigned=False))
    return dict(new_junction_mapping=dict(sorted(pairs.items())),riser_port_correspondences=ports,riser_role_evidence=evidence,bounded_routes=routes,pending=pending,
        coordinates_used_for_matching=False,DN_used_for_matching=False,ordinal_identities_assigned=False,graphs_mutated=False,human_accepted=False)
