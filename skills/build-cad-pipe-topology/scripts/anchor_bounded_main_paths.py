"""Native main paths bounded by independently mapped junctions, including bends.

Mapped junctions are semantic boundaries. Search the complete eligible unknown
region with all incident known boundaries present: cycles/parallel alternatives
remain visible. This is not a shortest path and removes no prior writer to make
a path unique. Off-path branches are independently witnessed, never paired here.
"""
from collections import defaultdict,deque,Counter
from itertools import combinations
import copy
from crossview_equipment_branch_inventory import index_graph,native_tee
from match_source_checked_crossview_paths import bridge_main_path,selected_snapshot
from batch_native_path_coverage import collect as coverage
from attach_anchored_floor_main_attributes import horizontal_domain

TYPES={'tee','physical_junction'}
ALIASES={'球阀':'ball_valve','金属软接':'flexible_joint'}

def corridors(graph,mapped,floor):
    nodes,edges,adj=index_graph(graph);result=defaultdict(list)
    for system in('supply','return'):
        eligible={n for n,row in nodes.items()if row.get('floor')==floor and row.get('node_type')in TYPES and row.get('review_required')is not True and len(adj[n])==3 and {e['system']for e in adj[n]}=={system}}
        remaining=eligible-set(mapped)
        while remaining:
            seed=min(remaining);component={seed};queue=deque([seed]);remaining.remove(seed)
            while queue:
                n=queue.popleft()
                for e in adj[n]:
                    peer=e['end_node_id']if e['start_node_id']==n else e['start_node_id']
                    if peer in remaining:remaining.remove(peer);component.add(peer);queue.append(peer)
            boundary={peer for n in component for e in adj[n]for peer in(e['start_node_id'],e['end_node_id'])if peer in eligible and peer in mapped}
            allowed=component|boundary
            # All edges among these real nodes remain, including prior writers.
            scope=dict(nodes=[nodes[n]for n in sorted(allowed)],edges=[e for e in graph['edges']if e['system']==system and {e['start_node_id'],e['end_node_id']}<=allowed])
            for start,end in combinations(sorted(boundary),2):
                try:route=bridge_main_path(scope,start,end,system,floor)
                except ValueError:continue
                if len(route['edges'])<2 or any(n in boundary for n in route['nodes'][1:-1]):continue
                key=(system,tuple(sorted((mapped[start],mapped[end]))))
                result[key].append(dict(start=start,end=end,**route,region_unknown_nodes=sorted(component),region_known_boundary_nodes=sorted(boundary),region_edges=sorted(e['edge_id']for e in scope['edges'])))
    return result

def component_profiles(components,eids):
    return[dict(sorted(Counter(ALIASES.get(r['equipment_type'],r['equipment_type'])for r in components if r['edge_id']==eid).items()))for eid in eids]

def discover(graphs,mapping,prior_records,floor,components):
    if len(mapping)!=len(set(mapping.values())):raise ValueError('independent junction identities collapse')
    if set(graphs)!={'plan','iso'}or type(floor)is not int:raise ValueError('explicit two-view floor required')
    paths={v:corridors(g,mapping if v=='plan'else{n:n for n in mapping.values()},floor)for v,g in graphs.items()}
    used={v:{eid for r in prior_records for eid in r[v+'_edges']}for v in graphs};accepted=[];pending=[]
    for key,pp in sorted(paths['plan'].items()):
        aa=paths['iso'].get(key,[])
        if len(pp)!=1 or len(aa)!=1:
            pending.append(dict(system=key[0],anchors=list(key[1]),reason='missing_or_parallel_anchor_region_route',plan=pp,iso=aa));continue
        p,a=pp[0],aa[0]
        if mapping[p['start']]!=a['start']:a=dict(a,start=a['end'],end=a['start'],edges=a['edges'][::-1],nodes=a['nodes'][::-1])
        reason=None
        if len(p['edges'])!=len(a['edges']):reason='internal_native_branch_count_differs'
        elif used['plan'].intersection(p['edges'])or used['iso'].intersection(a['edges']):reason='prior_path_writer_present'
        cp,ca=component_profiles(components['plan'],p['edges']),component_profiles(components['iso'],a['edges'])
        if reason is None and cp!=ca:reason='per_interval_component_profiles_differ'
        row=dict(floor=floor,system=key[0],plan=p,iso=a,component_profiles=dict(plan=cp,iso=ca),known_endpoints_independent=True)
        if reason:pending.append(dict(row,reason=reason));continue
        accepted.append(row)
    # Multiple anchor-pair observations may share an interval, but must give
    # exactly the same complete node and edge correspondence in both views.
    pairs={};inverse={};bad=set()
    for i,row in enumerate(accepted):
        for p,a in zip(row['plan']['nodes'],row['iso']['nodes']):
            pairs.setdefault(p,{}).setdefault(a,set()).add(i);inverse.setdefault(a,{}).setdefault(p,set()).add(i)
    for candidates in list(pairs.values())+list(inverse.values()):
        if len(candidates)>1:
            for indices in candidates.values():bad.update(indices)
    good=[]
    for i,row in enumerate(accepted):
        if i in bad:pending.append(dict(row,reason='competing_internal_junction_identity'))
        else:good.append(row)
    return good,pending

def prove(docs,graphs,row,mapping,hashes,angles,junction_readers=None):
    if mapping.get(row['plan']['start'])!=row['iso']['start']or mapping.get(row['plan']['end'])!=row['iso']['end']:raise ValueError('independent endpoint identity changed')
    proofs={}
    for view,graph in graphs.items():
        paths=corridors(graph,mapping if view=='plan'else{n:n for n in mapping.values()},row['floor'])
        key=(row['system'],tuple(sorted((row['iso']['start'],row['iso']['end']))));options=paths.get(key,[])
        if len(options)!=1:raise ValueError('complete bounded native region path is not unique')
        actual=options[0];expected=row[view]
        if actual['start']!=expected['start']:actual=dict(actual,start=actual['end'],end=actual['start'],edges=actual['edges'][::-1],nodes=actual['nodes'][::-1])
        if actual!=expected:raise ValueError('native region differs from discovery')
        reader=(junction_readers or{}).get(view,native_tee)
        junctions={nid:reader(docs[view],graph,nid,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])for nid in actual['nodes']}
        native=coverage(docs[view],graph,actual['edges'],hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
        if any(s['status']!='single_source_line_covers'for e in native['edges']for s in e['segments']):raise ValueError('bounded main lacks unique native LINE witnesses')
        proofs[view]=dict(route=actual,junctions=junctions,path_coverage=native,snapshot=selected_snapshot(graph,actual['edges']),scope='complete_unknown_T_region_with_all_known_boundary_junctions',other_regions_not_asserted_unique=True)
    if len(proofs['plan']['route']['nodes'])!=len(proofs['iso']['route']['nodes']):raise ValueError('native T order differs')
    for i,eid in enumerate(row['iso']['edges']):
        horizontal_domain(graphs['iso'],dict(iso_edges=[eid],iso_start=row['iso']['nodes'][i],iso_end=row['iso']['nodes'][i+1],system=row['system'],floor=row['floor']),angles)
    return proofs

def apply(docs,graphs,parent,floor,components,hashes,angles,junction_readers=None):
    mapping=copy.deepcopy(parent['junction_mapping']);candidates,pending=discover(graphs,mapping,parent['records'],floor,components);groups=[];pairs={};node_pairs={}
    for index,row in enumerate(candidates,1):
        try:evidence=prove(docs,graphs,row,mapping,hashes,angles,junction_readers)
        except ValueError as exc:pending.append(dict(row,reason='native_bounded_path_check_failed',detail=str(exc)));continue
        gid=f'BOUND-F{floor}-{index:04d}';groups.append(dict(row,mapping_id=gid,native=evidence))
        for p,a in zip(row['plan']['nodes'],row['iso']['nodes']):
            if p not in mapping:node_pairs[p]=a
        for i,(pe,ae)in enumerate(zip(row['plan']['edges'],row['iso']['edges'])):
            key=(pe,ae);item=pairs.setdefault(key,dict(floor=floor,system=row['system'],plan_edges=[pe],iso_edges=[ae],plan_start=row['plan']['nodes'][i],plan_end=row['plan']['nodes'][i+1],iso_start=row['iso']['nodes'][i],iso_end=row['iso']['nodes'][i+1],source_group_ids=[]))
            # Reversed observations are the same undirected pipe correspondence.
            if {item['plan_start'],item['plan_end']}!={row['plan']['nodes'][i],row['plan']['nodes'][i+1]}:raise ValueError('overlapping route endpoint identity differs')
            item['source_group_ids'].append(gid)
    # One writer per pipe in each view; a duplicated observation is not a new edge.
    records=[];seen={v:set()for v in graphs}
    for index,((pe,ae),item)in enumerate(sorted(pairs.items()),1):
        if pe in seen['plan']or ae in seen['iso']:raise ValueError('paired intervals have competing writers')
        seen['plan'].add(pe);seen['iso'].add(ae);records.append(dict(item,mapping_id=f'BOUND-EDGE-F{floor}-{index:04d}',kind='native_anchor_bounded_T_order_main',human_accepted=False))
    return dict(records=records,groups=groups,pending=pending,new_junction_mapping=node_pairs,independent_parent_mapping=mapping,counts=dict(source_checked_groups=len(groups),unique_new_axis_edges=len(records),new_junctions=len(node_pairs)),graph_mutated=False,off_path_branch_correspondence_assigned=False,DN_used_for_matching=False,length_ratios_used=False,human_accepted=False)
