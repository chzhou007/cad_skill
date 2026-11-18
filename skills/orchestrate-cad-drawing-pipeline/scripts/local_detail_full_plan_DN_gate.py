"""Validate local native detail evidence without promoting unrelated semantics."""
import sys
from pathlib import Path
from main_continuity_full_plan_DN_gate import check as previous_check

def check(data):
    if data.get('mode')!='complete_local_plan_native_DN_unowned_detail_T_v7'or data.get('previous_main_continuity_mode')!='complete_local_plan_native_DN_source_main_continuity_v6':
        raise ValueError('local detail T complete-plan entry required')
    report=previous_check(dict(data,mode=data['previous_main_continuity_mode']));inventory={}
    for floor,result in data['floors'].items():
        proofs=result.get('native_local_detail_T_evidence',{});selected=sorted(proofs)
        if result.get('native_local_detail_T_nodes')!=selected:raise ValueError('local detail T inventory differs')
        for nid,proof in proofs.items():
            if (proof.get('status')!='native_local_detail_circle_T_replayed_without_equipment_owner'
                or result.get('roles',{}).get(nid,{}).get('source_T_proof')!=proof
                or proof.get('equipment_ownership_inferred')is not False or proof.get('main_detail_correspondence_inferred')is not False
                or proof.get('physical_ports_verified')is not False or proof.get('physical_length_mm')is not None
                or proof.get('graph_mutated')is not False or proof.get('human_accepted')is not False
                or proof.get('source_view_domain')!='detail_drawing_only_not_plan_metric_proof'):
                raise ValueError('local detail source proof missing or semantics promoted')
        inventory[floor]=selected
    report['source_replay']='all_current_local_owners_main_DN_continuity_and_unowned_native_detail_Ts_replayed'
    report['native_local_detail_T_nodes']=inventory
    return report

def validate(directory):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_local_detail_full_plan_DN import verify_output
    return check(verify_output(directory))
