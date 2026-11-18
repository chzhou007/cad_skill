"""Apply inherited through-T rules and explicit branch overrides on a full plan.

Only source-proved edge scopes and T roles enter the transfer graph. Direct
annotations are boundaries. Derived branch values never become new boundaries,
so a later conflicting source remains visible rather than being hidden by an
iteration-order dependent inferred seed. No hydraulic flow direction is used.
"""
import collections,copy,math
from through_source_DN_inheritance import infer as through_infer


def infer(graph,seeds,verified_edges,junctions,source_hash,graph_hash):
    scope=set(verified_edges);by={e['edge_id']:e for e in graph['edges']}
    if len(by)!=len(graph['edges'])or not scope<=set(by)or any(by[e]['system']not in ('supply','return')for e in scope):raise ValueError('invalid complete local edge scope')
    witnesses=set();direct_values=collections.defaultdict(set)
    for seed in seeds:
        value=seed['nominal_mm'];witness=seed['evidence_id']
        if (seed['edge_id']not in scope or isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value)or value<=0
            or not isinstance(witness,str)or not witness or witness in witnesses):raise ValueError('invalid or repeated native DN seed')
        witnesses.add(witness);direct_values[seed['edge_id']].add(value)
    if any(len(v)>1 for v in direct_values.values()):raise ValueError('different direct DN values need source segment subdivision')
    validation_seeds=seeds or ([dict(edge_id=sorted(scope)[0],nominal_mm=1,evidence_id='validation-only-not-in-output')]if scope else [])
    base=through_infer(graph,validation_seeds,scope,junctions,source_hash,graph_hash)if scope and junctions else dict(roles={})
    direct={s['edge_id']for s in seeds}
    scoped={s['edge_id']for s in seeds if s.get('scope_only')is True}
    parent={eid:eid for eid in scope}
    def root(eid):
        while parent[eid]!=eid:parent[eid]=parent[parent[eid]];eid=parent[eid]
        return eid
    for role in base['roles'].values():
        a,b=role['through']
        if {a,b}<=scope and not {a,b}&scoped:parent[root(a)]=root(b)
    labelled_regions={root(eid)for eid in direct};uncertain_regions=set()
    for role in base['roles'].values():
        pair=set(role['through'])
        if len(pair&scope)==1:uncertain_regions.add(root(next(iter(pair&scope))))
    links=collections.defaultdict(list)
    for nid,role in base['roles'].items():
        a,b=role['through'];branch=role['branch']
        if not {a,b}<=scope:continue
        if b not in direct and a not in scoped:links[a].append((b,nid,'through'))
        if a not in direct and b not in scoped:links[b].append((a,nid,'through'))
        if (branch in scope and branch not in direct and root(branch)not in labelled_regions
            and root(branch)not in uncertain_regions and not {a,b}&scoped):
            links[a].append((branch,nid,'branch_default'));links[b].append((branch,nid,'branch_default'))
    values=collections.defaultdict(lambda:collections.defaultdict(dict))
    for seed in sorted(seeds,key=lambda s:(s['edge_id'],s['nominal_mm'],s['evidence_id'])):
        start=seed['edge_id'];value=seed['nominal_mm'];witness=seed['evidence_id']
        if seed.get('scope_only')is True:
            values[start][value][witness]=dict(evidence_id=witness,edge_path=[start],transfers=[],scope_only=True)
            continue
        todo=collections.deque([(start,[start],[])]);visited={start}
        while todo:
            current,path,transfers=todo.popleft()
            values[current][value][witness]=dict(evidence_id=witness,edge_path=path,transfers=transfers)
            for peer,nid,kind in sorted(links[current]):
                if peer in visited:continue
                visited.add(peer);todo.append((peer,path+[peer],transfers+[dict(node_id=nid,kind=kind,from_edge=current,to_edge=peer)]))
    records=[]
    for eid in sorted(scope):
        candidates=values.get(eid,{})
        has_branch=any(t['kind']=='branch_default'for rows in candidates.values()for r in rows.values()for t in r['transfers'])
        state=('reviewed_plan_DN_scope'if eid in scoped else 'direct_plan_DN'if eid in direct else 'T_branch_inherited_plan_DN'if len(candidates)==1 and has_branch
            else 'T_through_inherited_plan_DN'if len(candidates)==1 else 'conflict'if candidates else 'unresolved')
        records.append(dict(edge_id=eid,system=by[eid]['system'],nominal_mm=next(iter(candidates))if len(candidates)==1 else None,
            status=state,lineage=[dict(nominal_mm=v,evidence=[rows[w]for w in sorted(rows)])for v,rows in sorted(candidates.items())],
            scope_paths=copy.deepcopy(by[eid]['attribute_paths']),scope='source_checked_local_plan_pipe_paths_only',human_accepted=False))
    return dict(mode='complete_plan_native_T_DN_inheritance_v1',records=records,roles=base['roles'],
        source_sha256=source_hash,graph_sha256=graph_hash,direct_seed_boundaries=sorted(direct),
        reviewed_scopes_not_exported_as_annotation_seeds=sorted(scoped),
        inferred_branches_promoted_to_direct_boundaries=False,branch_labels_backflow_to_parent_through_arms=False,
        explicit_branch_annotation_overrides_its_checked_through_region=True,
        branch_default_regions_blocked_by_explicit_DN=sorted(eid for eid in scope if root(eid)in labelled_regions),
        branch_default_regions_with_unverified_frontiers=sorted(eid for eid in scope if root(eid)in uncertain_regions),
        physical_flow_direction_inferred=False,crossview_mapping_used_to_select_scope=False,
        graph_mutated=False,human_accepted=False)
