import copy,sys
from pathlib import Path
from full_plan_DN_gate import check as original_check


def check(data):
    if data.get('mode')!='complete_local_plan_native_DN_inherited_annotations_v2'or data.get('historical_native_implementations_or_globals_changed')is not False:
        raise ValueError('inherited whole-plan DN source entry required')
    projected=dict(data,mode=data['previous_mode']);report=original_check(projected)
    report['source_replay']='all_current_local_owners_ordered_F_and_native_calibration_replayed'
    report['inherited_annotations']={f:rows['inherited_annotation_readers_applied']for f,rows in data['floors'].items()}
    return report


def validate(directory):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from verify_inherited_plan_DN_semantics import verify_output
    return check(verify_output(directory))
