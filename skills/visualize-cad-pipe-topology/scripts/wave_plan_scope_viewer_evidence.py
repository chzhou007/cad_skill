"""Replay current plan adoption and reuse its freshly verified lower ancestry."""
import copy,hashlib,json,sys
from pathlib import Path


def verify(graph_path,graph):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from adopt_wave_rebased_plan_scopes import verify_output,ROOT
    from attach_axis_riser_segment_attributes import viewer_ancestry
    graph_path=Path(graph_path);audit=verify_output(graph_path.parent)
    return from_audit(graph_path,graph,audit)


def from_audit(graph_path,graph,audit):
    """Reuse a freshly replayed parent audit; all graph/ancestry checks remain."""
    from adopt_wave_rebased_plan_scopes import ROOT
    from attach_axis_riser_segment_attributes import viewer_ancestry
    graph_path=Path(graph_path);digest=hashlib.sha256(graph_path.read_bytes()).hexdigest();stage=audit['proof']
    if (graph_path.name!='graph_with_edges.json' or json.loads(graph_path.read_text('utf8'))!=graph or audit['output_graph_sha256']!=digest
        or graph.get(ROOT)!=stage or stage.get('prior_topology_components_and_other_attributes_preserved') is not True
        or stage.get('whole_DN_or_lengths_added')!=0 or stage.get('related_HIL_confirmation_inherited') is not False
        or audit.get('human_accepted') is not False or audit.get('hil_ready') is not False):raise ValueError('current plan viewer graph differs from native scope adoption')
    rows=stage['records'];edge_rows=[e['cross_view_attributes']['current_plan_scope_evidence'] for e in graph['edges'] if 'current_plan_scope_evidence' in e.get('cross_view_attributes',{})]
    if len(edge_rows)!=len(rows) or len({r['edge_id'] for r in rows})!=len(rows) or {r['edge_id']:r for r in edge_rows}!={r['edge_id']:r for r in rows}:
        raise ValueError('current plan viewer edge/root evidence differs')
    lower=audit['verified_lower_parent'];upper=lower['verified_upper_parent'];named=upper['verified_named_parent'];axis=named['verified_axis_segment_parent']
    if lower['output_graph_sha256']!=audit['parent_graph']['sha256']:raise ValueError('current plan viewer lower ancestry changed')
    segment_rows=[r for e in graph['edges'] for r in e.get('plan_segment_attributes',[])];expected_segments=upper['records']+lower['records']
    if {r['mapping_id']:r for r in segment_rows}!={r['mapping_id']:r for r in expected_segments} or len(segment_rows)!=len(expected_segments):
        raise ValueError('current plan viewer lost earlier upper/lower scopes')
    ancestor,proof=viewer_ancestry(axis,digest)
    proof['records']+=copy.deepcopy(named['records']);proof['plan_DN_scope_fusion']+=copy.deepcopy(named['plan_DN_scope_fusion'])
    for row in rows:
        if not row['added_attribute']:continue
        c=next(e for e in graph['edges'] if e['edge_id']==row['edge_id'])['cross_view_attributes']
        proof['records'].append(dict(mapping_id=c['mapping_id'],kind=c['mapping_kind'],system=c['system'],plan_edges=c['plan_edges'],iso_edges=c['iso_edges'],
            plan_horizontal_projection_mm=c['horizontal_projection']['value_mm'],diameter_status=c['diameter']['status']))
        proof['plan_DN_scope_fusion'].append(dict(mapping_id=c['mapping_id'],iso_edge=row['edge_id'],plan_edges=c['plan_edges'],plan_drawn_nominal_mm=c['diameter']['plan_drawn_nominal_mm'],whole_main_DN_and_centerline_route=False,human_accepted=False))
    proof.update(named_riser_plan_attribute_audit=named,axis_riser_attribute_parent_graph_path=named['parent_graph']['path'],upper_floor_plan_segment_attribute_audit=upper,
        lower_floor_plan_segment_attribute_audit=lower,wave_plan_scope_adoption_audit=audit,human_accepted=False,hil_ready=False)
    return ancestor,proof


def dependency_paths(proof,graph_path):
    audit=proof['wave_plan_scope_adoption_audit'];lower=audit['verified_lower_parent'];upper=lower['verified_upper_parent'];named=upper['verified_named_parent']
    skills=Path(__file__).resolve().parents[2];owner=skills/'build-cad-pipe-topology/scripts';graph_path=Path(graph_path)
    return dict(wave_plan_scope_adoption_audit=graph_path.parent/'wave-plan-scope-adoption-audit.json',
        wave_plan_scope_adoption_verifier=owner/'adopt_wave_rebased_plan_scopes.py',wave_plan_scope_viewer_validator=Path(__file__).resolve(),
        wave_axis_DN_segment_domain_verifier=owner/'axis_local_DN_segment_domains.py',wave_current_mapping=Path(audit['mapping_path']),
        wave_current_plan_attributes=Path(audit['attribute_scope_path']),wave_current_DN_comparison=Path(audit['inputs']['comparison']['path']),
        lower_floor_plan_attribute_audit=Path(audit['parent_graph']['path']).parent/'lower-floor-plan-attribute-fusion-audit.json',
        upper_floor_plan_attribute_audit=Path(lower['inputs']['parent_graph']['path']).parent/'upper-floor-plan-attribute-fusion-audit.json',
        named_riser_plan_attribute_audit=Path(upper['inputs']['parent_graph']['path']).parent/'named-riser-plan-attribute-fusion-audit.json',
        axis_riser_segment_attribute_audit=Path(named['parent_graph']['path']).parent/'axis-riser-attribute-audit.json')
