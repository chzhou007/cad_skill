import copy
import unittest

from native_named_prefix_version_bridge import MODE, check_result, scope_values


class NamedPrefixPreservationTests(unittest.TestCase):
    def fixture(self):
        rows, diameter, metric = [], [], []
        for i, system in enumerate(('supply', 'return', 'supply', 'return')):
            pid, aid, mid = 'P'+str(i), 'A'+str(i), 'M'+str(i)
            dn = dict(edge_id=pid, system=system, nominal_mm=300 if i < 2 else 250,
                lineage=[dict(evidence_id='native:'+str(i), edge_path=[pid])])
            length = dict(status='native_plan_horizontal_projection_partial_length', value_mm=1000+i,
                pieces=[dict(plan_edge=pid, source_line_handle='LINE'+str(i), length_mm=1000+i)],
                installed_whole_edge_length_mm=None, unshown_connection_length_mm=None)
            rows.append(dict(mapping_id=mid, floor=3, system=system, plan_edges=[pid], iso_edges=[aid],
                diameter=copy.deepcopy(dn), horizontal_projection=copy.deepcopy(length),
                whole_axis_DN_selected=False, whole_axis_physical_length_mm=None,
                physical_port_verified=False, human_accepted=False))
            diameter.append(dn)
            metric.append(dict(scope_id=mid, horizontal_projection=length))
        return dict(records=rows), dict(records=diameter), dict(measured_scopes=metric)

    def test_unchanged_native_values_preserve_unknown_physical_extents_and_inputs(self):
        stored, dn, metric = self.fixture()
        before = copy.deepcopy((stored, dn, metric))
        rows = scope_values(stored, dn, metric)
        self.assertEqual([r['nominal_mm'] for r in rows], [300, 300, 250, 250])
        self.assertTrue(all(r['whole_axis_values_assigned'] is False for r in rows))
        self.assertEqual((stored, dn, metric), before)

    def test_changed_diameter_or_its_inheritance_chain_requires_recomputation(self):
        for changed in ('value', 'lineage'):
            stored, dn, metric = self.fixture()
            if changed == 'value':
                dn['records'][0]['nominal_mm'] = 200
            else:
                dn['records'][0]['lineage'][0]['edge_path'].append('different_T_branch')
            with self.assertRaises(ValueError):
                scope_values(stored, dn, metric)

    def test_equal_length_with_different_source_pipe_does_not_pass(self):
        stored, dn, metric = self.fixture()
        metric['measured_scopes'][0]['horizontal_projection']['pieces'][0]['source_line_handle'] = 'other_LINE'
        with self.assertRaises(ValueError):
            scope_values(stored, dn, metric)

    def test_unknown_or_zero_DN_is_not_filled(self):
        for value in (None, 0, False, float('nan')):
            stored, dn, metric = self.fixture()
            dn['records'][0]['nominal_mm'] = value
            stored['records'][0]['diameter']['nominal_mm'] = value
            with self.assertRaises(ValueError):
                scope_values(stored, dn, metric)

    def test_installed_length_or_human_confirmation_cannot_be_inherited(self):
        for kind in ('installed', 'connector', 'human', 'whole_DN'):
            stored, dn, metric = self.fixture()
            if kind in ('installed', 'connector'):
                key = 'installed_whole_edge_length_mm' if kind == 'installed' else 'unshown_connection_length_mm'
                metric['measured_scopes'][0]['horizontal_projection'][key] = 0
                stored['records'][0]['horizontal_projection'][key] = 0
            else:
                stored['records'][0]['human_accepted' if kind == 'human' else 'whole_axis_DN_selected'] = True
            with self.assertRaises(ValueError):
                scope_values(stored, dn, metric)

    def test_repeated_or_missing_pipe_scope_blocks_preservation(self):
        for mutation in ('metric', 'plan', 'axis', 'missing'):
            stored, dn, metric = self.fixture()
            if mutation == 'metric':
                metric['measured_scopes'].append(copy.deepcopy(metric['measured_scopes'][0]))
            elif mutation == 'missing':
                stored['records'].pop()
            else:
                key = 'plan_edges' if mutation == 'plan' else 'iso_edges'
                stored['records'][1][key] = stored['records'][0][key]
            with self.assertRaises(ValueError):
                scope_values(stored, dn, metric)

    def test_source_replay_remains_pending_for_mapping_fusion_and_HIL(self):
        stored, dn, metric = self.fixture()
        result = dict(mode=MODE, status='native_current_named_prefix_scopes_preserved_mapping_adoption_pending',
            both_native_parent_ancestries_replayed=True, records=scope_values(stored, dn, metric),
            graph_mutated=False, related_HIL_confirmation_inherited=False, human_accepted=False, hil_ready=False,
            new_mappings=0, new_physical_values_assigned=0)
        self.assertEqual(check_result(result)['status'], 'pending')
        for key, value in [('both_native_parent_ancestries_replayed', False), ('new_mappings', False),
                           ('human_accepted', True), ('graph_mutated', True)]:
            bad = copy.deepcopy(result)
            bad[key] = value
            with self.assertRaises(ValueError):
                check_result(bad)


if __name__ == '__main__':
    unittest.main()
