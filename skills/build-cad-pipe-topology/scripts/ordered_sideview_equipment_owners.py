"""Use complete native rows and independent owners to resolve strip collisions.

This extends logical equipment ownership only. Native source paths, components,
unknown connector lengths and prior independent owner records are conserved.
No nearest-body choice, DN matching or label-number sorting is permitted.
"""
import collections,copy,hashlib,math,re
from confirm_crossview_paths import encode
from canonicalize_confirmed_sideviews import source_expression_context,verify_tee,DECISION
from calibrated_equipment_interface_ownership import equipment,native_interface,projected_candidates
from native_sideview_equipment_branch_evidence import validate_owner,collect as detail_T
from native_line_path_evidence import LAYERS
from edge_endpoint_semantics import reconcile
MODE='complete_native_row_order_sideview_ownership_v1'
TOL=.05

def solve_order(pairs,bodies,fixed,minimum_controls=3):
    if type(minimum_controls)is not int or minimum_controls<3:raise ValueError('at least three independent row anchors are required')
    if len(pairs)!=len(bodies)or len(pairs)<minimum_controls+1:raise ValueError('complete row cardinality is not established')
    if len({r['pair_id']for r in pairs})!=len(pairs)or len({r['equipment_id']for r in bodies})!=len(bodies):raise ValueError('duplicate row identity')
    p=sorted(pairs,key=lambda r:r['station']);b=sorted(bodies,key=lambda r:r['station'])
    if any(y['station']-x['station']<=TOL for rows in(p,b)for x,y in zip(rows,rows[1:])):raise ValueError('row order is ambiguous')
    if not set(fixed)<={r['pair_id']for r in p}or len(fixed)<minimum_controls or len(set(fixed.values()))!=len(fixed):raise ValueError('insufficient independent row anchors')
    mapping={x['pair_id']:y['equipment_id']for x,y in zip(p,b)}
    if any(mapping[k]!=v for k,v in fixed.items()):raise ValueError('native row order contradicts independent owners')
    return dict(mapping=mapping,fixed_owners=copy.deepcopy(fixed),minimum_controls=minimum_controls,unresolved_pair_ids=[r['pair_id']for r in p if r['pair_id']not in fixed],
        method='complete_native_cohort_monotone_bijection_checked_against_independent_owners',DN_used=False,nearest_body_used=False,equipment_label_numbers_used=False)

def collect(doc,graph,source_hash,graph_hash,minimum_controls=3):
    root=graph.get('sourceSideviewEquipmentOwnership',{});state=graph.get('confirmedSideviewCanonicalization',{})
    if graph.get('metadata',{}).get('source_sha256')!=source_hash or root.get('source_sha256')!=source_hash or state.get('source_sha256')!=source_hash or graph.get('sourceOrderedSideviewEquipmentOwnership'):raise ValueError('ordered owner source or stage differs')
    context=source_expression_context(graph);nodes={n['node_id']:n for n in context['nodes']};edges={e['edge_id']:e for e in context['edges']};bodies=equipment(doc,graph);groups=collections.defaultdict(list)
    for a in state['records']:
        if a.get('answer',{}).get('decision')!=DECISION or not re.fullmatch('[0-9a-f]{64}',a.get('pair_sha256',''))or a.get('physical_length')!='unknown'or a.get('projected_main_identity')!='not_inferred':raise ValueError('original confirmed alias scope changed')
        groups[(a['question_id'],a['pair_sha256'])].append(a)
    records=[]
    for (qid,pair_hash),aliases in sorted(groups.items()):
        if len(aliases)!=2 or {a['system']for a in aliases}!={'supply','return'}:raise ValueError('complete confirmed service pair required')
        native=[native_interface(doc,nodes[a['abbreviated_interface']],edges[a['abbreviated_edge']])for a in aliases]
        u=native[0]['pipe']['direction'];v=[-u[1],u[0]];spacing=math.dist(native[0]['point'],native[1]['point'])
        if max(abs(u[0]),abs(u[1]))<1-1e-8 or sum(x*y for x,y in zip(u,native[1]['pipe']['direction']))<1-1e-8 or not 100<=spacing<=600 or native[0]['floor']!=native[1]['floor']:raise ValueError('unsupported native paired row orientation')
        dot=lambda p,w:sum(x*y for x,y in zip(p,w));level=sum(dot(n['point'],u)for n in native)/2
        if any(abs(dot(n['point'],u)-level)>TOL for n in native):raise ValueError('native pair normal levels differ')
        owned=[e for e in graph['edges']if e.get('source_sideview_equipment_interface',{}).get('question_id')==qid]
        owner=None
        if owned:
            if len(owned)!=2 or {e['system']for e in owned}!={'supply','return'}:raise ValueError('incomplete previous independent owner pair')
            metas=[validate_owner(graph,e,source_hash)for e in owned];owners={m['equipment_id']for m in metas}
            if len(owners)!=1 or {m['pair_sha256']for m in metas}!={pair_hash}:raise ValueError('previous pair identity differs')
            owner=next(iter(owners));max_gap=max(m['body_evidence']['normal_gap']for m in metas)+TOL
            hits,reason=projected_candidates(native,bodies,max_gap)
            if reason or len(hits)!=1 or hits[0]['equipment_id']!=owner:raise ValueError('independent native projection control no longer holds')
            for e in owned:detail_T(doc,graph,e['source_sideview_equipment_interface']['source_alias']['native_detail_tee']['tee'],source_hash,graph_hash)
        records.append(dict(pair_id=qid,pair_sha256=pair_hash,aliases=copy.deepcopy(aliases),native_interfaces=native,floor=native[0]['floor'],direction=u,
            normal_level=level,spacing=spacing,station=sum(dot(n['point'],v)for n in native)/2,independent_owner=owner))
    # Full row scope is discovered from all confirmed pairs before solving it.
    cohorts=[];remaining=list(records)
    while remaining:
        first=remaining[0];rr=[r for r in remaining if r['floor']==first['floor']and math.dist(r['direction'],first['direction'])<1e-8 and abs(r['normal_level']-first['normal_level'])<=TOL and abs(r['spacing']-first['spacing'])<=TOL]
        remaining=[r for r in remaining if r not in rr];fixed={r['pair_id']:r['independent_owner']for r in rr if r['independent_owner']}
        if not any(r['independent_owner']is None for r in rr):continue
        if len(fixed)<minimum_controls:raise ValueError('row lacks independent native owner controls')
        u=first['direction'];v=[-u[1],u[0]];dot=lambda p,w:sum(x*y for x,y in zip(p,w));controls=[bodies[k]for k in fixed.values()]
        def normal_range(body):return sorted({dot([x,y],u)for x in body['bounds'][:2]for y in body['bounds'][2:]})
        template=normal_range(controls[0])
        if any(any(abs(a-b)>TOL for a,b in zip(normal_range(c),template))for c in controls):raise ValueError('independent controls do not describe one native equipment row')
        cohort=[dict(equipment_id=k,station=dot([b['node']['x'],b['node']['y']],v),native_body=copy.deepcopy(b))for k,b in bodies.items()if b['node'].get('floor')==first['floor']and len(b['source_caption_handles'])==1 and len(normal_range(b))==len(template)and all(abs(a-c)<=TOL for a,c in zip(normal_range(b),template))]
        if not cohort:raise ValueError('native equipment row empty')
        lo=min(dot([x,y],v)for b in cohort for x in b['native_body']['bounds'][:2]for y in b['native_body']['bounds'][2:]);hi=max(dot([x,y],v)for b in cohort for x in b['native_body']['bounds'][:2]for y in b['native_body']['bounds'][2:])
        expected={i['circle_handle']for r in rr for i in r['native_interfaces']};radii={round(i['radius'],6)for r in rr for i in r['native_interfaces']}
        if len(radii)!=1:raise ValueError('native row glyph sizes differ')
        actual={c.dxf.handle for c in doc.modelspace().query('CIRCLE')if c.dxf.layer in LAYERS.values()and abs(c.dxf.radius-next(iter(radii)))<=TOL and abs(dot(list(c.ocs().to_wcs(c.dxf.center))[:2],u)-first['normal_level'])<=TOL and lo-TOL<=dot(list(c.ocs().to_wcs(c.dxf.center))[:2],v)<=hi+TOL}
        if actual!=expected:raise ValueError('complete native row glyph population differs; do not hide extra or missing pairs')
        result=solve_order(rr,cohort,fixed,minimum_controls);result.update(pairs=rr,equipment=cohort,native_row_circle_handles=sorted(actual),floor=first['floor'],source_row_normal_level=first['normal_level']);cohorts.append(result)
    if not cohorts:raise ValueError('no unresolved complete native row')
    selected=[dict(pair=next(p for p in c['pairs']if p['pair_id']==qid),equipment=next(e for e in c['equipment']if e['equipment_id']==c['mapping'][qid]),cohort_index=index)for index,c in enumerate(cohorts)for qid in c['unresolved_pair_ids']]
    if len({s['equipment']['equipment_id']for s in selected})!=len(selected):raise ValueError('row cohorts claim the same equipment')
    return dict(mode=MODE,source_sha256=source_hash,graph_sha256=graph_hash,cohorts=cohorts,selected=selected,old_owner_root_sha256=hashlib.sha256(encode(root)).hexdigest(),sideview_alias_root_sha256=hashlib.sha256(encode(state)).hexdigest(),graph_mutated=False,physical_ports_verified=False,physical_lengths_assigned=0,human_accepted=False)

def apply(doc,graph,evidence,source_hash,graph_hash):
    if evidence['mode']!=MODE or evidence['source_sha256']!=source_hash or evidence['graph_sha256']!=graph_hash or hashlib.sha256(encode(graph['sourceSideviewEquipmentOwnership'])).hexdigest()!=evidence['old_owner_root_sha256']:raise ValueError('ordered ownership evidence changed')
    if evidence.get('graph_mutated')is not False or evidence.get('physical_lengths_assigned')!=0 or evidence.get('human_accepted')is not False or hashlib.sha256(encode(graph['confirmedSideviewCanonicalization'])).hexdigest()!=evidence.get('sideview_alias_root_sha256'):raise ValueError('ordered alias or unknown physical scope changed')
    out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};edges={e['edge_id']:e for e in out['edges']};root=out['sourceSideviewEquipmentOwnership'];retired={};records=[];claimed=set();proof_hash=hashlib.sha256(encode(evidence)).hexdigest()
    for row in evidence['selected']:
        cohort=evidence['cohorts'][row['cohort_index']];pair_id=row['pair']['pair_id']
        if row['pair']not in cohort['pairs']or row['equipment']not in cohort['equipment']or pair_id not in cohort['unresolved_pair_ids']or cohort['mapping'].get(pair_id)!=row['equipment']['equipment_id']or solve_order(cohort['pairs'],cohort['equipment'],cohort['fixed_owners'],cohort['minimum_controls'])['mapping']!=cohort['mapping']:raise ValueError('selected ordered owner is not the complete independently anchored row solution')
        pair=row['pair'];body=row['equipment']['native_body'];did=row['equipment']['equipment_id'];owner=nodes[did]
        if any(did in(e.get('start_node_id'),e.get('end_node_id'))for e in graph['edges'])or owner.get('node_type')!='equipment':raise ValueError('ordered target already has a logical owner')
        for alias in pair['aliases']:
            eid=alias['canonical_edge'];nid=alias['canonical_interface'];edge=edges[eid]
            if alias['canonical_interface_kind']!='node'or nid not in nodes or nodes[nid].get('node_type')!='virtual_equipment'or eid in claimed or edge.get('source_sideview_equipment_interface'):raise ValueError('new ordered owner requires a unique unresolved canonical node')
            if sum(nid in(e.get('start_node_id'),e.get('end_node_id'))for e in graph['edges'])!=1:raise ValueError('canonical interface is not terminal')
            sides=[s for s in('start','end')if edge.get(s+'_node_id')==nid]
            if len(sides)!=1 or edge['system']!=alias['system']or nodes[nid].get('floor')!=owner.get('floor'):raise ValueError('ordered endpoint service or floor differs')
            side=sides[0];tee,checked=verify_tee(doc,graph,edge,nid)
            if checked['attribute_paths']!=edge['attribute_paths']:raise ValueError('new owner source path needs normalization')
            original=copy.deepcopy(nodes[nid]);prior={k:copy.deepcopy(edge[k])for k in('path_length_scope','drawing_path_length','physical_length_status','physical_length','path_length_complete')if k in edge}
            if edge.get('equipment_connector_length_mm')is not None or edge.get('physical_length')not in(None,'unknown'):raise ValueError('known physical connector requires reconciliation')
            endpoint=dict(canonical_edge=eid,canonical_interface=nid,canonical_interface_kind='node',canonical_side=side,system=alias['system'],abbreviated_edge=alias['abbreviated_edge'],abbreviated_interface=alias['abbreviated_interface'],native_detail_tee=tee,canonical_path_coordinate_kind='confirmed_detail_view_not_plan_metric_proof',unshown_plan_connector_length_mm=None)
            edge[side+'_node_id']=did;edge.pop(side+'_port_id',None);edge.update(physical_length='unknown',path_length_complete=False,equipment_connector_length_mm=None,equipment_connector_length_status='unshown_source_view_to_equipment_unknown')
            edge.setdefault('length_scope_evidence',[]).extend([dict(kind='inherited_sideview_edge_scope',source_graph_sha256=graph_hash,edge_id=eid,properties=prior),dict(kind='ordered_row_logical_equipment_link',source_graph_sha256=graph_hash,edge_id=eid,equipment_id=did,physical_length_mm=None,physical_port_verified=False)])
            native_body=dict(equipment_id=did,equipment_handle=owner['source_handle'],native_body_bounds=body['bounds'],source_caption_handle=body['source_caption_handles'][0],ownership_basis='complete_native_row_order_checked_against_independent_owners',individual_projection_strip_is_not_claimed=True)
            record=dict(equipment_id=did,edge_id=eid,system=edge['system'],interface_side=side,original_canonical_interface_id=nid,original_canonical_interface_kind='node',original_canonical_endpoint=original,
                source_sha256=source_hash,input_graph_sha256=root['input_graph_sha256'],ordered_extension_input_graph_sha256=graph_hash,question_id=pair['pair_id'],pair_sha256=pair['pair_sha256'],sideview_root_sha256=evidence['sideview_alias_root_sha256'],calibration_sha256=proof_hash,endpoint_floor_evidence=dict(floor=original['floor'],source='canonical_endpoint',legacy_node_id=None),body_evidence=native_body,source_alias=endpoint,prior_edge_length_scope=prior,physical_port_verified=False,interface_to_equipment_length_known=False,human_accepted=False,
                endpoint_snapshot=dict(start_node_id=edge.get('start_node_id'),end_node_id=edge.get('end_node_id'),start_boundary_id=edge.get('start_boundary_id'),end_boundary_id=edge.get('end_boundary_id'),equipment_xy=[owner['x'],owner['y']],equipment_source_handle=owner['source_handle'],system=edge['system'],attribute_paths=copy.deepcopy(edge['attribute_paths'])))
            edge['source_sideview_equipment_interface']=record;root['records'].append(record);root['node_aliases'][nid]=did;root['retired_interface_nodes'].append(original);retired[nid]=original;records.append(record);claimed.add(eid)
        owner.update(connection_status='source_checked_ordered_sideview_equipment_physical_ports_unknown',source_sideview_interface_ids=[a['canonical_interface']for a in pair['aliases']])
    out['nodes']=[n for n in out['nodes']if n['node_id']not in retired];ports=[p for p in out.get('virtual_equipment_ports',[])if p.get('node_id')in retired or p.get('virtual_equipment_id')in retired];out['virtual_equipment_ports']=[p for p in out.get('virtual_equipment_ports',[])if p not in ports];root['retired_virtual_ports'].extend(ports)
    if 'sourceTerminalGlyphs'in out:
        glyphs=[p for p in out['sourceTerminalGlyphs']if p.get('node_id')in retired];out['sourceTerminalGlyphs']=[p for p in out['sourceTerminalGlyphs']if p not in glyphs];root['retired_display_glyphs'].extend(glyphs)
    root.setdefault('scope_composition',[]).append(dict(method=MODE,current_input_graph_sha256=graph_hash,independent_old_owner_root_sha256=evidence['old_owner_root_sha256'],ordered_row_evidence_sha256=proof_hash,new_edge_ids=sorted(claimed),inherited_alias_metric_domain_graph_sha256=root['input_graph_sha256']))
    out,changes=reconcile(out);by={e['edge_id']:e for e in out['edges']}
    for r in records:by[r['edge_id']]['source_sideview_equipment_interface']=r
    if len(out['edges'])!=len(graph['edges'])or any(by[e['edge_id']]!=e for e in graph['edges']if e['edge_id']not in claimed):raise ValueError('ordered ownership changed unrelated edges')
    old_equipment={n['node_id']:n for n in graph['nodes']if n['node_type']=='equipment'}
    if set(old_equipment)!={n['node_id']for n in out['nodes']if n['node_type']=='equipment'}or graph['confirmedSideviewCanonicalization']!=out['confirmedSideviewCanonicalization']:raise ValueError('equipment or original alias population changed')
    out['sourceOrderedSideviewEquipmentOwnership']=dict(mode=MODE,source_sha256=source_hash,input_graph_sha256=graph_hash,ordered_row_evidence_sha256=proof_hash,records=records,retired_interface_ids=sorted(retired),old_owner_records_preserved=len(graph['sourceSideviewEquipmentOwnership']['records']),independent_owner_pairs=sum(len(c['fixed_owners'])for c in evidence['cohorts']),equipment_instances_conserved=True,source_pipe_paths_unchanged=True,supply_return_independent=True,physical_ports_verified=False,physical_lengths_assigned=0,human_accepted=False)
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_ordered_sideview_equipment_ownership');out['derivedEvidenceInvalidation']=dict(previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),reason='complete native row and independent owners resolved terminal strip collision',recompute=['source_comparison','branch_inventory','crossview_mapping','diameter_inheritance','length_fusion','human_acceptance'],historical_annotations_preserved=True)
    for r in records:detail_T(doc,out,r['source_alias']['native_detail_tee']['tee'],source_hash,'new_graph_pending_hash')
    return out,dict(records=records,retired_interface_ids=sorted(retired),endpoint_type_changes=changes,equipment_instances_preserved=True,inline_component_assignments_changed=False,source_pipe_paths_changed=False,physical_lengths_assigned=0)
