"""Match a remaining ordinary T arm from two independently scoped incident paths.

Retain members, competing endpoints, mixed directions and source detail differences.
This is a scoped topology correspondence, never a component merge or a DN/metric
writer. A primitive source audit is required before allowing a detail mismatch.
"""
import collections,copy,hashlib,math
from crossview_equipment_branch_inventory import index_graph,native_tee
from anchor_bounded_main_paths import component_profiles
from batch_native_path_coverage import collect as coverage
from attach_anchored_floor_main_attributes import horizontal_domain
from legacy_named_provider_inventory import current_plan_reader,require
from native_ball_contact_reapplication import footprint,source_owners
from native_flange_contact_ownership import flange_contacts
from native_line_path_evidence import LAYERS,_on

TYPES={'tee','physical_junction'}
ALIASES={'球阀':'ball_valve','Ball Valve':'ball_valve','ball_valve':'ball_valve'}


def discover(graphs,provider,floor,components):
    require(set(graphs)=={'plan','iso'}and type(floor)is int,'explicit two-view floor required')
    indexes={v:index_graph(g)for v,g in graphs.items()};mapping=provider['ordinary_junction_mappings'][str(floor)]
    require(len(mapping)==len(set(mapping.values())),'ordinary anchor identities collapse')
    require(not any(p.startswith('MEMBER:')or a.startswith('MEMBER:')for p,a in mapping.items()),'member identity cannot become an ordinary T anchor')
    inverse={a:p for p,a in mapping.items()};observed={r['edge_id']:r for r in provider['records']}
    one=[];used_plan=set()
    for row in provider['records']:
        for obs in row['correspondence_observations']:
            if obs['domain']not in('ordinary_local_graph','named_plan_horizontal_segment','named_riser_interface_path','separate_named_external_port'):continue
            f=obs.get('floor',indexes['iso'][1][row['edge_id']]['floor_start'])
            if f!=floor:continue
            pp,aa=obs['plan_edges'],obs.get('grouped_axis_edges',[row['edge_id']])
            used_plan.update(pp)
            if len(pp)==len(aa)==1 and pp[0]in indexes['plan'][1]and aa[0]in indexes['iso'][1]:
                one.append(dict(plan_edge=pp[0],axis_edge=aa[0],mapping_id=obs['mapping_id'],provider=obs['provider'],domain=obs['domain']))
    proposals=[];held=[]
    for pn,an in sorted(mapping.items()):
        if pn not in indexes['plan'][0]or an not in indexes['iso'][0]:raise ValueError('known T missing')
        if any(indexes[v][0][n].get('node_type')not in TYPES or indexes[v][0][n].get('floor')!=floor or indexes[v][0][n].get('review_required')is True for v,n in [('plan',pn),('iso',an)]):continue
        adj={v:indexes[v][2][n]for v,n in [('plan',pn),('iso',an)]}
        if any(len(es)!=3 or len({e['system']for e in es})!=1 for es in adj.values()):continue
        known=[o for o in one if o['plan_edge']in{e['edge_id']for e in adj['plan']}and o['axis_edge']in{e['edge_id']for e in adj['iso']}]
        pairs={(r['plan_edge'],r['axis_edge'])for r in known}
        if len(pairs)!=2 or len({p for p,a in pairs})!=2 or len({a for p,a in pairs})!=2:continue
        unknown={v:[e for e in adj[v]if e['edge_id']not in{p[i]for p in pairs}]for i,v in enumerate(('plan','iso'))}
        if any(len(es)!=1 for es in unknown.values()):continue
        pe,ae=unknown['plan'][0],unknown['iso'][0]
        if pe['system']!=ae['system']:continue
        pt=pe['end_node_id']if pe['start_node_id']==pn else pe['start_node_id'];at=ae['end_node_id']if ae['start_node_id']==an else ae['start_node_id']
        row=dict(floor=floor,system=pe['system'],plan_anchor=pn,axis_anchor=an,plan_edge_id=pe['edge_id'],axis_edge_id=ae['edge_id'],plan_remote=pt,axis_remote=at,known_incident_relations=copy.deepcopy(known),component_profiles={v:component_profiles(components[v],[e['edge_id']])[0]for v,e in [('plan',pe),('iso',ae)]})
        reason=None
        if observed[ae['edge_id']]['has_existing_correspondence']:reason='already_qualified_provider_or_member_scope_do_not_rematch'
        elif pt not in indexes['plan'][0]or at not in indexes['iso'][0]:reason='remote_graph_endpoint_missing'
        elif pt in mapping and mapping[pt]!=at or at in inverse and inverse[at]!=pt:reason='remote_anchor_conflict_requires_member_or_path_scope'
        elif pe['edge_id']in used_plan:reason='prior_plan_scope_writer_present'
        elif observed[ae['edge_id']]['classification']!='horizontal_only':reason='mixed_or_unresolved_axis_path_needs_segment_owner'
        elif any(indexes[v][0][n].get('node_type')not in TYPES or indexes[v][0][n].get('floor')!=floor or indexes[v][0][n].get('review_required')is True or len(indexes[v][2][n])!=3 or{e['system']for e in indexes[v][2][n]}!={pe['system']}for v,n in [('plan',pt),('iso',at)]):reason='unqualified_remote_T'
        elif len(pe.get('attribute_paths',[]))!=1 or len(ae.get('attribute_paths',[]))!=1:reason='fragmented_carrier_requires_member_or_extent_owner'
        if reason:held.append(dict(row,reason=reason));continue
        proposals.append(row)
    conflicts=set();pairs={};inverse_pairs={};edges={};inverse_edges={}
    for i,row in enumerate(proposals):
        for table,key,value in [(pairs,row['plan_remote'],row['axis_remote']),(inverse_pairs,row['axis_remote'],row['plan_remote']),(edges,row['plan_edge_id'],row['axis_edge_id']),(inverse_edges,row['axis_edge_id'],row['plan_edge_id'])]:table.setdefault(key,{}).setdefault(value,set()).add(i)
    for table in(pairs,inverse_pairs,edges,inverse_edges):
        for options in table.values():
            if len(options)>1:
                for ids in options.values():conflicts.update(ids)
    accepted=[]
    for i,row in enumerate(proposals):
        if i in conflicts:held.append(dict(row,reason='competing_third_arm_cohort_identity'))
        else:accepted.append(row)
    return accepted,held


def plan_owners(geometry,pipes,graph):
    systems={v:k for k,v in LAYERS.items()};native=[];owners=[]
    for line in pipes:
        if line.dxf.layer not in systems:continue
        a,b=list(line.dxf.start),list(line.dxf.end);contacts=flange_contacts(geometry,a,b)
        if contacts is not None:native.append(dict(source_LINE=line.dxf.handle,system=systems[line.dxf.layer],start=a,end=b,flange_contacts=contacts))
    if len(native)==1:
        n=native[0];points=[p['point_WCS']for p in n['flange_contacts']]
        for edge in graph['edges']:
            if edge['system']!=n['system']or edge.get('source_handles')is not None and n['source_LINE']not in edge['source_handles']:continue
            for pi,path in enumerate(edge.get('attribute_paths',[])):
                for si,(a,b)in enumerate(zip(path,path[1:])):
                    if math.dist(a,b)>.05 and all(_on(p[:2],a,b,.05)for p in points)and all(_on(p,n['start'][:2],n['end'][:2],.05)for p in(a,b)):owners.append(dict(edge_id=edge['edge_id'],path_index=pi,segment_index=si))
    return native,owners


def native_component_profiles(doc,graph,components,edge_ids,view):
    target=set(edge_ids);claims=collections.defaultdict(list)
    for c in components:
        handle=c.get('source_top_handle')or c.get('source_handle')
        if handle:claims[handle].append(c)
    pipes=list(doc.modelspace().query('LINE'));records=[];by_edge=collections.defaultdict(list);seen=set()
    for insert in doc.modelspace().query('INSERT'):
        if insert.dxf.name!='H-PICPNT-91':continue
        geometry=footprint(insert)
        if geometry is None:continue
        native,owners=(plan_owners if view=='plan'else source_owners)(geometry,pipes,graph)
        prior=claims.get(insert.dxf.handle,[])
        if not(any(c['edge_id']in target for c in prior)or any(o['edge_id']in target for o in owners)):continue
        require(len(native)==len(owners)==len(prior)==1,'target component ownership or source signature is not unique')
        require(prior[0]['edge_id']==owners[0]['edge_id']and ALIASES.get(prior[0]['equipment_type'])=='ball_valve','target component source/graph owner differs')
        row=dict(source_handle=insert.dxf.handle,edge_id=owners[0]['edge_id'],geometry=geometry,native_contact=native[0],native_graph_owner=owners[0],original_instance=copy.deepcopy(prior[0]))
        records.append(row);by_edge[row['edge_id']].append(row);seen.add(insert.dxf.handle)
    for c in components:
        if c['edge_id']in target:
            require(ALIASES.get(c['equipment_type'])=='ball_valve'and(c.get('source_top_handle')or c.get('source_handle'))in seen,
                    'an unmatched source detail difference needs another native component owner')
    return dict(records=records,profiles={eid:dict(collections.Counter('ball_valve'for _ in by_edge[eid]))for eid in edge_ids},
                source_scope='complete_modelspace_known_ball_signature_on_selected_intervals',component_owners_mutated=False)


def prove(row,graphs,docs,provider,hashes,config,components,angles,profiles):
    indexes={v:index_graph(g)for v,g in graphs.items()};proofs={};ordinary=provider['ordinary_junction_mappings'][str(row['floor'])]
    require(ordinary.get(row['plan_anchor'])==row['axis_anchor'],'independent known anchor differs')
    owner_records={r['edge_id']:r for r in provider['records']}
    require(not owner_records[row['axis_edge_id']]['has_existing_correspondence'],'third arm already has a provider')
    for view,key in [('plan','plan_edge_id'),('iso','axis_edge_id')]:
        require(component_profiles(components[view],[row[key]])[0]==row['component_profiles'][view],'preserved component inventory changed after discovery')
    for relation in row['known_incident_relations']:
        require(any(o['mapping_id']==relation['mapping_id']and o['provider']==relation['provider']and o['plan_edges']==[relation['plan_edge']]and o.get('grouped_axis_edges',[relation['axis_edge']])==[relation['axis_edge']]for o in owner_records[relation['axis_edge']]['correspondence_observations']),
                'incident relation no longer belongs to the complete native parent')
        for view,key,anchor in [('plan','plan_edge',row['plan_anchor']),('iso','axis_edge',row['axis_anchor'])]:
            e=indexes[view][1][relation[key]];require(anchor in(e['start_node_id'],e['end_node_id'])and e['system']==row['system'],'known arm incidence differs')
        if relation['domain']=='named_plan_horizontal_segment':
            source=[s for s in provider.get('inherited_legacy_named_scopes',[])if s['mapping_id']==relation['mapping_id']]
            require(len(source)==1,'partial named arm lacks its exact current source scope')
            for view,nid,paths in [('plan',row['plan_anchor'],list(source[0]['plan_paths'].values())[0]),('iso',row['axis_anchor'],source[0]['axis_scope_paths'])]:
                n=indexes[view][0][nid];require(any(math.dist(p,[n['x'],n['y']])<=.05 for path in paths for p in(path[0],path[-1])),'partial scope does not reach the actual incident T')
    horizontal_domain(graphs['iso'],dict(iso_edges=[row['axis_edge_id']],system=row['system'],floor=row['floor'],iso_start=row['axis_anchor'],iso_end=row['axis_remote']),angles)
    for view,eid,ends in [('plan',row['plan_edge_id'],[row['plan_anchor'],row['plan_remote']]),('iso',row['axis_edge_id'],[row['axis_anchor'],row['axis_remote']])]:
        edge=indexes[view][1][eid];require({edge['start_node_id'],edge['end_node_id']}==set(ends),'third-arm path endpoints differ')
        reader=current_plan_reader(config,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])if view=='plan'else native_tee
        junctions={n:reader(docs[view],graphs[view],n,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])for n in ends}
        native=coverage(docs[view],graphs[view],[eid],hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
        require(not native['unresolved']and all(s['status']=='single_source_line_covers'for e in native['edges']for s in e['segments']),'third arm lacks complete unique native LINE fragments')
        proofs[view]=dict(junctions=junctions,native_path=native,attribute_paths=copy.deepcopy(edge['attribute_paths']),edge_id=eid)
    different=row['component_profiles']['plan']!=row['component_profiles']['iso']
    if different:
        require(profiles is not None,'material difference requires actual primitive source replay')
        for view,eid in [('plan',row['plan_edge_id']),('iso',row['axis_edge_id'])]:
            require(profiles[view]['profiles'][eid]==row['component_profiles'][view],'source primitive counts differ from the preserved inventory')
    key='|'.join([str(row['floor']),row['system'],row['plan_edge_id'],row['axis_edge_id'],row['plan_anchor'],row['axis_anchor']])
    return dict(row,mapping_id='THIRD-ARM-F'+str(row['floor'])+'-'+hashlib.sha256(key.encode()).hexdigest()[:16],
        kind='source_checked_remaining_ordinary_T_arm_topology',plan_edges=[row['plan_edge_id']],iso_edges=[row['axis_edge_id']],
        ordinary_endpoint_pairs=[[row['plan_anchor'],row['axis_anchor']],[row['plan_remote'],row['axis_remote']]],
        native_proofs=proofs,source_detail_difference=different,
        source_detail_status='native_drawings_have_different_ball_counts_no_owner_or_component_changed'if different else'preserved_profiles_agree',
        attribute_adoption_allowed=not different,component_correspondence_or_merge_assigned=False,DN_used_for_matching=False,
        physical_values_assigned=0,source_graphs_mutated=False,human_accepted=False)
