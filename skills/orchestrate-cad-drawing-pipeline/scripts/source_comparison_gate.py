"""Machine contract for native comparison/repair BEFORE final expert HIL."""
import hashlib,json,importlib.util,math
from collections import Counter
from pathlib import Path

def verify_batch_circle_stage(root,graph_hash):
    root=Path(root).resolve();stage_path=root/'reports/batch-confirmed-circle-stage.json';audit_path=root/'reports/batch-confirmed-circle-audit.json'
    if not stage_path.exists() and not audit_path.exists():return
    if not stage_path.is_file() or not audit_path.is_file():raise ValueError('missing batch circle stage or audit')
    stage=json.loads(stage_path.read_text(encoding='utf8'))
    directory=Path(stage['artifact_directory']).resolve()
    if (not directory.is_relative_to(root) or stage.get('status')!='source_pinned_batch_circle_reconstruction'
        or stage.get('graph_sha256')!=graph_hash or stage.get('hil_ready') is not False
        or hashlib.sha256(audit_path.read_bytes()).hexdigest()!=stage.get('audit_sha256')
        or audit_path.read_bytes()!=(directory/'batch-confirmed-circle-audit.json').read_bytes()):
        raise ValueError('unsafe or stale batch circle evidence')
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from reconstruct_batch_circle_junctions import verify_output
    audit=verify_output(directory)
    if audit['source_sha256']!=stage.get('source_sha256') or audit['output_graph_sha256']!=graph_hash:
        raise ValueError('batch circle output mismatch')

def verify_confirmed_sideview_stage(root,graph_hash):
    root=Path(root).resolve();stage_path=root/'reports/confirmed-sideview-stage.json';audit_path=root/'reports/sideview-canonicalization-audit.json'
    if not stage_path.exists() and not audit_path.exists():return
    if not stage_path.is_file() or not audit_path.is_file():raise ValueError('missing confirmed side-view stage or audit')
    stage=json.loads(stage_path.read_text(encoding='utf8'));directory=Path(stage['artifact_directory']).resolve()
    if (not directory.is_relative_to(root) or stage.get('status')!='source_pinned_confirmed_sideview_canonicalization'
        or stage.get('graph_sha256')!=graph_hash or stage.get('hil_ready') is not False
        or hashlib.sha256(audit_path.read_bytes()).hexdigest()!=stage.get('audit_sha256')
        or audit_path.read_bytes()!=(directory/'sideview-canonicalization-audit.json').read_bytes()):
        raise ValueError('unsafe or stale confirmed side-view evidence')
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from canonicalize_confirmed_sideviews import verify_output
    audit=verify_output(directory)
    if audit['inputs']['source']['sha256']!=stage.get('source_sha256') or audit['output_graph_sha256']!=graph_hash:
        raise ValueError('confirmed side-view output mismatch')
    return audit

def verify_confirmed_near_tee_stage(root,graph_hash,graph=None):
    root=Path(root).resolve();stage_path=root/'reports/confirmed-near-tee-stage.json';audit_path=root/'reports/near-tee-confirmation-audit.json'
    if not stage_path.exists() and not audit_path.exists():
        if graph and graph.get('sourceNearTeeConfirmations'):raise ValueError('confirmed near-tee graph requires its source stage')
        return
    if not stage_path.is_file() or not audit_path.is_file():raise ValueError('missing near-tee confirmation stage or audit')
    stage=json.loads(stage_path.read_text(encoding='utf8'));directory=Path(stage['artifact_directory']).resolve()
    if (not directory.is_relative_to(root) or stage.get('status')!='source_pinned_normalized_near_tee_confirmation'
        or stage.get('graph_sha256')!=graph_hash or stage.get('hil_ready') is not False
        or hashlib.sha256(audit_path.read_bytes()).hexdigest()!=stage.get('audit_sha256')
        or audit_path.read_bytes()!=(directory/'near-tee-confirmation-audit.json').read_bytes()):raise ValueError('unsafe or stale near-tee confirmation evidence')
    audit=json.loads(audit_path.read_text(encoding='utf8'))
    actual=json.loads((directory/'graph_with_confirmed_near_tees.json').read_text(encoding='utf8'))
    if (audit.get('source_sha256')!=stage.get('source_sha256') or audit.get('output_graph_sha256')!=graph_hash
        or hashlib.sha256((directory/'graph_with_confirmed_near_tees.json').read_bytes()).hexdigest()!=graph_hash
        or graph is not None and graph!=actual):raise ValueError('confirmed near-tee output mismatch')
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from normalized_near_tee_state_gate import check as check_near_tee_state
    normalization=json.loads(Path(audit['normalization']).read_text(encoding='utf8'))
    check_near_tee_state(actual,normalization['near_junction'],audit['source_sha256'],confirmed_directory=directory)
    return audit


def verify_confirmed_equipment_pair_stage(root,graph_hash,graph=None):
    root=Path(root).resolve();stage_path=root/'reports/confirmed-equipment-pair-stage.json';audit_path=root/'reports/equipment-pair-reconstruction-audit.json'
    if not stage_path.exists() and not audit_path.exists():
        if graph and graph.get('confirmedEquipmentPairReconstruction'):raise ValueError('confirmed equipment graph requires its source stage')
        return
    if not stage_path.is_file() or not audit_path.is_file():raise ValueError('missing equipment pair stage or audit')
    stage=json.loads(stage_path.read_text(encoding='utf8'));directory=Path(stage['artifact_directory']).resolve()
    if (not directory.is_relative_to(root) or stage.get('status')!='source_pinned_confirmed_equipment_pair_reconstruction'
        or stage.get('graph_sha256')!=graph_hash or stage.get('hil_ready') is not False
        or hashlib.sha256(audit_path.read_bytes()).hexdigest()!=stage.get('audit_sha256')
        or audit_path.read_bytes()!=(directory/'equipment-pair-reconstruction-audit.json').read_bytes()):raise ValueError('unsafe or stale equipment pair evidence')
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from reconstruct_confirmed_equipment_pairs import verify_output
    audit=verify_output(directory)
    if audit['inputs']['source']['sha256']!=stage.get('source_sha256') or audit['output_graph_sha256']!=graph_hash:raise ValueError('equipment pair output mismatch')
    if graph is not None and graph!=json.loads((directory/'graph_with_edges.json').read_text(encoding='utf8')):raise ValueError('equipment graph differs from replayed stage')
    return audit

def confirmed_sideview_source_handles(root,graph_hash,graph):
    """Classify archived drawing lines only after full native stage replay."""
    state=graph.get('confirmedSideviewCanonicalization')
    if state is None:return set()
    equipment=verify_confirmed_equipment_pair_stage(root,graph_hash,graph)
    parent_hash=equipment['inputs']['graph']['sha256'] if equipment else graph_hash
    audit=verify_confirmed_sideview_stage(root,parent_hash)
    if audit is None:raise ValueError('confirmed side-view graph requires its native stage')
    stage=json.loads((Path(root)/'reports/confirmed-sideview-stage.json').read_text(encoding='utf8'))
    actual=json.loads((Path(stage['artifact_directory'])/'graph_with_canonical_sideviews.json').read_text(encoding='utf8'))
    if (not equipment and graph!=actual) or state!=actual.get('confirmedSideviewCanonicalization') or state['records']!=audit['records']:raise ValueError('side-view classification graph differs from replayed output')
    return {h for edge in state['representation_only_edges'] for h in edge['source_handles']}

def bulk_dn_screen_blockers(root,graph_hash):
    """Consume scoped axis annotation ambiguity before expert review."""
    root=Path(root).resolve();evidence=root/'source_dn_bulk_screen_final.json';receipt_path=root/'rebuild-receipt.json'
    if not evidence.exists():
        if receipt_path.is_file() and json.loads(receipt_path.read_text(encoding='utf8')).get('final_bulk_dn_sha256'):raise ValueError('declared final DN screen is missing')
        return []
    if any(not p.resolve().is_relative_to(root) or not p.is_file() for p in (evidence,receipt_path)):raise ValueError('missing or unsafe DN screen')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    data=json.loads(evidence.read_text(encoding='utf8'));receipt=json.loads(receipt_path.read_text(encoding='utf8'))
    extractor=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology'/'scripts'/'source_dn_bulk_screen.py'
    text_guard=extractor.with_name('native_dn_text_position.py')
    rows=data.get('records');allowed={'unique_source_line_and_graph_segment_candidate','ambiguous_source_lines','no_source_line_in_local_scope','no_matching_graph_segment','ambiguous_graph_segments','unsupported_text_transform'}
    if (not extractor.is_file() or not text_guard.is_file() or data.get('text_guard_sha256')!=sha(text_guard) or data.get('script_sha256')!=sha(extractor) or receipt.get('final_bulk_dn_sha256')!=sha(evidence)
        or receipt.get('final_graph_sha256')!=graph_hash or data.get('graph_sha256')!=graph_hash
        or data.get('source_sha256')!=receipt.get('inputs',{}).get('dxf') or data.get('status')!='native_dn_bulk_screen_candidates_only'
        or data.get('graph_mutated') is not False or data.get('human_accepted') is not False or data.get('hil_ready') is not False or not isinstance(rows,list)):
        raise ValueError('stale or invalid final DN screen')
    if any(not isinstance(r,dict) or not isinstance(r.get('text_handle'),str) or not r['text_handle'] or not isinstance(r.get('text'),str) or not r['text'] or r.get('status') not in allowed for r in rows):raise ValueError('invalid DN screen record')
    if len({r['text_handle'] for r in rows})!=len(rows) or dict(Counter(r['status'] for r in rows))!=data.get('summary'):raise ValueError('DN screen count mismatch')
    nested=data.get('nested_scope')
    if not isinstance(nested,dict) or not isinstance(nested.get('failed_roots'),list):raise ValueError('invalid nested scope')
    grouped=set();detail_groups={};detail=root/'source_dn_detail_scope_final.json'
    if receipt.get('final_dn_detail_scope_sha256') and not detail.is_file():raise ValueError('declared detail scope is missing')
    if detail.exists():
        if not detail.resolve().is_relative_to(root) or not detail.is_file():raise ValueError('unsafe detail scope')
        scope=json.loads(detail.read_text(encoding='utf8'));owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology'/'scripts';scope_script=owner/'isometric_detail_dn_scope.py';legacy=owner/'legacy_v17'/'analyze_graph.py';scoped=scope.get('records');by={r['text_handle']:r for r in rows}
        if (receipt.get('final_dn_detail_scope_sha256')!=sha(detail) or not scope_script.is_file() or not legacy.is_file() or scope.get('script_sha256')!=sha(scope_script) or scope.get('legacy_geometry_sha256')!=sha(legacy)
            or scope.get('status')!='excluded_scope_not_main_assignment' or scope.get('source_sha256')!=data['source_sha256'] or scope.get('graph_sha256')!=graph_hash
            or scope.get('bulk_screen_sha256')!=sha(evidence) or scope.get('graph_mutated') is not False or scope.get('detail_mapping_ready') is not False or scope.get('hil_ready') is not False or not isinstance(scoped,list) or not scoped):raise ValueError('stale detail scope')
        for x in scoped:
            if not isinstance(x,dict) or x.get('status') not in ('excluded_left_scope_detail_correspondence_pending','excluded_right_scope_detail_correspondence_pending'):raise ValueError('invalid detail scope record')
            h=x.get('text_handle');r=by.get(h)
            if not r or h in grouped or r.get('status')!='no_source_line_in_local_scope' or r.get('text')!=x.get('text'):raise ValueError('detail scope and bulk mismatch')
            sid=x.get('scope_id','left')
            if not isinstance(sid,str) or not sid:raise ValueError('invalid detail scope identity')
            grouped.add(h);detail_groups.setdefault(sid,[]).append(h)
    pattern_file=root/'source_dn_ambiguity_patterns_final.json';pattern_by_handle={}
    if receipt.get('final_dn_pattern_sha256') and not pattern_file.is_file():raise ValueError('declared DN patterns missing')
    if pattern_file.exists():
        script=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology'/'scripts'/'group_ambiguous_dn_patterns.py'
        if not pattern_file.resolve().is_relative_to(root) or not pattern_file.is_file() or not script.is_file():raise ValueError('unsafe DN patterns')
        pattern=json.loads(pattern_file.read_text(encoding='utf8'));groups=pattern.get('groups')
        if (receipt.get('final_dn_pattern_sha256')!=sha(pattern_file) or pattern.get('script_sha256')!=sha(script)
            or pattern.get('policy_sha256')!=receipt.get('final_dn_pattern_policy_sha256') or pattern.get('bulk_screen_sha256')!=sha(evidence)
            or pattern.get('source_sha256')!=data['source_sha256'] or pattern.get('graph_sha256')!=graph_hash
            or pattern.get('status')!='repeated_dn_ambiguity_patterns_not_attribution' or pattern.get('graph_mutated') is not False
            or pattern.get('mapping_ready') is not False or pattern.get('hil_ready') is not False or not isinstance(groups,list) or not groups):raise ValueError('stale DN patterns')
        spec=importlib.util.spec_from_file_location('group_ambiguous_dn_patterns_gate',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        try: expected=module.group(data,{'groups':[{'text_handles':x['text_handles']} for x in groups]})['groups']
        except (KeyError,TypeError,ValueError) as exc:raise ValueError('invalid DN patterns') from exc
        if expected!=groups:raise ValueError('DN patterns do not match screen')
        for index,x in enumerate(groups):
            for handle in x['text_handles']:
                if handle in grouped:raise ValueError('DN pattern overlaps detail scope')
                pattern_by_handle[handle]=index+1
    result=[{'source_text_handle':r['text_handle'],'source_text':r['text'],'status':r['status'],**({'ambiguity_pattern':pattern_by_handle[r['text_handle']]} if r['text_handle'] in pattern_by_handle else {})} for r in rows if r['status']!='unique_source_line_and_graph_segment_candidate' and r['text_handle'] not in grouped]
    for sid,handles in sorted(detail_groups.items()):result.append({'scope_id':sid,'source_text_handles':sorted(handles),'status':'excluded_detail_scope_correspondence_pending'})
    result.extend({'source_insert_handle':x.get('handle'),'status':'nested_decomposition_failed'} for x in nested['failed_roots'])
    return result

def segment_dn_withheld_blockers(root,graph_hash):
    """Bind axis DN sidecar to its input graph and current extractor; never hide withheld text."""
    root=Path(root).resolve(); evidence=root/'native_segment_dn_candidates.json'
    if not evidence.exists():
        receipt_path=root/'rebuild-receipt.json'
        if receipt_path.is_file() and json.loads(receipt_path.read_text(encoding='utf8')).get('inputs',{}).get('segment-dn-policy'):
            raise ValueError('declared segment DN stage is missing')
        return []
    files=[evidence,root/'graph_with_edges.json',root/'native_line_path_evidence.json',root/'rebuild-receipt.json']
    if any(not p.resolve().is_relative_to(root) or not p.is_file() for p in files):raise ValueError('missing or unsafe segment DN stage')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result=json.loads(evidence.read_text(encoding='utf8'));receipt=json.loads(files[3].read_text(encoding='utf8'))
    extractor=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology'/'scripts'/'native_segment_dn_candidates.py'
    text_guard=extractor.with_name('native_dn_text_position.py')
    rows=result.get('withheld_observations')
    if (not extractor.is_file() or not text_guard.is_file() or result.get('text_guard_sha256')!=sha(text_guard) or result.get('script_sha256')!=sha(extractor)
        or result.get('status')!='segment_candidates_not_accepted' or result.get('graph_mutated') is not False
        or result.get('hil_ready') is not False or result.get('graph_sha256')!=sha(files[1])
        or result.get('line_evidence_sha256')!=sha(files[2]) or result.get('source_sha256')!=receipt.get('inputs',{}).get('dxf')
        or result.get('policy_sha256')!=receipt.get('inputs',{}).get('segment-dn-policy')
        or receipt.get('final_graph_sha256')!=graph_hash or not isinstance(rows,list)):
        raise ValueError('stale or incomplete segment DN stage')
    out=[];seen=set()
    for row in rows:
        if not isinstance(row,dict) or row.get('status')!='withheld_not_attributed' or not isinstance(row.get('source_text'),dict):raise ValueError('invalid withheld DN record')
        t=row['source_text'];handle=t.get('handle');reason=row.get('reason')
        if not isinstance(handle,str) or not handle or handle in seen or not isinstance(reason,str) or not reason.strip() or t.get('source_sha256')!=result['source_sha256'] or not t.get('text'):raise ValueError('invalid withheld DN record')
        seen.add(handle);out.append({'source_text_handle':handle,'source_text':t['text'],'reason':reason})
    return out

def equipment_comparison_blockers(graph):
    """Inspect explicit unresolved equipment-source contacts, without inventing ports."""
    result=[]
    for node in graph.get('nodes',[]):
        if node.get('node_type') != 'equipment':
            continue
        state = node.get('source_port_completeness','')
        candidates = node.get('source_port_candidates') or []
        unresolved = [c for c in candidates if c.get('status') in
                      ('source_mark_candidate_not_bound','algorithm_pending','unbound')]
        if state == 'unbound_source_contacts_require_comparison' or unresolved or node.get('connection_status') == 'ports_unresolved':
            result.append({'node_id':node.get('node_id'), 'source_port_completeness':state,
                           'connection_status':node.get('connection_status'),
                           'unbound_candidate_count':len(unresolved)})
    return result

def resolved_circle_crossover_history(graph):
    """Ignore this one historical family only while its archived repair still holds.

    Empty current conflicts alone are not evidence of resolution. This does not
    suppress other historical families, comparison states or HIL prerequisites.
    """
    if graph.get('sourceCircleCrossoverConflicts') != []:
        return False
    history = graph.get('sourceCircleCrossoverConflictHistory')
    if not isinstance(history, list) or not history:
        return False
    nodes = {n.get('node_id'): n for n in graph.get('nodes', [])}
    edges = {e.get('edge_id'): e for e in graph.get('edges', [])}
    if len(nodes) != len(graph.get('nodes', [])) or len(edges) != len(graph.get('edges', [])):
        return False
    for audit in history:
        if (audit.get('source_sha256') != graph.get('metadata', {}).get('source_sha256')
                or audit.get('connectivity_changed') is not False or not audit.get('records')):
            return False
        for record in audit['records']:
            original = record.get('original_conflict', {})
            original_hash = hashlib.sha256(json.dumps(original, sort_keys=True, ensure_ascii=False,
                                                      separators=(',', ':')).encode('utf8')).hexdigest()
            if (record.get('conflict_sha256') != original_hash
                    or record.get('resolution') != 'separate_confirmed_tees_on_native_main_not_collinear_gap'):
                return False
            connections = record.get('connections', [])
            if len(connections) != 2 or len({c.get('node_id') for c in connections}) != 2:
                return False
            for c in connections:
                node = nodes.get(c.get('node_id')); branch = edges.get(c.get('branch_edge'))
                if not node or not branch or node.get('node_type') != 'tee':return False
                incident = [e for e in edges.values() if c['node_id'] in (e.get('start_node_id'), e.get('end_node_id'))]
                if len(incident) != 3 or branch not in incident or any(e.get('system') != node.get('system') for e in incident):return False
                if set(c.get('main_edges', [])) != {e['edge_id'] for e in incident if e is not branch}:return False
                for obj in (node, branch):
                    ev = obj.get('user_confirmed_overlap_connection', {})
                    if (ev.get('circle_handle') != c.get('circle_handle') or ev.get('branch_handle') != c.get('branch_handle')
                            or ev.get('user_evidence_manifest_sha256') != audit.get('evidence_manifest_sha256')):return False
            joining = edges.get(record.get('native_main_edge'))
            if not joining or {joining.get('start_node_id'), joining.get('end_node_id')} != {c['node_id'] for c in connections}:return False
    return True


def graph_comparison_blockers(graph):
    """Read unresolved algorithm work from the graph, independent of its receipt."""
    nodes=[]
    for node in graph.get('nodes', []):
        if (node.get('boundary_type')=='unresolved_source_terminal' or
            node.get('resolution_state') in ('local_symbol_form_equipment_overlap_pending','source_declared_connection_route_pending','source_glyph_system_conflict_pending','source_main_continuation_branch_pending')):
            nodes.append({'node_id':node.get('node_id'),
                          'boundary_type':node.get('boundary_type'),
                          'resolution_state':node.get('resolution_state')})
    comparison=graph.get('preHilComparison') or {}
    families=[];seen=set()
    conflicts=graph.get('sourceCircleCrossoverConflicts',[])
    if not isinstance(conflicts,list) or any(not isinstance(x,dict) for x in conflicts):raise ValueError('invalid circle crossover conflicts')
    if conflicts:families.append('circle_crossover_conflict')
    inline_conflicts=graph.get('sourceInlineSystemConflicts',[])
    if not isinstance(inline_conflicts,list) or any(not isinstance(x,dict) for x in inline_conflicts):raise ValueError('invalid inline system conflicts')
    if inline_conflicts:families.append('inline_component_system_conflict')
    circle_history_resolved = resolved_circle_crossover_history(graph)
    while comparison:
        if not isinstance(comparison,dict) or id(comparison) in seen:raise ValueError('invalid or cyclic comparison history')
        seen.add(id(comparison));state=comparison.get('status')
        if state is not None and state not in ('resolved','source_ambiguity'):
            families.append('source_comparison_status:'+str(state))
        entries=comparison.get('families',[])
        if not isinstance(entries,list) or any(not isinstance(f,dict) for f in entries):raise ValueError('invalid comparison families')
        families.extend(f.get('id','unknown') for f in entries if f.get('status') not in ('resolved','source_ambiguity')
                        and not (f.get('id') == 'circle_crossover_conflict' and circle_history_resolved))
        comparison=comparison.get('previous_comparison') or {}
    return nodes,list(dict.fromkeys(families))

def reference_component_blockers(graph):
    return [{'group_id':g.get('group_id'),'reference_insert_handle':g.get('source_provenance',{}).get('reference_insert_handle')}
            for g in graph.get('sourceInlineEndpointGroups',[])
            if g.get('source_provenance',{}).get('individual_primary_proxy_identity')=='not_established']

def hidden_branch_screen_blockers(root, graph_hash, graph_source_hash, report):
    """Require explicit disposition of each source-pinned candidate relation."""
    root=Path(root).resolve();screen=root/'reports'/'hidden-branch-circle-screen.json';receipt=root/'reports'/'hidden-branch-circle-screen-stage.json'
    if not screen.exists() and not receipt.exists():return []
    if not screen.resolve().is_relative_to(root) or not receipt.resolve().is_relative_to(root) or not screen.is_file() or not receipt.is_file():raise ValueError('missing or unsafe hidden branch stage')
    evidence=json.loads(screen.read_text(encoding='utf8'));stage=json.loads(receipt.read_text(encoding='utf8'))
    if (stage.get('graph_sha256')!=graph_hash or stage.get('evidence_sha256')!=hashlib.sha256(screen.read_bytes()).hexdigest() or
        evidence.get('graph_sha256')!=graph_hash or evidence.get('source_sha256')!=graph_source_hash or evidence.get('status')!='candidates_not_connectivity_proof'):
        raise ValueError('stale hidden branch screen')
    candidates=evidence.get('candidates');ambiguous=evidence.get('ambiguous');dispositions=report.get('hidden_branch_dispositions',[])
    if not isinstance(candidates,list) or not isinstance(ambiguous,list) or not isinstance(dispositions,list):raise ValueError('invalid hidden branch screen')
    def key(x):
        fields=('terminal','branch_handle','main_handle','circle_handle')
        if not isinstance(x,dict) or any(not isinstance(x.get(k),str) or not x[k] for k in fields):raise ValueError('invalid hidden branch relation')
        return tuple(x[k] for k in fields)
    disposition_by_key={}
    for x in dispositions:
        k=key(x)
        evidence_path=x.get('evidence_path');evidence_sha=x.get('evidence_sha256')
        if (k in disposition_by_key or x.get('status') not in ('resolved','source_ambiguity') or not isinstance(x.get('disposition'),str) or not x['disposition'].strip() or
            not isinstance(evidence_path,str) or not isinstance(evidence_sha,str) or not any(e.get('path')==evidence_path and e.get('sha256')==evidence_sha for e in report.get('native_comparisons',[]))):raise ValueError('invalid hidden branch disposition')
        disposition_by_key[k]=x
    keys=[key(x) for x in candidates]
    if len(set(keys))!=len(keys) or any(x.get('status')!='candidate_not_connectivity_proof' for x in candidates):raise ValueError('invalid hidden branch candidates')
    if not set(disposition_by_key).issubset(keys):raise ValueError('disposition not bound to current candidate')
    if any(not isinstance(x,dict) or not x.get('terminal') or not x.get('reason') for x in ambiguous):raise ValueError('invalid hidden branch ambiguities')
    return [{'terminal':k[0],'branch_handle':k[1],'main_handle':k[2],'circle_handle':k[3]} for k in keys if k not in disposition_by_key]+[{'terminal':x['terminal'],'reason':x['reason']} for x in ambiguous]

def equipment_datum_screen_blockers(root,graph_hash,graph):
    root=Path(root).resolve();screen=root/'equipment_datum_position_screen_final.json';receipt=root/'equipment_datum_position_screen_stage.json'
    if not screen.exists() and not receipt.exists():return []
    if not screen.resolve().is_relative_to(root) or not receipt.resolve().is_relative_to(root) or not screen.is_file() or not receipt.is_file():raise ValueError('missing or unsafe equipment datum stage')
    e=json.loads(screen.read_text(encoding='utf8'));s=json.loads(receipt.read_text(encoding='utf8'));rows=e.get('records')
    if (e.get('status')!='drawing_anchor_datum_comparison_not_floor_assignment' or e.get('graph_sha256')!=graph_hash or not isinstance(e.get('source_sha256'),str) or not e['source_sha256'] or e.get('graph_mutated') is not False or e.get('human_accepted') is not False or e.get('hil_ready') is not False or not isinstance(rows,list) or not rows or s.get('status') not in ('screened_floor_interpretation_pending','screened_not_physical_floor_confirmation') or not isinstance(s.get('policy_sha256'),str) or not s['policy_sha256'] or s.get('graph_sha256')!=graph_hash or s.get('source_sha256')!=e.get('source_sha256') or s.get('evidence_sha256')!=hashlib.sha256(screen.read_bytes()).hexdigest() or s.get('hil_ready') is not False):raise ValueError('invalid or stale equipment datum stage')
    source=graph.get('metadata',{}).get('source_sha256')
    if s.get('policy_sha256')!=e.get('policy_sha256'):raise ValueError('equipment datum policy mismatch')
    if source is not None and source!=e.get('source_sha256'):raise ValueError('equipment datum source mismatch')
    nodes={n['node_id']:n for n in graph.get('nodes',[]) if n.get('node_type') in ('equipment','physical_equipment')};seen=set();blockers=[]
    for x in rows:
        id=x.get('equipment_id');n=nodes.get(id);anchor=x.get('anchor');state=x.get('status')
        if (not isinstance(id,str) or id in seen or n is None or n.get('floor')!=x.get('graph_floor_label') or not isinstance(anchor,list) or len(anchor)!=2 or anchor!=[n.get('x'),n.get('y')] or x.get('physical_floor_verified') is not False or state not in ('on_datum','below_first_known_datum','anchor_band_matches_graph_label','anchor_band_differs_from_graph_label')):raise ValueError('invalid equipment datum row')
        seen.add(id)
        if state!='anchor_band_matches_graph_label':blockers.append({'equipment_id':id,'status':state,'anchor_x_within_claimed_native_baseline':x.get('anchor_x_within_claimed_native_baseline')})
    unscreened=e.get('unscreened_equipment_ids')
    if not isinstance(unscreened,list) or any(not isinstance(x,str) for x in unscreened) or len(unscreened)!=len(set(unscreened)) or set(unscreened)!=set(nodes)-seen or e.get('eligible_equipment_count')!=len(nodes) or e.get('scope_complete')!=(not unscreened):raise ValueError('equipment datum scope mismatch')
    blockers.extend({'equipment_id':id,'status':'equipment_not_in_datum_screen'} for id in unscreened)
    if s.get('candidate_count')!=len(blockers) or (s['status']=='screened_floor_interpretation_pending')!=bool(blockers):raise ValueError('equipment datum count mismatch')
    if 'interpretation_families' in e:
        import sys
        owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology'/'scripts'
        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
        from screen_equipment_datum_positions import interpretation_families
        families=interpretation_families(rows)
        if e['interpretation_families']!=families:raise ValueError('equipment datum family membership changed')
        by_id={ident:f['id'] for f in families for ident in f['member_equipment_ids']}
        for blocker in blockers:
            if blocker['equipment_id'] in by_id:blocker['interpretation_family']=by_id[blocker['equipment_id']]
    return blockers

def missing_gap_joint_blockers(root, graph_hash, graph):
    root=Path(root).resolve(); evidence=root/'missing_gap_joint_candidates_final.json';stage=root/'missing_gap_joint_candidates_stage.json'
    if not evidence.exists() and not stage.exists():return []
    if not evidence.is_file() or not stage.is_file() or not evidence.resolve().is_relative_to(root) or not stage.resolve().is_relative_to(root):raise ValueError('missing or unsafe gap joint evidence')
    e=json.loads(evidence.read_text(encoding='utf8'));s=json.loads(stage.read_text(encoding='utf8'));rows=e.get('records');edges={x['edge_id']:x for x in graph['edges']}
    if (e.get('status')!='missing_source_joints_candidate_screen' or e.get('graph_mutated') is not False or e.get('hil_ready') is not False or not isinstance(rows,list) or not rows or s.get('status')!='missing_joint_candidates_pending_source_comparison' or s.get('final_graph_sha256')!=graph_hash or s.get('input_graph_sha256')!=e.get('graph_sha256') or s.get('source_sha256')!=e.get('source_sha256') or s.get('coverage_sha256')!=e.get('coverage_sha256') or s.get('inventory_sha256')!=e.get('inventory_sha256') or s.get('policy_sha256')!=e.get('policy_sha256') or s.get('script_sha256')!=e.get('script_sha256') or s.get('evidence_sha256')!=hashlib.sha256(evidence.read_bytes()).hexdigest() or s.get('graph_mutated') is not False or s.get('human_accepted') is not False or s.get('hil_ready') is not False):raise ValueError('invalid or stale gap joint evidence')
    graph_source=graph.get('metadata',{}).get('source_sha256')
    if graph_source is None:
        receipt_path=root/'rebuild-receipt.json'
        if not receipt_path.is_file() or not receipt_path.resolve().is_relative_to(root):raise ValueError('gap joint graph source receipt missing')
        receipt=json.loads(receipt_path.read_text(encoding='utf8'))
        if receipt.get('final_graph_sha256')!=graph_hash:raise ValueError('gap joint receipt graph mismatch')
        graph_source=receipt.get('inputs',{}).get('dxf')
    if graph_source!=e.get('source_sha256'):raise ValueError('gap joint source mismatch')
    handles=[];out=[]
    for row in rows:
        h=row.get('insert_handle');edge=edges.get(row.get('edge_id'))
        if not isinstance(h,str) or not h or h in handles or not edge or edge.get('system')!=row.get('system') or row.get('candidate_type')!='金属软接' or row.get('status')!='source_calibrated_joint_unassigned_pending_review' or row.get('physical_length')!='unknown' or row.get('human_accepted') is not False:raise ValueError('invalid gap joint candidate')
        handles.append(h);out.append({'source_handle':h,'edge_id':row['edge_id'],'system':row['system'],'status':row['status']})
    if s.get('candidate_count')!=len(rows) or s.get('candidate_handles')!=handles:raise ValueError('gap joint scope mismatch')
    if s.get('joint_inventory_evidence_sha256') is not None:
        invpath=root/'calibrated_joint_inventory_final.json'
        if not invpath.is_file() or not invpath.resolve().is_relative_to(root) or hashlib.sha256(invpath.read_bytes()).hexdigest()!=s['joint_inventory_evidence_sha256']:raise ValueError('joint inventory missing or stale')
        inv=json.loads(invpath.read_text(encoding='utf8'));invrows=inv.get('records')
        if (inv.get('status')!='direct_calibrated_joint_inventory_not_ownership_acceptance' or inv.get('source_sha256')!=e.get('source_sha256') or inv.get('inventory_sha256')!=e.get('inventory_sha256') or inv.get('policy_sha256')!=e.get('policy_sha256') or inv.get('script_sha256')!=s.get('joint_inventory_script_sha256') or not isinstance(invrows,list) or inv.get('total_source_instances')!=len(invrows)):raise ValueError('joint inventory binding mismatch')
        ih=[r.get('source_handle') for r in invrows]
        if any(not isinstance(h,str) or not h for h in ih) or len(ih)!=len(set(ih)) or not set(handles).issubset(ih):raise ValueError('joint inventory scope mismatch')
        statuses=('unassigned_source_instance','duplicate_inventory_claims','inventory_type_conflict','inventory_assignment_unresolved','inventory_assignment_present_not_verified')
        if any(r.get('status') not in statuses for r in invrows):raise ValueError('invalid joint inventory status')
        actual_counts={k:sum(r['status']==k for r in invrows) for k in statuses if any(r['status']==k for r in invrows)}
        if inv.get('counts')!=actual_counts or any(r['status']!='unassigned_source_instance' for r in invrows if r['source_handle'] in handles):raise ValueError('joint inventory totals or selected claims mismatch')
        if 'same_fingerprint_block_definitions' in inv or 'nested_definition_references' in inv:
            defs=inv.get('same_fingerprint_block_definitions');nested=inv.get('nested_definition_references')
            if not isinstance(defs,list) or not defs or len(defs)!=len(set(defs)) or inv.get('block_name') not in defs or not isinstance(nested,list):raise ValueError('invalid joint block definition scope')
            for name in defs:
                if name!=inv['block_name']:out.append({'source_block':name,'status':'same_fingerprint_alternate_block_not_in_direct_inventory'})
            for n in nested:
                if not isinstance(n,dict) or n.get('referenced_block') not in defs or not n.get('parent_block') or not n.get('insert_handle'):raise ValueError('invalid nested joint reference')
                out.append({'source_handle':n['insert_handle'],'source_block':n['parent_block'],'status':'nested_joint_definition_reference_unexpanded'})
        for r in invrows:
            if r['status']!='inventory_assignment_present_not_verified' and r['source_handle'] not in handles:
                out.append({'source_handle':r['source_handle'],'status':r['status']})
        if s.get('joint_contact_reconciliation_sha256') is not None:
            recpath=root/'calibrated_joint_contact_reconciliation_final.json'
            if not recpath.is_file() or not recpath.resolve().is_relative_to(root) or hashlib.sha256(recpath.read_bytes()).hexdigest()!=s['joint_contact_reconciliation_sha256']:raise ValueError('joint contact reconciliation missing or stale')
            rec=json.loads(recpath.read_text(encoding='utf8'));rr=rec.get('records')
            if (rec.get('status')!='joint_inventory_contacts_bound_to_final_graph_not_acceptance' or rec.get('source_sha256')!=e.get('source_sha256') or rec.get('inventory_sha256')!=e.get('inventory_sha256') or rec.get('final_graph_sha256')!=graph_hash or rec.get('inventory_evidence_sha256')!=s['joint_inventory_evidence_sha256'] or rec.get('script_sha256')!=s.get('joint_contact_reconciliation_script_sha256') or rec.get('human_accepted') is not False or not isinstance(rr,list) or len(rr)!=len(invrows)):raise ValueError('invalid joint contact reconciliation')
            byhandle={r['source_handle']:r for r in rr}
            if len(byhandle)!=len(rr) or set(byhandle)!=set(ih):raise ValueError('joint contact scope mismatch')
            for item in invrows:
                record=byhandle[item['source_handle']];expected=item['status']
                if record.get('human_accepted') is not False:raise ValueError('invalid joint review status')
                if expected=='inventory_assignment_present_not_verified':
                    if record.get('status') not in ('two_source_contacts_witnessed_not_acceptance','contact_evidence_pending'):raise ValueError('invalid contact disposition')
                    if record['status']=='contact_evidence_pending':out.append({'source_handle':item['source_handle'],'status':'contact_evidence_pending'})
                elif record.get('status')!=expected:raise ValueError('joint inventory disposition mismatch')
    return out

def near_offset_circle_blockers(root,graph_hash,source_hash,graph):
    root=Path(root).resolve();screen=root/'reports/near-offset-circle-screen.json';stage=root/'reports/near-offset-circle-stage.json'
    if not screen.exists() and not stage.exists():return []
    if any(not p.is_file() or not p.resolve().is_relative_to(root) for p in (screen,stage)):raise ValueError('missing near-offset circle evidence')
    e=json.loads(screen.read_text(encoding='utf8'));s=json.loads(stage.read_text(encoding='utf8'));rows=e.get('candidates');amb=e.get('ambiguous_native_geometry');ids={x['edge_id']:x for x in graph.get('edges',[])};nodes={x['node_id']:x for x in graph.get('nodes',[])}
    if (e.get('status')!='near_offset_circle_candidates_only' or s.get('status')!='near_offset_circle_screen_required' or e.get('source_sha256')!=source_hash or s.get('source_sha256')!=source_hash or e.get('graph_sha256')!=graph_hash or s.get('graph_sha256')!=graph_hash or s.get('evidence_sha256')!=hashlib.sha256(screen.read_bytes()).hexdigest() or s.get('policy_sha256')!=e.get('policy_sha256') or e.get('graph_mutated') is not False or e.get('human_accepted') is not False or e.get('hil_ready') is not False or s.get('hil_ready') is not False or not isinstance(rows,list) or not isinstance(amb,list) or s.get('candidate_count')!=len(rows) or s.get('ambiguous_count')!=len(amb)):raise ValueError('invalid near-offset circle evidence')
    for key in ('policy_sha256','policy_map_sha256'):
        value=s.get(key)
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError('invalid near-offset policy hash')
    limit=e.get('max_main_offset');radius=e.get('circle_radius')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (limit,radius)) or limit<=.05:raise ValueError('invalid near-offset scope')
    seen=set();out=[]
    for row in rows:
        h=row.get('circle_handle');system=row.get('line_system');key=(h,system);offset=row.get('main_offset_drawing_units');main=row.get('main_graph_edges');branch=row.get('branch_graph_edges');term=row.get('rim_virtual_nodes')
        if (not h or system not in ('supply','return') or key in seen or row.get('status')!='near_main_not_connection_confirmation' or row.get('radius')!=radius or isinstance(offset,bool) or not isinstance(offset,(int,float)) or not math.isfinite(offset) or not .05<offset<=limit or not all(isinstance(v,list) and len(v)==len(set(v)) for v in (main,branch,term)) or any(i not in ids or ids[i].get('system')!=system or row.get('main_handle') not in ids[i].get('source_handles',[]) for i in main) or any(i not in ids or ids[i].get('system')!=system or row.get('branch_handle') not in ids[i].get('source_handles',[]) for i in branch) or any(i not in nodes or nodes[i].get('system')!=system for i in term)):raise ValueError('invalid near-offset circle candidate')
        seen.add(key);out.append({'circle_handle':h,'line_system':system,'status':row['status'],'main_offset_drawing_units':offset})
    for row in amb:
        if not isinstance(row,dict) or not row.get('circle_handle') or row.get('system') not in ('supply','return'):raise ValueError('invalid ambiguous near-offset circle')
        out.append({'circle_handle':row['circle_handle'],'line_system':row['system'],'status':'ambiguous_near_offset_geometry'})
    if graph.get('confirmedEquipmentPairReconstruction'):
        proof=verify_confirmed_equipment_pair_stage(root,graph_hash,graph)
        confirmed={(r['circle_handle'],r['system']) for r in proof['records']}
        out=[r for r in out if not (r['status']=='near_main_not_connection_confirmation' and (r['circle_handle'],r['line_system']) in confirmed)]
    return out

def additional_circle_screens(root,graph_hash,source_hash):
    root=Path(root).resolve();stage=root/'reports/source-circle-rim-additional-stage.json'
    if not stage.exists():return []
    if not stage.is_file() or not stage.resolve().is_relative_to(root):raise ValueError('invalid additional circle stage path')
    s=json.loads(stage.read_text(encoding='utf8'));rows=s.get('screens');ph=s.get('policy_map_sha256')
    if (s.get('status')!='additional_circle_screens_required' or s.get('source_sha256')!=source_hash or s.get('graph_sha256')!=graph_hash or s.get('hil_ready') is not False or not isinstance(rows,list) or not rows or not isinstance(ph,str) or len(ph)!=64 or any(c not in '0123456789abcdef' for c in ph)):raise ValueError('invalid additional circle stage')
    result=[];radii=set()
    for i,row in enumerate(rows,1):
        path=f'reports/source-circle-rim-extra-{i}.json';p=(root/path).resolve();radius=row.get('radius');policy=row.get('policy_sha256')
        if (row.get('path')!=path or not p.is_relative_to(root) or not p.is_file() or isinstance(radius,bool) or not isinstance(radius,(int,float)) or not math.isfinite(radius) or radius<=0 or radius in radii or not isinstance(policy,str) or len(policy)!=64 or any(c not in '0123456789abcdef' for c in policy) or row.get('evidence_sha256')!=hashlib.sha256(p.read_bytes()).hexdigest()):raise ValueError('invalid additional circle evidence')
        e=json.loads(p.read_text(encoding='utf8'))
        if e.get('source_sha256')!=source_hash or e.get('graph_sha256')!=graph_hash or e.get('circle_radius')!=radius or e.get('policy_sha256')!=policy or e.get('graph_mutated') is not False or e.get('hil_ready') is not False:raise ValueError('stale additional circle evidence')
        radii.add(radius);result.append({'path':path,'sha256':row['evidence_sha256'],'binding':'current_graph','kind':'source_circle_rim_screen'})
    return result

def final_plan_line_blockers(root,graph_hash,source_hash,graph):
    root=Path(root).resolve();screen=root/'reports/final-plan-line-inventory.json';stage=root/'reports/final-plan-line-stage.json'
    declaration=root/'plan-line-required.json';coincident=root/'reports/final-coincident-source-segments.json'
    if declaration.exists():
        if not declaration.is_file() or not declaration.resolve().is_relative_to(root):raise ValueError('invalid plan line declaration path')
        d=json.loads(declaration.read_text(encoding='utf8'));policy=d.get('policy_map_sha256')
        if (d.get('status')!='required_plan_line_screen' or d.get('source_sha256')!=source_hash or d.get('graph_sha256')!=graph_hash or not isinstance(policy,str) or len(policy)!=64 or any(c not in '0123456789abcdef' for c in policy) or d.get('evidence_path')!='reports/final-plan-line-inventory.json' or d.get('stage_path')!='reports/final-plan-line-stage.json' or d.get('coincident_path')!='reports/final-coincident-source-segments.json' or d.get('hil_ready') is not False):raise ValueError('invalid plan line declaration')
        if any(not p.is_file() or not p.resolve().is_relative_to(root) for p in (screen,stage,coincident)):raise ValueError('required plan line stage missing')
    if not screen.exists() and not stage.exists():return []
    if any(not p.is_file() or not p.resolve().is_relative_to(root) for p in (screen,stage)):raise ValueError('missing final plan line evidence')
    e=json.loads(screen.read_text(encoding='utf8'));s=json.loads(stage.read_text(encoding='utf8'));rows=e.get('records');edges={x['edge_id']:x for x in graph.get('edges',[])}
    if (e.get('status')!='final_plan_line_handle_inventory_not_acceptance' or s.get('status')!=e['status'] or e.get('source_sha256')!=source_hash or s.get('source_sha256')!=source_hash or e.get('graph_sha256')!=graph_hash or s.get('graph_sha256')!=graph_hash or s.get('evidence_sha256')!=hashlib.sha256(screen.read_bytes()).hexdigest() or e.get('graph_mutated') is not False or e.get('human_accepted') is not False or e.get('hil_ready') is not False or s.get('hil_ready') is not False or not isinstance(rows,list)):raise ValueError('invalid final plan line evidence')
    statuses={'source_handle_referenced','source_handle_system_conflict','shorter_than_normalization_tolerance_unclassified','coincident_referenced_source_candidate','unreferenced_source_line_unclassified'};out=[];seen=set()
    for x in rows:
        h=x.get('source_handle');state=x.get('status');direct=x.get('direct_edge_ids')
        if not h or h in seen or state not in statuses or x.get('physical_identity_resolved') is not False or not isinstance(direct,list) or len(set(direct))!=len(direct) or any(i not in edges or h not in edges[i].get('source_handles',[]) for i in direct):raise ValueError('invalid final plan line row')
        if state=='source_handle_referenced' and (not direct or any(edges[i].get('system')!=x.get('system') for i in direct)):raise ValueError('invalid referenced source line')
        if state in ('shorter_than_normalization_tolerance_unclassified','coincident_referenced_source_candidate','unreferenced_source_line_unclassified') and direct:raise ValueError('unreferenced line has direct edge')
        seen.add(h)
        if state!='source_handle_referenced':out.append({'source_handle':h,'system':x.get('system'),'status':state,'coincident_referenced_sources':x.get('coincident_referenced_sources',[])})
    if s.get('candidate_count')!=len(out):raise ValueError('final plan line count mismatch')
    if declaration.exists():
        c=json.loads(coincident.read_text(encoding='utf8'));records=c.get('records')
        if (s.get('coincident_evidence_sha256')!=hashlib.sha256(coincident.read_bytes()).hexdigest() or c.get('status')!='coincident_source_segments_not_physical_identity' or c.get('source_sha256')!=source_hash or c.get('graph_sha256')!=graph_hash or c.get('inventory_sha256')!=hashlib.sha256(screen.read_bytes()).hexdigest() or c.get('graph_mutated') is not False or c.get('human_accepted') is not False or c.get('hil_ready') is not False or not isinstance(records,list)):raise ValueError('invalid coincident plan line evidence')
        handles=[x.get('unreferenced_source_handle') for x in records]
        if len(handles)!=len(set(handles)) or set(handles)!={x['source_handle'] for x in rows if x['status']=='coincident_referenced_source_candidate'} or any(x.get('physical_identity_resolved') is not False for x in records):raise ValueError('coincident source candidate mismatch')
    if 'micro_family_evidence_sha256' in s:
        family_path=root/'reports/final-micro-line-families.json'
        if not family_path.is_file() or not family_path.resolve().is_relative_to(root) or hashlib.sha256(family_path.read_bytes()).hexdigest()!=s['micro_family_evidence_sha256']:raise ValueError('micro line family evidence missing or stale')
        f=json.loads(family_path.read_text(encoding='utf8'));families=f.get('families');ungrouped=f.get('ungrouped_source_handles');short={x['source_handle'] for x in rows if x['status']=='shorter_than_normalization_tolerance_unclassified'}
        if (f.get('status')!='micro_line_families_not_classification' or f.get('source_sha256')!=source_hash or f.get('graph_sha256')!=graph_hash or f.get('inventory_sha256')!=hashlib.sha256(screen.read_bytes()).hexdigest() or f.get('graph_mutated') is not False or f.get('human_accepted') is not False or f.get('hil_ready') is not False or not isinstance(families,list) or not isinstance(ungrouped,list)):raise ValueError('invalid micro line family evidence')
        nodes={n['node_id']:n for n in graph.get('nodes',[])};members=[];by_handle={x['source_handle']:x for x in out}
        for index,family in enumerate(families,1):
            if family.get('status')!='same_source_geometry_unclassified' or not isinstance(family.get('members'),list) or not family['members']:raise ValueError('invalid micro line family')
            for member in family['members']:
                h=member.get('source_handle');nid=member.get('node_id');node=nodes.get(nid);incident=sorted(eid for eid,edge in edges.items() if nid in (edge.get('start_node_id'),edge.get('end_node_id')))
                if h not in short or not node or node.get('node_type')!='tee' or incident!=member.get('incident_edge_ids') or len(incident)!=3 or any(edges[eid].get('system')!=family.get('system') for eid in incident) or by_handle[h]['system']!=family.get('system') or not member.get('circle_handle'):raise ValueError('invalid micro line family member')
                members.append(h);by_handle[h]['source_geometry_family']=f'MICRO-{index:03d}'
        combined=members+ungrouped
        if len(combined)!=len(set(combined)) or set(combined)!=short or f.get('source_handle_count')!=len(short):raise ValueError('micro line family scope mismatch')
    if graph.get('confirmedSideviewCanonicalization') is not None:
        alternate=confirmed_sideview_source_handles(root,graph_hash,graph)
        out=[x for x in out if not (x['status']=='unreferenced_source_line_unclassified' and x['source_handle'] in alternate)]
    return out

def compound_dn_context(root,graph_hash,source_hash,graph):
    root=Path(root).resolve();screen=root/'reports/final-compound-dn-evidence.json';stage=root/'reports/final-compound-dn-stage.json'
    declaration=root/'compound-dn-required.json'
    if declaration.exists():
        if not declaration.is_file() or not declaration.resolve().is_relative_to(root):raise ValueError('invalid compound DN declaration path')
        d=json.loads(declaration.read_text(encoding='utf8'))
        if (d.get('status')!='required_compound_dn_screen' or d.get('source_sha256')!=source_hash or d.get('graph_sha256')!=graph_hash or not isinstance(d.get('policy_map_sha256'),str) or len(d['policy_map_sha256'])!=64 or any(c not in '0123456789abcdef' for c in d['policy_map_sha256']) or d.get('evidence_path')!='reports/final-compound-dn-evidence.json' or d.get('stage_path')!='reports/final-compound-dn-stage.json' or d.get('hil_ready') is not False):raise ValueError('invalid compound DN declaration')
        if not screen.is_file() or not stage.is_file():raise ValueError('required compound DN stage missing')
    if not screen.exists() and not stage.exists():return []
    if any(not p.is_file() or not p.resolve().is_relative_to(root) for p in (screen,stage)):raise ValueError('missing compound DN evidence')
    s=json.loads(stage.read_text(encoding='utf8'));e=json.loads(screen.read_text(encoding='utf8'));rows=e.get('records');ids={x['edge_id'] for x in graph.get('edges',[])}
    if (e.get('status')!='compound_dn_text_evidence_not_binding' or s.get('status')!=e['status'] or e.get('source_sha256')!=source_hash or s.get('source_sha256')!=source_hash or e.get('graph_sha256')!=graph_hash or s.get('graph_sha256')!=graph_hash or s.get('evidence_sha256')!=hashlib.sha256(screen.read_bytes()).hexdigest() or e.get('graph_mutated') is not False or e.get('human_accepted') is not False or e.get('hil_ready') is not False or s.get('hil_ready') is not False or not isinstance(rows,list) or s.get('candidate_count')!=len(rows)):raise ValueError('invalid compound DN stage')
    out=[];seen=set()
    for row in rows:
        text=row.get('source_text',{});handle=text.get('handle');values=row.get('values_in_text_order');candidates=row.get('candidate_edge_ids')
        if (not handle or handle in seen or text.get('source_sha256')!=source_hash or not isinstance(text.get('text'),str) or not text['text'] or row.get('status')!='compound_values_unbound' or row.get('edge_binding_confirmed') is not False or row.get('human_accepted') is not False or row.get('parenthesized_value_meaning')!='uninterpreted' or not isinstance(values,list) or len(values)!=2 or [x.get('order_in_text') for x in values]!=[1,2] or any(isinstance(x.get('nominal_mm'),bool) or not isinstance(x.get('nominal_mm'),(int,float)) or not math.isfinite(x['nominal_mm']) or x['nominal_mm']<=0 for x in values) or not isinstance(candidates,list) or len(candidates)!=len(set(candidates)) or not set(candidates)<=ids):raise ValueError('invalid compound DN record')
        seen.add(handle);out.append({'source_handle':handle,'text':text['text'],'candidate_edge_ids':candidates,'status':'compound_dn_edge_binding_unverified'})
    return out

def detail_frame_context(root,graph_hash,source_hash):
    root=Path(root).resolve();screen=root/'reports/source-detail-frame-context.json';stage=root/'reports/source-detail-frame-context-stage.json';glyph=root/'reports/source-detail-glyph-ambiguity.json'
    if not screen.exists() and not stage.exists():return []
    if any(not p.is_file() or not p.resolve().is_relative_to(root) for p in (screen,stage,glyph)):raise ValueError('missing detail frame evidence')
    s=json.loads(stage.read_text(encoding='utf8'));e=json.loads(screen.read_text(encoding='utf8'));g=json.loads(glyph.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=e.get('candidate_rows');frames=e.get('frames')
    if (e.get('status')!='source_dashed_frame_context_not_mapping' or s.get('status')!=e['status'] or e.get('source_sha256')!=source_hash or s.get('source_sha256')!=source_hash or e.get('graph_sha256')!=graph_hash or s.get('graph_sha256')!=graph_hash or e.get('glyphs_sha256')!=sha(glyph) or s.get('evidence_sha256')!=sha(screen) or e.get('policy_sha256')!=s.get('policy_sha256') or e.get('mapping_ready') is not False or s.get('mapping_ready') is not False or e.get('human_accepted') is not False or e.get('graph_mutated') is not False or e.get('hil_ready') is not False or s.get('hil_ready') is not False or not isinstance(rows,list) or not isinstance(frames,list) or s.get('candidate_count')!=len(rows)):raise ValueError('invalid detail frame context')
    ids=[f.get('frame_id') for f in frames]
    if len(ids)!=len(set(ids)) or any(not x for x in ids):raise ValueError('invalid detail frame identities')
    keys=lambda rr:[(x.get('system'),x.get('rank'),x.get('upper_edge'),x.get('detail_edge')) for x in rr]
    if keys(rows)!=keys(g.get('rows',[])) or len(keys(rows))!=len(set(keys(rows))):raise ValueError('detail frame candidate mismatch')
    if any(r.get('status')!='source_frame_context_not_individual_mapping' or not isinstance(r.get('shared_frame_candidates'),list) or not set(r['shared_frame_candidates']).issubset(ids) for r in rows):raise ValueError('invalid detail frame row')
    if s.get('relative_evidence_sha256') is not None:
        rp=root/'reports/source-detail-frame-relative-candidates.json'
        if not rp.is_file() or not rp.resolve().is_relative_to(root) or sha(rp)!=s['relative_evidence_sha256']:raise ValueError('missing relative frame evidence')
        relative=json.loads(rp.read_text(encoding='utf8'));records=relative.get('records')
        if (relative.get('status')!='frame_relative_position_not_mapping' or relative.get('source_sha256')!=source_hash or relative.get('graph_sha256')!=graph_hash or relative.get('glyphs_sha256')!=sha(glyph) or relative.get('frames_sha256')!=sha(screen) or relative.get('script_sha256')!=s.get('relative_script_sha256') or relative.get('mapping_ready') is not False or relative.get('human_accepted') is not False or relative.get('graph_mutated') is not False or not isinstance(records,list) or len(records)!=len(rows)):raise ValueError('invalid relative frame evidence')
        if [(r.get('system'),r.get('rank'),r.get('upper_edge'),r.get('proposed_detail_edge')) for r in records]!=keys(rows) or any(r.get('status')!='regional_position_evidence_not_mapping' for r in records):raise ValueError('relative frame candidate mismatch')
    out=[{'system':r['system'],'rank':r['rank'],'status':'individual_mapping_unverified','shared_frames':r['shared_frame_candidates']} for r in rows]
    if s.get('boundary_evidence_sha256') is not None:
        bp=root/'reports/source-detail-frame-boundary-candidates.json';scope=root/'reports/detail-scope-coverage.json';boundaries=root/'reports/detail-boundary-coverage.json'
        if any(not p.is_file() or not p.resolve().is_relative_to(root) for p in (bp,scope,boundaries)) or sha(bp)!=s['boundary_evidence_sha256']:raise ValueError('missing frame boundary evidence')
        b=json.loads(bp.read_text(encoding='utf8'));prior=json.loads(boundaries.read_text(encoding='utf8'));br=b.get('records')
        if (b.get('status')!='frame_boundary_candidates_not_mapping' or b.get('source_sha256')!=source_hash or b.get('graph_sha256')!=graph_hash or b.get('frames_sha256')!=sha(screen) or b.get('scope_sha256')!=sha(scope) or b.get('boundaries_sha256')!=sha(boundaries) or b.get('script_sha256')!=s.get('boundary_script_sha256') or b.get('mapping_ready') is not False or b.get('human_accepted') is not False or b.get('graph_mutated') is not False or not isinstance(br,list) or len(br)!=len(prior.get('rows',[]))):raise ValueError('invalid frame boundary evidence')
        bkeys=lambda rr:[(x.get('system'),x.get('upper_glyph'),x.get('detail_boundary'),x.get('detail_edge')) for x in rr]
        if bkeys(br)!=bkeys(prior['rows']) or any(r.get('status')!='source_frame_boundary_context_not_mapping' or r.get('boundary_kind') not in ('expert_non_node_source_boundary','user_confirmed_non_node_source_boundary') or r.get('frame_id') not in ids for r in br):raise ValueError('frame boundary candidate mismatch')
        out.extend({'system':r['system'],'upper_glyph':r['upper_glyph'],'detail_boundary':r['detail_boundary'],'status':'individual_mapping_unverified','shared_frames':[r['frame_id']]} for r in br)
    return out

def check_confirmed_gap_joint_graph(root,report,graph_hash,graph_path):
    """Reuse parent geometry only after replaying an inventory-only child stage."""
    import copy,sys
    root=Path(root).resolve();graph_path=Path(graph_path).resolve()
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_confirmed_gap_joints import verify_output
    audit=verify_output(graph_path.parent)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:
        raise ValueError('gap-joint graph is outside its verified stage')
    policy=json.loads(Path(audit['inputs']['policy']['path']).read_text(encoding='utf8'))
    parent=Path(audit['inputs']['graph']['path']).resolve();parent_root=Path(policy['parent_task_root']).resolve()
    if not parent.is_relative_to(parent_root):raise ValueError('gap-joint parent graph is outside its task')
    report_path=parent_root/'source-comparison-report.json';receipt_path=parent_root/'rebuild-receipt.json'
    for path,key in [(report_path,'parent_report_sha256'),(receipt_path,'parent_receipt_sha256')]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=policy[key]:raise ValueError('stale gap-joint parent comparison')
    parent_hash=audit['inputs']['graph']['sha256'];prior=json.loads(report_path.read_text(encoding='utf8'))
    receipt=json.loads(receipt_path.read_text(encoding='utf8'))
    if report!=prior or receipt.get('final_graph_sha256')!=parent_hash:raise ValueError('gap-joint parent report or graph differs')
    result=copy.deepcopy(check(prior,parent_hash,parent_root,parent))
    old=result.get('missing_gap_joint_blockers',[]);confirmed={r['insert_handle'] for r in audit['records']}
    matched={r.get('source_handle') for r in old if r.get('source_handle') in confirmed}
    if matched!=confirmed:raise ValueError('confirmed gap joints do not match parent candidate scope')
    remaining=[r for r in old if r.get('source_handle') not in confirmed]
    result['pending']=[p for p in result['pending'] if p!=f'{len(old)} source joint candidates require comparison']
    if remaining:result['pending'].append(f'{len(remaining)} source joint candidates require comparison')
    result['missing_gap_joint_blockers']=remaining
    result.update(status='failed' if result['errors'] else 'pending' if result['pending'] else 'completed',
        hil_ready=not result['errors'] and not result['pending'],graph_sha256=graph_hash,
        confirmed_gap_joint_stage=dict(source_replay='passed',confirmed_handles=sorted(confirmed),
            parent_graph_sha256=parent_hash,parent_report_sha256=policy['parent_report_sha256'],
            canonical_inventory_sha256=hashlib.sha256((root/'edge_device_instances.csv').read_bytes()).hexdigest(),
            geometry_reused_only_because_paths_and_nodes_unchanged=True,physical_lengths='unknown',human_accepted=False))
    return result

def check_crossview_attribute_graph(root,report,graph_hash,graph_path):
    import copy,sys
    root=Path(root).resolve();graph_path=Path(graph_path).resolve()
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_crossview_plan_attributes import verify_output
    audit=verify_output(graph_path.parent)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:raise ValueError('cross-view graph outside verified attribute stage')
    parent=Path(audit['parent_graph']['path']).resolve()
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=audit['parent_graph']['sha256']:raise ValueError('cross-view local parent changed')
    prior=json.loads(Path(audit['inputs']['parent_report']['path']).read_text(encoding='utf8'))
    if report!=prior:raise ValueError('cross-view parent comparison differs')
    result=copy.deepcopy(check(prior,audit['parent_graph']['sha256'],parent.parent,parent))
    disagreements=sum(r['diameter_status']=='candidate_disagreement_unresolved' for r in audit['records'])
    if disagreements:result['pending'].append(f'{disagreements} cross-view diameter candidate disagreements require source attribution')
    result['pending'].append('cross-view plan projection is partial; same-floor drops, equipment connections and whole-edge physical lengths remain unknown')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,
        crossview_attribute_stage=dict(source_replay='passed',local_parent_graph_sha256=audit['parent_graph']['sha256'],
            records=audit['records'],whole_edge_physical_lengths_complete=False,human_accepted=False))
    return result


def check_equipment_identity_layout_graph(root,report,graph_hash,graph_path):
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from resolve_rotated_equipment_labels import verify_output
    graph_path=Path(graph_path).resolve();root=Path(root).resolve();audit=verify_output(graph_path.parent)
    if (graph_path.name!='graph_with_edges.json' or graph_path.parent not in (root,root/'topology-rotated-equipment-identity')
        or audit['output_graph_sha256']!=graph_hash):raise ValueError('identity graph outside verified layout stage')
    parent=Path(audit['parent_graph']['path']).resolve()
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=audit['parent_graph']['sha256']:raise ValueError('layout parent graph changed')
    if report.get('graph_sha256')!=audit['parent_graph']['sha256']:raise ValueError('layout comparison must bind the unchanged local parent')
    parent_root=parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
    result=copy.deepcopy(check(report,audit['parent_graph']['sha256'],parent_root,parent))
    result['pending'].append('equipment labels source-checked; device port ownership, cross-view correspondence and human acceptance remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,
        equipment_identity_layout_stage=dict(source_replay='passed',records=audit['records'],parent_graph_sha256=audit['parent_graph']['sha256'],
            equipment_instances_conserved=True,source_paths_unchanged=True,ports_verified=False,human_accepted=False))
    return result

def check_named_riser_plan_attribute_graph(root,report,graph_hash,graph_path):
    """Replay named approach fusion and retain every complete-parent issue."""
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_named_riser_plan_attributes import verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(root)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:
        raise ValueError('named approach fusion outside verified output')
    if (audit.get('prior_edges_and_vertical_attributes_preserved') is not True
        or audit.get('physical_ports_verified') is not False or audit.get('whole_edge_DN_assigned')!=0
        or audit.get('installed_lengths_assigned')!=0 or audit.get('related_HIL_confirmation_inherited') is not False):
        raise ValueError('named approach fusion preservation or physical extent differs')
    parent=Path(audit['parent_graph']['path']);parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('named approach parent changed')
    cached=parent.parent/'source-comparison-gate.json';previous=json.loads(cached.read_text(encoding='utf8'))
    if previous.get('graph_sha256')!=parent_hash or report!=previous:raise ValueError('named approach comparison requires exact complete parent context')
    if not isinstance(previous.get('errors'),list) or not isinstance(previous.get('pending'),list):raise ValueError('named approach parent issue lists missing')
    result=copy.deepcopy(previous)
    result['pending'].append('named floor approaches have checked plan DN and XY projection only; physical interface/connector extent, other floors, explicit axis vertical lengths and whole drawing/human acceptance remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        named_riser_plan_attribute_stage=dict(source_replay='passed',added_axis_edges=audit['added_axis_edges'],
            records=audit['records'],plan_DN_scope_fusion=audit['plan_DN_scope_fusion'],
            source_scope_sha256=audit['source_scope_sha256'],mapping_sha256=audit['mapping_sha256'],
            prior_graph_sha256=parent_hash,prior_graph_comparison_sha256=hashlib.sha256(cached.read_bytes()).hexdigest(),
            prior_plan_vertical_and_component_fields_preserved=True,whole_edge_DN_assigned=0,installed_lengths_assigned=0,human_accepted=False))
    return result


def check_axis_riser_attribute_graph(root,report,graph_hash,graph_path):
    """Replay segment-only axis values and preserve the complete parent check."""
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_axis_riser_segment_attributes import verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(root)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:raise ValueError('axis riser attributes outside verified output')
    if (audit.get('all_prior_plan_attributes_preserved') is not True or audit.get('local_topology_and_components_preserved') is not True
        or audit.get('whole_edge_DN_assigned')!=0 or audit.get('installed_lengths_assigned')!=0
        or audit.get('related_prior_HIL_confirmation_inherited') is not False):raise ValueError('axis segment attachment preservation or extent differs')
    parent=Path(audit['parent_graph']['path']);parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('axis segment attribute parent changed')
    cached=parent.parent/'source-comparison-gate.json';previous=json.loads(cached.read_text(encoding='utf8'))
    if previous.get('graph_sha256')!=parent_hash or report!=previous:raise ValueError('axis segment comparison requires exact complete parent context')
    if not isinstance(previous.get('errors'),list) or not isinstance(previous.get('pending'),list):raise ValueError('axis segment parent issue lists missing')
    result=copy.deepcopy(previous);result['pending'].append('axis DN checked only on declared native vertical segment domains; horizontal approaches need floor-plan mapping, explicit axis physical lengths and whole drawing/human acceptance remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        axis_riser_segment_attribute_stage=dict(source_replay='passed',segments=audit['added_segment_attributes'],affected_axis_edges=audit['affected_axis_edges'],
            source_scope_sha256=audit['source_scope_sha256'],prior_graph_sha256=parent_hash,prior_graph_comparison_sha256=hashlib.sha256(cached.read_bytes()).hexdigest(),
            prior_plan_attributes_preserved=True,whole_edge_DN_assigned=0,installed_lengths_assigned=0,human_accepted=False))
    return result


def check_refined_paired_attribute_graph(root,report,graph_hash,graph_path):
    """Replay the replacement child; carry exact nonpaired source issues."""
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from compose_refined_paired_plan_attributes import verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(root)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:raise ValueError('refined composition outside verified output')
    if (audit.get('all_prior_attribute_values_preserved') is not True or audit.get('old_nodes_edges_source_roots_and_components_preserved') is not True
        or audit.get('coarse_paired_child_not_added') is not True or audit.get('related_prior_HIL_confirmation_inherited') is not False):raise ValueError('refined composition preservation or replacement state differs')
    parent=Path(audit['parent_graph']['path']);parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('refined composition base changed')
    cached=parent.parent/'source-comparison-gate.json';previous=json.loads(cached.read_text(encoding='utf8'))
    if previous.get('graph_sha256')!=parent_hash or report!=previous:raise ValueError('refined comparison requires the exact nonpaired base comparison context')
    if not isinstance(previous.get('errors'),list) or not isinstance(previous.get('pending'),list):raise ValueError('nonpaired comparison lacks issue lists')
    result=copy.deepcopy(previous);result['pending'].append('native junction-refined mapping, plan DN and allocated horizontal mains are checked only in the declared replacement scope; unshown connectors, other routes, vertical metrics, full comparison and human acceptance remain pending')
    dn=audit['plan_DN_scope_fusion']
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        refined_paired_attribute_stage=dict(source_replay='passed',records=audit['records'],added_axis_edges=audit['added_axis_edges'],
            plan_drawn_DN_edges=sum(r['plan_drawn_nominal_mm'] is not None for r in dn),complete_horizontal_main_DN_and_centerline_edges=sum(r['whole_main_DN_and_centerline_route'] for r in dn),
            superseded_mapping_records=audit['superseded_mapping_records'],coarse_child_replaced_not_added=True,
            prior_graph_comparison_sha256=hashlib.sha256(cached.read_bytes()).hexdigest(),prior_graph_sha256=parent_hash,
            comparison_reuse_basis='independent_native_replay_plus_exact_preservation_of_all_prior_nonpaired_data_and_attributes',
            original_issues_retained=True,expert_confirmation_claimed=False,human_accepted=False))
    return result


def check_paired_attribute_graph(root,report,graph_hash,graph_path):
    """Replay the extension; retain comparison of exactly unchanged old data."""
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from compose_paired_plan_attribute_scope import verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(root)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:raise ValueError('paired extension outside verified output')
    if audit.get('all_prior_attribute_values_preserved') is not True or audit.get('old_nodes_edges_source_roots_and_components_preserved') is not True:raise ValueError('paired extension did not preserve the prior local graph')
    parent=Path(audit['parent_graph']['path']);parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('paired extension base changed')
    cached=parent.parent/'source-comparison-gate.json';previous=json.loads(cached.read_text(encoding='utf8'))
    if previous.get('graph_sha256')!=parent_hash or report!=previous:raise ValueError('paired comparison requires the exact prior graph comparison context')
    if not isinstance(previous.get('errors'),list) or not isinstance(previous.get('pending'),list):raise ValueError('prior comparison has no explicit issue lists')
    result=copy.deepcopy(previous);result['pending'].append('paired service plan DN and horizontal metrics are checked only in the declared added scope; intermediate route allocation, unshown connectors, full comparison and human acceptance remain pending')
    dn=audit['plan_DN_scope_fusion']
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        paired_plan_attribute_stage=dict(source_replay='passed',records=audit['records'],added_axis_edges=audit['added_axis_edges'],
            plan_drawn_DN_edges=sum(r['plan_drawn_nominal_mm'] is not None for r in dn),complete_horizontal_main_DN_and_centerline_edges=sum(r['whole_main_DN_and_centerline_route'] for r in dn),
            prior_graph_comparison_sha256=hashlib.sha256(cached.read_bytes()).hexdigest(),prior_graph_sha256=parent_hash,
            comparison_reuse_basis='independent_native_replay_plus_exact_preservation_of_all_prior_local_data_and_attributes',
            original_issues_retained=True,expert_confirmation_claimed=False,human_accepted=False))
    return result


def check_source_checked_attribute_graph(root,report,graph_hash,graph_path):
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from compose_source_checked_plan_scopes import verify_attribute_output as verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(graph_path.parent)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:raise ValueError('source-checked attribute graph outside its verified stage')
    parent=Path(audit['parent_graph']['path']).resolve();parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('source-checked attribute parent changed')
    result=copy.deepcopy(check(report,parent_hash,parent.parent,parent))
    dn=audit.get('plan_DN_scope_fusion')
    if dn is None:
        result['pending'].append('source-checked branch/main correspondence and plan projections remain scoped; DN inheritance, whole installed lengths and human acceptance require further checks')
    else:
        result['pending'].append('plan DN inheritance and complete horizontal main centerline routes are checked only in declared scopes; unseen equipment connectors, other routes, net pipe cut lengths and human acceptance remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,
        source_checked_crossview_attribute_stage=dict(source_replay='passed',records=audit['records'],parent_graph_sha256=parent_hash,
            prior_attributes_preserved=True,expert_confirmation_claimed=False,human_accepted=False))
    if dn is not None:
        result['source_checked_crossview_attribute_stage'].update(plan_DN_scope_replay='passed',
            plan_drawn_DN_edges=sum(r['plan_drawn_nominal_mm'] is not None for r in dn),
            complete_horizontal_main_DN_and_centerline_edges=sum(r['whole_main_DN_and_centerline_route'] for r in dn),
            net_pipe_cut_lengths_complete=False)
    return result


def check_native_block_branch_graph(root,report,graph_hash,graph_path):
    """Validate changed source paths, preserving the original parent comparison."""
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from reconstruct_native_block_branches import verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(graph_path.parent)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:raise ValueError('native block branch graph outside verified stage')
    parent=Path(audit['parent_graph']['path']).resolve();parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('native block branch parent changed')
    parent_root=parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
    result=copy.deepcopy(check(report,parent_hash,parent_root,parent))
    graph=json.loads(graph_path.read_text(encoding='utf8'));state=graph['sourceNativeBlockBranchReconstruction']
    result['pending'].append('native block source paths changed: recompute affected DN attribution, lengths, cross-view mapping and human review')
    if state['pending']:result['pending'].append(f"{len(state['pending'])} selected block endpoint chains still require source comparison")
    result.update(status='failed' if result['errors'] else 'pending',hil_ready=False,graph_sha256=graph_hash,
        native_block_branch_stage=dict(source_replay='passed',parent_graph_sha256=parent_hash,
            reconstructed_edges=[r['edge_id'] for r in state['records']],unresolved_edges=state['pending'],
            physical_ports_verified=False,components_conserved=True,human_accepted=False))
    return result


def check_layout_equipment_ownership_graph(root,report,graph_hash,graph_path):
    """Replay calibrated ownership, then reassess only current graph blockers.

    The comparison report belongs to the original local-screen ancestor.  Its
    hash must be checked by that ancestor, not rebound to an intermediate graph.
    """
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from calibrated_ownership_scope_composition import verify_ownership_output as verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve()
    audit=verify_output(graph_path.parent)
    if (graph_path.name!='graph_with_edges.json'
        or graph_path.parent not in (root,root/'topology-source-layout-equipment-ownership')
        or audit['output_graph_sha256']!=graph_hash):raise ValueError('ownership graph outside verified source-layout stage')
    parent=Path(audit['parent_graph']['path']).resolve();parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('ownership parent graph changed')
    if graph_path.parent!=root:
        stage=json.loads((root/'reports/source-layout-equipment-ownership-stage.json').read_text(encoding='utf8'))
        if (stage.get('artifact_directory')!=str(graph_path.parent)
            or stage.get('graph_sha256')!=graph_hash or stage.get('parent_graph_sha256')!=parent_hash
            or stage.get('source_sha256')!=audit['inputs']['source']['sha256']
            or stage.get('audit_sha256')!=hashlib.sha256((graph_path.parent/'calibrated-equipment-ownership-audit.json').read_bytes()).hexdigest()
            or stage.get('hil_ready') is not False):raise ValueError('stale ownership stage receipt')
    parent_root=parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
    result=copy.deepcopy(check(report,parent_hash,parent_root,parent))
    graph=json.loads(graph_path.read_text(encoding='utf8'))
    result['ownership_parent_comparison']=copy.deepcopy(result)
    # Remove only exact messages emitted for these three graph-bound lists.
    # All native screen/report blockers and parent errors remain in force.
    replacements=[('equipment_source_port_blockers','equipment nodes have unresolved source-port ownership',equipment_comparison_blockers(graph)),
        ('graph_unresolved_node_blockers','graph nodes have unresolved source-terminal or equipment-overlap semantics',graph_comparison_blockers(graph)[0])]
    for key,message,current in replacements:
        old=result.get(key,[])
        prior=f'{len(old)} {message}'
        result['pending']=[p for p in result['pending'] if p!=prior]
        result[key]=current
        if current:result['pending'].append(f'{len(current)} {message}')
    old_families=result.get('graph_algorithm_family_blockers',[])
    result['pending']=[p for p in result['pending'] if p not in ['graph algorithm family not consumed: '+str(f) for f in old_families]]
    result['graph_algorithm_family_blockers']=graph_comparison_blockers(graph)[1]
    result['pending'].extend('graph algorithm family not consumed: '+str(f) for f in result['graph_algorithm_family_blockers'])
    result['pending']=[p for p in result['pending'] if p!='equipment labels source-checked; device port ownership, cross-view correspondence and human acceptance remain pending']
    result['pending'].append('source-calibrated logical equipment ownership; physical ports, unshown connector lengths, cross-view correspondence and human acceptance remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,
        source_layout_equipment_ownership_stage=dict(source_replay='passed',records=audit['records'],parent_graph_sha256=parent_hash,
            equipment_instances_conserved=True,source_paths_unchanged=True,physical_ports_verified=False,human_accepted=False))
    return result


def check_sideview_equipment_ownership_graph(root,report,graph_hash,graph_path):
    """Replay the new owner stage without rebinding its ancestor comparison."""
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from reconstruct_sideview_equipment_ownership import verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve()
    audit=verify_output(graph_path.parent)
    if (graph_path.name!='graph_with_edges.json'
        or graph_path.parent not in (root,root/'topology-source-sideview-equipment-ownership')
        or audit['output_graph_sha256']!=graph_hash):raise ValueError('sideview ownership graph outside verified stage')
    parent=Path(audit['parent_graph']['path']).resolve();parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('sideview ownership parent graph changed')
    if graph_path.parent!=root:
        stage=json.loads((root/'reports/source-sideview-equipment-ownership-stage.json').read_text(encoding='utf8'))
        if (stage.get('status')!='native_confirmed_sideview_logical_ownership_source_checked'
            or stage.get('artifact_directory')!=str(graph_path.parent)
            or stage.get('graph_sha256')!=graph_hash or stage.get('parent_graph_sha256')!=parent_hash
            or stage.get('source_sha256')!=audit['inputs']['source']['sha256']
            or stage.get('audit_sha256')!=hashlib.sha256((graph_path.parent/'sideview-equipment-ownership-audit.json').read_bytes()).hexdigest()
            or stage.get('hil_ready') is not False or stage.get('physical_ports_verified') is not False
            or stage.get('detail_view_metric_verified') is not False):raise ValueError('stale sideview ownership stage receipt')
    parent_root=parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
    result=copy.deepcopy(check(report,parent_hash,parent_root,parent))
    graph=json.loads(graph_path.read_text(encoding='utf8'))
    result['sideview_ownership_parent_comparison']=copy.deepcopy(result)
    replacements=[('equipment_source_port_blockers','equipment nodes have unresolved source-port ownership',equipment_comparison_blockers(graph)),
        ('graph_unresolved_node_blockers','graph nodes have unresolved source-terminal or equipment-overlap semantics',graph_comparison_blockers(graph)[0])]
    for key,message,current in replacements:
        prior=f'{len(result.get(key,[]))} {message}'
        result['pending']=[p for p in result['pending'] if p!=prior];result[key]=current
        if current:result['pending'].append(f'{len(current)} {message}')
    prior_families=result.get('graph_algorithm_family_blockers',[])
    result['pending']=[p for p in result['pending'] if p not in ['graph algorithm family not consumed: '+str(f) for f in prior_families]]
    result['graph_algorithm_family_blockers']=graph_comparison_blockers(graph)[1]
    result['pending'].extend('graph algorithm family not consumed: '+str(f) for f in result['graph_algorithm_family_blockers'])
    result['pending'].append('confirmed-view logical ownership replayed; physical ports, detail-view metrics, cross-view attributes and human acceptance remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,
        source_sideview_equipment_ownership_stage=dict(source_replay='passed',records=audit['records'],parent_graph_sha256=parent_hash,
            source_paths_unchanged=True,equipment_instances_conserved=True,physical_ports_verified=False,detail_view_metric_verified=False,human_accepted=False))
    return result


def check_known_project_erratum_graph(root,report,graph_hash,graph_path):
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from apply_known_project_pipe_erratum import verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(graph_path.parent)
    if graph_path.name!='graph_with_edges.json' or graph_path.parent not in (root,root/'topology-project-known-erratum') or audit['output_graph_sha256']!=graph_hash:raise ValueError('project erratum outside verified stage')
    parent=Path(audit['parent_graph']['path']);parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('project erratum parent changed')
    if graph_path.parent!=root:
        stage=json.loads((root/'reports/project-known-erratum-stage.json').read_text(encoding='utf8'))
        if stage.get('graph_sha256')!=graph_hash or stage.get('parent_graph_sha256')!=parent_hash or stage.get('artifact_directory')!=str(graph_path.parent) or stage.get('audit_sha256')!=hashlib.sha256((graph_path.parent/'project-known-erratum-audit.json').read_bytes()).hexdigest() or stage.get('hil_ready') is not False:raise ValueError('stale project erratum full-entry receipt')
    parent_root=parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
    result=copy.deepcopy(check(report,parent_hash,parent_root,parent))
    result['pending'].append('explicit project drawing erratum reconstructed; physical omitted spans, dependent mapping/attributes and human acceptance remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,
        project_known_erratum_stage=dict(source_replay='passed',records=audit['records'],parent_graph_sha256=parent_hash,general_circle_rule_added=False,human_accepted=False))
    return result


def check_circle_path_normalization_graph(root,report,graph_hash,graph_path):
    import copy,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from normalize_plan_circle_paths import verify_output
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(graph_path.parent)
    if graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash:raise ValueError('circle path stage graph differs')
    parent=Path(audit['parent_graph']['path']);parent_hash=audit['parent_graph']['sha256']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=parent_hash:raise ValueError('circle path parent changed')
    parent_root=parent.parent.parent if parent.parent.name.startswith('topology-') else parent.parent
    result=copy.deepcopy(check(report,parent_hash,parent_root,parent))
    result['pending'].append('source circle radii excluded; cross-view mapping, DN/length scope and human acceptance require current replay')
    result.update(status='failed' if result['errors'] else 'pending',hil_ready=False,graph_sha256=graph_hash,
        circle_path_normalization_stage=dict(source_replay='passed',parent_graph_sha256=parent_hash,normalized_edges=[r['edge_id'] for r in audit['records']],human_accepted=False))
    return result


def check(report, graph_hash, root, graph_path=None):
    candidate=Path(graph_path) if graph_path is not None else Path(root)/'graph_with_edges.json'
    if candidate.is_file():
        has_current_floor_scopes=False;has_external_feed_attributes=False;has_network_named_prefix_attributes=False;has_anchored_main_attributes=False;has_upper_floor_plan_attributes=False;has_lower_floor_plan_attributes=False;has_wave_plan_scope_adoption=False;has_inherited_wave_continuity=False;has_project_scoped_descendant=False;has_plan_circle_continuity=False
        try:
            current=json.loads(candidate.read_text(encoding='utf8'));has_gap_stage=bool(current.get('sourceConfirmedGapJoints'))
            has_current_floor_scopes='sourceCurrentFloorPlanScopeAdoption' in current or any('current_floor_plan_scope_evidence' in e for e in current.get('edges',[]))
            has_plan_circle_continuity='sourcePendingNativeJunctionResolution' in current or 'sourceTwoArmCircleContinuity' in current or any(e.get('source_circle_continuity') for e in current.get('edges',[]))
            has_project_scoped_descendant='sourceDeclaredCappedBranchInterfaces' in current or 'sourceSH16RelatedCornerKnownIssue' in current
            has_anchored_main_attributes='sourceAnchoredFloorMainAttributes' in current or any('anchored_floor_main_attributes' in e for e in current.get('edges',[]))
            has_external_feed_attributes='sourceExternalFeedPlanAttributes' in current or any('external_feed_plan_attributes' in e for e in current.get('edges',[])) or any('source_external_destination_context' in n for n in current.get('nodes',[]))
            has_network_named_prefix_attributes='sourceNetworkNamedLowerPlanAttributes' in current or any('network_named_lower_plan_attributes' in e for e in current.get('edges',[]))
            has_wave_plan_scope_adoption='sourceWaveRebasedPlanScopeAdoption' in current or any('current_plan_scope_evidence' in e.get('cross_view_attributes',{}) for e in current.get('edges',[]))
            has_inherited_wave_continuity='sourceInheritedWavePairContinuity' in current or any(e.get('connection_mode')=='source_inherited_wave_omission_unreviewed' for e in current.get('edges',[]))
            has_lower_floor_plan_attributes='sourceLowerFloorPlanSegmentAttributes' in current or any(a.get('scope')=='native_plan_matched_lower_floor_axis_segments_only' for e in current.get('edges',[]) for a in e.get('plan_segment_attributes',[]))
            has_upper_floor_plan_attributes='sourceUpperFloorPlanSegmentAttributes' in current or any('plan_segment_attributes' in e for e in current.get('edges',[]))
            has_crossview_stage=bool(current.get('crossViewAttributeFusion')) or any(e.get('cross_view_attributes') for e in current.get('edges',[]))
            has_identity_stage=bool(current.get('sourceEquipmentIdentityResolution')) or any(n.get('source_identity_evidence',{}).get('rule')=='robust_rotated_caption_footprint' for n in current.get('nodes',[]))
            has_ownership_stage=bool(current.get('sourceLayoutEquipmentOwnership')) or any(e.get('source_layout_equipment_interface') for e in current.get('edges',[]))
            has_sideview_ownership_stage='sourceSideviewEquipmentOwnership' in current or any('source_sideview_equipment_interface' in e for e in current.get('edges',[]))
            has_block_branch_stage=bool(current.get('sourceNativeBlockBranchReconstruction')) or any(e.get('source_native_block_branch') for e in current.get('edges',[]))
            has_source_checked_attributes=bool(current.get('sourceCheckedCrossViewAttributeFusion')) or any(e.get('cross_view_attributes',{}).get('mapping_basis')=='native_source_and_main_branch_order' for e in current.get('edges',[]))
            has_paired_attributes='pairedServiceCrossViewAttributeFusion' in current or any(e.get('cross_view_attributes',{}).get('mapping_basis')=='native_paired_service_corridors' for e in current.get('edges',[]))
            has_refined_paired_attributes='pairedJunctionCrossViewAttributeFusion' in current or any(e.get('cross_view_attributes',{}).get('mapping_basis')=='native_paired_service_junction_correspondence' for e in current.get('edges',[]))
            has_axis_riser_attributes='sourceAxisRiserSegmentAttributes' in current or any('axis_riser_attributes' in e for e in current.get('edges',[]))
            has_named_riser_attributes='sourceNamedRiserPlanAttributeFusion' in current or any(e.get('cross_view_attributes',{}).get('mapping_basis')=='native_named_riser_and_independent_equipment_service' for e in current.get('edges',[]))
            has_project_erratum_stage=bool(current.get('sourceDraftingErrata')) or any(e.get('source_drafting_erratum') for e in current.get('edges',[]))
            has_circle_path_stage='sourceCirclePathNormalization' in current or any('source_circle_path_normalization' in e for e in current.get('edges',[]))
        except (ValueError,OSError,UnicodeDecodeError):has_gap_stage=False;has_crossview_stage=False;has_identity_stage=False;has_ownership_stage=False;has_sideview_ownership_stage=False;has_block_branch_stage=False;has_source_checked_attributes=False;has_circle_path_stage=False;has_project_erratum_stage=False;has_paired_attributes=False;has_refined_paired_attributes=False;has_axis_riser_attributes=False;has_named_riser_attributes=False
        if 'sourceFullPlanBatchAttributes' in locals().get('current',{}):
            try:
                from full_batch_plan_attribute_gate import check as check_full_batch
                return check_full_batch(root,report,graph_hash,candidate)
            except (ValueError,OSError,KeyError,TypeError,ImportError) as exc:
                return dict(status='failed',errors=list(report.get('errors',[]))+['complete batch plan attributes: '+str(exc)],pending=list(report.get('pending',[])),graph_sha256=graph_hash,hil_ready=False,human_accepted=False)
        if 'sourceWaveMainCohort' in locals().get('current',{}):
            from wave_main_cohort_gate import check as check_wave_main_cohort
            return check_wave_main_cohort(root,report,graph_hash,graph_path)
        if ('sourceReviewedDrawingGapContinuity' in locals().get('current',{}) or any('reviewed_drawing_gap_continuity' in e for e in locals().get('current',{}).get('edges',[]))):
            try:
                from reviewed_plan_gap_gate import check as check_reviewed_gap
                return check_reviewed_gap(root,report,graph_hash,candidate)
            except Exception as exc:
                return dict(status='failed',errors=list(report.get('errors',[]))+['reviewed plan gap invalid: '+str(exc)],pending=list(report.get('pending',[])),graph_sha256=graph_hash,hil_ready=False,human_accepted=False)
        if ('sourceReviewedInterfaceOwners' in locals().get('current',{}) or any('reviewed_interface_owner' in e for e in locals().get('current',{}).get('edges',[]))):
            try:
                from reviewed_interface_owner_gate import check as check_reviewed_owner
                return check_reviewed_owner(root,report,graph_hash,candidate)
            except Exception as exc:
                return dict(status='failed',errors=list(report.get('errors',[]))+['reviewed interface ownership invalid: '+str(exc)],pending=list(report.get('pending',[])),graph_sha256=graph_hash,hil_ready=False,human_accepted=False)
        if 'sourceCurrentNamedUpperPrefixEvidence' in locals().get('current',{}):
            try:
                from current_named_prefix_evidence_gate import check as check_current_named_prefix
                return check_current_named_prefix(root,report,graph_hash,candidate)
            except (ValueError,OSError,KeyError,TypeError,ImportError) as exc:
                return dict(status='failed',errors=list(report.get('errors',[]))+['current named prefix evidence: '+str(exc)],pending=list(report.get('pending',[])),graph_sha256=graph_hash,hil_ready=False,human_accepted=False)
        if 'sourceKnownJunctionMainAttributes' in locals().get('current',{}):
            try:
                from known_junction_main_fusion_gate import check as check_known_main
                return check_known_main(root,report,graph_hash,candidate)
            except (ValueError,OSError,KeyError,TypeError,ImportError) as exc:
                return dict(status='failed',errors=['known-junction main fusion: '+str(exc)],pending=[],graph_sha256=graph_hash,hil_ready=False,human_accepted=False)
        if has_current_floor_scopes:
            try:
                from current_floor_scope_adoption_gate import check as check_current_floor
                return check_current_floor(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['current floor scope adoption invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_plan_circle_continuity:
            try:
                from plan_circle_continuity_source_gate import check as check_plan_circle
                return check_plan_circle(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['plan circle continuity invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_external_feed_attributes:
            try:
                from external_feed_plan_fusion_gate import check as check_external_feed
                return check_external_feed(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['external feed fusion invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_network_named_prefix_attributes:
            try:
                from network_named_lower_plan_fusion_gate import check as check_network_prefix
                return check_network_prefix(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['network named prefix attributes invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_anchored_main_attributes:
            try:
                from anchored_floor_main_fusion_gate import check as check_anchored_main
                return check_anchored_main(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['anchored main attributes invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_project_scoped_descendant:
            try:
                from project_descendant_dispatch import check as check_project_descendant_dispatch
                return check_project_descendant_dispatch(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['project-scoped source descendant invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_wave_plan_scope_adoption:
            try:
                from wave_plan_scope_adoption_gate import check_wave_plan_scope_adoption
                return check_wave_plan_scope_adoption(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['current wave plan scope adoption invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_inherited_wave_continuity:
            try:
                from inherited_wave_source_gate import check_inherited_wave_graph
                return check_inherited_wave_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['inherited wave continuity invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_lower_floor_plan_attributes:
            try:
                from lower_floor_plan_attribute_gate import check_lower_floor_plan_attribute_graph
                return check_lower_floor_plan_attribute_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['lower floor plan segment attributes invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_upper_floor_plan_attributes:
            try:
                from upper_floor_plan_attribute_gate import check_upper_floor_plan_attribute_graph
                return check_upper_floor_plan_attribute_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=list(report.get('errors',[]))+['upper floor plan segment attributes invalid: '+str(exc)],pending=list(report.get('pending',[])),hil_ready=False,human_accepted=False)
        if has_named_riser_attributes:
            try:return check_named_riser_plan_attribute_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['named riser plan attribute extension invalid: '+str(exc)],pending=[],hil_ready=False,human_accepted=False)
        if has_axis_riser_attributes:
            try:return check_axis_riser_attribute_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['axis riser segment attribute extension invalid: '+str(exc)],pending=[],hil_ready=False,human_accepted=False)
        if has_refined_paired_attributes:
            try:return check_refined_paired_attribute_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['refined paired attribute composition invalid: '+str(exc)],pending=[],hil_ready=False,human_accepted=False)
        if has_paired_attributes:
            try:return check_paired_attribute_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['paired plan attribute extension invalid: '+str(exc)],pending=[],hil_ready=False)
        if has_source_checked_attributes:
            try:return check_source_checked_attribute_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['source-checked cross-view attributes invalid: '+str(exc)],pending=[],hil_ready=False)
        if has_crossview_stage:
            try:return check_crossview_attribute_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['cross-view attribute stage invalid: '+str(exc)],pending=[],hil_ready=False)
        if has_block_branch_stage:
            try:return check_native_block_branch_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['native block branch stage invalid: '+str(exc)],pending=[],hil_ready=False)
        if has_circle_path_stage:
            try:return check_circle_path_normalization_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['source circle path normalization invalid: '+str(exc)],pending=[],hil_ready=False)
        if has_sideview_ownership_stage:
            try:return check_sideview_equipment_ownership_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['source-sideview equipment ownership stage invalid: '+str(exc)],pending=[],hil_ready=False)
        if has_ownership_stage:
            try:return check_layout_equipment_ownership_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['source-layout equipment ownership stage invalid: '+str(exc)],pending=[],hil_ready=False)
        if has_project_erratum_stage:
            try:return check_known_project_erratum_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['project drawing erratum stage invalid: '+str(exc)],pending=[],hil_ready=False)
        if has_identity_stage:
            try:return check_equipment_identity_layout_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['equipment caption identity stage invalid: '+str(exc)],pending=[],hil_ready=False)
        if has_gap_stage:
            try:return check_confirmed_gap_joint_graph(root,report,graph_hash,candidate)
            except Exception as exc:return dict(status='failed',errors=['confirmed gap-joint stage invalid: '+str(exc)],pending=[],hil_ready=False)
    errors=[];pending=[];circle_screen_blockers=[];circle_screen_sources=[];near_screen_blockers=[];near_screen_sources=[];root=Path(root).resolve()
    if report.get('graph_sha256')!=graph_hash:errors.append('comparison is stale for graph')
    if report.get('rounds_completed',0)<1:pending.append('native comparison round missing')
    if not report.get('families'):pending.append('source issue families not classified')
    if not report.get('native_comparisons'):pending.append('native comparison evidence missing')
    comparison_items=list(report.get('native_comparisons',[]))
    try:verify_batch_circle_stage(root,graph_hash)
    except Exception as exc:errors.append('batch circle reconstruction evidence invalid: '+str(exc))
    try:verify_confirmed_near_tee_stage(root,graph_hash,json.loads(candidate.read_text(encoding='utf8')) if candidate.is_file() else None)
    except Exception as exc:errors.append('near-tee confirmation evidence invalid: '+str(exc))
    sideview_stage_audit=None;equipment_pair_stage_audit=None
    try:equipment_pair_stage_audit=verify_confirmed_equipment_pair_stage(root,graph_hash)
    except Exception as exc:errors.append('confirmed equipment pair stage invalid: '+str(exc))
    try:sideview_stage_audit=verify_confirmed_sideview_stage(root,equipment_pair_stage_audit['inputs']['graph']['sha256'] if equipment_pair_stage_audit else graph_hash)
    except Exception as exc:errors.append('confirmed side-view evidence invalid: '+str(exc))
    automatic_screen=root/'reports'/'source-circle-rim-screen.json';automatic_receipt=root/'reports'/'source-circle-rim-screen-stage.json'
    if automatic_screen.exists() or automatic_receipt.exists():
        try:
            if not automatic_screen.resolve().is_relative_to(root) or not automatic_receipt.resolve().is_relative_to(root) or not automatic_screen.is_file() or not automatic_receipt.is_file():raise ValueError('missing or unsafe screen stage')
            stage=json.loads(automatic_receipt.read_text(encoding='utf8'));actual=hashlib.sha256(automatic_screen.read_bytes()).hexdigest()
            if stage.get('graph_sha256')!=graph_hash or stage.get('evidence_sha256')!=actual:raise ValueError('stale circle screen stage')
            if not any(x.get('kind')=='source_circle_rim_screen' and (root/x.get('path','')).resolve()==automatic_screen.resolve() for x in comparison_items):
                comparison_items.append({'path':automatic_screen.relative_to(root).as_posix(),'sha256':actual,'binding':'current_graph','kind':'source_circle_rim_screen'})
        except (OSError,UnicodeDecodeError,ValueError,TypeError,AttributeError):errors.append('circle rim screen stage missing, unsafe or stale')
    try:
        if (root/'reports/source-circle-rim-additional-stage.json').exists() and not automatic_receipt.is_file():raise ValueError('additional screen requires primary receipt')
        circle_source=json.loads(automatic_receipt.read_text(encoding='utf8')).get('source_sha256') if automatic_receipt.is_file() else None
        for item in additional_circle_screens(root,graph_hash,circle_source):
            if not any(x.get('kind')==item['kind'] and x.get('path')==item['path'] for x in comparison_items):comparison_items.append(item)
    except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('additional circle screen stage missing, unsafe or stale')
    near_screen=root/'reports'/'near-endpoint-crossing-screen.json';near_receipt=root/'reports'/'near-endpoint-crossing-screen-stage.json'
    if near_screen.exists() or near_receipt.exists():
        try:
            if not near_screen.resolve().is_relative_to(root) or not near_receipt.resolve().is_relative_to(root) or not near_screen.is_file() or not near_receipt.is_file():raise ValueError('missing or unsafe near-endpoint stage')
            stage=json.loads(near_receipt.read_text(encoding='utf8'));actual=hashlib.sha256(near_screen.read_bytes()).hexdigest();evidence=json.loads(near_screen.read_text(encoding='utf8'))
            if stage.get('graph_sha256')!=graph_hash or stage.get('evidence_sha256')!=actual or stage.get('source_sha256')!=evidence.get('source_sha256') or stage.get('candidate_count')!=len(evidence['candidates']):raise ValueError('stale near-endpoint stage')
            if not any(x.get('kind')=='near_endpoint_crossing_screen' and (root/x.get('path','')).resolve()==near_screen.resolve() for x in comparison_items):comparison_items.append({'path':near_screen.relative_to(root).as_posix(),'sha256':actual,'binding':'current_graph','kind':'near_endpoint_crossing_screen'})
        except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('near-endpoint screen stage missing, unsafe or stale')
    named_screen=root/'reports'/'named-endpoint-leader-screen.json';named_receipt=root/'reports'/'named-endpoint-leader-screen-stage.json'
    if named_screen.exists() or named_receipt.exists():
        try:
            if not named_screen.resolve().is_relative_to(root) or not named_receipt.resolve().is_relative_to(root) or not named_screen.is_file() or not named_receipt.is_file():raise ValueError('missing or unsafe named leader stage')
            stage=json.loads(named_receipt.read_text(encoding='utf8'));evidence=json.loads(named_screen.read_text(encoding='utf8'));actual=hashlib.sha256(named_screen.read_bytes()).hexdigest();rows=evidence['selections']
            if stage.get('graph_sha256')!=graph_hash or evidence.get('graph_sha256')!=graph_hash or stage.get('evidence_sha256')!=actual or stage.get('source_sha256')!=evidence.get('source_sha256') or stage.get('candidate_count')!=len(rows) or stage.get('hil_ready') is not False or evidence.get('status')!='scoped_leader_candidates_not_binding' or evidence.get('graph_mutated') is not False or evidence.get('mapping_ready') is not False or evidence.get('hil_ready') is not False:raise ValueError('invalid named leader stage')
            if not graph_path or not Path(graph_path).is_file() or json.loads(Path(graph_path).read_text(encoding='utf8')).get('metadata',{}).get('source_sha256')!=evidence.get('source_sha256'):raise ValueError('named leader source mismatch')
            if not isinstance(rows,list) or not rows or any(not isinstance(x,dict) or x.get('status')!='source_geometry_candidate_not_binding' or x.get('system') not in ('supply','return') or not all(x.get(k) for k in ('node_id','pipe_handle','leader_handle','text_handle')) for x in rows):raise ValueError('invalid named leader candidate')
            graph_nodes={n.get('node_id'):n for n in json.loads(Path(graph_path).read_text(encoding='utf8')).get('nodes',[])}
            if len({x['node_id'] for x in rows})!=len(rows) or any(x['node_id'] not in graph_nodes or graph_nodes[x['node_id']].get('system')!=x['system'] or x['pipe_handle'] not in graph_nodes[x['node_id']].get('source_handles',[]) for x in rows):raise ValueError('named leader graph identity mismatch')
            pending.append(f'{len(rows)} named endpoint leader candidates require comparison')
        except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('named endpoint leader stage missing, unsafe or stale')
    for item in comparison_items:
        p=(root/item['path']).resolve()
        if not p.is_relative_to(root)or not p.is_file():errors.append('missing/unsafe comparison evidence');continue
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item.get('sha256'):errors.append('comparison evidence hash mismatch')
        if item.get('binding')=='current_graph':
            try:
                evidence=json.loads(p.read_text(encoding='utf-8'))
                if evidence.get('graph_sha256')!=graph_hash:
                    errors.append('current-graph evidence is stale: '+item['path'])
            except (OSError, UnicodeDecodeError, ValueError, AttributeError):
                errors.append('current-graph evidence is invalid: '+item['path'])
        elif item.get('binding') not in (None, 'historical'):
            errors.append('unknown comparison evidence binding: '+item['path'])
        if item.get('kind')=='near_endpoint_crossing_screen':
            if item.get('binding')!='current_graph':errors.append('near-endpoint screen must bind current graph');continue
            try:
                evidence=json.loads(p.read_text(encoding='utf-8'));rows=evidence['candidates']
                if evidence.get('status')!='source_near_endpoint_crossings_not_connections' or evidence.get('graph_sha256')!=graph_hash or not isinstance(evidence.get('source_sha256'),str) or evidence.get('graph_mutated') is not False or evidence.get('hil_ready') is not False or not isinstance(rows,list) or evidence.get('counts',{}).get('candidates')!=len(rows):raise ValueError('invalid near-endpoint screen')
                keys=[]
                for x in rows:
                    if x.get('status')!='near_endpoint_crossing_candidate_not_connection' or x.get('system') not in ('supply','return') or not all(x.get(k) for k in ('source_branch_handle','source_main_handle','endpoint_node_id')):raise ValueError('invalid near-endpoint candidate')
                    keys.append((x['source_branch_handle'],x['source_main_handle'],x['endpoint_node_id']))
                if len(keys)!=len(set(keys)):raise ValueError('duplicate near-endpoint candidates')
                near_screen_sources.append(evidence['source_sha256']);near_screen_blockers.extend(rows)
            except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('near-endpoint screen is invalid: '+item['path'])
        if item.get('kind')=='source_circle_rim_screen':
            if item.get('binding')!='current_graph':errors.append('circle rim screen must bind the current graph');continue
            try:
                evidence=json.loads(p.read_text(encoding='utf-8'));candidates=evidence['candidates'];ambiguous=evidence['ambiguous_native_geometry'];unsupported=evidence['unsupported_circle_transforms']
                if evidence.get('graph_sha256')!=graph_hash or evidence.get('status')!='source_shape_comparison_not_connectivity' or not isinstance(candidates,list) or not isinstance(ambiguous,list) or not isinstance(unsupported,list) or not isinstance(evidence.get('source_sha256'),str):raise ValueError('invalid circle screen')
                if any(not isinstance(x,dict) or x.get('status') not in ('existing_graph_connection_unreviewed','source_shape_graph_connection_not_established') or not x.get('circle_handle') or x.get('line_system') not in ('supply','return') for x in candidates):raise ValueError('invalid circle candidate')
                keys=[(x['circle_handle'],x['line_system']) for x in candidates]
                if len(keys)!=len(set(keys)) or any(not isinstance(x,dict) or not x.get('circle_handle') for x in ambiguous) or any(not isinstance(h,str) or not h for h in unsupported):raise ValueError('invalid circle screen entities')
                circle_screen_sources.append(evidence['source_sha256'])
                unresolved=[{'circle_handle':x['circle_handle'],'line_system':x['line_system'],'status':x['status']} for x in candidates if x['status']=='source_shape_graph_connection_not_established']
                circle_screen_blockers.extend(unresolved+[{'status':'ambiguous_native_geometry','circle_handle':x.get('circle_handle')} for x in ambiguous]+[{'status':'unsupported_circle_transform','circle_handle':h} for h in unsupported])
            except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('circle rim screen is invalid: '+item['path'])
    for family in report.get('families',[]):
        if family.get('status')not in ('resolved','source_ambiguity'):pending.append('algorithm family not consumed: '+family.get('id','unknown'))
        if not family.get('source_handles')or not family.get('disposition'):errors.append('family lacks source evidence/disposition')
    if circle_screen_blockers:pending.append(f'{len(circle_screen_blockers)} source circle-rim shapes require comparison')
    if near_screen_blockers:pending.append(f'{len(near_screen_blockers)} near-endpoint crossings require comparison')
    if report.get('algorithm_blockers'):pending.extend(report['algorithm_blockers'])
    if report.get('unclassified_terminal_count',0)>0:pending.append('unclassified terminals cannot be transferred to experts')
    equipment_blockers=[];graph_nodes=[];graph_families=[];reference_blockers=[];detail_blockers=[];hidden_branch_blockers=[];equipment_datum_blockers=[];segment_dn_blockers=[];bulk_dn_blockers=[];gap_joint_blockers=[];frame_context=[];compound_dn_blockers=[];plan_line_blockers=[];near_circle_blockers=[]
    explicit_graph=graph_path is not None
    graph_path=Path(graph_path).resolve() if explicit_graph else root/'graph_with_edges.json'
    if (root/'native_segment_dn_candidates.json').exists() and not graph_path.is_file():errors.append('segment DN stage requires the current graph')
    if (root/'source_dn_bulk_screen_final.json').exists() and not graph_path.is_file():errors.append('final DN screen requires the current graph')
    if circle_screen_sources and not graph_path.is_file():errors.append('circle rim screen requires the current graph')
    if ((root/'reports/near-offset-circle-screen.json').exists() or (root/'reports/near-offset-circle-stage.json').exists()) and not graph_path.is_file():errors.append('near-offset circle screen requires the current graph')
    if near_screen_sources and not graph_path.is_file():errors.append('near-endpoint screen requires the current graph')
    if ((root/'reports'/'hidden-branch-circle-screen.json').exists() or (root/'reports'/'hidden-branch-circle-screen-stage.json').exists()) and not graph_path.is_file():errors.append('hidden branch screen requires the current graph')
    if ((root/'equipment_datum_position_screen_final.json').exists() or (root/'equipment_datum_position_screen_stage.json').exists()) and not graph_path.is_file():errors.append('equipment datum screen requires the current graph')
    if ((root/'missing_gap_joint_candidates_final.json').exists() or (root/'missing_gap_joint_candidates_stage.json').exists()) and not graph_path.is_file():errors.append('gap joint screen requires the current graph')
    if ((root/'reports/source-detail-frame-context.json').exists() or (root/'reports/source-detail-frame-context-stage.json').exists()) and not graph_path.is_file():errors.append('detail frame context requires the current graph')
    if explicit_graph and not graph_path.is_relative_to(root):
        errors.append('graph outside task')
    elif explicit_graph and not graph_path.is_file():
        errors.append('current graph missing')
    elif graph_path.is_file():
        data=graph_path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=graph_hash:
            errors.append('current graph hash mismatch')
        else:
            try:
                graph=json.loads(data.decode('utf-8'))
                if graph.get('confirmedEquipmentPairReconstruction') and equipment_pair_stage_audit is None:
                    errors.append('confirmed equipment graph is missing native stage evidence')
                if (graph.get('sourceInlineSystemResolutions') or
                        any(e.get('source_inline_system_resolutions') for e in graph.get('edges',[]))):
                    try:
                        import sys
                        owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology'/'scripts'
                        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
                        from repair_upstream_joint_systems import verify_output
                        verify_output(graph_path)
                    except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError,ImportError):
                        errors.append('upstream joint system repair missing, stale or not source-reproducible')
                elif graph.get('sourceFloorLabelRepair'):
                    try:
                        import sys
                        owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology'/'scripts'
                        if str(owner) not in sys.path:sys.path.insert(0,str(owner))
                        from repair_source_floor_labels import verify_output as verify_floor_output
                        verify_floor_output(graph_path)
                    except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError,ImportError):
                        errors.append('source floor label repair missing, stale or not source-reproducible')
                try:
                    plan_line_blockers=final_plan_line_blockers(root,graph_hash,graph.get('metadata',{}).get('source_sha256'),graph)
                    if plan_line_blockers:pending.append(f'{len(plan_line_blockers)} final plan source lines require classification')
                except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('final plan line stage missing, unsafe, stale or invalid')
                try:
                    near_circle_blockers=near_offset_circle_blockers(root,graph_hash,graph.get('metadata',{}).get('source_sha256'),graph)
                    if near_circle_blockers:pending.append(f'{len(near_circle_blockers)} near-offset circle candidates require comparison')
                except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('near-offset circle stage missing, unsafe, stale or invalid')
                try:
                    compound_dn_blockers=compound_dn_context(root,graph_hash,graph.get('metadata',{}).get('source_sha256'),graph)
                    if compound_dn_blockers:pending.append(f'{len(compound_dn_blockers)} compound DN annotations require pipe attribution')
                except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('compound DN stage missing, unsafe, stale or invalid')
                try:
                    frame_context=detail_frame_context(root,graph_hash,graph.get('metadata',{}).get('source_sha256'))
                    if frame_context:pending.append(f'{len(frame_context)} detail frame candidates remain individually unverified')
                except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('detail frame context missing, unsafe, stale or invalid')
                try:
                    gap_joint_blockers=missing_gap_joint_blockers(root,graph_hash,graph)
                    if gap_joint_blockers:pending.append(f'{len(gap_joint_blockers)} source joint candidates require comparison')
                except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('gap joint screen missing, unsafe, stale or invalid')
                try:
                    equipment_datum_blockers=equipment_datum_screen_blockers(root,graph_hash,graph)
                    if equipment_datum_blockers:
                        groups={b.get('interpretation_family') for b in equipment_datum_blockers}
                        pending.append(f'{len(groups)} equipment datum interpretation families retain {len(equipment_datum_blockers)} unresolved records' if None not in groups else f'{len(equipment_datum_blockers)} equipment anchor/datum positions require interpretation')
                except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('equipment datum screen missing, unsafe, stale or invalid')
                try:
                    hidden_branch_blockers=hidden_branch_screen_blockers(root,graph_hash,graph.get('metadata',{}).get('source_sha256'),report)
                    if hidden_branch_blockers:pending.append(f'{len(hidden_branch_blockers)} hidden branch candidates require comparison')
                except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('hidden branch screen missing, unsafe, stale or invalid')
                if circle_screen_sources and any(h!=graph.get('metadata',{}).get('source_sha256') for h in circle_screen_sources):errors.append('circle rim screen source does not match graph')
                if near_screen_sources and any(h!=graph.get('metadata',{}).get('source_sha256') for h in near_screen_sources):errors.append('near-endpoint screen source does not match graph')
                if graph.get('metadata',{}).get('hil_ready') is False:
                    pending.append('current graph explicitly marks HIL not ready')
                try:
                    segment_dn_blockers=segment_dn_withheld_blockers(root,graph_hash)
                    if segment_dn_blockers:pending.append(f'{len(segment_dn_blockers)} source DN annotations require attribution')
                except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('segment DN stage missing, unsafe, stale or invalid')
                try:
                    bulk_dn_blockers=bulk_dn_screen_blockers(root,graph_hash)
                    if bulk_dn_blockers:pending.append(f'{len(bulk_dn_blockers)} bulk source DN observations require comparison')
                except (OSError,UnicodeDecodeError,ValueError,TypeError,KeyError,AttributeError):errors.append('final bulk DN screen missing, unsafe, stale or invalid')
                equipment_blockers=equipment_comparison_blockers(graph)
                graph_nodes,graph_families=graph_comparison_blockers(graph)
                reference_blockers=reference_component_blockers(graph)
                # A comparison record denotes alternative source representations;
                # a completed receipt cannot prove equipment/port correspondence.
                # Match the hydraulic projection's conservative contract.
                detail=graph.get('sourceDetailComparison')
                if detail is not None:
                    if not isinstance(detail,dict):
                        errors.append('source detail comparison is invalid')
                    else:
                        confirmed={r['abbreviated_edge']:r for r in (graph.get('confirmedSideviewCanonicalization') or {}).get('records',[])}
                        scoped=sideview_stage_audit is not None and bool(detail.get('pairs')) and all(
                            p.get('upper_edge') in confirmed and confirmed[p['upper_edge']]['system']==p.get('system')
                            and confirmed[p['upper_edge']]['verified_detail_tee']['tee']==p.get('detail_tee') for p in detail['pairs'])
                        detail_blockers.append({'expert_issue':detail.get('expert_issue'),
                            'status':'representations_canonicalized_main_ends_and_equipment_pending' if scoped else detail.get('status')})
                        pending.append('confirmed detail representations still require main-end and equipment mapping before HIL' if scoped else 'source detail alternatives require verified replacement before HIL')
                if reference_blockers:pending.append(f'{len(reference_blockers)} reference component groups lack individual primary proxy correspondence')
                if graph_nodes:pending.append(f'{len(graph_nodes)} graph nodes have unresolved source-terminal or equipment-overlap semantics')
                pending.extend('graph algorithm family not consumed: '+str(f) for f in graph_families)
                if equipment_blockers:
                    pending.append(f"{len(equipment_blockers)} equipment nodes have unresolved source-port ownership")
            except (UnicodeDecodeError,ValueError,TypeError,AttributeError):
                errors.append('current graph is unreadable or invalid')
    return {'status':'failed'if errors else 'pending'if pending else 'completed','errors':errors,'pending':pending,'hil_ready':not errors and not pending,
            'equipment_source_port_blockers':equipment_blockers,
            'graph_unresolved_node_blockers':graph_nodes,'graph_algorithm_family_blockers':graph_families,
            'reference_component_blockers':reference_blockers,
            'source_detail_comparison_blockers':detail_blockers,'circle_rim_screen_blockers':circle_screen_blockers,'near_offset_circle_blockers':near_circle_blockers,
            'hidden_branch_screen_blockers':hidden_branch_blockers,'equipment_datum_screen_blockers':equipment_datum_blockers,'segment_dn_withheld_blockers':segment_dn_blockers,'bulk_dn_screen_blockers':bulk_dn_blockers,'missing_gap_joint_blockers':gap_joint_blockers,'detail_frame_context':frame_context,'compound_dn_blockers':compound_dn_blockers,'final_plan_line_blockers':plan_line_blockers}
