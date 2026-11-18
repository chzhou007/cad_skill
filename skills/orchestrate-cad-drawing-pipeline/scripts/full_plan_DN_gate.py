"""Validate local DN evidence without promoting cross-view or HIL acceptance."""
import math,sys
from pathlib import Path


def check(data):
    if (data.get('mode')!='complete_local_plan_native_DN_batch_v1'
        or any(data.get(k)is not False for k in ('local_graphs_mutated','human_accepted','hil_ready','crossview_mapping_required_to_read_plan'))
        or data.get('axis_values_fused')!=0 or data.get('physical_lengths_assigned')!=0):raise ValueError('local DN cannot promote topology, axis fusion, physical lengths or HIL')
    total=known=0;states={};conflicts=0
    if not data.get('floors')or set(data['floors'])!=set(data['local_parent_replay']):raise ValueError('complete local parent scope required')
    for floor,result in data['floors'].items():
        rows=result['records'];ids=[r['edge_id']for r in rows]
        if (len(ids)!=len(set(ids))or len(ids)!=result['counts']['graph_edges']
            or result.get('crossview_subset_used_for_scope')is not False
            or data['local_parent_replay'][floor].get('native_replay_passed')is not True):raise ValueError('full local edge inventory or independent owner replay missing')
        for row in rows:
            value=row['nominal_mm'];known+=value is not None
            if value is not None and (isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value)or value<=0
                or row['status']in ('conflict','unresolved','annotation_blocked','source_scope_unverified')):raise ValueError('unverified DN must remain unknown')
            if row.get('human_accepted')is not False:raise ValueError('technical evidence is not human acceptance')
            states[row['status']]=states.get(row['status'],0)+1;conflicts+=row['status']=='conflict'
        total+=len(rows)
    if data['counts']!=dict(total_plan_edges=total,known_plan_DN_edges=known):raise ValueError('local DN counts differ from actual complete records')
    return dict(status='pending',source_replay='all_local_topology_owners_and_complete_plan_DN_replayed',
        total_plan_edges=total,known_plan_DN_edges=known,states=states,conflicting_DN_edges=conflicts,
        crossview_mapping_required_to_read_plan=False,axis_values_fused=0,human_accepted=False,hil_ready=False,
        pending=['Native annotation/provider gaps must be processed before grouping remaining semantic conflicts for HIL; axis mapping, lengths and fusion are separate'])


def validate(directory):
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_full_plan_DN import verify_output
    return check(verify_output(directory))
