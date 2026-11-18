"""Compose old native bend/T/caption rules across segmented axis mains.

The edge INSERT may be an omission glyph. Pipe roots come from the original
per-segment native witnesses, never from that edge-level drawing handle.
"""
import collections,copy,math
from confirm_crossview_paths import encode
from axis_continuous_source_vertical_DN import modelspace_seeds,scoped_guard
from axis_unbranched_vertical_DN import source_key,chain_evidence,source_Z,annotation_index
from crossview_equipment_branch_inventory import native_tee,index_graph

MODE='native_multiline_main_T_vertical_DN_composition_v1'
RULE='original_native_multiline_main_through_T_and_branch_continuity'

def source_path_chain(edge,entry,nodes,rows,items,stop=None):
    point=[nodes[entry]['x'],nodes[entry]['y']];hits=[(pi,side)for pi,p in enumerate(edge['attribute_paths'])for side in(0,-1)if math.dist(p[side],point)<=.05]
    if len(hits)!=1:raise ValueError('one native path at graph endpoint required')
    pi,side=hits[0];path=edge['attribute_paths'][pi];indices=list(range(len(path)-1));indices=indices if side==0 else indices[::-1]
    if stop is not None:
        if stop['path_index']!=pi or stop['segment_index']not in indices:raise ValueError('seed is on another drawing path')
        indices=indices[:indices.index(stop['segment_index'])+1]
    scopes=[copy.deepcopy(rows[edge['edge_id'],pi,i])for i in indices]
    if side==-1:
        for s in scopes:s['scope_points'].reverse()
    roots={None if s['native_witnesses'][0]['scope']=='modelspace'else s['native_witnesses'][0]['source_handle']for s in scopes if s['native_source_status']=='single_source_line_covers'}
    if len(roots)!=1:raise ValueError('one source-owner namespace per corridor required')
    root=next(iter(roots));proof=chain_evidence(scopes,root,items);proof['actual_native_source_root']=root
    return scopes,proof

def opposite(a,b):return sum(x*y for x,y in zip(a['direction'],b['direction']))<-math.cos(math.radians(.1))

def collect(doc,graph,route,parent,items,sh,gh):
    if graph['metadata']['source_sha256']!=sh or route['inputs']['source']['sha256']!=sh or route['inputs']['graph']['sha256']!=gh:raise ValueError('current native source/graph/routing identities required')
    before=encode(graph),encode(route),encode(parent),encode(items);nodes,edges,adj=index_graph(graph);rows={source_key(s):s for s in route['records']};pending_keys={source_key(s)for s in parent['pending']}
    if len(rows)!=len(route['records'])or len(pending_keys)!=len(parent['pending'])or parent['counts']['current_known']+len(pending_keys)!=sum(s['direction_class']=='vertical'for s in route['records']):raise ValueError('complete current vertical population required')
    for s in route['records']:
        if edges[s['edge_id']]['system']!=s['system']or edges[s['edge_id']]['attribute_paths'][s['path_index']][s['segment_index']:s['segment_index']+2]!=s['scope_points']:raise ValueError('original route and graph segment differ')
    seeds=modelspace_seeds(doc,graph,route,sh,gh);index=annotation_index(doc,graph,sh);byedge=collections.defaultdict(list);cache={};records=[];pending=[];diagnostics=[]
    for s in seeds['records']:byedge[s['edge_id']].append(s)
    def tee(nid):
        if nid not in cache:
            try:cache[nid]=dict(proof=native_tee(doc,graph,nid,sh,gh))
            except ValueError as exc:cache[nid]=dict(reason=str(exc))
        if'proof'not in cache[nid]:raise ValueError('native T: '+cache[nid]['reason'])
        p=cache[nid]['proof'];rays=p.get('junctions',[{}])[0].get('source_rays',[])
        if len(rays)!=3:raise ValueError('exactly three native rays required')
        if {e['system']for e in adj[nid]}!={edges[rays[0]['edge_id']]['system']}:raise ValueError('mixed-system native T')
        return p,rays
    for prior in parent['pending']:
        if prior['original_reason']!='no_qualified_axis_annotation_on_this_vertical_segment':pending.append(copy.deepcopy(prior));continue
        target=rows[source_key(prior)];edge=edges[target['edge_id']];choices=[];failures=[];encountered_seed_values=set()
        if target['direction_class']!='vertical':raise ValueError('target must remain an original vertical scope')
        for nid in(edge['start_node_id'],edge['end_node_id']):
            if nodes[nid]['node_type']not in('tee','physical_junction'):continue
            try:
                rootproof,rays=tee(nid);pairs=[(a,b)for i,a in enumerate(rays)for b in rays[i+1:]if opposite(a,b)]
                if len(pairs)!=1 or edge['edge_id']in{r['edge_id']for r in pairs[0]}:raise ValueError('target is not the third native T arm')
                branch_scopes,branch=source_path_chain(edge,nid,nodes,rows,items,target)
                # A label on the other half of the root main can delimit a
                # reducer even when its direct owner is still ambiguous.
                # Candidate-path success must not discard that whole-LINE cue.
                root_main_scopes=[]
                for handle in sorted({r.get('source_line_handle')for r in pairs[0]}):
                    line=doc.entitydb.get(handle)
                    if line is None or line.dxftype()!='LINE' or line not in doc.modelspace():raise ValueError('original root through-main LINE required')
                    root_main_scopes.append(dict(system=target['system'],scope_points=[list(line.dxf.start)[:2],list(line.dxf.end)[:2]],native_source_guard_handle=handle,scope_role='complete_root_main_annotation_guard_not_new_attribute_domain'))
                for initial in pairs[0]:
                    current_id=initial['edge_id'];entry=nid;visited=set();parts=[];junctions=[rootproof];prior_item=branch['native_chain'][0]
                    try:
                        while True:
                            if current_id in visited:raise ValueError('main corridor cycle has no unique seed boundary')
                            visited.add(current_id);current=edges[current_id]
                            if current['system']!=edge['system']:raise ValueError('system changed on main corridor')
                            on=[s for s in byedge[current_id]if s['system']==edge['system']]
                            if on:
                                for seed in on:
                                    try:
                                        scopes,proof=source_path_chain(current,entry,nodes,rows,items,seed);point=[nodes[entry]['x'],nodes[entry]['y']]
                                        if abs(source_Z(prior_item,point)-source_Z(proof['native_chain'][0],point))>.05:raise ValueError('seed main XYZ contact differs')
                                        encountered_seed_values.add(seed['nominal_mm'])
                                        corridor=[s for p in parts for s in p['scopes']]+scopes+root_main_scopes+[s for s in route['records']if s['edge_id']==edge['edge_id']]
                                        guard=scoped_guard(doc,[seed],corridor,index,sh,branch['actual_native_source_root'],seeds['records'])
                                        choices.append(dict(seed=seed,main_parts=parts+[dict(scopes=scopes,source_continuity=proof)],junctions=copy.deepcopy(junctions),branch=branch,root_through_main_full_source_extents=root_main_scopes,annotation_guard=guard))
                                    except ValueError as exc:failures.append(str(exc))
                                break
                            scopes,proof=source_path_chain(current,entry,nodes,rows,items);point=[nodes[entry]['x'],nodes[entry]['y']]
                            if abs(source_Z(prior_item,point)-source_Z(proof['native_chain'][0],point))>.05:raise ValueError('main native XYZ contact differs')
                            parts.append(dict(scopes=scopes,source_continuity=proof));far=next(x for x in(current['start_node_id'],current['end_node_id'])if x!=entry);point=[nodes[far]['x'],nodes[far]['y']]
                            if math.dist(scopes[-1]['scope_points'][-1],point)>.05:raise ValueError('main has unproved drawing omission or multiple paths')
                            p,rr=tee(far);incoming=[r for r in rr if r['edge_id']==current_id];out=[r for r in rr if len(incoming)==1 and opposite(incoming[0],r)]
                            if len(out)!=1:raise ValueError('main continuation is not unique native through arm')
                            prior_item=proof['native_chain'][-1];junctions.append(p);entry,current_id=far,out[0]['edge_id']
                    except ValueError as exc:failures.append(str(exc))
            except ValueError as exc:failures.append(str(exc))
        if choices and len(encountered_seed_values)==1:
            records.append(dict(edge_id=target['edge_id'],path_index=target['path_index'],segment_index=target['segment_index'],scope_points=target['scope_points'],system=target['system'],floor_start=target['floor_start'],floor_end=target['floor_end'],nominal_mm=choices[0]['seed']['nominal_mm'],candidate_evidence=choices,connection_rule=RULE,physical_length_mm=None,whole_edge_DN_assigned=False,human_accepted=False))
        else:
            pending.append(copy.deepcopy(prior));diagnostics.append(dict(**prior,failures=sorted(set(failures)),competing_values=sorted(encountered_seed_values)))
    newkeys={source_key(r)for r in records};heldkeys={source_key(r)for r in pending}
    if newkeys&heldkeys or newkeys|heldkeys!=pending_keys or len(newkeys)!=len(records)or len(heldkeys)!=len(pending):raise ValueError('complete pending scope conservation differs')
    if before!=(encode(graph),encode(route),encode(parent),encode(items)):raise ValueError('source inputs or previous values mutated')
    return dict(mode=MODE,records=records,pending=pending,diagnostics=diagnostics,seeds=seeds,native_T_cache=cache,counts=dict(previous_known=parent['counts']['current_known'],screened_pending=len(parent['pending']),screened_corridors=len(records)+len(diagnostics),new_known=len(records),current_known=parent['counts']['current_known']+len(records),remaining_unknown=len(pending)),whole_branch_annotation_barriers_checked=True,whole_root_main_annotation_extents_checked=True,conflicting_source_connected_seeds_blocked=True,branch_DN_never_used_as_main_seed=True,source_roots_from_native_witnesses=True,graph_mutated=False,components_reassigned=False,horizontal_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)
