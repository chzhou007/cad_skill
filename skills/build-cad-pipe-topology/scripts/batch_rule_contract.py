"""Check a complete batch partition without promoting candidates to acceptance."""
import collections


def check(result,axis):
    expected=[e['edge_id'] for e in axis['edges']]
    rows=result.get('records',[]);ids=[r.get('edge_id') for r in rows]
    if len(expected)!=len(set(expected)) or len(ids)!=len(set(ids)) or set(ids)!=set(expected):
        raise ValueError('every current axis edge must appear exactly once')
    if result.get('total_edges')!=len(expected) or result.get('states')!=dict(collections.Counter(r['state'] for r in rows)):
        raise ValueError('batch partition counts differ')
    accepted_states={'rule_matched_native_attribute_application_pending',
        'conflict_multiple_mapping_writers','previous_partial_scope_requires_current_path_replay',
        'axis_vertical_or_mixed_scope_requires_segment_rule','unmatched_local_or_main_detail_path'}
    if any(r['state'] not in accepted_states or r.get('human_accepted') is not False or r.get('physical_length_mm') is not None for r in rows):
        raise ValueError('correspondence batch cannot invent acceptance or physical lengths')
    return dict(processed_edges=len(rows),source_matched_candidates=sum(r['state']=='rule_matched_native_attribute_application_pending' for r in rows),
        technical_or_evidence_followup=sum(r['state']!='rule_matched_native_attribute_application_pending' for r in rows),
        human_accepted=False,whole_goal_complete=False)
