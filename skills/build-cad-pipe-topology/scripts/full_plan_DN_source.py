"""Read complete local-plan DN evidence before any cross-view edge selection."""
import collections,json,math,re
from crossview_equipment_branch_inventory import index_graph,native_tee
from pipe_annotation_attributes import direct_diameters,parse_dn_annotation,contact
from plan_pipe_diameter_scopes import catalog,guard_leader_bridges
from source_direct_dn_evidence import collect as direct_collect
from batch_native_path_coverage import collect as path_collect
from native_line_path_evidence import LAYERS,_on
from discover_native_component_DN import discover as component_collect
from full_plan_DN_inheritance import infer


def annotation_inventory(doc,graph,source_hash,graph_hash):
    ids=[e['edge_id']for e in graph['edges']if e['system']in LAYERS]
    texts,inventory=catalog(doc,graph,ids,source_hash,graph_hash)
    components=component_collect(doc,graph,source_hash,graph_hash)
    excluded=set(components['candidate_component_DN_text_handles'])|set(inventory['F_text_handles'])
    scalar=[t for t in texts if t['handle']not in excluded];layers={t['layer']for t in texts}
    assigned,pending=direct_diameters(scalar,graph['edges'],set(),layers)
    unparsed=[dict(t,text='DN1')for t in scalar if re.search('DN',t['text'],re.I)and parse_dn_annotation(t['text'])is None]
    extra_a,extra_p=direct_diameters(unparsed,graph['edges'],set(),layers)
    blocked=collections.defaultdict(list);seeds=[];observations=[];exceptions=[];edges={e['edge_id']:e for e in graph['edges']}
    for reason,rows in [('ambiguous_scalar_DN',pending),('compound_or_named_DN_needs_its_native_scope',extra_a+extra_p)]:
        for row in rows:
            for eid in row['candidate_edge_ids']:blocked[eid].append(dict(reason=reason,text_handle=row['text']['handle']))
    for row in assigned:
        eid=row['edge_id'];edge=edges[eid];point=row['point'];hits=[]
        for handle in edge.get('source_handles',[]):
            line=doc.entitydb.get(handle)
            if (line is not None and line.dxftype()=='LINE'and line in doc.modelspace()and line.dxf.layer==LAYERS.get(edge['system'])
                and _on(point,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)):hits.append(handle)
        spec=dict(text_handle=row['text']['handle'],edge_id=eid,expected_text=row['text']['text'])
        if len(hits)!=1:
            reason=dict(reason='native_scalar_pipe_owner_missing_or_multiple',selection=spec);exceptions.append(reason);blocked[eid].append(reason);continue
        spec['source_line_handle']=hits[0]
        try:
            proof=direct_collect(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,text_layers=sorted(layers),selections=[spec]),source_hash,graph_hash)
        except ValueError as exc:
            reason=dict(reason='native_scalar_binding_not_proved',detail=str(exc),selection=spec);exceptions.append(reason);blocked[eid].append(reason);continue
        item=proof['observations'][0];observations.append(item)
        seeds.append(dict(edge_id=eid,nominal_mm=item['nominal_mm'],evidence_id='source:'+row['text']['handle']))
    return dict(texts=texts,annotation_inventory=inventory,component_DN=components,assigned=assigned,pending=pending,
        unparsed_candidates=extra_a+extra_p,blocked_edges=dict(blocked),seeds=seeds,direct_observations=observations,exceptions=exceptions)


def leader_barriers(doc,graph,annotation,initial_scope):
    by={e['edge_id']:e for e in graph['edges']};scope=set(initial_scope);blocked={};issues=[]
    consumed=set(annotation['component_DN']['consumed_DN_text_handles'])
    texts=[t for t in annotation['texts']if t['handle']not in consumed]
    while scope:
        try:
            guard_leader_bridges(doc,texts,[p for eid in sorted(scope)for p in by[eid]['attribute_paths']],annotation['component_DN']['consumed_leader_handles'])
            break
        except ValueError as exc:
            message=str(exc)
            if '; use the F/leader feature: 'not in message:
                issues.append(dict(reason='unsupported_annotation_geometry',detail=message))
                for eid in scope:blocked[eid]=dict(reason='annotation_coverage_not_established',detail=message)
                scope.clear();break
            evidence=json.loads(message.split('; use the F/leader feature: ',1)[1]);segments=evidence['segments']
            affected={eid for eid in scope if any(contact(*segment,a,b)is not None for segment in segments for path in by[eid]['attribute_paths']for a,b in zip(path,path[1:]))}
            if not affected:raise ValueError('native leader guard did not identify its affected path')from exc
            for eid in affected:blocked[eid]=dict(reason='unclassified_native_DN_leader',evidence=evidence)
            scope-=affected;issues.append(dict(reason='unclassified_native_DN_leader',edges=sorted(affected),evidence=evidence))
    return blocked,issues


def _has_through(proof):
    rays=proof.get('junctions',[{}])[0].get('source_rays',[]);pairs=0
    for i,a in enumerate(rays):
        for b in rays[i+1:]:
            u,v=a.get('direction',[]),b.get('direction',[])
            if len(u)!=2 or len(v)!=2 or min(math.hypot(*u),math.hypot(*v))<=1e-6:return False
            if sum(x*y for x,y in zip(u,v))/(math.hypot(*u)*math.hypot(*v))<=-math.cos(math.radians(1)):pairs+=1
    return len(rays)==3 and pairs==1


def collect(doc,graph,source_hash,graph_hash,reviewed_seeds=(),announce=lambda x:None,circle_policy=None):
    if graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('full-plan DN source differs from local topology')
    nodes,edges,adj=index_graph(graph);annotation=annotation_inventory(doc,graph,source_hash,graph_hash)
    announce(f'Complete plan scalar labels: {len(annotation["seeds"])}; component captions: {len(annotation["component_DN"]["records"])}')
    coverage={};coverage_errors={};eligible=set()
    for eid,edge in sorted(edges.items()):
        if edge['system']not in LAYERS:coverage_errors[eid]='unknown_system';continue
        try:proof=path_collect(doc,graph,[eid],source_hash,graph_hash)
        except ValueError as exc:coverage_errors[eid]=str(exc);continue
        coverage[eid]=proof
        segments=[s for row in proof['edges']for s in row['segments']]
        if segments and all(s['status']=='single_source_line_covers'for s in segments):eligible.add(eid)
        else:coverage_errors[eid]='source_path_missing_or_multiple_LINE_witnesses'
    blocked={eid:list(rows)for eid,rows in annotation['blocked_edges'].items()}
    leaders,leader_issues=leader_barriers(doc,graph,annotation,eligible)
    for eid,row in leaders.items():blocked.setdefault(eid,[]).append(row)
    eligible-=set(blocked);junctions={};junction_errors={}
    waves={r['tee_id']:r for r in graph.get('sourceWaveMainCohort',{}).get('records',[])}
    for nid,node in sorted(nodes.items()):
        if node['node_type']not in ('tee','physical_junction'):continue
        try:
            if nid in waves:
                from rebuild_wave_cohort_crossview_batch import wave_branch
                row=waves[nid];proof=wave_branch(doc,graph,row['equipment_id'],row['system'],source_hash,graph_hash)['junction_evidence']
            elif node.get('expert_confirmed_circle')or node.get('calibrated_duplicate_circle')or nid in (circle_policy or {}).get('external_cases',{}):
                from native_inherited_duplicate_circle_evidence import collect as inherited_circle
                proof=inherited_circle(doc,graph,nid,source_hash,graph_hash,circle_policy)
            else:proof=native_tee(doc,graph,nid,source_hash,graph_hash)
            if not _has_through(proof):raise ValueError('native T has no unique source through pair')
            junctions[nid]=proof
        except ValueError as exc:junction_errors[nid]=str(exc)
    seeds=[s for s in annotation['seeds']if s['edge_id']in eligible]
    for seed in reviewed_seeds:
        if seed['edge_id']not in eligible:raise ValueError('explicit reviewed DN scope blocked by fresh native evidence')
        seeds.append(seed)
    announce(f'Native source-qualified T roles: {len(junctions)}; checked inheritance edges: {len(eligible)}')
    result=infer(graph,seeds,eligible,junctions,source_hash,graph_hash)
    rows=result['records'];present={r['edge_id']for r in rows}
    for eid,edge in sorted(edges.items()):
        if eid in present:continue
        rows.append(dict(edge_id=eid,system=edge['system'],nominal_mm=None,status='annotation_blocked'if eid in blocked else 'source_scope_unverified',
            scope_paths=edge.get('attribute_paths',[]),lineage=[],human_accepted=False))
    result.update(annotation_evidence=annotation,source_path_evidence=coverage,source_path_exceptions=coverage_errors,
        annotation_barriers=blocked,annotation_leader_issues=leader_issues,source_T_exceptions=junction_errors,
        direct_seed_evidence=seeds,counts=dict(graph_edges=len(edges),source_qualified_edges=len(eligible),native_T_roles=len(junctions),
            known_DN_edges=sum(r['nominal_mm']is not None for r in rows),statuses=dict(collections.Counter(r['status']for r in rows))),
        graph_mutated=False,physical_lengths_assigned=0,crossview_subset_used_for_scope=False,hil_ready=False)
    return result
