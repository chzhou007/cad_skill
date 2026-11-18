"""Retain every parent comparison issue when adding checked direct-main values."""
import copy
import sys
from pathlib import Path

_owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
if str(_owner) not in sys.path:sys.path.insert(0,str(_owner))

from confirm_crossview_paths import load,sha
from native_replay_session import verify_once


def check(root,report,graph_hash,graph_path):
    from attach_known_junction_main_plan_attributes import verify_output,restore,ROOT
    path=Path(graph_path);audit=verify_once(path.parent,verify_output);graph=load(path)
    if (path.name!='graph_with_edges.json' or Path(root).resolve()!=path.resolve().parent
        or sha(path)!=graph_hash or audit['output_graph_sha256']!=graph_hash
        or audit.get('human_accepted') is not False or audit.get('hil_ready') is not False):
        raise ValueError('Known-junction fusion source root differs')
    parent=Path(audit['parent_graph']['path']);ph=audit['parent_graph']['sha256']
    if sha(parent)!=ph or audit['verified_complete_parent']['output_graph_sha256']!=ph:raise ValueError('Known-junction fusion complete parent changed')
    restore(graph,audit['stage'],load(parent))
    prior_path=parent.parent/'source-comparison-gate.json';prior=load(prior_path)
    if prior.get('graph_sha256')!=ph or not isinstance(prior.get('errors'),list) or not isinstance(prior.get('pending'),list):
        raise ValueError('Known-junction fusion lacks a bound complete parent comparison')
    result=copy.deepcopy(prior)
    result['pending'].append('Additional direct-main plan DN/XY source scopes are checked; inline interiors, unshown connections, complete physical lengths and HIL remain pending')
    result.update(status='failed' if result['errors'] else 'pending',graph_sha256=graph_hash,hil_ready=False,human_accepted=False,
        known_junction_main_attribute_stage=dict(source_replay='passed',**copy.deepcopy(audit['stage']),prior_graph_sha256=ph,prior_comparison_sha256=sha(prior_path)))
    if report!=prior and report!=result:raise ValueError('Known-junction fusion discarded or altered parent comparison issues')
    return result
