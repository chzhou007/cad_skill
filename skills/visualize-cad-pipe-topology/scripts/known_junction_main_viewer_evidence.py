"""Replay direct-main fusion, then use its freshly checked complete parent audit."""
from pathlib import Path
import sys

for _path in (Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts',Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'):
    if str(_path) not in sys.path:sys.path.insert(0,str(_path))

from confirm_crossview_paths import load,sha
from native_replay_session import verify_once


def verify(graph_path,graph):
    from attach_known_junction_main_plan_attributes import verify_output
    path=Path(graph_path)
    return from_audit(path,graph,verify_once(path.parent,verify_output))


def from_audit(graph_path,graph,audit):
    from attach_known_junction_main_plan_attributes import restore,ROOT
    from current_floor_scope_adoption_gate import restore as restore_current
    from external_feed_plan_viewer_evidence import from_audit as external_from_audit
    path=Path(graph_path);digest=sha(path)
    if (path.name!='graph_with_edges.json' or load(path)!=graph or audit['output_graph_sha256']!=digest
        or graph.get(ROOT)!=audit['stage'] or audit.get('hil_ready') is not False or audit.get('human_accepted') is not False):
        raise ValueError('Known-junction viewer root differs')
    parent=Path(audit['parent_graph']['path']);old=load(parent);current=audit['verified_complete_parent']
    if sha(parent)!=audit['parent_graph']['sha256'] or current['output_graph_sha256']!=sha(parent):raise ValueError('Known-junction viewer parent changed')
    restore(graph,audit['stage'],old)
    external=Path(current['parent_graph']['path']);external_graph=load(external)
    if sha(external)!=current['parent_graph']['sha256'] or current['verified_complete_parent']['output_graph_sha256']!=sha(external):
        raise ValueError('Known-junction current-floor external ancestor changed')
    restore_current(old,current['stage'],external_graph)
    ancestor,proof=external_from_audit(external,external_graph,current['verified_complete_parent'])
    proof.update(current_floor_plan_scope_adoption_audit=current,known_junction_main_fusion_audit=audit,
                 output_graph_sha256=digest,human_accepted=False,hil_ready=False)
    return ancestor,proof


def dependency_paths(proof,graph_path):
    from current_floor_scope_viewer_evidence import dependency_paths as parent_paths
    audit=proof['known_junction_main_fusion_audit'];parent=Path(audit['parent_graph']['path'])
    paths=parent_paths(proof,parent);skills=Path(__file__).resolve().parents[2]
    attr=Path(audit['attribute_scope_path']);mapping=Path(audit['mapping_path'])
    paths.update(known_junction_main_fusion_audit=Path(graph_path).parent/'known-junction-main-fusion-audit.json',
        known_junction_main_fusion_verifier=skills/'build-cad-pipe-topology/scripts/attach_known_junction_main_plan_attributes.py',
        known_junction_main_source_gate=skills/'orchestrate-cad-drawing-pipeline/scripts/known_junction_main_fusion_gate.py',
        known_junction_main_viewer_verifier=Path(__file__).resolve(),known_junction_main_attributes=attr,
        known_junction_main_attribute_receipt=attr.with_name('known-main-attribute-receipt.json'),
        known_junction_main_mapping=mapping,known_junction_main_mapping_receipt=mapping.with_name('source-mapping-receipt.json'))
    return paths
