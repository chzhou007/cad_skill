"""Reapply original full-plan DN propagation after current native T validation.

Annotation, F/calibration, source-path, leader and propagation owners remain
unchanged. Configured current T readers replace the obsolete local T dispatch.
No axis label selects a local seed or resolves conflicting plan declarations.
"""
import collections,copy,json
from confirm_crossview_paths import encode
from full_plan_DN_inherited_annotations import inventory,barriers
from full_plan_DN_source import _has_through
from projected_circle_plan_DN import infer
from native_projected_circle_main_role import STATUS as PROJECTED_MAIN_STATUS
from source_main_DN_continuity import STATUS as CONFIRMED_MAIN_STATUS
from batch_native_path_coverage import collect as coverage
from legacy_named_provider_inventory import require

def annotation_equal(fresh,previous):
    require(json.loads(encode(fresh))==previous,'original complete native annotation evidence changed; requalify its owner')

def reviewed_seeds(previous,annotation,graph,eligible):
    by={e['edge_id']:e for e in graph['edges']};seeds=copy.deepcopy(annotation['seeds'])
    for seed in previous['direct_seed_evidence']:
        if seed.get('scope_only')is not True:continue
        require(seed.get('source_kind')=='explicit_reviewed_drawn_plan_scope_not_new_annotation'and seed['evidence_id'].startswith('reviewed:'),'reviewed seed escaped explicit original scope')
        require(seed['edge_id']in eligible and seed['scope_paths']==by[seed['edge_id']]['attribute_paths'],'reviewed DN scope changed with current graph')
        seeds.append(copy.deepcopy(seed))
    require(json.loads(encode(seeds))==previous['direct_seed_evidence'],'current local DN seeds differ from independently replayed original')
    return seeds

def preserve_known(previous,records):
    by={r['edge_id']:r for r in records}
    for old in previous['records']:
        if old['nominal_mm']is not None:
            require(old['edge_id']in by and by[old['edge_id']]['nominal_mm']==old['nominal_mm'],
                    'a previously known local plan DN changed; source conflict needs explicit reconciliation')

def collect(doc,graph,previous,source_hash,graph_hash,reader,annotation_config):
    require(previous['source_sha256']==source_hash and previous['graph_sha256']==graph_hash
            and graph.get('metadata',{}).get('source_sha256')==source_hash,'current T DN source or graph differs from original local scope')
    annotation=inventory(doc,graph,source_hash,graph_hash,annotation_config);annotation_equal(annotation,previous['annotation_evidence'])
    paths={};path_errors={};eligible=set();by={e['edge_id']:e for e in graph['edges']}
    for eid in sorted(by):
        try:
            proof=coverage(doc,graph,[eid],source_hash,graph_hash);paths[eid]=proof
            segments=[s for e in proof['edges']for s in e['segments']]
            if segments and all(s['status']=='single_source_line_covers'for s in segments):eligible.add(eid)
            else:path_errors[eid]='source_path_missing_or_multiple_LINE_witnesses'
        except ValueError as exc:path_errors[eid]=str(exc)
    blocked=set(annotation['blocked_edges']);leaders,issues=barriers(doc,graph,annotation,eligible);eligible-=blocked|set(leaders)
    junctions={};held={}
    for node in sorted(graph['nodes'],key=lambda n:n['node_id']):
        if node.get('node_type')not in('tee','physical_junction'):continue
        nid=node['node_id']
        try:
            proof=reader(doc,graph,nid,source_hash,graph_hash)
            require(proof.get('status')==PROJECTED_MAIN_STATUS or _has_through(proof),'current native T lacks supported original main identity or one unique through pair')
            junctions[nid]=proof
        except ValueError as exc:held[nid]=str(exc)
    seeds=reviewed_seeds(previous,annotation,graph,eligible)
    result=infer(graph,seeds,eligible,junctions,source_hash,graph_hash)
    require(set(result.get('native_main_continuity_nodes',[]))=={n for n,p in junctions.items()if p.get('status')==CONFIRMED_MAIN_STATUS}
            and set(result.get('native_projected_circle_main_identity_nodes',[]))=={n for n,p in junctions.items()if p.get('status')==PROJECTED_MAIN_STATUS},
            'an existing native main-role feature was not applied by the current inheritance entry')
    present={r['edge_id']for r in result['records']}
    for eid in sorted(set(by)-present):
        result['records'].append(dict(edge_id=eid,system=by[eid]['system'],nominal_mm=None,
            status='annotation_blocked'if eid in blocked or eid in leaders else'source_scope_unverified',
            scope_paths=copy.deepcopy(by[eid].get('attribute_paths',[])),lineage=[],human_accepted=False))
    preserve_known(previous,result['records'])
    old={r['edge_id']:r for r in previous['records']}
    result.update(mode='current_native_T_complete_plan_DN_reapplication_v1',annotation_evidence=annotation,
        source_path_evidence=paths,source_path_exceptions=path_errors,annotation_barriers=sorted(blocked|set(leaders)),
        annotation_leader_issues=issues,native_current_T_evidence=junctions,source_T_exceptions=held,
        direct_seed_evidence=seeds,all_original_known_DN_preserved=True,all_current_native_main_roles_reapplied=True,original_annotation_and_inference_owners_reused=True,
        crossview_subset_used_for_scope=False,axis_values_used_to_choose_DN=False,physical_lengths_assigned=0,
        counts=dict(graph_edges=len(by),old_native_T_roles=len(previous['roles']),current_native_T_roles=len(junctions),
            original_main_continuity_roles=len(result.get('native_main_continuity_nodes',[])),projected_main_identity_roles=len(result.get('native_projected_circle_main_identity_nodes',[])),
            old_known_DN=sum(r['nominal_mm']is not None for r in previous['records']),known_DN=sum(r['nominal_mm']is not None for r in result['records']),
            new_known_DN=sum(r['nominal_mm']is not None and old[r['edge_id']]['nominal_mm']is None for r in result['records']),
            conflicts=sum(r['status']=='conflict'for r in result['records'])))
    return result
