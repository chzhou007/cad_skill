import copy
import unittest

from match_junction_rebased_paired_paths import MODE, preserve_history, check_result


def state():
    rows = []
    for did in ('D1', 'D2'):
        for system in ('supply', 'return'):
            key = did+system
            rows.append(dict(mapping_id=key, kind='equipment_branch', equipment_id=did, floor=2, system=system,
                plan_edges=['P'+key], iso_edges=['I'+key], plan_start='PT'+key, plan_end=did,
                iso_start='IT'+key, iso_end=did, plan_snapshot={}, iso_snapshot={}, physical_ports_verified=False, human_accepted=False))
    result = dict(mode=MODE, status='source_checked_current_paired_junction_paths_attributes_pending', records=rows,
        equipment_scope=['D1', 'D2'], context_only_equipment_ids=[], floor=2, source_sha256=dict(plan='PS', iso='IS'),
        plan_graph_sha256='NEW', iso_graph_sha256='AXIS', local_graphs_mutated=False, physical_values_fused=False,
        physical_values_assigned=0, whole_floor_connectivity_confirmed=False, expert_confirmation_claimed=False, human_accepted=False, hil_ready=False)
    result['historical_mapping_lineage'] = [dict(previous_mapping_id='OLD'+r['mapping_id'], current_mapping_id=r['mapping_id'],
        local_paths_and_snapshots_preserved=True, human_confirmation_transferred=False) for r in rows]
    result['current_native_base_correspondence'] = {k: copy.deepcopy(result[k]) for k in (
        'equipment_scope', 'context_only_equipment_ids', 'floor', 'source_sha256', 'plan_graph_sha256', 'iso_graph_sha256')}
    result['current_native_base_correspondence']['evidence'] = dict(paired_services=[{}])
    return result


class CurrentPairedPathTests(unittest.TestCase):
    def test_history_is_exact_local_geometry_and_identity_not_just_labels(self):
        current = state(); previous = copy.deepcopy(current); previous['plan_graph_sha256'] = 'ORIGINAL'
        preserve_history(current, previous, 'ORIGINAL')
        for field in ('plan_edges', 'plan_snapshot', 'target_equipment_id', 'system', 'floor'):
            wrong = copy.deepcopy(previous); wrong['records'][0][field] = 'OTHER'
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'reconciliation'):
                preserve_history(current, wrong, 'ORIGINAL')

    def test_source_ancestry_and_duplicate_history_are_blockers(self):
        current = state(); previous = copy.deepcopy(current); previous['plan_graph_sha256'] = 'ORIGINAL'
        for change in ('source', 'axis', 'owner', 'duplicate'):
            wrong = copy.deepcopy(previous)
            if change == 'source': wrong['source_sha256']['plan'] = 'OTHER'
            elif change == 'axis': wrong['iso_graph_sha256'] = 'OTHER'
            elif change == 'owner': wrong['equipment_scope'] = ['D1', 'OTHER']
            else: wrong['records'].append(copy.deepcopy(wrong['records'][0]))
            with self.subTest(change=change), self.assertRaises(ValueError): preserve_history(current, wrong, 'ORIGINAL')

    def test_current_pairs_keep_physical_values_and_HIL_pending(self):
        result = check_result(state())
        self.assertEqual(result['mapped_paths'], 4)
        self.assertEqual(result['source_checked_pairs'], 1)
        self.assertFalse(result['hil_ready'])

    def test_wrong_service_duplicate_writer_or_inherited_approval_blocks(self):
        for change in ('service', 'writer', 'approval', 'base_version', 'whole_floor'):
            data = state()
            if change == 'service': data['records'][0]['system'] = 'return'
            elif change == 'writer': data['records'][1]['iso_edges'] = data['records'][0]['iso_edges']
            elif change == 'approval': data['historical_mapping_lineage'][0]['human_confirmation_transferred'] = True
            elif change == 'base_version': data['current_native_base_correspondence']['plan_graph_sha256'] = 'OLD'
            else: data['whole_floor_connectivity_confirmed'] = True
            with self.subTest(change=change), self.assertRaises(ValueError): check_result(data)


if __name__ == '__main__': unittest.main()
