import copy
import unittest
from unittest.mock import patch

import ezdxf
import two_arm_circle_branch_inventory as owner


class CircleInventoryTests(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        self.doc.modelspace().add_text('DEV1')
        service = dict(ready_for_mapping_comparison=True)
        self.parent = dict(inventory_mode='source_endpoint_branch_inventory_v2', status='source_comparison_inventory_not_mapping',
            mapped_paths=0, local_graphs_mutated=False, human_accepted=False, hil_ready=False,
            records=[dict(equipment_id='DEV1', floor=2, views=dict(plan=dict(services=dict(supply=service, return_=service)),
                         iso=dict(services=dict(supply=service, return_=service))), ready_for_mapping_comparison=True)])
        for view in self.parent['records'][0]['views'].values():
            view['services']['return'] = view['services'].pop('return_')
        self.graph = dict(nodes=[dict(node_id='DEV1', node_type='equipment', floor=2)], edges=[],
            sourceTwoArmCircleContinuity=dict(records=[dict(circle_handle='C1')], physical_Ts_added=0, edge_id_aliases={'E1': 'E2'}))

    def run_rebuild(self, good=True):
        def inspect(*args):
            return dict(ready_for_mapping_comparison=good, graph_sha256=args[4]['graph_sha256'], reason='blocked' if not good else '')
        with patch.object(owner, 'inspect_branch', side_effect=inspect):
            return owner.rebuild(self.doc, self.graph, self.parent, 'SOURCE', 'NEWGRAPH')

    def test_fresh_plan_and_exact_axis_retained_without_mutation(self):
        original = copy.deepcopy(self.parent)
        result = self.run_rebuild()
        self.assertEqual(self.parent, original)
        self.assertEqual(result['counts'], dict(equipment=1, ready_for_mapping_comparison=1))
        self.assertEqual(result['records'][0]['views']['iso'], original['records'][0]['views']['iso'])
        self.assertEqual(result['records'][0]['views']['plan']['services']['supply']['graph_sha256'], 'NEWGRAPH')
        self.assertEqual(len(result['two_arm_circle_inventory_rebase']['fresh_plan_service_checks']), 2)
        self.assertEqual(result['mapped_paths'], 0)
        self.assertFalse(result['hil_ready'])

    def test_old_ready_service_cannot_silently_regress(self):
        with self.assertRaisesRegex(ValueError, 'Previously ready plan service'):
            self.run_rebuild(False)

    def test_missing_or_duplicate_caption_cannot_inherit_ready(self):
        self.doc.modelspace().add_text('DEV1')
        with self.assertRaisesRegex(ValueError, 'Previously ready plan service'):
            self.run_rebuild()

    def test_acceptance_or_wrong_parent_mode_is_rejected(self):
        for field, value in [('human_accepted', True), ('mapped_paths', 1), ('inventory_mode', 'unreplayed')]:
            original = copy.deepcopy(self.parent)
            self.parent[field] = value
            with self.assertRaises(ValueError):
                self.run_rebuild()
            self.parent = original

    def test_third_arm_reconstruction_cannot_use_this_rebase(self):
        self.graph['sourceTwoArmCircleContinuity']['physical_Ts_added'] = 1
        with self.assertRaisesRegex(ValueError, 'two-arm transition'):
            self.run_rebuild()


if __name__ == '__main__':
    unittest.main()
