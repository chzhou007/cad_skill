"""Preserve the entire checked-main comparison when adding named prefixes."""
import copy,hashlib,json,sys
from pathlib import Path


def check(root,report,graph_hash,graph_path):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_network_named_lower_plan_attributes import verify_output,ROOT,FIELD
    graph_path=Path(graph_path);audit=verify_output(graph_path.parent);stage=audit['stage'];graph=json.loads(graph_path.read_text('utf-8'))
    if (Path(root).resolve()!=graph_path.resolve().parent or graph_path.name!='graph_with_edges.json'
        or audit['output_graph_sha256']!=graph_hash or hashlib.sha256(graph_path.read_bytes()).hexdigest()!=graph_hash or graph.get(ROOT)!=stage
        or audit.get('hil_ready') is not False or audit.get('human_accepted') is not False
        or stage.get('prior_topology_components_and_attributes_preserved') is not True
        or stage.get('related_HIL_confirmation_inherited') is not False):raise ValueError('named prefix comparison output differs')
    parent=Path(audit['parent_graph']['path']);ph=audit['parent_graph']['sha256'];comparison=parent.parent/'source-comparison-gate.json'
    old=json.loads(parent.read_text('utf-8'));previous=json.loads(comparison.read_text('utf-8'))
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=ph or audit['verified_main_parent']['output_graph_sha256']!=ph:raise ValueError('named prefix comparison parent differs')
    restored=copy.deepcopy(graph);restored.pop(ROOT);restored['metadata']=copy.deepcopy(old.get('metadata',{}))
    for e in restored['edges']:e.pop(FIELD,None)
    if (restored!=old or report!=previous or previous.get('graph_sha256')!=ph or not isinstance(previous.get('errors'),list)
        or not isinstance(previous.get('pending'),list)):raise ValueError('named prefix needs exact complete parent comparison')
    result=copy.deepcopy(previous);result['pending'].append('Named horizontal prefixes use plan DN/XY only; remaining mappings, mixed-edge lengths, vertical physical lengths and HIL remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        network_named_lower_plan_attribute_stage=dict(source_replay='passed',**copy.deepcopy(stage),prior_graph_sha256=ph,prior_comparison_sha256=hashlib.sha256(comparison.read_bytes()).hexdigest()))
    return result
