import copy
import unittest

from attach_reviewed_interface_owners import bindings, compose
import test_confirmed_equipment_interfaces as existing_tests


def fixture_question():
    return dict(id='Q', text='B1 and B2 respectively belong to D1 and D2',
        options=['是，两组分别接对应设备，供回水独立', '对应关系不同，见说明'],
        answer=dict(decision='是，两组分别接对应设备，供回水独立'),
        source_evidence=dict(equipment_ids=['D1', 'D2'], interface_ids=['V0', 'V1', 'V2', 'V3']))


class ReviewedOwnerTests(unittest.TestCase):
    def fixture(self):
        old = existing_tests.ConfirmedInterfaces()
        old.setUp()
        for edge in old.g['edges']:
            edge['attribute_paths'] = [copy.deepcopy(edge['path'])]
            edge['path_points'] = copy.deepcopy(edge['path'])
            edge['path_length_scope'] = 'source_pipe_only_circle_radius_excluded'
            edge['physical_length_status'] = 'unknown_circle_and_equipment_connector'
            edge['drawing_path_length'] = 1
            edge['length_scope_evidence'] = [dict(kind='historical_circle_normalization')]
        return old

    def apply(self, old):
        question = fixture_question()
        by_interface = {nid: question for nid, owner in bindings(question)}
        return compose(old.g, old.p, old.inv, old.h, old.gh, by_interface)

    def test_ordered_review_groups_define_owners_without_nearest_pairing(self):
        self.assertEqual(bindings(fixture_question()), [('V0', 'D1'), ('V1', 'D1'), ('V2', 'D2'), ('V3', 'D2')])

    def test_single_owner_and_supply_first_order_are_supported(self):
        q = fixture_question()
        q['source_evidence'] = dict(equipment_id='D', interface_ids=['SUPPLY', 'RETURN'])
        self.assertEqual(bindings(q), [('SUPPLY', 'D'), ('RETURN', 'D')])

    def test_partial_erratum_or_missing_answer_does_not_assign_owners(self):
        for answer in ({}, dict(decision='对应关系不同，见说明', comment='two surplus circles')):
            q = fixture_question()
            q['answer'] = answer
            with self.assertRaisesRegex(ValueError, 'explicit supported'):
                bindings(q)

    def test_incomplete_duplicate_or_empty_paired_scope_is_rejected(self):
        for variant in ('missing', 'duplicate_interface', 'duplicate_owner', 'empty_owner'):
            q = fixture_question()
            if variant == 'missing':
                q['source_evidence']['interface_ids'].pop()
            elif variant == 'duplicate_interface':
                q['source_evidence']['interface_ids'][1] = 'V0'
            elif variant == 'duplicate_owner':
                q['source_evidence']['equipment_ids'][1] = 'D1'
            else:
                q['source_evidence']['equipment_ids'][1] = ''
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                bindings(q)

    def test_confirmed_owners_preserve_prior_circle_scopes_and_every_source_path(self):
        old = self.fixture()
        before = copy.deepcopy(old.g)
        result, audit = self.apply(old)
        self.assertEqual(old.g, before)
        self.assertEqual(len(audit['records']), 4)
        self.assertEqual(len(result['edges']), len(before['edges']))
        for edge, original in zip(result['edges'], before['edges']):
            for key in ('system', 'source_handles', 'path', 'path_points', 'attribute_paths', 'path_length', 'path_length_scope', 'drawing_path_length', 'physical_length_status'):
                self.assertEqual(edge[key], original[key])
            self.assertIsNone(edge['equipment_connector_length_mm'])
            self.assertEqual(edge['physical_length'], 'unknown')
            self.assertFalse(edge['path_length_complete'])
            self.assertEqual(edge['length_scope_evidence'][0], original['length_scope_evidence'][0])
            self.assertFalse(edge['confirmed_equipment_interface']['physical_port_verified'])
        self.assertEqual({n['node_id'] for n in result['nodes'] if n.get('node_type') == 'equipment'}, {'D1', 'D2'})
        self.assertFalse(result['metadata']['hil_ready'])

    def test_previous_confirmed_and_calibrated_ownership_records_are_retained(self):
        old = self.fixture()
        old.g['confirmedEquipmentInterfaceRepair'] = dict(mappings=[dict(retired_node_id='HISTORICAL')])
        old.g['sourceLayoutEquipmentOwnership'] = dict(records=[dict(edge_id='HISTORICAL')])
        result, audit = self.apply(old)
        self.assertEqual(result['sourceLayoutEquipmentOwnership'], old.g['sourceLayoutEquipmentOwnership'])
        self.assertEqual(result['confirmedEquipmentInterfaceRepair']['previous_repair'], old.g['confirmedEquipmentInterfaceRepair'])

    def test_existing_owner_connection_is_not_duplicated_or_silently_reassigned(self):
        old = self.fixture()
        old.g['edges'].append(dict(edge_id='EXISTING', start_node_id='D1', end_node_id='T0', system='supply'))
        with self.assertRaisesRegex(ValueError, 'already has connections'):
            self.apply(old)

    def test_measured_connectors_or_downstream_fusion_require_explicit_reconciliation(self):
        for variant in ('measured', 'fusion'):
            old = self.fixture()
            if variant == 'measured':
                old.g['edges'][0]['equipment_connector_length_mm'] = 100
            else:
                old.g['edges'][0]['cross_view_attributes'] = dict(previous='verified scope')
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                self.apply(old)

    def test_existing_complete_drawn_pipe_does_not_complete_the_new_connector(self):
        old = self.fixture()
        old.g['edges'][0]['path_length_complete'] = True
        old.g['edges'][0]['physical_length_status'] = 'source_drawn_pipe_complete'
        result, _ = self.apply(old)
        edge = result['edges'][0]
        self.assertFalse(edge['path_length_complete'])
        self.assertIsNone(edge['equipment_connector_length_mm'])
        self.assertTrue(edge['reviewed_interface_owner']['prior_length_scope']['path_length_complete'])


if __name__ == '__main__':
    unittest.main()
