"""Replay current floor evidence before the retained complete axis parent."""
import hashlib
import json
import sys
from pathlib import Path


def verify(graph_path, graph):
    skills = Path(__file__).resolve().parents[2]
    for path in (skills/'build-cad-pipe-topology/scripts', skills/'orchestrate-cad-drawing-pipeline/scripts'):
        if str(path) not in sys.path: sys.path.insert(0, str(path))
    from adopt_current_floor_plan_scopes import verify_output, ROOT
    from current_floor_scope_adoption_gate import restore
    from external_feed_plan_viewer_evidence import from_audit
    graph_path = Path(graph_path); audit = verify_output(graph_path.parent)
    digest = hashlib.sha256(graph_path.read_bytes()).hexdigest()
    if (graph_path.name != 'graph_with_edges.json' or json.loads(graph_path.read_text('utf-8')) != graph
            or audit['output_graph_sha256'] != digest or graph.get(ROOT) != audit['stage']
            or audit.get('human_accepted') is not False or audit.get('hil_ready') is not False): raise ValueError('Current floor viewer root differs')
    parent = Path(audit['parent_graph']['path']); old = json.loads(parent.read_text('utf-8'))
    if hashlib.sha256(parent.read_bytes()).hexdigest() != audit['parent_graph']['sha256']: raise ValueError('Current floor viewer parent changed')
    restore(graph, audit['stage'], old)
    ancestor, proof = from_audit(parent, old, audit['verified_complete_parent'])
    proof.update(current_floor_plan_scope_adoption_audit=audit, output_graph_sha256=digest, human_accepted=False, hil_ready=False)
    return ancestor, proof


def dependency_paths(proof, graph_path):
    from external_feed_plan_viewer_evidence import dependency_paths as parent_paths
    audit = proof['current_floor_plan_scope_adoption_audit']
    paths = parent_paths(proof, Path(audit['parent_graph']['path']))
    skills = Path(__file__).resolve().parents[2]
    paths.update(current_floor_scope_adoption_audit=Path(graph_path).parent/'current-floor-plan-scope-adoption-audit.json',
        current_floor_scope_adoption_verifier=skills/'build-cad-pipe-topology/scripts/adopt_current_floor_plan_scopes.py',
        current_floor_scope_source_gate=skills/'orchestrate-cad-drawing-pipeline/scripts/current_floor_scope_adoption_gate.py',
        current_floor_scope_viewer_verifier=Path(__file__).resolve())
    for name, spec in audit['stage']['source_scope_files'].items(): paths['current_floor_scope_'+name] = Path(spec['path'])
    return paths
