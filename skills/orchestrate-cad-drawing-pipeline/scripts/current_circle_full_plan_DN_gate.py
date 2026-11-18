"""Check current source-circle ancestry without upgrading graph/HIL state."""
import sys
from pathlib import Path
from full_plan_DN_gate import check as original_check


def check(data):
    if (data.get('mode') != 'complete_local_plan_native_DN_current_circle_main_lineage_v3'
            or data.get('historical_native_implementations_or_globals_changed') is not False):
        raise ValueError('current-circle complete-plan DN entry required')
    report = original_check(dict(data, mode=data['previous_mode']))
    nodes = {}
    for floor, result in data['floors'].items():
        evidence = result.get('current_circle_lineage_evidence', {})
        if result.get('current_circle_lineage_nodes') != sorted(evidence):
            raise ValueError('current circle lineage inventory differs')
        for nid, proof in evidence.items():
            if (nid not in result.get('roles', {}) or nid in result['source_T_exceptions']
                    or proof.get('graph_sha256') != data['local_parent_replay'][floor]['graph_sha256']
                    or proof.get('source_sha256') != result.get('source_sha256')
                    or proof.get('graph_mutated') is not False or proof.get('physical_values_assigned') != 0
                    or proof.get('historical_reader_or_globals_changed') is not False
                    or not proof.get('current_main_lineage')):
                raise ValueError('current circle lineage is not a current source-proved T')
        nodes[floor] = sorted(evidence)
    report['source_replay'] = 'all_current_local_owners_inherited_annotations_and_native_circle_main_lineage_replayed'
    report['current_circle_lineage_nodes'] = nodes
    return report


def validate(directory):
    owner = Path(__file__).resolve().parents[2] / 'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:
        sys.path.insert(0, str(owner))
    from rebuild_current_circle_full_plan_DN import verify_output
    return check(verify_output(directory))
