"""Preserve the complete parent comparison after named-prefix evidence adoption."""
import copy
import sys
from pathlib import Path


def check(root, report, graph_hash, graph_path):
    scripts = Path(__file__).resolve().parents[2] / 'build-cad-pipe-topology/scripts'
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from confirm_crossview_paths import load, sha
    from adopt_current_named_prefix_evidence import verify_output, restore
    graph_path = Path(graph_path)
    audit = verify_output(graph_path.parent)
    if (Path(root).resolve() != graph_path.resolve().parent or graph_path.name != 'graph_with_edges.json'
        or audit['output_graph_sha256'] != graph_hash or sha(graph_path) != graph_hash
        or audit.get('hil_ready') is not False or audit.get('human_accepted') is not False):
        raise ValueError('Current named prefix source root differs')
    parent_path = Path(audit['parent_graph']['path'])
    parent_hash = audit['parent_graph']['sha256']
    if sha(parent_path) != parent_hash or audit['verified_complete_parent']['output_graph_sha256'] != parent_hash:
        raise ValueError('Current named prefix complete parent differs')
    graph, parent = load(graph_path), load(parent_path)
    restore(graph, parent)
    prior_path = parent_path.parent / 'source-comparison-gate.json'
    prior = load(prior_path)
    if (prior.get('graph_sha256') != parent_hash or not isinstance(prior.get('errors'), list)
        or not isinstance(prior.get('pending'), list)):
        raise ValueError('Complete parent comparison is missing or bound to another graph')
    result = copy.deepcopy(prior)
    result['pending'].append('Current named upper prefix source/version evidence replayed; all old values and pending scopes retained; viewer and HIL remain pending')
    result.update(status='failed' if result['errors'] else 'pending', graph_sha256=graph_hash,
        hil_ready=False, human_accepted=False, current_named_prefix_evidence_stage=dict(
            source_replay='passed', **copy.deepcopy(audit['stage']), prior_graph_sha256=parent_hash,
            prior_comparison_sha256=sha(prior_path)))
    if report != prior and report != result:
        raise ValueError('Current named prefix comparison altered old errors or pending issues')
    return result
