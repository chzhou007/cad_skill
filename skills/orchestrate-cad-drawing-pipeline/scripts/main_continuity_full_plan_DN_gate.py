"""Require source main continuity semantics without accepting geometry/metrics."""
import sys
from pathlib import Path
from confirmed_overlap_full_plan_DN_gate import check as previous_check


def check(data):
    if data.get('mode')!='complete_local_plan_native_DN_source_main_continuity_v6'or data.get('previous_overlap_mode')!='complete_local_plan_native_DN_confirmed_overlap_roles_v5':
        raise ValueError('source-main-continuity complete-plan DN entry required')
    report=previous_check(dict(data,mode=data['previous_overlap_mode']));nodes={}
    for floor,result in data['floors'].items():
        selected=sorted(nid for nid,role in result['roles'].items()if role.get('role_basis')=='original_native_center_arm_main_continuity_across_confirmed_circle')
        if result.get('native_main_continuity_nodes')!=selected or result.get('native_ray_directions_or_graph_geometry_changed')is not False:
            raise ValueError('native main-continuity inventory or unchanged geometry differs')
        for nid in selected:
            role=result['roles'][nid]
            if (len(role['through'])!=2 or role['branch']in role['through']or not role.get('original_main_source_edge')
                or role.get('physical_flow_direction_inferred')is not False
                or role.get('source_T_proof')!=result['user_circle_endpoint_evidence'].get(nid)):
                raise ValueError('main continuity lacks its unchanged original native source proof')
        nodes[floor]=selected
    report['source_replay']='all_current_local_owners_and_native_main_continuity_DN_roles_replayed'
    report['native_main_continuity_nodes']=nodes
    return report


def validate(directory):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_main_continuity_full_plan_DN import verify_output
    return check(verify_output(directory))
