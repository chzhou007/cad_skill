"""Check old confirmed-overlap roles without inventing pipe/metric acceptance."""
import sys
from pathlib import Path
from user_circle_full_plan_DN_gate import check as previous_check


def check(data):
    if data.get('mode')!='complete_local_plan_native_DN_confirmed_overlap_roles_v5'or data.get('previous_user_circle_mode')!='complete_local_plan_native_DN_user_circle_endpoint_rays_v4':
        raise ValueError('original confirmed-overlap complete-plan entry required')
    report=previous_check(dict(data,mode=data['previous_user_circle_mode']))
    nodes={}
    for floor,result in data['floors'].items():
        evidence=result.get('confirmed_overlap_T_evidence',{})
        if result.get('confirmed_overlap_T_nodes')!=sorted(evidence):raise ValueError('confirmed-overlap T inventory differs')
        for nid,proof in evidence.items():
            if (nid not in result.get('roles',{})or nid in result['source_T_exceptions']
                or proof.get('graph_sha256')!=data['local_parent_replay'][floor]['graph_sha256']
                or proof.get('source_sha256')!=result['source_sha256']
                or proof.get('original_owner')not in result.get('confirmed_overlap_owner_inputs',[])
                or proof.get('original_owner_replayed')is not True or proof.get('graph_mutated')is not False
                or proof.get('physical_values_assigned')!=0 or proof.get('human_accepted')is not False
                or proof.get('display_route_is_physical')is not False or proof.get('hidden_connection_length_mm')is not None):
                raise ValueError('confirmed-overlap native role stale or symbolic connector promoted')
        nodes[floor]=sorted(evidence)
    report['source_replay']='all_current_local_owners_inherited_annotations_circle_lineage_user_corners_and_original_confirmed_overlaps_replayed'
    report['confirmed_overlap_T_nodes']=nodes
    return report


def validate(directory):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_confirmed_overlap_full_plan_DN import verify_output
    return check(verify_output(directory))
