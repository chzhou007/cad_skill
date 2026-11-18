"""Replay pipe scopes plus destination context before the retained prefix root."""
import copy,hashlib,json,sys
from pathlib import Path


def verify(graph_path,graph):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_external_feed_plan_attributes import verify_output,ROOT,FIELD,NODE_FIELD
    graph_path=Path(graph_path);audit=verify_output(graph_path.parent)
    return from_audit(graph_path,graph,audit)


def from_audit(graph_path,graph,audit):
    """Reuse only the complete parent audit freshly replayed by a child."""
    from attach_external_feed_plan_attributes import ROOT,FIELD,NODE_FIELD
    from network_named_lower_plan_viewer_evidence import from_audit as prefix_from_audit
    graph_path=Path(graph_path);digest=hashlib.sha256(graph_path.read_bytes()).hexdigest();stage=audit['stage']
    if (graph_path.name!='graph_with_edges.json' or json.loads(graph_path.read_text('utf-8'))!=graph or audit['output_graph_sha256']!=digest
        or graph.get(ROOT)!=stage or stage.get('prior_topology_components_and_attributes_preserved') is not True
        or stage.get('related_HIL_confirmation_inherited') is not False or audit.get('hil_ready') is not False or audit.get('human_accepted') is not False):raise ValueError('external feed viewer root differs')
    rows=[e[FIELD] for e in graph['edges'] if FIELD in e];contexts={n['node_id']:n[NODE_FIELD] for n in graph['nodes'] if NODE_FIELD in n}
    if (len(rows)!=stage['added_external_pipe_scopes'] or len({r['axis_edge'] for r in rows})!=len(rows)
        or {r['axis_edge']:r for r in rows}!={r['axis_edge']:r for r in stage['records']}
        or contexts!=stage['node_contexts'] or len(contexts)!=stage['source_declared_boundary_contexts']):raise ValueError('external root/edge/node evidence differs')
    parent=Path(audit['parent_graph']['path']);ph=audit['parent_graph']['sha256'];old=json.loads(parent.read_text('utf-8'))
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=ph or audit['verified_prefix_parent']['output_graph_sha256']!=ph:raise ValueError('external viewer parent changed')
    restored=copy.deepcopy(graph);restored.pop(ROOT);restored['metadata']=copy.deepcopy(old.get('metadata',{}))
    for e in restored['edges']:e.pop(FIELD,None)
    for n in restored['nodes']:n.pop(NODE_FIELD,None)
    if restored!=old:raise ValueError('external viewer changed prior topology, components or attributes')
    ancestor,proof=prefix_from_audit(parent,old,audit['verified_prefix_parent'])
    proof.update(external_feed_plan_attribute_audit=audit,output_graph_sha256=digest,human_accepted=False,hil_ready=False)
    return ancestor,proof


def dependency_paths(proof,graph_path):
    from network_named_lower_plan_viewer_evidence import dependency_paths as prior_paths
    audit=proof['external_feed_plan_attribute_audit'];paths=prior_paths(proof,Path(audit['parent_graph']['path']));skills=Path(__file__).resolve().parents[2]
    paths.update(external_feed_plan_fusion_audit=Path(graph_path).parent/'external-feed-plan-fusion-audit.json',external_feed_plan_fusion_verifier=skills/'build-cad-pipe-topology/scripts/attach_external_feed_plan_attributes.py',
        external_feed_plan_viewer_verifier=Path(__file__).resolve(),external_feed_plan_mapping=Path(audit['mapping_path']),external_feed_plan_attributes=Path(audit['attribute_scope_path']))
    for side,path in audit['destination_evidence_paths'].items():paths['external_feed_destination_'+side]=Path(path)
    return paths
