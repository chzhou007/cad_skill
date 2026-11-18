"""Main-path DN candidates constrained by independently replayed native T rays.

Opposite native rays define a source through pair, not hydraulic flow direction.
Branch labels cannot seed that pair; an explicit DN edge remains a boundary.
Equipment branch defaults still belong to the inherited branch-scope owner.
"""
import collections,copy,itertools,math
from crossview_equipment_branch_inventory import index_graph

def infer(graph,seeds,verified_edges,junctions,source_hash,graph_hash):
    nodes,edges,adj=index_graph(graph);scope=set(verified_edges)
    if not scope or not scope<=set(edges) or not junctions:raise ValueError('complete checked source scope required')
    if any(edges[e]['system'] not in ('supply','return') for e in scope):raise ValueError('unknown pipe service')
    roles={};neighbours=collections.defaultdict(list)
    for nid,proof in sorted(junctions.items()):
        node=nodes.get(nid)
        if (not node or node.get('node_type') not in ('tee','physical_junction') or node.get('review_required') is True
            or len(adj[nid])!=3 or len({e['system'] for e in adj[nid]})!=1
            or proof.get('source_sha256')!=source_hash or proof.get('graph_sha256')!=graph_hash or proof.get('graph_mutated') is not False):
            raise ValueError('native through-T source, graph, role or service differs')
        records=proof.get('junctions',[])
        if len(records)!=1 or records[0].get('node_id')!=nid or math.dist(records[0]['position'],[node['x'],node['y']])>.05:raise ValueError('native T position or identity differs')
        rays=records[0].get('source_rays',[])
        if len(rays)!=3 or {r['edge_id'] for r in rays}!={e['edge_id'] for e in adj[nid]}:raise ValueError('complete native T ray ownership required')
        pairs=[]
        for a,b in itertools.combinations(rays,2):
            x,y=a['direction'],b['direction']
            if any(len(v)!=2 or any(not isinstance(n,(int,float)) or isinstance(n,bool) or not math.isfinite(n) for n in v) or math.hypot(*v)<=.000001 for v in (x,y)):
                raise ValueError('invalid native T ray direction')
            cosine=sum(u*v for u,v in zip(x,y))/(math.hypot(*x)*math.hypot(*y))
            if cosine<=-math.cos(math.radians(1)):pairs.append((a['edge_id'],b['edge_id']))
        if len(pairs)!=1:raise ValueError('native T lacks one unique through pair')
        a,b=pairs[0];branch=next(r['edge_id'] for r in rays if r['edge_id'] not in (a,b))
        roles[nid]=dict(through=[a,b],branch=branch,source_T_proof=copy.deepcopy(proof))
        if {a,b}<=scope:neighbours[a].append((b,nid));neighbours[b].append((a,nid))
    owners={};by_edge=collections.defaultdict(list)
    for seed in seeds:
        eid=seed['edge_id'];value=seed['nominal_mm'];witness=seed['evidence_id']
        if eid not in scope or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0 or not isinstance(witness,str) or not witness:
            raise ValueError('invalid source diameter seed')
        if witness in owners:raise ValueError('native DN annotation seeded more than once')
        owners[witness]=(eid,value);by_edge[eid].append((value,witness))
    if not seeds or any(len({v for v,_ in rows})!=1 for rows in by_edge.values()):raise ValueError('different direct DN values on one edge need source segment subdivision')
    candidates=collections.defaultdict(lambda:collections.defaultdict(list))
    for eid,rows in sorted(by_edge.items()):
        for value,witness in sorted(rows):
            todo=[(eid,[eid],[])];seen={eid}
            while todo:
                current,path,Ts=todo.pop();candidates[current][value].append(dict(evidence_id=witness,edge_path=path,through_T_ids=Ts))
                for peer,nid in sorted(neighbours[current]):
                    if peer in seen or peer in by_edge:continue
                    seen.add(peer);todo.append((peer,path+[peer],Ts+[nid]))
    records=[]
    for eid in sorted(scope):
        values=candidates.get(eid,{})
        records.append(dict(edge_id=eid,system=edges[eid]['system'],nominal_mm=next(iter(values)) if len(values)==1 else None,
            status='direct_plan_DN' if eid in by_edge else 'T_inherited_plan_DN' if len(values)==1 else 'conflict' if values else 'unresolved',
            lineage=[dict(nominal_mm=value,evidence=proof) for value,proof in sorted(values.items())],scope_paths=copy.deepcopy(edges[eid]['attribute_paths']),
            scope='source_checked_native_through_plan_pipe_paths_only',human_accepted=False))
    return dict(mode='source_through_T_DN_candidates_v1',records=records,roles=roles,source_sha256=source_hash,graph_sha256=graph_hash,
        branch_labels_backflow_to_through_arms=False,branch_defaults_inferred=False,physical_flow_direction_inferred=False,graph_mutated=False,human_accepted=False)
