"""Replay the new prefix root before its exact, freshly verified known-main parent."""
import sys
from pathlib import Path

for _path in (Path(__file__).resolve().parents[2] / 'build-cad-pipe-topology/scripts',
              Path(__file__).resolve().parents[2] / 'orchestrate-cad-drawing-pipeline/scripts'):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from confirm_crossview_paths import load, sha


def verify(graph_path, graph):
    from adopt_current_named_prefix_evidence import verify_output, restore, ROOT
    from known_junction_main_viewer_evidence import from_audit
    path = Path(graph_path)
    audit = verify_output(path.parent)
    digest = sha(path)
    if (path.name != 'graph_with_edges.json' or load(path) != graph or audit['output_graph_sha256'] != digest
        or graph.get(ROOT) != audit['stage'] or audit.get('hil_ready') is not False
        or audit.get('human_accepted') is not False):
        raise ValueError('Current named prefix viewer root differs')
    parent = Path(audit['parent_graph']['path'])
    old = load(parent)
    if sha(parent) != audit['parent_graph']['sha256']:
        raise ValueError('Current named prefix viewer parent changed')
    restore(graph, old)
    ancestor, proof = from_audit(parent, old, audit['verified_complete_parent'])
    proof.update(current_named_prefix_evidence_fusion_audit=audit,
        output_graph_sha256=digest, human_accepted=False, hil_ready=False)
    return ancestor, proof


def dependency_paths(proof, graph_path):
    from known_junction_main_viewer_evidence import dependency_paths as parent_paths
    audit = proof['current_named_prefix_evidence_fusion_audit']
    parent = Path(audit['parent_graph']['path'])
    paths = parent_paths(proof, parent)
    skills = Path(__file__).resolve().parents[2]
    bridge = Path(audit['native_prefix_bridge']['path'])
    receipt = bridge.with_name('prefix-version-bridge-receipt.json')
    paths.update(current_named_prefix_fusion_audit=Path(graph_path).parent/'current-named-prefix-evidence-fusion-audit.json',
        current_named_prefix_fusion_verifier=skills/'build-cad-pipe-topology/scripts/adopt_current_named_prefix_evidence.py',
        current_named_prefix_bridge_verifier=skills/'build-cad-pipe-topology/scripts/native_named_prefix_version_bridge.py',
        current_named_prefix_source_gate=skills/'orchestrate-cad-drawing-pipeline/scripts/current_named_prefix_evidence_gate.py',
        current_named_prefix_viewer_verifier=Path(__file__).resolve(),
        current_named_prefix_native_bridge=bridge, current_named_prefix_native_bridge_receipt=receipt)
    for key, spec in load(receipt)['inputs'].items():
        paths['current_named_prefix_' + key] = Path(spec['path'])
    return paths
