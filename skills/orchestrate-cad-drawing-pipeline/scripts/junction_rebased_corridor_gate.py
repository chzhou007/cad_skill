"""Validate independently replayed current corridor groups, not whole drawings."""


def validate(mapping):
    mode = 'source_checked_junction_rebased_corridor_groups_v1'
    inventory = mapping.get('evidence', {}).get('inherited_pending_scope', {})
    if (mapping.get('mode') != mode or mapping.get('status') != 'source_checked_path_correspondence_attributes_pending'
            or inventory.get('mode') != 'pending_native_junction_rebased_branch_inventory_v1'
            or inventory.get('plan_graph_sha256') != mapping.get('plan_graph_sha256')
            or inventory.get('preserved_axis_evidence_on_identical_inputs') is not True
            or any(mapping.get(k) is not False for k in ('local_graphs_mutated', 'expert_confirmation_claimed', 'whole_floor_connectivity_confirmed', 'human_accepted', 'hil_ready'))
            or mapping.get('physical_values_assigned') != 0):
        raise ValueError('Current corridor batch has stale or promoted inventory evidence')
    groups = mapping.get('groups', [])
    if not groups or len({g['group_id'] for g in groups}) != len(groups):
        raise ValueError('Missing or repeated independent corridor groups')
    rows, equipment = [], []
    used = dict(plan=set(), iso=set())
    for group in groups:
        count = len(group['equipment_scope'])
        lineages = group.get('historical_mapping_lineage', [])
        if (count < 3 or len(set(group['equipment_scope'])) != count or len(group['records']) != 4*count-2
                or any(group.get(k) != mapping.get(k) for k in ('plan_graph_sha256', 'iso_graph_sha256', 'source_sha256'))
                or len(lineages) != len(group['records'])
                or any(x.get('local_paths_and_snapshots_preserved') is not True or x.get('human_confirmation_transferred') is not False for x in lineages)
                or any(group.get(k) is not False for k in ('local_graphs_mutated', 'expert_confirmation_claimed', 'human_accepted', 'hil_ready'))):
            raise ValueError('Current corridor lost a complete source/equipment/history scope')
        for system in ('supply', 'return'):
            service = [r for r in group['records'] if r['system'] == system]
            if (sum(r['kind'] == 'equipment_branch' for r in service) != count
                    or sum(r['kind'] == 'main_between_equipment_branches' for r in service) != count-1):
                raise ValueError('Current corridor paired services incomplete')
            checks = group.get('evidence', {}).get('main_topology', {}).get(system, {})
            if len(checks.get('pairwise_order_checks', [])) != count*(count-1)//2 or len(checks.get('adjacent', [])) != count-1:
                raise ValueError('Current corridor independent main order evidence missing')
        for view in used:
            ids = [eid for row in group['records'] for eid in row[view+'_edges']]
            if len(ids) != len(set(ids)) or set(ids) & used[view]:
                raise ValueError('Current corridor repeats local graph writers')
            used[view].update(ids)
        rows += [dict(row, group_id=group['group_id']) for row in group['records']]
        equipment += group['equipment_scope']
    if (rows != mapping['records'] or sorted(equipment) != mapping['equipment_scope']
            or len(set(equipment)) != len(equipment) or len({r['mapping_id'] for r in rows}) != len(rows)):
        raise ValueError('Current corridor batch lost or repeated records/equipment')
    return dict(status='pending', path_correspondence='native_junction_rebased_corridor_groups_replayed',
        mapped_paths=len(rows), equipment=len(equipment), independent_groups=len(groups), plan_graph_sha256=mapping['plan_graph_sha256'],
        whole_floor_connectivity_confirmed=False, physical_values_assigned=0, expert_confirmation_claimed=False,
        human_accepted=False, hil_ready=False,
        pending=['Rebuild current plan DN/length scopes and full-parent fusion; retain other subviews, missing connections and HIL independently'])
