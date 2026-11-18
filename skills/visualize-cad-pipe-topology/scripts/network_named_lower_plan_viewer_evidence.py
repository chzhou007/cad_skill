"""Replay named prefixes and retain the fresh complete-main viewer evidence."""
import copy,hashlib,json,sys
from pathlib import Path


def verify(graph_path,graph):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_network_named_lower_plan_attributes import verify_output,ROOT,FIELD
    graph_path=Path(graph_path);audit=verify_output(graph_path.parent)
    return from_audit(graph_path,graph,audit)


def from_audit(graph_path,graph,audit):
    """Reuse only the complete prefix audit freshly replayed by a later root."""
    from attach_network_named_lower_plan_attributes import ROOT,FIELD
    from anchored_floor_main_viewer_evidence import from_audit as prior_audit
    graph_path=Path(graph_path);digest=hashlib.sha256(graph_path.read_bytes()).hexdigest();stage=audit['stage']
    if (graph_path.name!='graph_with_edges.json' or json.loads(graph_path.read_text('utf-8'))!=graph or audit['output_graph_sha256']!=digest
        or graph.get(ROOT)!=stage or stage.get('prior_topology_components_and_attributes_preserved') is not True
        or stage.get('related_HIL_confirmation_inherited') is not False or audit.get('hil_ready') is not False or audit.get('human_accepted') is not False):raise ValueError('named prefix viewer root differs')
    rows=[e[FIELD] for e in graph['edges'] if FIELD in e]
    if len(rows)!=2 or len(stage['records'])!=2 or {r['edge_id']:r for r in rows}!={r['edge_id']:r for r in stage['records']}:raise ValueError('named prefix viewer edge/root differs')
    parent=Path(audit['parent_graph']['path']);ph=audit['parent_graph']['sha256'];old=json.loads(parent.read_text('utf-8'))
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=ph or audit['verified_main_parent']['output_graph_sha256']!=ph:raise ValueError('named prefix viewer parent changed')
    restored=copy.deepcopy(graph);restored.pop(ROOT);restored['metadata']=copy.deepcopy(old.get('metadata',{}))
    for e in restored['edges']:e.pop(FIELD,None)
    if restored!=old:raise ValueError('named prefix viewer lost prior values or topology')
    ancestor,proof=prior_audit(parent,old,audit['verified_main_parent'])
    proof.update(network_named_lower_plan_attribute_audit=audit,output_graph_sha256=digest,human_accepted=False,hil_ready=False)
    return ancestor,proof


def dependency_paths(proof,graph_path):
    from anchored_floor_main_viewer_evidence import dependency_paths as prior_paths
    audit=proof['network_named_lower_plan_attribute_audit'];paths=prior_paths(proof,Path(audit['parent_graph']['path']));skills=Path(__file__).resolve().parents[2]
    paths.update(network_named_lower_plan_fusion_audit=Path(graph_path).parent/'network-named-lower-plan-fusion-audit.json',
        network_named_lower_plan_fusion_verifier=skills/'build-cad-pipe-topology/scripts/attach_network_named_lower_plan_attributes.py',
        network_named_lower_plan_viewer_verifier=Path(__file__).resolve(),network_named_lower_plan_mapping=Path(audit['mapping_path']),network_named_lower_plan_attributes=Path(audit['attribute_scope_path']))
    return paths
