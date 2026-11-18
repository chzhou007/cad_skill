"""Match an unknown simple chain beside an independently mapped direct arm.

Retain the complete source cycle and its known bypass. An anchored unknown
region has a different semantic role from that bypass; graph order only pairs
intervals when both independently anchored chains are unique and equal sized.
No off-chain terminal, component correspondence or physical value is assigned.
"""
import collections,copy,hashlib
from crossview_equipment_branch_inventory import index_graph,native_tee
from legacy_named_provider_inventory import require,current_plan_reader
from batch_native_path_coverage import collect as coverage
from attach_anchored_floor_main_attributes import horizontal_domain
from anchor_bounded_main_paths import component_profiles
from source_stable_junction_reapplication import unchanged_star

MODE='native_complementary_independently_anchored_chain_batch_v1'
TYPES={'tee','physical_junction'}

def regions(graph,mapping,floor):
    nodes,edges,adj=index_graph(graph);result=collections.defaultdict(list)
    for system in('supply','return'):
        eligible={n for n,row in nodes.items()if row.get('floor')==floor and row.get('node_type')in TYPES
                  and row.get('review_required')is not True and len(adj[n])==3
                  and{e['system']for e in adj[n]}=={system}}
        remaining=eligible-set(mapping)
        while remaining:
            seed=min(remaining);unknown={seed};todo=[seed];remaining.remove(seed)
            while todo:
                nid=todo.pop()
                for edge in adj[nid]:
                    peer=edge['end_node_id']if edge['start_node_id']==nid else edge['start_node_id']
                    if peer in remaining:remaining.remove(peer);unknown.add(peer);todo.append(peer)
            boundary={p for n in unknown for e in adj[n]for p in(e['start_node_id'],e['end_node_id'])if p in eligible and p in mapping}
            if len(boundary)!=2:continue
            allowed=unknown|boundary
            full=[e for e in graph['edges']if e['system']==system and{e['start_node_id'],e['end_node_id']}<=allowed]
            chain=[e for e in full if{e['start_node_id'],e['end_node_id']}&unknown]
            bypass=[e for e in full if{e['start_node_id'],e['end_node_id']}==boundary]
            if len(bypass)!=1 or len(chain)!=len(unknown)+1:continue
            local=collections.defaultdict(list)
            for edge in chain:
                for n in(edge['start_node_id'],edge['end_node_id']):local[n].append(edge)
            if any(len(local[n])!=(1 if n in boundary else 2)for n in allowed):continue
            start=min(boundary);nid=start;walk_nodes=[nid];walk_edges=[]
            while len(walk_edges)<len(chain):
                options=[e for e in local[nid]if e['edge_id']not in walk_edges]
                if len(options)!=1:break
                edge=options[0];walk_edges.append(edge['edge_id'])
                nid=edge['end_node_id']if edge['start_node_id']==nid else edge['start_node_id'];walk_nodes.append(nid)
            if len(walk_edges)!=len(chain)or nid not in boundary or nid==start:continue
            key=(system,tuple(sorted(mapping[n]for n in boundary)))
            result[key].append(dict(start=start,end=nid,nodes=walk_nodes,edges=walk_edges,
                unknown_nodes=sorted(unknown),boundary_nodes=sorted(boundary),known_bypass=bypass[0]['edge_id'],
                complete_region_edges=sorted(e['edge_id']for e in full)))
    return result

def known_relation(provider,floor,plan_edge,axis_edge):
    rows=[r for r in provider['records']if r['edge_id']==axis_edge]
    if len(rows)!=1:return []
    return[o for o in rows[0]['correspondence_observations']if o['domain']=='ordinary_local_graph'
           and o.get('floor',floor)==floor and o['plan_edges']==[plan_edge]
           and o.get('grouped_axis_edges',[axis_edge])==[axis_edge]]

def discover(graphs,provider,floor):
    mapping=provider['ordinary_junction_mappings'][str(floor)]
    require(len(mapping)==len(set(mapping.values())),'independent anchor identities collapse')
    require(not any(n.startswith('MEMBER:')for pair in mapping.items()for n in pair),'member identity cannot enter ordinary anchors')
    paths={v:regions(g,mapping if v=='plan'else{n:n for n in mapping.values()},floor)for v,g in graphs.items()}
    observed={r['edge_id']:r for r in provider['records']};used_plan=set();axis_edges=index_graph(graphs['iso'])[1]
    for r in provider['records']:
        for o in r['correspondence_observations']:
            if o.get('floor',axis_edges[r['edge_id']].get('floor_start',floor))==floor:used_plan.update(o['plan_edges'])
    accepted=[];held=[]
    for key,plans in sorted(paths['plan'].items()):
        axes=paths['iso'].get(key,[]);reason=None
        if len(plans)!=len(axes)or len(plans)!=1:
            held.append(dict(floor=floor,system=key[0],anchors=list(key[1]),reason='missing_or_parallel_complementary_region',plan=plans,iso=axes));continue
        p,a=copy.deepcopy(plans[0]),copy.deepcopy(axes[0])
        if mapping[p['start']]!=a['start']:
            a.update(start=a['end'],end=a['start'],nodes=list(reversed(a['nodes'])),edges=list(reversed(a['edges'])))
        relations=known_relation(provider,floor,p['known_bypass'],a['known_bypass'])
        if len(relations)!=1:reason='direct_bypass_lacks_one_independent_existing_correspondence'
        elif len(p['edges'])!=len(a['edges']):reason='unknown_native_chain_branch_counts_differ'
        elif used_plan.intersection(p['edges']):reason='old_plan_scope_writer_present'
        elif any(observed[e]['has_existing_correspondence']for e in a['edges']):reason='old_axis_provider_present'
        elif any(observed[e]['classification']!='horizontal_only'for e in a['edges']):reason='mixed_or_unresolved_chain_requires_segment_owner'
        row=dict(floor=floor,system=key[0],plan=p,iso=a,independent_bypass_observations=copy.deepcopy(relations))
        if reason:held.append(dict(row,reason=reason))
        else:accepted.append(row)
    # No two accepted regions may introduce competing identities or intervals.
    for side in('plan','iso'):
        edge_ids=[e for r in accepted for e in r[side]['edges']]
        require(len(edge_ids)==len(set(edge_ids)),'overlapping complementary chain proposals')
    return accepted,held

def prove(row,graphs,current_plan,docs,provider,hashes,configuration,angles,components,profiles,risks):
    floor=row['floor'];mapping=provider['ordinary_junction_mappings'][str(floor)]
    require(mapping.get(row['plan']['start'])==row['iso']['start']and mapping.get(row['plan']['end'])==row['iso']['end'],'complementary independent endpoints differ')
    require(known_relation(provider,floor,row['plan']['known_bypass'],row['iso']['known_bypass'])==row['independent_bypass_observations'],'known bypass no longer independently belongs to parent')
    native={}
    for view in('plan','iso'):
        g=graphs[view];route=row[view];by={e['edge_id']:e for e in g['edges']};sh=hashes[view]['source_sha256'];gh=hashes[view]['graph_sha256']
        reader=current_plan_reader(configuration,sh,gh)if view=='plan'else native_tee
        junctions={nid:reader(docs[view],g,nid,sh,gh)for nid in route['nodes']}
        stable={nid:unchanged_star(g,current_plan,nid)for nid in route['nodes']}if view=='plan'else None
        path=coverage(docs[view],g,route['edges'],sh,gh)
        require(not path['unresolved']and all(s['status']=='single_source_line_covers'for e in path['edges']for s in e['segments']),'complementary path lacks unique native LINE witnesses')
        if view=='plan':
            handles={h for eid in route['edges']for h in by[eid].get('source_handles',[])}
            require(not any(r['source_LINE']in handles for r in risks['corridors']),'compound carrier requires independent physical member owner')
        require({eid:profiles[view]['profiles'][eid]for eid in route['edges']}=={eid:component_profiles(components[view],[eid])[0]for eid in route['edges']},'native primitive profiles differ from inherited inventory')
        native[view]=dict(junctions=junctions,path_coverage=path,current_reading_stars=stable,
                          full_region_edges_retained=route['complete_region_edges'],known_bypass_retained=route['known_bypass'])
    records=[]
    for i,(pe,ae)in enumerate(zip(row['plan']['edges'],row['iso']['edges'])):
        spec=dict(iso_edges=[ae],iso_start=row['iso']['nodes'][i],iso_end=row['iso']['nodes'][i+1],floor=floor,system=row['system'])
        horizontal_domain(graphs['iso'],spec,angles)
        cp={v:profiles[v]['profiles'][eid]for v,eid in [('plan',pe),('iso',ae)]};different=cp['plan']!=cp['iso']
        key='|'.join([str(floor),row['system'],pe,ae,*row['plan']['boundary_nodes'],*row['iso']['boundary_nodes']])
        records.append(dict(mapping_id='COMPLEMENT-F'+str(floor)+'-'+hashlib.sha256(key.encode()).hexdigest()[:16],
            kind='native_complementary_anchored_chain_topology',axis_edge_id=ae,plan_edges=[pe],iso_edges=[ae],floor=floor,system=row['system'],
            plan_start=row['plan']['nodes'][i],plan_end=row['plan']['nodes'][i+1],iso_start=row['iso']['nodes'][i],iso_end=row['iso']['nodes'][i+1],
            ordinary_endpoint_pairs=[[row['plan']['nodes'][j],row['iso']['nodes'][j]]for j in(i,i+1)],
            component_profiles=cp,source_detail_difference=different,attribute_adoption_allowed=not different,
            independent_bypass_observations=row['independent_bypass_observations'],
            physical_values_assigned=0,off_chain_terminal_identity_assigned=False,human_accepted=False))
    return dict(source_region=copy.deepcopy(row),native=native,records=records,DN_used_for_matching=False,
                known_bypass_deleted=False,off_chain_branch_correspondences_assigned=False,human_accepted=False)

def inherit(original,records):
    result=copy.deepcopy(original);by={r['edge_id']:r for r in result['records']};added=[]
    require(len(records)==len({r['axis_edge_id']for r in records})==len({r['mapping_id']for r in records}),'duplicate complementary writer')
    for proof in records:
        eid=proof['axis_edge_id'];row=by[eid]
        require(not row['has_existing_correspondence']and not row['correspondence_observations'],'complementary chain competes with an old provider')
        require(row['classification']=='horizontal_only'and proof['physical_values_assigned']==0 and proof['off_chain_terminal_identity_assigned']is False,'complementary scope escaped')
        mapping=result['ordinary_junction_mappings'][str(proof['floor'])]
        for p,a in proof['ordinary_endpoint_pairs']:
            require(not p.startswith('MEMBER:')and not a.startswith('MEMBER:'),'member namespace cannot enter ordinary chain')
            require(not(p in mapping and mapping[p]!=a or a in mapping.values()and mapping.get(p)!=a),'complementary endpoint conflicts with independently known anchor')
            if p not in mapping:added.append(dict(floor=proof['floor'],plan_node=p,axis_node=a,mapping_id=proof['mapping_id']))
            mapping[p]=a
        row['has_existing_correspondence']=True
        row['correspondence_observations'].append(dict(provider=MODE,domain='ordinary_local_graph',mapping_id=proof['mapping_id'],floor=proof['floor'],
            plan_edges=proof['plan_edges'],grouped_axis_edges=proof['iso_edges'],attribute_adoption_allowed=proof['attribute_adoption_allowed'],source_detail_difference=proof['source_detail_difference']))
    remaining=[];new={r['axis_edge_id']:r for r in records}
    for old in original['remaining_horizontal_attributes']:
        row=copy.deepcopy(old);proof=new.get(row['edge_id'])
        if proof:
            require(row['next_scope']=='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path','complementary interval is outside unmatched horizontal frontier')
            row.update(next_scope='known_complementary_chain_native_detail_difference'if proof['source_detail_difference']else'known_complementary_chain_attribute_application_pending',
                       existing_mapping_id=proof['mapping_id'],existing_plan_edges=proof['plan_edges'],correspondence_observations=copy.deepcopy(by[row['edge_id']]['correspondence_observations']))
        remaining.append(row)
    result.update(mode=MODE,new_complementary_chain_records=copy.deepcopy(records),new_complementary_chain_anchors=added,remaining_horizontal_attributes=remaining)
    result['current_horizontal_frontier']['records']=remaining
    result['counts'].update(existing_correspondence_edges=sum(r['has_existing_correspondence']for r in result['records']),
                            horizontal_next_scopes=dict(collections.Counter(r['next_scope']for r in remaining)))
    result['current_horizontal_frontier']['remaining_by_next_scope']=result['counts']['horizontal_next_scopes']
    result['history_counts_before_complementary_chain_census']=copy.deepcopy(original['counts'])
    counts=result['counts'];remaining=result['remaining_horizontal_attributes'];frontier=result['current_horizontal_frontier']
    horizontal_total=frontier['pure_horizontal_complete']+len(remaining)
    counts.update(member_domain_observations=len(result['member_domain_observations']),
                  mixed_edges_without_any_correspondence=sum(r['classification']=='mixed_horizontal_vertical'and not r['has_existing_correspondence']for r in result['records']),
                  pure_horizontal_complete_DN_and_centerline=frontier['pure_horizontal_complete'],
                  pure_horizontal_complete_centerline=horizontal_total-sum(not r['complete_centerline']for r in remaining),
                  pure_horizontal_remaining_attributes=len(remaining))
    frontier['pure_horizontal_complete_centerline']=counts['pure_horizontal_complete_centerline']
    result.update(component_owners_changed=False,physical_values_assigned=0,human_accepted=False,whole_goal_complete=False)
    require(result['member_domain_observations']==original['member_domain_observations']and result['current_component_inventory']==original['current_component_inventory'],'complementary chain changed member or component inventory')
    return result
