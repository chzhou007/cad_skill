"""Inherit drawing11 main DN through source-checked Ts and unlabelled branches.

Check every original branch path for later labels before borrowing main DN.
No new connection, whole-edge diameter or physical length is introduced.
"""
import copy,math
from confirm_crossview_paths import encode
from axis_continuous_source_vertical_DN import modelspace_seeds,through_line_evidence,scoped_guard
from axis_unbranched_vertical_DN import source_key,annotation_index,chain_evidence,source_Z
from crossview_equipment_branch_inventory import native_tee,index_graph
from native_line_path_evidence import LAYERS
MODE='native_axis_checked_main_T_DN_inheritance_v1'

def collect(doc,graph,route,prior,items,sh,gh):
    if graph['metadata']['source_sha256']!=sh or route['inputs']['source']['sha256']!=sh or route['inputs']['graph']['sha256']!=gh:raise ValueError('current source graph and routing identities required')
    before=encode(graph),encode(route),encode(prior)
    seeds=modelspace_seeds(doc,graph,route,sh,gh);scopes={source_key(s):s for s in route['records']};nodes,edges,adj=index_graph(graph);index=annotation_index(doc,graph,sh);tee_cache={};records=[];pending=[];diagnostics=[]
    for p in prior['pending']:
        key=source_key(p);edge=edges[key[0]];target=scopes[key];choices=[];failures=[]
        if p.get('original_reason')!='no_qualified_axis_annotation_on_this_vertical_segment':pending.append(copy.deepcopy(p));continue
        path=edge['attribute_paths'][key[1]]
        for nid in(edge['start_node_id'],edge['end_node_id']):
            if nodes[nid]['node_type']not in('physical_junction','tee'):continue
            point=[nodes[nid]['x'],nodes[nid]['y']]
            if min(math.dist(point,path[0]),math.dist(point,path[-1]))>.05:continue
            try:
                if nid not in tee_cache:
                    try:tee_cache[nid]=dict(proof=native_tee(doc,graph,nid,sh,gh))
                    except ValueError as e:tee_cache[nid]=dict(reason=str(e))
                if'proof'not in tee_cache[nid]:raise ValueError('current native T not qualified: '+tee_cache[nid]['reason'])
                tproof=tee_cache[nid]['proof'];rays=tproof.get('junctions',[{}])[0].get('source_rays',[])
                if len(rays)!=3:raise ValueError('three native source rays required')
                pairs=[(a,b)for i,a in enumerate(rays)for b in rays[i+1:]if sum(x*y for x,y in zip(a['direction'],b['direction']))<-math.cos(math.radians(.1))]
                if len(pairs)!=1:raise ValueError('unique through-main ray pair required')
                a,b=pairs[0];handle=a.get('source_line_handle')
                if not handle or handle!=b.get('source_line_handle'):raise ValueError('main arms do not share one original source LINE')
                actual=doc.entitydb.get(handle)
                if actual is None or actual.dxftype()!='LINE'or actual.dxf.layer!=LAYERS[edge['system']]:raise ValueError('same-system original main source LINE required')
                low,high=(0,key[2])if math.dist(point,path[0])<=.05 else(key[2],len(path)-2);branch=[scopes[key[0],key[1],i]for i in range(low,high+1)]
                roots={None if s['native_witnesses'][0]['scope']=='modelspace'else s['native_witnesses'][0]['source_handle']for s in branch if s['native_source_status']=='single_source_line_covers'}
                if len(roots)!=1:raise ValueError('branch corridor crosses native root identities')
                bends=chain_evidence(branch,next(iter(roots)),items);at=bends['native_chain'][0]if math.dist(point,path[0])<=.05 else bends['native_chain'][-1];mainitem=dict(XYZ=[list(actual.dxf.start),list(actual.dxf.end)])
                if abs(source_Z(at,point)-source_Z(mainitem,point))>.05:raise ValueError('native main and branch source Z do not contact')
                connectors=[s for s in route['records']if s['edge_id']in(a['edge_id'],b['edge_id'])and s['native_source_status']=='single_source_line_covers'and s['native_witnesses'][0]['scope']=='modelspace'and s['native_witnesses'][0]['source_handle']==handle and any(math.dist(q,point)<=.05 for q in s['scope_points'])]
                if len(connectors)!=2:raise ValueError('two original through-main connector domains required')
                candidates=[s for s in seeds['records']if s['system']==edge['system']and s['source_line_handle']==handle]
                if not candidates:raise ValueError('no freshly source-owned annotation on through-main LINE')
                for seed in candidates:
                    for connector in connectors:
                        try:
                            through=through_line_evidence(doc,graph,connector,seed,items,sh,gh,tee_cache)
                            corridor=[dict(connector,scope_points=through['scope_points'])]+[s for s in route['records']if s['edge_id']==key[0]]
                            guard=scoped_guard(doc,[seed],corridor,index,sh,next(iter(roots)),seeds['records'])
                            choices.append(dict(seed=seed,main=through,root_T=tproof,branch=bends,annotation_guard=guard,main_LINE=handle))
                        except ValueError as e:failures.append(dict(node_id=nid,seed_domain=list(source_key(seed)),reason=str(e)))
            except ValueError as e:failures.append(dict(node_id=nid,reason=str(e)))
        if choices and len({c['seed']['nominal_mm']for c in choices})==1:
            records.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],nominal_mm=choices[0]['seed']['nominal_mm'],scope_points=copy.deepcopy(target['scope_points']),system=target['system'],floor_start=target['floor_start'],floor_end=target['floor_end'],candidate_evidence=choices,connection_rule='original_native_main_T_and_unlabelled_branch_continuity',source='axis11_native_main_annotation_T_and_branch_path',whole_edge_DN_assigned=False,physical_length_mm=None,human_accepted=False))
        else:
            pending.append(copy.deepcopy(p));diagnostics.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],reason='competing_native_main_DN_values'if choices else'no_checked_main_T_to_target_corridor',failures=failures))
    if before!=(encode(graph),encode(route),encode(prior)):raise ValueError('original graph, routing or parent source result mutated')
    oldkeys={source_key(p)for p in prior['pending']};newkeys={source_key(r)for r in records};heldkeys={source_key(p)for p in pending}
    if len(newkeys)!=len(records)or len(heldkeys)!=len(pending)or newkeys&heldkeys or newkeys|heldkeys!=oldkeys:raise ValueError('current pending source-domain conservation failed')
    previous=prior['counts']['current_known'];total=sum(s['direction_class']=='vertical'for s in route['records'])
    if previous+len(oldkeys)!=total:raise ValueError('actual previous vertical population differs')
    return dict(mode=MODE,records=records,pending=pending,diagnostics=diagnostics,seeds=seeds,native_T_cache=tee_cache,counts=dict(previous_known=previous,screened_pending=len(oldkeys),new_known=len(records),current_known=previous+len(records),remaining_unknown=len(pending)),whole_branch_annotation_barriers_checked=True,branch_DN_never_used_as_main_seed=True,graph_mutated=False,horizontal_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)

