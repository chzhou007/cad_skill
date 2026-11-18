"""Compare current floor evidence without losing the complete parent report."""
import copy
import hashlib
import json
import sys
from pathlib import Path


def restore(graph, stage, parent):
    from adopt_current_floor_plan_scopes import ROOT, FIELD
    if (graph.get(ROOT) != stage or stage.get('prior_topology_components_and_all_attributes_preserved') is not True
            or stage.get('whole_values_or_connections_added') != 0 or stage.get('related_HIL_confirmation_inherited') is not False):
        raise ValueError('Current floor adoption stage changed physical or historical state')
    actual = [e[FIELD] for e in graph['edges'] if FIELD in e]
    if (len(actual) != stage['source_checked_plan_scopes'] or len({r['edge_id'] for r in actual}) != len(actual)
            or {r['edge_id']: r for r in actual} != {r['edge_id']: r for r in stage['records']}):
        raise ValueError('Current floor root and edge evidence differ')
    restored = copy.deepcopy(graph); restored.pop(ROOT); restored['metadata'] = copy.deepcopy(parent.get('metadata', {}))
    for edge in restored['edges']: edge.pop(FIELD, None)
    if restored != parent: raise ValueError('Current floor adoption changed parent topology, components or attributes')
    return restored


def check(root, report, graph_hash, graph_path):
    owner = Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path: sys.path.insert(0, str(owner))
    from adopt_current_floor_plan_scopes import verify_output, ROOT
    graph_path = Path(graph_path); audit = verify_output(graph_path.parent); graph = json.loads(graph_path.read_text('utf-8'))
    if (Path(root).resolve() != graph_path.resolve().parent or graph_path.name != 'graph_with_edges.json'
            or audit['output_graph_sha256'] != graph_hash or hashlib.sha256(graph_path.read_bytes()).hexdigest() != graph_hash
            or audit.get('hil_ready') is not False or audit.get('human_accepted') is not False): raise ValueError('Current floor source root differs')
    parent_path = Path(audit['parent_graph']['path']); parent_hash = audit['parent_graph']['sha256']; parent = json.loads(parent_path.read_text('utf-8'))
    if hashlib.sha256(parent_path.read_bytes()).hexdigest() != parent_hash or audit['verified_complete_parent']['output_graph_sha256'] != parent_hash:
        raise ValueError('Current floor source parent changed')
    restore(graph, audit['stage'], parent)
    prior_path = parent_path.parent/'source-comparison-gate.json'; prior = json.loads(prior_path.read_text('utf-8'))
    if prior.get('graph_sha256') != parent_hash or not isinstance(prior.get('errors'), list) or not isinstance(prior.get('pending'), list):
        raise ValueError('Current floor adoption lacks complete parent comparison')
    result = copy.deepcopy(prior)
    result['pending'].append('Current floor plan DN/XY scopes are independently replayed; prior attributes remain historical, axis local DN extents, unknown connectors, full network and HIL remain pending')
    result.update(status='failed' if result['errors'] else 'pending', graph_sha256=graph_hash, hil_ready=False, human_accepted=False,
        current_floor_plan_scope_adoption_stage=dict(source_replay='passed', **copy.deepcopy(audit['stage']),
            prior_graph_sha256=parent_hash, prior_comparison_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest()))
    if report != prior and report != result: raise ValueError('Current floor comparison discarded or altered parent issues')
    return result
