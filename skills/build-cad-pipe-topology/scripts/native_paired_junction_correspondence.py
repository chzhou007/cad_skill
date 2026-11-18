"""Match existing paired-main Ts by independently checked off-corridor targets.

No nearest-point matching, invented device, connection or length allocation.
"""
from crossview_equipment_branch_inventory import index_graph,native_tee,service_route
from match_source_checked_crossview_paths import native_main_corridor,bridge_main_path
from native_path_coverage_audit import audit as audit_paths


def collect(docs,graphs,mapping,hashes):
    if set(docs)!= {'plan','iso'} or set(graphs)!=set(docs):raise ValueError('two native views required')
    if mapping.get('local_graphs_mutated') is not False or mapping.get('human_accepted') is not False:raise ValueError('unsupported paired source mapping state')
    pairs=mapping['evidence']['paired_services'];floor=mapping['floor'];indices={v:index_graph(g) for v,g in graphs.items()}
    if len({p['pair_id'] for p in pairs})!=len(pairs):raise ValueError('duplicate paired source identity')
    if any(set(p['services'])!={'supply','return'} for p in pairs):raise ValueError('both paired service proofs required')
    known={v:{s:{} for s in ('supply','return')} for v in graphs}
    for pair in pairs:
        for system,state in pair['services'].items():
            if system not in ('supply','return'):raise ValueError('unknown paired system')
            for view in graphs:
                for did,nid in state['taps'][view].items():
                    if nid in known[view][system] or service_route(graphs[view],did,system).get('tee')!=nid:raise ValueError('paired target ownership or unique T changed')
                    owner=indices[view][0][did];captions=[e for e in docs[view].modelspace().query('TEXT MTEXT') if e.plain_text()==did]
                    if owner.get('floor')!=floor or owner.get('node_type') not in ('equipment','physical_equipment') or len(captions)!=1:raise ValueError('paired target native identity differs')
                    known[view][system][nid]=did
    records=[]
    for parent in pairs:
        for system,state in parent['services'].items():
            internal=state['internal_native_junctions'];candidates={v:[] for v in graphs}
            for view in graphs:
                for original in internal[view]:
                    nid=original['node_id'];node=indices[view][0][nid]
                    if node.get('floor')!=floor or node.get('review_required') is True:raise ValueError('parent interior T unresolved or on another floor')
                    proof=native_tee(docs[view],graphs[view],nid,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
                    if proof!=original['evidence']:raise ValueError('parent interior T source evidence changed')
                    rows=proof.get('junctions',[])
                    if len(rows)!=1:raise ValueError('interior T requires a supported native through-role reader')
                    through=state['native_corridors'][view]['source_line_handle'];off=[r['edge_id'] for r in rows[0]['source_rays'] if r.get('source_line_handle')!=through]
                    if len(off)!=1:raise ValueError('interior T has no unique native non-through branch')
                    for other in pairs:
                        if other['pair_id']==parent['pair_id']:continue
                        target_state=other['services'][system]
                        for did,target in target_state['taps'][view].items():
                            try:
                                scope,corridor=native_main_corridor(docs[view],graphs[view],{'source_junction':nid,did:target},system,floor)
                                if corridor['source_line_handle']!=target_state['native_corridors'][view]['source_line_handle']:continue
                                route=bridge_main_path(scope,nid,target,system,floor)
                                if route['edges'][0]!=off[0] or set(route['nodes'][1:-1]).intersection(known[view][system]):continue
                                coverage=audit_paths(docs[view],graphs[view],dict(hashes[view],edges=route['edges']),hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
                                if any(s['status']!='single_source_line_covers' for e in coverage['edges'] for s in e['segments']):continue
                                interior=[]
                                for peer in route['nodes'][1:-1]:
                                    if len(indices[view][2][peer])==2:continue
                                    interior.append(native_tee(docs[view],graphs[view],peer,hashes[view]['source_sha256'],hashes[view]['graph_sha256']))
                                native_tee(docs[view],graphs[view],target,hashes[view]['source_sha256'],hashes[view]['graph_sha256'])
                                candidates[view].append(dict(parent_node=nid,target_pair_id=other['pair_id'],target_equipment_id=did,
                                    route=dict(start=nid,end=target,**route),native_corridor=corridor,coverage=coverage,intermediate_native_junctions=interior))
                            except ValueError:continue
            signatures={v:{} for v in graphs}
            for view in graphs:
                for candidate in candidates[view]:
                    key=(candidate['target_pair_id'],candidate['target_equipment_id']);signatures[view].setdefault(key,[]).append(candidate)
            matched=[];used={v:set() for v in graphs}
            for key in sorted(set(signatures['plan'])&set(signatures['iso'])):
                a,b=signatures['plan'][key],signatures['iso'][key]
                if len(a)!=1 or len(b)!=1:continue
                views=dict(plan=a[0],iso=b[0])
                if any(views[v]['parent_node'] in used[v] for v in graphs):raise ValueError('interior T has competing matched branch identities')
                if len(a[0]['intermediate_native_junctions'])!=len(b[0]['intermediate_native_junctions']):raise ValueError('branch link has different native branch topology')
                for view in graphs:used[view].add(views[view]['parent_node'])
                matched.append(dict(junction_mapping_id=f'PJ-{parent["pair_id"]}-{system}-{len(matched)+1:02d}',
                    target_pair_id=key[0],target_equipment_id=key[1],views=views))
            expected={v:{r['node_id'] for r in internal[v]} for v in graphs}
            if any(expected.values()):records.append(dict(parent_pair_id=parent['pair_id'],system=system,matches=matched,
                complete=all(used[v]==expected[v] for v in graphs),unmatched_nodes={v:sorted(expected[v]-used[v]) for v in graphs}))
    return dict(status='native_offcorridor_target_supported_junction_candidates',records=records,
        graph_mutated=False,physical_lengths_assigned=0,expert_confirmation_claimed=False,human_accepted=False)
