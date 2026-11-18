"""Follow replayed sideview aliases before existing native owner calibration.

Read-only. The caller independently replays canonicalization and calibration.
Source-expression context is never returned as a replacement physical graph.
"""
import collections,hashlib,math,re
from confirm_crossview_paths import encode
from canonicalize_confirmed_sideviews import source_expression_context,verify_tee,DECISION
from calibrated_equipment_interface_ownership import screen

def collect(doc,graph,model,source_hash,graph_hash):
    state=graph.get('confirmedSideviewCanonicalization',{})
    if graph.get('metadata',{}).get('source_sha256')!=source_hash or state.get('source_sha256')!=source_hash:raise ValueError('sideview owner source differs')
    if (model.get('status')!='source_calibrated_supported_projection_pattern' or model.get('physical_ports_verified') is not False
        or model.get('human_accepted') is not False or not model.get('spacings')
        or not isinstance(model.get('maximum_gap_ratio'),(int,float)) or isinstance(model['maximum_gap_ratio'],bool)
        or not math.isfinite(model['maximum_gap_ratio']) or model['maximum_gap_ratio']<=0):raise ValueError('sideview owner needs independently replayed calibration')
    context=source_expression_context(graph);records=state.get('records',[]);groups=collections.defaultdict(list)
    if not records:raise ValueError('empty confirmed sideview scope')
    node_aliases={};edge_aliases={};canonical=set()
    for row in records:
        if (row.get('answer',{}).get('decision')!=DECISION or not re.fullmatch(r'[0-9a-f]{64}',row.get('pair_sha256',''))
            or row.get('physical_length')!='unknown' or row.get('projected_main_identity')!='not_inferred'):raise ValueError('sideview original answer/scope changed')
        nid,eid=row['abbreviated_interface'],row['abbreviated_edge']
        if nid in node_aliases or eid in edge_aliases or row['canonical_edge'] in canonical:raise ValueError('sideview alias repeats a pipe/interface')
        node_aliases[nid]=row['canonical_interface'];edge_aliases[eid]=row['canonical_edge'];canonical.add(row['canonical_edge'])
        groups[(row['question_id'],row['pair_sha256'])].append(row)
    if node_aliases!=state.get('node_aliases') or edge_aliases!=state.get('edge_aliases'):raise ValueError('sideview alias map differs from confirmed records')
    # Existing screen evaluates all pairs and all native bodies before selecting.
    # Do not filter by requested equipment and accidentally hide competition.
    evidence=screen(doc,context,model);nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']};anchors={a['boundary_id']:a for a in graph.get('boundary_anchors',[])}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']) or len(anchors)!=len(graph.get('boundary_anchors',[])):raise ValueError('duplicate active sideview identity')
    rows=[];selected=[]
    for (qid,pair),aliases in groups.items():
        if len(aliases)!=2 or {r['system'] for r in aliases}!={'supply','return'}:raise ValueError('sideview owner needs paired independent services')
        ids={r['abbreviated_interface'] for r in aliases};matches=[r for r in evidence['pairs'] if {i['node_id'] for i in r['interfaces']}==ids]
        current=[]
        for alias in aliases:
            edge=edges.get(alias['canonical_edge']);nid=alias['canonical_interface'];kind=alias['canonical_interface_kind']
            if edge is None or edge.get('system')!=alias['system']:raise ValueError('sideview canonical pipe/system changed')
            if kind=='node':
                target=nodes.get(nid)
                if not target or target.get('node_type')=='equipment' or target.get('system')!=alias['system']:raise ValueError('sideview canonical interface role changed')
                sides=[s for s in ('start','end') if edge.get(s+'_node_id')==nid]
            elif kind=='non_node_boundary':
                if nid in nodes or nid not in anchors or anchors[nid].get('system')!=alias['system']:raise ValueError('sideview non-node boundary changed')
                sides=[s for s in ('start','end') if edge.get(s+'_boundary_id')==nid and edge.get(s+'_node_id') is None]
            else:raise ValueError('unsupported sideview endpoint kind')
            if len(sides)!=1:raise ValueError('canonical alias does not identify one endpoint')
            tee,checked=verify_tee(doc,graph,edge,nid)
            if checked.get('attribute_paths')!=edge.get('attribute_paths'):raise ValueError('canonical source path needs its own normalization first')
            current.append(dict(canonical_edge=edge['edge_id'],canonical_interface=nid,canonical_interface_kind=kind,canonical_side=sides[0],
                system=alias['system'],abbreviated_edge=alias['abbreviated_edge'],abbreviated_interface=alias['abbreviated_interface'],native_detail_tee=tee,
                canonical_path_coordinate_kind='confirmed_detail_view_not_plan_metric_proof',unshown_plan_connector_length_mm=None))
        row=dict(question_id=qid,pair_sha256=pair,canonical_endpoints=current,physical_ports_verified=False,human_accepted=False)
        if len(matches)!=1:
            row.update(status='archived_native_pair_not_unique_or_supported',candidate_owner=None)
        else:
            match=matches[0];row['native_layout_evidence']=match
            owner=match.get('proposed_owner')
            if owner and match in evidence['selected']:
                row.update(status='calibrated_owner_through_confirmed_sideview_not_applied',candidate_owner=owner['equipment_id']);selected.append(row)
            else:row.update(status=match['status'],candidate_owner=None)
        rows.append(row)
    return dict(status='source_sideview_equipment_owner_evidence_not_topology',source_sha256=source_hash,graph_sha256=graph_hash,
        sideview_root_sha256=hashlib.sha256(encode(state)).hexdigest(),calibration_sha256=hashlib.sha256(encode(model)).hexdigest(),
        records=rows,selected=selected,global_pair_status_counts=dict(collections.Counter(r['status'] for r in evidence['pairs'])),
        source_expression_context_only=True,context_promoted_to_physical_graph=False,parent_stage_replay_required=True,
        topology_mutated=False,mapped_paths=0,whole_physical_lengths_selected=False,human_accepted=False,hil_ready=False)
