"""Inherited DN attribution kernel for independently checked topology scopes.

The attribution body is retained from the established three-anchor scope entry;
topology validation belongs to the caller. Historical entry files stay frozen.
Only an explicitly proved non-through frontier can be excluded from propagation.
"""
import copy,re
from confirm_crossview_paths import encode
from crossview_equipment_branch_inventory import index_graph
from plan_pipe_diameter_scopes import trim_frontier,guard_leader_bridges
from pipe_annotation_attributes import direct_diameters,parse_dn_annotation
from source_direct_dn_evidence import collect as direct_evidence
from native_dn_text_position import supported
from native_line_path_evidence import _on
from native_path_coverage_audit import audit as coverage_audit
from native_equipment_body import point_segment_distance
from diameter_tee_inheritance import infer


def attribute_checked_scope(doc,graph,group,texts,source_hash,graph_hash,F_handles,*,junctions,verified_taps,
        branch_frontier_edges=(),direct_collector=direct_evidence,path_auditor=coverage_audit,verified_nonpipe_annotation_strokes=()):
    nodes,edges,adj=index_graph(graph);branches=group['branches'];mains=set(group['main_edges']);taps=set(verified_taps)
    selected=mains|{b['edge_id'] for b in branches};branch_frontier_edges=set(branch_frontier_edges)
    if set(junctions)!=taps or not taps or len(selected)!=len(mains)+len(branches):raise ValueError('topology contract differs from DN scope')
    from native_line_f_diameter_evidence import collect as collect_line_F
    line_F=collect_line_F(doc,graph,group['line_F_frames'],source_hash,graph_hash) if group.get('line_F_frames') else dict(frames=[])
    recognized_F_texts={h for frame in line_F['frames'] for h in frame['text_handles']}
    recognized_F_strokes={h for frame in line_F['frames'] for h in frame['stroke_handles']}
    scalar_texts=[t for t in texts if t['handle'] not in recognized_F_texts]
    seeds=group['seeds'];layers=sorted({t['layer'] for t in texts})
    if any(s['text_handle'] in F_handles for s in seeds):raise ValueError('F label needs its ordering feature before inheritance')
    direct=direct_collector(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,text_layers=layers,selections=seeds),source_hash,graph_hash)
    observations={r['edge_id']:r for r in direct['observations']};projection=copy.deepcopy(graph);pe={e['edge_id']:e for e in projection['edges']};frontiers=[];frontier_ids=set()
    # Set iteration order varies across Python processes; it must not reorder
    # boundary evidence or the projection hash bound by native coverage.
    for tee in sorted(taps):
        for e in adj[tee]:
            if e['edge_id'] in selected:continue
            if e['start_node_id'] in taps and e['end_node_id'] in taps:raise ValueError('unselected main between checked Ts')
            observation=observations.get(e['edge_id']);cut,boundary,receipt=trim_frontier(graph,e,tee,observation['graph_projection'] if observation else None)
            pe[e['edge_id']].update(cut);projection.setdefault('boundary_anchors',[]).append(boundary);frontiers.append(receipt);frontier_ids.add(e['edge_id'])
    if not branch_frontier_edges<=frontier_ids:raise ValueError('excluded branch frontier is not an actual source frontier')
    propagating_edges=mains|(frontier_ids-branch_frontier_edges)
    if not set(observations)<=propagating_edges:raise ValueError('main seed outside checked through frontier')
    covered=sorted(selected|frontier_ids);projection_hash=__import__('hashlib').sha256(encode(projection)).hexdigest()
    coverage=path_auditor(doc,projection,dict(source_sha256=source_hash,graph_sha256=projection_hash,edges=covered),source_hash,projection_hash)
    if any(s['status']!='single_source_line_covers' for row in coverage['edges'] for s in row['segments']):raise ValueError('selected DN pipe path lacks unique native source coverage')
    paths=[path for eid in covered for path in pe[eid]['attribute_paths']]
    guard_leader_bridges(doc,scalar_texts,paths,recognized_F_strokes|set(verified_nonpipe_annotation_strokes))
    all_assigned,_=direct_diameters(scalar_texts,graph['edges'],set(),set(layers));originally_bound={r['text']['handle'] for r in all_assigned}|{r['source_text']['handle'] for r in direct['observations']}
    for t in scalar_texts:
        if re.search(r'DN',t['text'],re.I) and t['handle'] not in originally_bound and any(point_segment_distance(t['position'],a,b)<=3*t['height'] for path in paths for a,b in zip(path,path[1:])):raise ValueError('unattributed DN near scope cannot be treated as an absent change mark')
    # Every visible single DN on a checked path participates, including a new
    # branch annotation. Foreign/compound/ambiguous labels block this scope.
    assigned,pending=direct_diameters(scalar_texts,projection['edges'],set(),set(layers));allowed={o['source_text']['handle'] for o in observations.values()}
    for row in pending:
        if selected.intersection(row['candidate_edge_ids']):raise ValueError('ambiguous source DN overlaps selected paths')
    local={}
    for frame in line_F['frames']:
        for binding in frame['bindings']:
            if binding['edge_id'] in selected|frontier_ids:local.setdefault(binding['edge_id'],[]).append(binding)
    for row in assigned:
        if row['edge_id'] not in selected|frontier_ids:continue
        h=row['text']['handle'];native=doc.entitydb.get(h)
        if h in F_handles or native is None or not supported(native):raise ValueError('unsupported DN label transform/leader')
        if h in allowed:continue
        witness=next(r for r in coverage['edges'] if r['edge_id']==row['edge_id'])
        lines={w['source_handle'] for s in witness['segments'] for w in s['witnesses'] if _on(row['point'],s['start'],s['end'],.05)}
        if len(lines)!=1:raise ValueError('additional label native owner is ambiguous')
        extra=dict(text_handle=h,edge_id=row['edge_id'],source_line_handle=next(iter(lines)),expected_text=row['text']['text'])
        fresh=direct_collector(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,text_layers=layers,selections=[extra]),source_hash,graph_hash)['observations'][0]
        local.setdefault(row['edge_id'],[]).append(fresh)
    for t in scalar_texts:
        if not re.search(r'DN',t['text'],re.I) or parse_dn_annotation(t['text']) is not None:continue
        probe=dict(t,text='DN1');a,p=direct_diameters([probe],projection['edges'],set(),set(layers))
        if any((selected|frontier_ids).intersection(row['candidate_edge_ids']) for row in a+p):raise ValueError('compound/system-qualified DN needs explicit scope attribution')
    all_main=copy.deepcopy(observations)
    for eid,items in local.items():
        if eid in propagating_edges:
            if len({r['nominal_mm'] for r in items})!=1:raise ValueError('multiple DN values on an edge require subdivision')
            all_main[eid]=items[0]
    seed_rows=[dict(edge_id=eid,nominal_mm=o['nominal_mm'],evidence_id='source:'+o['source_text']['handle']) for eid,o in all_main.items()]
    if {edges[eid]['system'] for eid in all_main}!={'supply','return'}:raise ValueError('both services need independent main DN evidence')
    inferred=infer(projection,seed_rows,propagating_edges,taps);by={r['edge_id']:r for r in inferred};results=[]
    for eid in sorted(mains):
        row=by[eid];results.append(dict(edge_id=eid,system=edges[eid]['system'],nominal_mm=row['nominal_mm'],status='direct_plan_DN' if row['status']=='direct' else 'T_inherited_plan_DN' if row['status']=='inherited_candidate' else row['status'],
            lineage=row['candidates'],scope_paths=edges[eid]['attribute_paths'],scope='native_plan_drawn_pipe_paths_only',human_accepted=False))
    for branch in branches:
        eid=branch['edge_id'];direct_branch=local.get(eid,[])
        if direct_branch:
            values={o['nominal_mm'] for o in direct_branch};value=next(iter(values)) if len(values)==1 else None;status='direct_branch_DN_override' if value is not None else 'conflict'
            lineage=[dict(nominal_mm=o['nominal_mm'],evidence=[dict(evidence_id='source:'+o['source_text']['handle'],edge_path=[eid])]) for o in direct_branch]
        else:
            arms=[e['edge_id'] for e in adj[branch['tee']] if e['edge_id']!=eid];values=[by[a]['nominal_mm'] for a in arms];value=values[0] if None not in values and len(set(values))==1 else None
            status='T_inherited_plan_DN' if value is not None else 'main_DN_conflict_or_unknown'
            lineage=[]
            for arm in arms:
                for candidate in by[arm]['candidates']:
                    lineage.append(dict(nominal_mm=candidate['nominal_mm'],evidence=[dict(ev,edge_path=ev['edge_path']+[eid]) for ev in candidate['evidence']]))
        results.append(dict(edge_id=eid,system=branch['system'],nominal_mm=value,status=status,lineage=lineage,scope_paths=edges[eid]['attribute_paths'],scope='native_plan_drawn_pipe_paths_only',human_accepted=False))
    result=dict(group_id=group['group_id'],records=results,source_DN_observations=direct['observations'],additional_DN_observations=local,line_F_evidence=line_F,
        frontier_fragments=frontiers,read_only_projection_sha256=projection_hash,coverage=coverage,junctions=junctions,
        rule='through_SOURCE_LINE_first_branch_explicit_label_overrides_inheritance',outside_frontiers_traversed=False,graph_mutated=False,human_accepted=False)
    if branch_frontier_edges:result['non_through_branch_frontiers_excluded_from_main_inheritance']=sorted(branch_frontier_edges)
    return result
