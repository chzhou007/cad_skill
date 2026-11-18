"""Reuse original confirmed corner-main rays inside complete local DN."""
import types
from current_circle_plan_DN import collect as previous_collect, current_tee as previous_tee
from native_user_circle_endpoint_rays import collect as endpoint_collect


def current_tee(doc, graph, node_id, source_hash, graph_hash, parents, review):
    try:
        return previous_tee(doc, graph, node_id, source_hash, graph_hash, parents)
    except ValueError as exc:
        if str(exc) != 'user circle native contact no longer unique':
            raise
        node = next(n for n in graph['nodes'] if n['node_id'] == node_id)
        if not node.get('user_confirmed_circle') or review is None:
            raise
        return endpoint_collect(doc, graph, node_id, source_hash, graph_hash, parents, review)


def collect(doc, graph, source_hash, graph_hash, reviewed_seeds=(), announce=lambda x:None,
            circle_policy=None, annotation_config=None, lineage_parents=(), endpoint_review=None):
    evidence = {}
    def tee(d, g, nid, sh, gh, parents):
        proof = current_tee(d, g, nid, sh, gh, parents, endpoint_review)
        if proof.get('original_main_rays_replayed'):
            evidence[nid] = proof
        return proof
    namespace = dict(previous_collect.__globals__)
    namespace['current_tee'] = tee
    reader = types.FunctionType(previous_collect.__code__, namespace, previous_collect.__name__)
    result = reader(doc, graph, source_hash, graph_hash, reviewed_seeds, announce, circle_policy, annotation_config, lineage_parents)
    result['user_circle_endpoint_review'] = endpoint_review
    result['user_circle_endpoint_evidence'] = evidence
    result['user_circle_endpoint_nodes'] = sorted(evidence)
    return result
