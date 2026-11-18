"""Keep original user-circle corner evidence separate from graph acceptance."""
import sys
from pathlib import Path
from current_circle_full_plan_DN_gate import check as previous_check


def check(data):
    if data.get('mode')!='complete_local_plan_native_DN_user_circle_endpoint_rays_v4'or data.get('previous_circle_mode')!='complete_local_plan_native_DN_current_circle_main_lineage_v3':
        raise ValueError('original user-circle complete-plan entry required')
    report=previous_check(dict(data,mode=data['previous_circle_mode']))
    nodes={}
    for floor,result in data['floors'].items():
        evidence=result.get('user_circle_endpoint_evidence',{})
        if result.get('user_circle_endpoint_nodes')!=sorted(evidence):raise ValueError('user-circle endpoint inventory differs')
        for nid,proof in evidence.items():
            if (nid not in result.get('roles',{})or nid in result['source_T_exceptions']
                or proof.get('graph_sha256')!=data['local_parent_replay'][floor]['graph_sha256']
                or proof.get('source_sha256')!=result['source_sha256']
                or proof.get('graph_mutated')is not False or proof.get('physical_values_assigned')!=0
                or proof.get('human_accepted')is not False or proof.get('circle_layer_rewritten')is not False
                or proof.get('original_main_rays_replayed')is not True
                or proof.get('through_pair_recomputed_from_native_rays')is not True
                or proof.get('original_review',{}).get('policy')!=result.get('user_circle_endpoint_review')):
                raise ValueError('user-circle original reply/native rays not current or acceptance promoted')
        nodes[floor]=sorted(evidence)
    report['source_replay']='all_current_local_owners_inherited_annotations_circle_lineage_and_original_user_corner_rays_replayed'
    report['user_circle_endpoint_nodes']=nodes
    return report


def validate(directory):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_user_circle_full_plan_DN import verify_output
    return check(verify_output(directory))
