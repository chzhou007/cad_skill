"""Preserve confirmed overlap connection roles inside the complete DN batch."""
import types
from user_circle_endpoint_plan_DN import collect as previous_collect,current_tee as previous_tee
from native_confirmed_overlap_rays import collect as overlap_collect


def current_tee(doc,graph,node_id,source_hash,graph_hash,parents,review,overlap_owners):
    try:return previous_tee(doc,graph,node_id,source_hash,graph_hash,parents,review)
    except ValueError as exc:
        if str(exc)!='missing or ambiguous graph T ray':raise
        node=next(n for n in graph['nodes']if n['node_id']==node_id)
        if not node.get('user_confirmed_overlap_connection')or not overlap_owners:raise
        return overlap_collect(doc,graph,node_id,source_hash,graph_hash,overlap_owners)


def collect(doc,graph,source_hash,graph_hash,reviewed_seeds=(),announce=lambda x:None,
            circle_policy=None,annotation_config=None,lineage_parents=(),endpoint_review=None,overlap_owners=()):
    evidence={}
    def tee(d,g,nid,sh,gh,parents,review):
        proof=current_tee(d,g,nid,sh,gh,parents,review,overlap_owners)
        if proof.get('original_owner_replayed'):evidence[nid]=proof
        return proof
    namespace=dict(previous_collect.__globals__);namespace['current_tee']=tee
    reader=types.FunctionType(previous_collect.__code__,namespace,previous_collect.__name__)
    result=reader(doc,graph,source_hash,graph_hash,reviewed_seeds,announce,circle_policy,annotation_config,lineage_parents,endpoint_review)
    result['confirmed_overlap_owner_inputs']=list(overlap_owners)
    result['confirmed_overlap_T_evidence']=evidence
    result['confirmed_overlap_T_nodes']=sorted(evidence)
    return result
