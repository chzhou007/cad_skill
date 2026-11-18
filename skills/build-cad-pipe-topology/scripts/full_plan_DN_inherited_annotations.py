"""Apply existing ordered-F and calibrated scalar readers before full-plan DN.

Use explicit private dependency injection so historical readers and receipts
retain their original algorithms and implementation identities.
"""
import copy,types
from full_plan_DN_source import annotation_inventory as original_inventory,leader_barriers as original_barriers,collect as original_collect
from native_line_f_diameter_evidence import collect as collect_F
from current_graph_calibrated_dn import collect as collect_calibrated,control_lineage


def current_calibration(doc,graph,calibration,source_hash,graph_hash):
    original=calibration['original_graph'];original_hash=calibration['original_graph_sha256'];policy=calibration['policy']
    # Check targets first; a changed target cannot use the control exception.
    control_lineage(graph,original,dict(policy,controls=[]),source_hash,graph_hash,original_hash)
    eligible=[];excluded=[]
    for spec in policy['controls']:
        try:control_lineage(graph,original,dict(policy,controls=[spec]),source_hash,graph_hash,original_hash)
        except ValueError as exc:excluded.append(dict(control=copy.deepcopy(spec),reason=str(exc)))
        else:eligible.append(spec)
    # The inherited collector still requires >=4 independent native LINEs,
    # both services, two directions and one consistent exact text profile.
    result=collect_calibrated(doc,graph,original,dict(policy,controls=eligible),source_hash,graph_hash,original_hash)
    result['all_original_controls_screened_against_current_geometry']=True
    result['ineligible_original_controls']=excluded
    result['controls_filtered_by_DN_or_normal_side']=False
    return result


def inventory(doc,graph,source_hash,graph_hash,config):
    result=original_inventory(doc,graph,source_hash,graph_hash);proofs={};observations=[];consumed=set();strokes=set()
    frames=config.get('line_F_frames',[])
    if frames:
        proof=collect_F(doc,graph,frames,source_hash,graph_hash);proofs['ordered_native_F']=proof
        for frame in proof['frames']:
            consumed.update(frame['text_handles']);strokes.update(frame['stroke_handles']);observations.extend(frame['bindings'])
    calibration=config.get('calibration')
    if calibration:
        proof=current_calibration(doc,graph,calibration,source_hash,graph_hash)
        proofs['current_calibrated_scalar']=proof
        observations.extend(proof['observations'])
    resolved=consumed|{r['source_text']['handle']for r in observations}
    if len({r['source_text']['handle']for r in observations})!=len(observations):raise ValueError('native annotation readers claim one text twice')
    def handle(row):return row.get('text_handle',row.get('selection',{}).get('text_handle',row.get('text',{}).get('handle')))
    result['blocked_edges']={eid:remaining for eid,rows in result['blocked_edges'].items()if (remaining:=[r for r in rows if handle(r)not in resolved])}
    for key in ('assigned','pending','unparsed_candidates','exceptions'):
        result[key]=[r for r in result[key]if handle(r)not in resolved]
    result['seeds']=[r for r in result['seeds']if r['evidence_id']not in {'source:'+h for h in resolved}]
    result['direct_observations']=[r for r in result['direct_observations']if r['source_text']['handle']not in resolved]
    for row in observations:
        result['seeds'].append(dict(edge_id=row['edge_id'],nominal_mm=row['nominal_mm'],evidence_id='source:'+row['source_text']['handle']))
    result['inherited_annotation_evidence']=proofs
    result['inherited_DN_observations']=observations
    result['inherited_consumed_text_handles']=sorted(consumed)
    result['inherited_consumed_stroke_handles']=sorted(strokes)
    result['historical_annotation_algorithms_or_globals_changed']=False
    return result


def barriers(doc,graph,annotation,scope):
    private=dict(annotation);component=dict(annotation['component_DN'])
    component['consumed_DN_text_handles']=sorted(set(component['consumed_DN_text_handles'])|set(annotation['inherited_consumed_text_handles']))
    component['consumed_leader_handles']=sorted(set(component['consumed_leader_handles'])|set(annotation['inherited_consumed_stroke_handles']))
    private['component_DN']=component
    return original_barriers(doc,graph,private,scope)


def collect(doc,graph,source_hash,graph_hash,reviewed_seeds=(),announce=lambda x:None,circle_policy=None,annotation_config=None):
    config=annotation_config or {}
    namespace=dict(original_collect.__globals__)
    namespace['annotation_inventory']=lambda d,g,sh,gh:inventory(d,g,sh,gh,config)
    namespace['leader_barriers']=barriers
    reader=types.FunctionType(original_collect.__code__,namespace,original_collect.__name__)
    result=reader(doc,graph,source_hash,graph_hash,reviewed_seeds,announce,circle_policy)
    result['inherited_annotation_readers_applied']=sorted(result['annotation_evidence']['inherited_annotation_evidence'])
    result['previous_DN_source_kernel_changed']=False
    return result
