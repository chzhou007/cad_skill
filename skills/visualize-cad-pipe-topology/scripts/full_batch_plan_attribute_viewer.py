"""Current batch ancestry over the exact, freshly replayed prefix parent."""
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts',Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'):
    if str(_p)not in sys.path:sys.path.insert(0,str(_p))
from confirm_crossview_paths import load,sha


def verify(graph_path,graph):
    from compose_full_batch_plan_attributes import verify_output,ROOT
    from full_batch_axis_attribute_composition import restore
    from adopt_current_named_prefix_evidence import restore as restore_prefix
    from known_junction_main_viewer_evidence import from_audit
    from native_replay_session import verify_once
    path=Path(graph_path);audit=verify_once(path.parent,verify_output);parent=Path(audit['parent_graph']['path']);old=load(parent)
    if (path.name!='graph_with_edges.json'or load(path)!=graph or sha(path)!=audit['output_graph_sha256']or graph.get(ROOT)!=audit['stage']
        or sha(parent)!=audit['parent_graph']['sha256']or audit['verified_complete_parent']['output_graph_sha256']!=sha(parent)):
        raise ValueError('complete batch viewer source or parent differs')
    restore(graph,old);prefix=audit['verified_complete_parent'];known=Path(prefix['parent_graph']['path']);known_graph=load(known)
    if sha(known)!=prefix['parent_graph']['sha256']:raise ValueError('retained current prefix native ancestry differs')
    restore_prefix(old,known_graph)
    ancestor,proof=from_audit(known,known_graph,prefix['verified_complete_parent'])
    proof.update(current_named_prefix_evidence_fusion_audit=prefix,full_batch_plan_attribute_fusion_audit=audit,
        output_graph_sha256=sha(path),human_accepted=False,hil_ready=False)
    return ancestor,proof


def dependency_paths(proof,graph_path):
    from current_named_prefix_viewer_evidence import dependency_paths as parent_paths
    audit=proof['full_batch_plan_attribute_fusion_audit'];parent=Path(audit['parent_graph']['path']);paths=parent_paths(proof,parent)
    skills=Path(__file__).resolve().parents[2];policy_path=Path(audit['policy']['path']);policy=load(policy_path)
    paths.update(full_batch_plan_fusion_audit=Path(graph_path).parent/'full-batch-plan-attribute-fusion-audit.json',full_batch_plan_policy=policy_path,
        full_batch_plan_fusion_verifier=skills/'build-cad-pipe-topology/scripts/compose_full_batch_plan_attributes.py',
        full_batch_plan_composition=skills/'build-cad-pipe-topology/scripts/full_batch_axis_attribute_composition.py',
        full_batch_plan_metric_reader=skills/'build-cad-pipe-topology/scripts/inherited_batch_plan_metrics.py',
        full_batch_plan_source_gate=skills/'orchestrate-cad-drawing-pipeline/scripts/full_batch_plan_attribute_gate.py',
        full_batch_plan_viewer_verifier=Path(__file__).resolve(),
        uniform_path_group_DN_reader=skills/'visualize-cad-pipe-topology/scripts/uniform_path_group_DN_context.py')
    for key,item in policy['inputs'].items():paths['full_batch_'+key]=Path(item['path'])
    for floor,item in policy['metric_policies'].items():paths['full_batch_metric_policy_'+floor]=Path(item['path'])
    return paths
