"""Current batch source comparison preserves the independently replayed parent."""
import copy,sys
from pathlib import Path


def _check(root,report,graph_hash,graph_path):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from confirm_crossview_paths import load,sha
    from compose_full_batch_plan_attributes import verify_output,ROOT
    from full_batch_axis_attribute_composition import restore
    from native_replay_session import verify_once
    path=Path(graph_path).resolve();audit=verify_once(path.parent,verify_output)
    if path.parent!=Path(root).resolve()or path.name!='graph_with_edges.json'or sha(path)!=graph_hash or audit['output_graph_sha256']!=graph_hash:
        raise ValueError('full-batch source output differs')
    parent=Path(audit['parent_graph']['path']);old=load(parent);graph=load(path)
    if sha(parent)!=audit['parent_graph']['sha256']or audit['verified_complete_parent']['output_graph_sha256']!=sha(parent):raise ValueError('complete batch parent native replay differs')
    restore(graph,old)
    prior_path=parent.parent/'source-comparison-gate.json';prior=load(prior_path)
    if prior.get('graph_sha256')!=sha(parent)or not isinstance(prior.get('errors'),list)or not isinstance(prior.get('pending'),list):
        raise ValueError('complete native parent comparison missing')
    result=copy.deepcopy(prior)
    result['pending'].append('Current whole-plan DN, correspondence and inherited inline/crossover pipe XY are composed; group allocation, omitted and vertical physical lengths, unresolved source scopes and HIL remain pending')
    result.update(status='failed'if result['errors']else'pending',graph_sha256=graph_hash,human_accepted=False,hil_ready=False,
        full_batch_plan_attributes_stage=dict(source_replay='passed',summary=audit['summary'],parent_graph_sha256=sha(parent),
            parent_comparison_sha256=sha(prior_path),identity_aliases=copy.deepcopy(graph[ROOT]['identity_aliases']),old_attributes_exactly_restorable=True))
    if report!=prior and report!=result:raise ValueError('complete batch comparison cannot alter prior errors or pending issues')
    return result


def check(root,report,graph_hash,graph_path):
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        return _check(root,report,graph_hash,graph_path)
