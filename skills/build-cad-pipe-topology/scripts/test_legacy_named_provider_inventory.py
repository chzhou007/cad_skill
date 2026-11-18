import copy, unittest
from unittest.mock import patch
from legacy_named_provider_inventory import inherit, same_local_edge, current_plan_reader, ROOTS


class Tests(unittest.TestCase):
    def fixture(self):
        original = dict(records=[dict(edge_id='WAIT', classification='horizontal_only', has_existing_correspondence=False, correspondence_observations=[])],
            ordinary_junction_mappings={'3': {'OLDP': 'OLDA'}}, member_domain_observations=[dict(id='MEMBER:keep')],
            remaining_horizontal_attributes=[dict(edge_id='WAIT', next_scope='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path', known_whole_DN=None, complete_centerline=False)],
            current_component_inventory=dict(count=10, unknown=['keep']), counts=dict(pure_horizontal_complete_DN_and_centerline=0), current_horizontal_frontier={})
        row = dict(provider=ROOTS[0], mapping_id='NAMED', axis_edge_id='WAIT', floor=3,
            system='supply', plan_paths={'P': [[[0, 0], [1, 0]]]}, scope_domain='separate_named_external_port',
            attribute_extent='partial_horizontal_extent', ordinary_anchor_pairs=[],
            current_local_core_paths_and_ports_unchanged=True, native_ordinary_anchors_replayed=True, human_accepted=False)
        return original, dict(records=[row])

    def test_legacy_scope_inheritance_preserves_unknown_values_components_and_namespaces(self):
        args = self.fixture(); before = copy.deepcopy(args); result = inherit(*args)
        self.assertEqual(args, before)
        self.assertEqual(result['counts']['existing_correspondence_edges'], 1)
        self.assertEqual(result['counts']['pure_horizontal_complete_DN_and_centerline'], 0)
        self.assertEqual(result['remaining_horizontal_attributes'][0]['next_scope'], 'known_legacy_named_scope_incomplete_whole_attributes')
        self.assertIsNone(result['remaining_horizontal_attributes'][0]['known_whole_DN'])
        self.assertFalse(result['remaining_horizontal_attributes'][0]['complete_centerline'])
        self.assertEqual(result['ordinary_junction_mappings'], args[0]['ordinary_junction_mappings'])
        self.assertEqual(result['current_component_inventory'], args[0]['current_component_inventory'])

    def test_member_ordinary_conflict_duplicate_scope_and_missing_native_replay_block(self):
        for kind in ('member', 'competing', 'repeated', 'unreplayed', 'unknown_provider'):
            args = self.fixture(); row = args[1]['records'][0]
            if kind == 'member': row['ordinary_anchor_pairs'] = [('MEMBER:P', 'A')]
            elif kind == 'competing': row['ordinary_anchor_pairs'] = [('NEWP', 'OLDA')]
            elif kind == 'repeated': args[1]['records'].append(copy.deepcopy(row))
            elif kind == 'unreplayed': row['native_ordinary_anchors_replayed'] = False
            else: row['provider'] = 'unregistered_shape_guess'
            with self.subTest(kind=kind), self.assertRaises(ValueError): inherit(*args)

    def test_new_native_T_anchor_is_separate_from_marker_interface(self):
        args = self.fixture(); args[1]['records'][0]['ordinary_anchor_pairs'] = [('PN', 'AN')]
        result = inherit(*args)
        self.assertEqual(result['ordinary_junction_mappings']['3']['PN'], 'AN')
        self.assertEqual(result['counts']['new_legacy_ordinary_anchors'], 1)
        self.assertFalse(result['records'][0]['correspondence_observations'][0]['whole_edge_values_assigned'])

    def test_local_path_or_port_change_invalidates_original_scope(self):
        edge = dict(edge_id='E', start_node_id='T', end_node_id='PORT', system='supply', attribute_paths=[[[0, 0], [1, 0]]], end_port_id='PORT-S')
        same_local_edge({'E': edge}, {'E': copy.deepcopy(edge)}, 'E')
        for key, value in [('system', 'return'), ('end_port_id', 'PORT-R'), ('attribute_paths', [[[0, 0], [2, 0]]])]:
            changed = dict(edge, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError): same_local_edge({'E': changed}, {'E': edge}, 'E')

    def test_direct_native_T_reuse_does_not_require_unrelated_circle_configuration(self):
        reader = current_plan_reader({}, 'source', 'graph')
        with patch('legacy_named_provider_inventory.native_tee', return_value={'native': 'T'}), patch('legacy_named_provider_inventory.make_reader') as fallback:
            self.assertEqual(reader(None, {}, 'T', 'source', 'graph'), {'native': 'T'})
            fallback.assert_not_called()
        with patch('legacy_named_provider_inventory.native_tee', side_effect=ValueError('unsupported')):
            with self.assertRaises(ValueError): reader(None, {}, 'T', 'source', 'graph')


if __name__ == '__main__': unittest.main()
