"""Use the new native root while retaining the full parent's viewer ancestry."""
import copy,hashlib,json,sys
from pathlib import Path

def verify(graph_path,graph):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_anchored_floor_main_attributes import verify_output,ROOT,FIELD
    graph_path=Path(graph_path);audit=verify_output(graph_path.parent)
    return from_audit(graph_path,graph,audit)


def from_audit(graph_path,graph,audit):
    """Consume the complete parent context freshly replayed by a later root."""
    from attach_anchored_floor_main_attributes import ROOT,FIELD
    from wave_plan_scope_viewer_evidence import from_audit as prior_audit
    graph_path=Path(graph_path);digest=hashlib.sha256(graph_path.read_bytes()).hexdigest();stage=audit['stage']
    if (graph_path.name!='graph_with_edges.json' or json.loads(graph_path.read_text('utf-8'))!=graph or audit['output_graph_sha256']!=digest
        or graph.get(ROOT)!=stage or stage.get('prior_topology_components_and_attributes_preserved') is not True
        or stage.get('related_HIL_confirmation_inherited') is not False or audit.get('hil_ready') is not False or audit.get('human_accepted') is not False):raise ValueError('main viewer root differs')
    rows=[e[FIELD] for e in graph['edges'] if FIELD in e]
    if len(rows)!=len(stage['records']) or {r['axis_edge']:r for r in rows}!={r['axis_edge']:r for r in stage['records']} or len({r['axis_edge'] for r in rows})!=len(rows):raise ValueError('main viewer edge/root evidence differs')
    parent=Path(audit['parent_graph']['path']);ph=audit['parent_graph']['sha256'];old=json.loads(parent.read_text('utf-8'))
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=ph or audit['verified_wave_parent']['output_graph_sha256']!=ph:raise ValueError('main viewer parent changed')
    candidate=copy.deepcopy(graph);candidate.pop(ROOT);candidate['metadata']=copy.deepcopy(old.get('metadata',{}))
    for e in candidate['edges']:e.pop(FIELD,None)
    if candidate!=old:raise ValueError('main viewer lost prior values, topology or evidence')
    ancestor,proof=prior_audit(parent,old,audit['verified_wave_parent'])
    proof['anchored_floor_main_attribute_audit']=audit;proof['anchored_floor_main_parent_graph_path']=str(parent)
    proof.update(output_graph_sha256=digest,human_accepted=False,hil_ready=False)
    return ancestor,proof

def dependency_paths(proof,graph_path):
    from wave_plan_scope_viewer_evidence import dependency_paths as prior_paths
    audit=proof['anchored_floor_main_attribute_audit'];paths=prior_paths(proof,Path(audit['parent_graph']['path']));skills=Path(__file__).resolve().parents[2]
    paths.update(anchored_main_fusion_audit=Path(graph_path).parent/'anchored-main-fusion-audit.json',anchored_main_fusion_verifier=skills/'build-cad-pipe-topology/scripts/attach_anchored_floor_main_attributes.py',
        anchored_main_viewer_verifier=Path(__file__).resolve(),anchored_main_mapping=Path(audit['mapping_path']),anchored_main_attributes=Path(audit['attribute_scope_path']))
    return paths
