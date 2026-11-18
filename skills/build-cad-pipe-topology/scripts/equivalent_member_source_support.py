"""Read coincident CAD witnesses inside an independently identified pipe member.

This never deduplicates the CAD or decides how many physical pipes its copies
represent. Complete native circle/label cohorts and an already qualified axis
chain identify the demanded member. The original T readers see the original
document; only per-path geometry readers get an explicit private observation.
"""
import copy,hashlib,math,types
from confirm_crossview_paths import encode
from native_line_path_evidence import LAYERS,_on
from crossview_equipment_branch_inventory import index_graph,service_route,native_tee
from batch_native_path_coverage import collect as original_coverage
from pipe_annotation_attributes import source_texts
from native_canonical_main_family_view import project as canonical_project,CanonicalLineDocument
import anchor_bounded_main_paths as original

MODE='complete_cohort_member_equivalent_source_support_v1'
TOL=.05

def _xyz(line):return [list(line.dxf.start),list(line.dxf.end)]
def _same(a,b):
    p,q=_xyz(a),_xyz(b)
    return (max(math.dist(x,y)for x,y in zip(p,q))<=TOL or max(math.dist(x,y)for x,y in zip(p,q[::-1]))<=TOL)
def _style(line):
    return tuple(line.dxf.get(k,v)for k,v in(('layer',''),('color',256),('true_color',None),('linetype','BYLAYER'),('lineweight',-1),('ltscale',1.),('extrusion',(0.,0.,1.))))
def _entity(doc,h,system):
    e=doc.entitydb.get(h)
    if e is None or e not in doc.modelspace()or e.dxftype()!='LINE'or e.dxf.layer!=LAYERS[system]or any(not math.isfinite(v)for p in _xyz(e)for v in p):raise ValueError('equivalent member source LINE differs')
    return e
def _z(line,p):
    a,b=_xyz(line);v=[b[i]-a[i]for i in(0,1)];den=sum(x*x for x in v)
    if den<=TOL*TOL:raise ValueError('degenerate projected member source')
    t=sum((p[i]-a[i])*v[i]for i in(0,1))/den
    return a[2]+t*(b[2]-a[2])

def qualify_cohort(docs,graphs,mapping,provider,floor,system,handles,hashes,plan_T_reader):
    """Require every native circle and its unique equipment in both views."""
    doc=docs['plan'];plan,axis=graphs['plan'],graphs['iso']
    if system not in LAYERS or type(floor)is not int or len(handles)<2 or len(set(handles))!=len(handles):raise ValueError('explicit duplicate family and service required')
    lines=[_entity(doc,h,system)for h in handles];line=lines[0];a,b=[p[:2]for p in _xyz(line)]
    if any(not _same(line,l)or _style(line)!=_style(l)for l in lines[1:]):raise ValueError('native family is not identical in XYZ and style')
    all_handles={l.dxf.handle for l in doc.modelspace().query('LINE')if l.dxf.layer==LAYERS[system]and _same(line,l)}
    if all_handles!=set(handles):raise ValueError('native duplicate family population incomplete')
    pn,pe,pa=index_graph(plan);an,ae,aa=index_graph(axis)
    circles=[c for c in doc.modelspace().query('CIRCLE')if _on(list(c.dxf.center)[:2],a,b,TOL)]
    if len(circles)<3:raise ValueError('at least three independent native circle branches required')
    text_index={v:{}for v in graphs}
    for view in graphs:
        for t in source_texts(docs[view],view,hashes[view]['source_sha256']):text_index[view].setdefault(t['text'].strip(),[]).append(t)
    rows=[];equipment_used=set()
    for c in circles:
        point=list(c.dxf.center)[:2]
        hits=[n for n in plan['nodes']if n.get('node_type')in original.TYPES and n.get('floor')==floor and n.get('system')==system and math.dist(point,[n['x'],n['y']])<=TOL]
        if c.dxf.layer!=LAYERS[system]or len(hits)!=1 or not math.isfinite(c.dxf.radius)or c.dxf.radius<=0:raise ValueError('unassigned or opposite-service native circle on member')
        n=hits[0];nid=n['node_id'];aid=mapping.get(nid)
        if aid not in an or len(pa[nid])!=3 or len(aa[aid])!=3:raise ValueError('complete member circle lacks a unique existing axis anchor')
        candidates=[]
        for eq in plan['nodes']:
            if eq.get('node_type')not in('equipment','physical_equipment')or eq.get('floor')!=floor:continue
            route=service_route(plan,eq['node_id'],system)
            if route.get('status')=='unique_graph_service_to_T'and route.get('tee')==nid:candidates.append((eq,route))
        if len(candidates)!=1:raise ValueError('member circle equipment branch is not unique')
        eq,route=candidates[0];eid=eq['node_id'];other=service_route(axis,eid,system)if eid in an else{}
        if eid in equipment_used or other.get('status')!='unique_graph_service_to_T'or other.get('tee')!=aid:raise ValueError('equipment identity or axis branch disagrees')
        labels={v:text_index[v].get(eid,[])for v in graphs}
        if any(not x for x in labels.values()):raise ValueError('independent native equipment labels missing')
        equipment_used.add(eid)
        pj=plan_T_reader(doc,plan,nid,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
        aj=native_tee(docs['iso'],axis,aid,hashes['iso']['source_sha256'],hashes['iso']['graph_sha256'])
        rows.append(dict(circle_handle=c.dxf.handle,plan_node=nid,axis_node=aid,equipment_id=eid,plan_branch=route,axis_branch=other,native_labels=labels,native_junctions=dict(plan=pj,iso=aj),position=point))
    remaining=[n['node_id']for n in plan['nodes']if n.get('floor')==floor and n.get('system')==system and n.get('node_type')in original.TYPES and _on([n['x'],n['y']],a,b,TOL)and n['node_id']not in{r['plan_node']for r in rows}]
    if remaining:raise ValueError('graph branch population exceeds checked native circles')
    vector=[b[i]-a[i]for i in(0,1)];rows.sort(key=lambda r:sum((r['position'][i]-a[i])*vector[i]for i in(0,1)))
    prior={r['edge_id']:r for r in provider['records']};links=[]
    for left,right in zip(rows,rows[1:]):
        pids=[e['edge_id']for e in pa[left['plan_node']]if right['plan_node']in(e['start_node_id'],e['end_node_id'])and e['system']==system]
        aids=[e['edge_id']for e in aa[left['axis_node']]if right['axis_node']in(e['start_node_id'],e['end_node_id'])and e['system']==system]
        if len(pids)!=1 or len(aids)!=1:raise ValueError('complete two-view member chain is interrupted or parallel')
        old=prior.get(aids[0],{});observations=old.get('correspondence_observations',[])
        if not old.get('has_existing_correspondence')or old.get('classification')!='horizontal_only'or not any(o.get('domain')=='ordinary_local_graph'and o.get('plan_edges')==pids for o in observations):raise ValueError('native member chain lacks qualified prior correspondence')
        cov=original_coverage(docs['iso'],axis,aids,hashes['iso']['source_sha256'],hashes['iso']['graph_sha256'])
        if any(s['status']!='single_source_line_covers'for e in cov['edges']for s in e['segments']):raise ValueError('axis cohort member source is ambiguous')
        links.append(dict(plan_edge=pids[0],axis_edge=aids[0],prior_observations=copy.deepcopy(observations),native_axis_path_coverage=cov))
    canonical=set(handles)
    for link in links:canonical.intersection_update(pe[link['plan_edge']].get('source_handles',[]))
    if len(canonical)!=1:raise ValueError('member cohort has no consistent original graph provenance owner')
    anchors={r['plan_node']:dict(evidence=r['native_junctions']['plan'],branch_edges=r['plan_branch']['edges'])for r in rows}
    _,_,basis=canonical_project(doc,plan,{r['equipment_id']:r['plan_node']for r in rows},system,floor,dict(canonical_source_handle=next(iter(canonical)),coincident_source_family=handles),anchors,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256'])
    key=[hashes,floor,system,sorted(handles),[(r['plan_node'],r['axis_node'],r['equipment_id'])for r in rows]]
    return dict(mode=MODE,scope_id='COHORT-MEMBER:'+hashlib.sha256(encode(key)).hexdigest()[:20],floor=floor,system=system,source_family=sorted(handles),native_endpoints=_xyz(line),native_circle_population=len(circles),branches=rows,links=links,inherited_canonical_reader_evidence=basis,source_hashes=copy.deepcopy(hashes),source_entity_physical_identity_resolved=False,physical_pipe_count_inferred=False,DN_used_for_matching=False,raw_graph_mutated=False,human_accepted=False)

def equivalent_support(doc,segment,system,cohorts,compound_handles):
    """Qualify only the common observed segment; tails remain in the raw CAD."""
    witnesses=segment['witnesses'];handles=[w['source_handle']for w in witnesses]
    if len(handles)<2 or len(set(handles))!=len(handles)or any(w['scope']!='modelspace'for w in witnesses):raise ValueError('explicit modelspace witness family required')
    lines=[_entity(doc,h,system)for h in handles];a,b=segment['start'],segment['end']
    if set(handles)&set(compound_handles):raise ValueError('compound carrier needs member-specific reconstruction first')
    for l in lines:
        p,q=[p[:2]for p in _xyz(l)]
        if not _on(a,p,q,TOL)or not _on(b,p,q,TOL)or _style(l)!=_style(lines[0])or max(abs(_z(l,p)-_z(lines[0],p))for p in(a,b))>TOL:raise ValueError('witness geometry, XYZ or style differs on selected interval')
    qualified=[]
    for c in cohorts:
        if c['mode']!=MODE or c['system']!=system:continue
        family=set(c['source_family'])
        if set(handles)<=family:qualified.append((c,'coincident_native_main_interval'));continue
        main=doc.entitydb[c['source_family'][0]];ma,mb=_xyz(main)
        # A cap is supported only at a native common bend. Its overlapping
        # subinterval is read; unequal source tails are never removed/added.
        bends=[p for p in(ma,mb)if all(any(math.dist(p,q)<=TOL for q in _xyz(l))for l in lines)]
        if len(bends)!=1:continue
        capvec=[lines[0].dxf.end[i]-lines[0].dxf.start[i]for i in(0,1)];mainvec=[mb[i]-ma[i]for i in(0,1)]
        if abs(sum(x*y for x,y in zip(capvec,mainvec)))>1e-6*math.hypot(*capvec)*math.hypot(*mainvec):continue
        qualified.append((c,'coincident_cap_common_interval_at_native_member_bend'))
    if len(qualified)!=1:raise ValueError('equivalent support lacks one independent complete member cohort')
    c,kind=qualified[0]
    longest=max(math.dist(*_xyz(l))for l in lines)
    chosen=max((l for l in lines if longest-math.dist(*_xyz(l))<=TOL),key=lambda l:l.dxf.handle)
    return dict(scope_id=c['scope_id'],kind=kind,system=system,segment=[copy.deepcopy(a),copy.deepcopy(b)],all_original_witnesses=copy.deepcopy(witnesses),representative_observation_handle=chosen.dxf.handle,excluded_from_private_reader=sorted(set(handles)-{chosen.dxf.handle}),native_endpoints={l.dxf.handle:_xyz(l)for l in lines},original_tails_unchanged=True,source_entity_physical_identity_resolved=False,physical_pipe_count_inferred=False)

ObservationDocument=CanonicalLineDocument

def member_coverage(doc,graph,ids,source_hash,graph_hash,cohorts,compound_handles):
    if any(c.get('source_hashes',{}).get('plan')!=dict(source_sha256=source_hash,graph_sha256=graph_hash)for c in cohorts):raise ValueError('member source observation used on another graph or document')
    selected={e['edge_id']:e for e in graph['edges']}
    if any(set(selected[eid].get('source_handles',[]))&set(compound_handles)for eid in ids):raise ValueError('compound carrier path requires member reconstruction before ordinary bounded mapping')
    original_result=original_coverage(doc,graph,ids,source_hash,graph_hash);by={e['edge_id']:e for e in graph['edges']};result=copy.deepcopy(original_result);proof=[]
    for edge in result['edges']:
        eid=edge['edge_id'];original_segments=copy.deepcopy(edge['segments']);projected=[]
        for pi,path in enumerate(by[eid]['attribute_paths']):
            segments=[s for s in original_segments if s.get('path_index',0)==pi];supports=[]
            for s in segments:
                if s['status']=='single_source_line_covers':continue
                if s['status']!='ambiguous_multiple_witnesses':raise ValueError('member observation never fills missing source geometry')
                supports.append(equivalent_support(doc,s,edge['system'],cohorts,compound_handles))
            excluded={h for s in supports for h in s['excluded_from_private_reader']}
            private=dict(graph,edges=[dict(by[eid],attribute_paths=[copy.deepcopy(path)])]);digest=hashlib.sha256(encode(private)).hexdigest()
            observed=original_coverage(ObservationDocument(doc,excluded),private,[eid],source_hash,digest)['edges'][0]
            if any(s['status']!='single_source_line_covers'for s in observed['segments']):raise ValueError('private member observation remains ambiguous')
            for s in observed['segments']:
                if len(by[eid]['attribute_paths'])>1:s['path_index']=pi
                projected.append(s)
            proof.append(dict(edge_id=eid,path_index=pi,reading_graph_sha256=digest,excluded_handles=sorted(excluded),equivalent_support=supports,original_segments=segments))
        edge['segments']=projected;edge['source_covered_drawing_length']=sum(s['drawing_length']for s in projected);edge['unverified_drawing_length']=0
    result.update(equivalent_member_observations=proof,reading_scope='member_bound_equivalent_geometry_observation_not_source_entity_identity',original_source_audit=original_result,source_document_mutated=False,physical_pipe_count_inferred=False)
    return result

def bounded_apply(docs,graphs,parent,floor,components,hashes,angles,junction_readers,cohorts,compound_handles):
    def selected_coverage(doc,graph,ids,sh,gh):
        if graph is not graphs['plan']:return original_coverage(doc,graph,ids,sh,gh)
        return member_coverage(doc,graph,ids,sh,gh,cohorts,compound_handles)
    namespace=dict(original.prove.__globals__,coverage=selected_coverage)
    prove=types.FunctionType(original.prove.__code__,namespace,original.prove.__name__,original.prove.__defaults__,original.prove.__closure__)
    apply_globals=dict(original.apply.__globals__,prove=prove)
    apply=types.FunctionType(original.apply.__code__,apply_globals,original.apply.__name__,original.apply.__defaults__,original.apply.__closure__)
    result=apply(docs,graphs,parent,floor,components,hashes,angles,junction_readers)
    for group in result['groups']:
        old=group['mapping_id'];group['mapping_id']='MEMBER-'+hashlib.sha256(encode([hashes,group['system'],group['plan']['edges'],group['iso']['edges']])).hexdigest()[:20]
        for row in result['records']:row['source_group_ids']=[group['mapping_id']if x==old else x for x in row['source_group_ids']]
    for row in result['records']:row['mapping_id']='MEMBER-INTERVAL-'+hashlib.sha256(encode([hashes,row['plan_edges'],row['iso_edges']])).hexdigest()[:20]
    result.update(mode=MODE,complete_member_cohorts=copy.deepcopy(cohorts),original_bounded_rule_code_reused=True,native_junctions_read_original_document=True,source_entities_deduplicated=False,physical_pipe_count_inferred=False)
    return result
