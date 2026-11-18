"""Check source-level discovery while keeping pipe metrics and HIL independent."""
import sys
from pathlib import Path

def check(result):
    if result.get('mode')!='native_level_marker_batch_discovery_using_original_verifier_v1'or result.get('original_verifier')!='native_level_evidence.verify':raise ValueError('original level verifier discovery entry required')
    if any(result.get(k)!=0 for k in('physical_lengths_assigned','pipe_floors_assigned'))or any(result.get(k)is not False for k in('graph_mutated','human_accepted','hil_ready')):raise ValueError('source datums promoted to graph or metric acceptance')
    seen=set();markers=0
    for group in result['groups']:
        proof=group['verification'];policy=group['policy']
        if (group.get('status')!='existing_native_level_verifier_replayed'or group.get('pipe_lengths_assigned')!=0
            or group.get('graph_mutated')is not False or group.get('human_accepted')is not False
            or proof.get('source_sha256')!=result['source_sha256']or policy.get('source_sha256')!=result['source_sha256']
            or proof.get('hil_ready')is not False or len(proof['levels'])!=len(policy['markers'])
            or any(v['physical_pipe_length']is not None for v in proof['consecutive_datum_differences'])):raise ValueError('native source stack verification or nonmetric scope differs')
        for row in proof['levels']:
            handles=set(row['source_handles'].values())
            if seen&handles:raise ValueError('native datum symbols shared across accepted stacks')
            seen.update(handles);markers+=1
    return dict(status='native_level_discovery_source_checked_pipe_metric_pending',accepted_stacks=len(result['groups']),accepted_markers=markers,
        unresolved_floor_texts=len(result['unresolved_floor_texts']),physical_lengths_assigned=0,pipe_floors_assigned=0,human_accepted=False,hil_ready=False)

def validate(directory):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from discover_native_level_markers import verify_output
    return check(verify_output(directory))
