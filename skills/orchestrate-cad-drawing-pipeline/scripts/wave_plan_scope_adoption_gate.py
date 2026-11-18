"""Source comparison for fresh plan scopes over an independently replayed parent."""
import copy,hashlib,json,sys
from pathlib import Path


def check_wave_plan_scope_adoption(root,report,graph_hash,graph_path):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from adopt_wave_rebased_plan_scopes import verify_output,ROOT
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();audit=verify_output(root);proof=audit['proof']
    if (graph_path.parent!=root or graph_path.name!='graph_with_edges.json' or audit['output_graph_sha256']!=graph_hash
        or hashlib.sha256(graph_path.read_bytes()).hexdigest()!=graph_hash or audit.get('hil_ready') is not False
        or proof.get('prior_topology_components_and_other_attributes_preserved') is not True
        or proof.get('whole_DN_or_lengths_added')!=0 or proof.get('related_HIL_confirmation_inherited') is not False):
        raise ValueError('current plan adoption graph or preservation scope differs')
    graph=json.loads(graph_path.read_text('utf8'))
    if graph.get(ROOT)!=proof:raise ValueError('current plan adoption root differs from native replay')
    parent=Path(audit['parent_graph']['path']);ph=audit['parent_graph']['sha256'];lower=audit['verified_lower_parent']
    if hashlib.sha256(parent.read_bytes()).hexdigest()!=ph or lower['output_graph_sha256']!=ph:
        raise ValueError('current plan adoption parent changed')
    previous_path=parent.parent/'source-comparison-gate.json';previous=json.loads(previous_path.read_text('utf8'))
    if (report!=previous or previous.get('graph_sha256')!=ph or not isinstance(previous.get('errors'),list)
        or not isinstance(previous.get('pending'),list) or previous.get('lower_floor_plan_segment_attribute_stage',{}).get('source_replay')!='passed'):
        raise ValueError('current plan adoption requires the exact complete lower-parent comparison')
    result=copy.deepcopy(previous);result['pending'].append('Current plan scopes preserve historical values and add partial projections; native local axis DN domains do not prove equal extents or a physical transition; whole drawing and HIL remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        wave_plan_scope_adoption_stage=dict(source_replay='passed',current_scope_edges=len(proof['records']),retained_historical_attributes=proof['retained_historical_attributes'],
            added_partial_attributes=proof['added_partial_attributes'],records=proof['records'],native_axis_annotation_domains=audit['axis_annotation_domains'],
            prior_graph_sha256=ph,prior_graph_comparison_sha256=hashlib.sha256(previous_path.read_bytes()).hexdigest(),
            previous_topology_components_and_attributes_preserved=True,whole_DN_or_lengths_added=0,human_accepted=False))
    return result
