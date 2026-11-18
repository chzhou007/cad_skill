"""Apply current-circle lineage inside the inherited complete-plan DN reader."""
import types
from crossview_equipment_branch_inventory import native_tee as original_tee
from full_plan_DN_source import collect as source_collect
from full_plan_DN_inherited_annotations import inventory, barriers
from current_circle_main_lineage import collect as circle_collect


def current_tee(doc, graph, node_id, source_hash, graph_hash, parents):
    try:
        return original_tee(doc, graph, node_id, source_hash, graph_hash)
    except ValueError as exc:
        # Unsupported descendant identity is the only fall-through. Geometric,
        # source, mixed-system and review failures retain the original barrier.
        if str(exc) not in ('reviewed main child identity differs', 'main descendant lacks one source-reviewed split'):
            raise
        node = next(n for n in graph['nodes'] if n['node_id'] == node_id)
        if not node.get('source_reviewed_circle'):
            raise
        return circle_collect(doc, graph, node_id, source_hash, graph_hash, parents)


def collect(doc, graph, source_hash, graph_hash, reviewed_seeds=(), announce=lambda x: None,
            circle_policy=None, annotation_config=None, lineage_parents=()):
    config = annotation_config or {}
    evidence = {}
    def tee(d, g, nid, sh, gh):
        proof = current_tee(d, g, nid, sh, gh, lineage_parents)
        if proof.get('current_main_lineage'):
            evidence[nid] = proof
        return proof
    namespace = dict(source_collect.__globals__)
    namespace['annotation_inventory'] = lambda d, g, sh, gh: inventory(d, g, sh, gh, config)
    namespace['leader_barriers'] = barriers
    namespace['native_tee'] = tee
    reader = types.FunctionType(source_collect.__code__, namespace, source_collect.__name__)
    result = reader(doc, graph, source_hash, graph_hash, reviewed_seeds, announce, circle_policy)
    result['inherited_annotation_readers_applied'] = sorted(result['annotation_evidence']['inherited_annotation_evidence'])
    result['previous_DN_source_kernel_changed'] = False
    result['current_circle_main_lineage_parents'] = list(lineage_parents)
    # Roles are the inheritance result, not source proofs. Keep actual lineage
    # receipts independently so the full result can be replayed and audited.
    result['current_circle_lineage_evidence'] = evidence
    result['current_circle_lineage_nodes'] = sorted(evidence)
    return result
