"""Extend the complete prefix comparison without hiding remaining unknowns."""
import copy,hashlib,json,sys
from pathlib import Path


def check(root,report,graph_hash,graph_path):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_external_feed_plan_attributes import verify_output,ROOT,FIELD,NODE_FIELD
    graph_path=Path(graph_path);audit=verify_output(graph_path.parent);stage=audit['stage'];graph=json.loads(graph_path.read_text('utf-8'))
    if (Path(root).resolve()!=graph_path.resolve().parent or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash
        or hashlib.sha256(graph_path.read_bytes()).hexdigest()!=graph_hash or graph.get(ROOT)!=stage
        or audit.get('hil_ready') is not False or audit.get('human_accepted') is not False or stage.get('prior_topology_components_and_attributes_preserved') is not True
        or stage.get('new_connections_added')!=0 or stage.get('whole_physical_lengths_assigned')!=0 or stage.get('related_HIL_confirmation_inherited') is not False):raise ValueError('external fusion root or preservation differs')
    parent=Path(audit['parent_graph']['path']);ph=audit['parent_graph']['sha256'];previous_path=parent.parent/'source-comparison-gate.json';old=json.loads(parent.read_text('utf-8'));previous=json.loads(previous_path.read_text('utf-8'))
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=ph or audit['verified_prefix_parent']['output_graph_sha256']!=ph:raise ValueError('external fusion parent changed')
    restored=copy.deepcopy(graph);restored.pop(ROOT);restored['metadata']=copy.deepcopy(old.get('metadata',{}))
    for e in restored['edges']:e.pop(FIELD,None)
    for n in restored['nodes']:n.pop(NODE_FIELD,None)
    if restored!=old or report!=previous or previous.get('graph_sha256')!=ph or not isinstance(previous.get('errors'),list) or not isinstance(previous.get('pending'),list):raise ValueError('external fusion needs exact complete prefix comparison')
    result=copy.deepcopy(previous);result['pending'].append('External source pipe DN/XY and destination context are checked; joint interiors, physical ports, external hydraulic connectivity, remaining device ownership and HIL remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        external_feed_plan_attribute_stage=dict(source_replay='passed',**copy.deepcopy(stage),prior_graph_sha256=ph,prior_comparison_sha256=hashlib.sha256(previous_path.read_bytes()).hexdigest()))
    return result
