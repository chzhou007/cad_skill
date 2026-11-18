"""Compare new main attributes against the complete verified axis parent."""
import copy,hashlib,json,sys
from pathlib import Path

def check(root,report,graph_hash,graph_path):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_anchored_floor_main_attributes import verify_output,ROOT
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(root);stage=audit['stage']
    if (graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash
        or hashlib.sha256(graph_path.read_bytes()).hexdigest()!=graph_hash or audit.get('hil_ready') is not False
        or stage.get('prior_topology_components_and_attributes_preserved') is not True or stage.get('related_HIL_confirmation_inherited') is not False
        or stage.get('human_accepted') is not False or json.loads(graph_path.read_text('utf-8')).get(ROOT)!=stage):raise ValueError('main fusion root or preservation differs')
    parent=Path(audit['parent_graph']['path']);ph=audit['parent_graph']['sha256'];previous_path=parent.parent/'source-comparison-gate.json';previous=json.loads(previous_path.read_text('utf-8'))
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=ph or audit['verified_wave_parent']['output_graph_sha256']!=ph:raise ValueError('main fusion parent changed')
    if (report!=previous or previous.get('graph_sha256')!=ph or not isinstance(previous.get('errors'),list) or not isinstance(previous.get('pending'),list)):
        raise ValueError('main fusion needs exact complete parent comparison')
    result=copy.deepcopy(previous);result['pending'].append('Additional floor main DN conflicts, inline interiors, remaining mappings, vertical physical lengths and full drawing/HIL acceptance remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        anchored_floor_main_attribute_stage=dict(source_replay='passed',**copy.deepcopy(stage),prior_graph_sha256=ph,prior_comparison_sha256=hashlib.sha256(previous_path.read_bytes()).hexdigest()))
    return result
