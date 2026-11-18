import copy
import unittest

from adopt_current_named_prefix_evidence import append, restore, ROOT, FIELD
from native_named_prefix_version_bridge import MODE as BRIDGE_MODE


class CurrentNamedPrefixFusionTests(unittest.TestCase):
    def fixture(self):
        old_rows, bridge_rows, edges = [], [], []
        for i, service in enumerate(('supply', 'return', 'supply', 'return')):
            eid, pid, mid = 'E'+str(i), 'P'+str(i), 'M'+str(i)
            paths = [[[i*10, 0], [i*10+1, 0], [i*10+2, 0]]]
            partial = i < 2
            dn = dict(edge_id=pid, system=service, nominal_mm=300 if partial else 250,
                lineage=[dict(source='native_DN'+str(i), through_Ts=[])])
            metric = dict(value_mm=1000+i, pieces=[dict(source_line_handle='LINE'+str(i))],
                installed_whole_edge_length_mm=None, unshown_connection_length_mm=None)
            old = dict(mapping_id=mid, edge_id=eid, floor=3, system=service, plan_edges=[pid],
                path_index=0, segment_indices=[1] if partial else [0, 1],
                scope_points=copy.deepcopy(paths[0][1:] if partial else paths[0]),
                nominal_mm=dn['nominal_mm'], diameter_evidence=dn, horizontal_projection=metric,
                whole_local_edge=not partial, whole_edge_nominal_mm=None if partial else dn['nominal_mm'],
                whole_edge_centerline_route_mm=None if partial else metric['value_mm'],
                local_graph_sha256=dict(plan='a'*64), source_sha256=dict(plan='d'*64),
                human_accepted=False, physical_port_verified=False)
            old_rows.append(old)
            edges.append(dict(edge_id=eid, system=service, attribute_paths=paths,
                plan_segment_attributes=[copy.deepcopy(old)], old_component_inventory=['valve'+str(i)],
                axis_riser_attributes=[dict(nominal_mm=450, physical_length_mm=None)] if partial else []))
            bridge_rows.append(dict(mapping_id=mid, floor=3, system=service, plan_edges=[pid], iso_edges=[eid],
                nominal_mm=dn['nominal_mm'], diameter_evidence=copy.deepcopy(dn), horizontal_projection=copy.deepcopy(metric),
                native_pipe_scope_and_DN_unchanged=True, whole_axis_values_assigned=False,
                physical_ports_verified=False, human_accepted=False))
        parent = dict(metadata=dict(hil_ready=False, graph_complete=False, review_status='old_pending'),
            nodes=[dict(node_id='equipment1', label='original native equipment')], edges=edges,
            sourceUpperFloorPlanSegmentAttributes=dict(records=old_rows, source_scope_sha256='c'*64,
                mapping_sha256='e'*64, human_accepted=False),
            sourceWaveRebasedPlanScopeAdoption=dict(records=[dict(plan_graph_sha256='b'*64)]),
            historical_pending=['unrelated_old_issue'], annotations_history=[dict(answer='retain')])
        bridge = dict(mode=BRIDGE_MODE, status='native_current_named_prefix_scopes_preserved_mapping_adoption_pending',
            both_native_parent_ancestries_replayed=True, graph_mutated=False, new_mappings=0, new_physical_values_assigned=0,
            related_HIL_confirmation_inherited=False, human_accepted=False, hil_ready=False,
            historical_attribute_scope_sha256='c'*64, original_mapping_sha256='e'*64,
            current_plan_graph_sha256='b'*64, historical_plan_graph_sha256='a'*64, source_sha256='d'*64,
            records=bridge_rows)
        return parent, bridge, dict(parent='f'*64, bridge='1'*64)

    def test_four_provenance_records_restore_every_prior_field_exactly(self):
        parent, bridge, hashes = self.fixture()
        original = copy.deepcopy((parent, bridge))
        graph, stage = append(parent, bridge, hashes)
        self.assertEqual(restore(graph, parent), parent)
        self.assertEqual((parent, bridge), original)
        self.assertEqual(stage['current_source_scopes'], 4)
        self.assertTrue(all(FIELD in e for e in graph['edges']))

    def test_vertical_values_and_unknown_mixed_whole_lengths_are_preserved(self):
        parent, bridge, hashes = self.fixture()
        graph, _ = append(parent, bridge, hashes)
        for before, after in zip(parent['edges'], graph['edges']):
            self.assertEqual(before['axis_riser_attributes'], after['axis_riser_attributes'])
            self.assertEqual(before['plan_segment_attributes'], after['plan_segment_attributes'])
        self.assertIsNone(graph['edges'][0]['plan_segment_attributes'][0]['whole_edge_nominal_mm'])
        self.assertEqual(graph['edges'][2]['plan_segment_attributes'][0]['whole_edge_nominal_mm'], 250)

    def test_wrong_source_versions_or_scope_values_cannot_be_attached(self):
        for mutation in ('graph', 'mapping', 'DN', 'metric', 'service'):
            parent, bridge, hashes = self.fixture()
            if mutation == 'graph':
                bridge['current_plan_graph_sha256'] = '9'*64
            elif mutation == 'mapping':
                bridge['original_mapping_sha256'] = '9'*64
            elif mutation == 'DN':
                bridge['records'][0]['nominal_mm'] = 200
            elif mutation == 'metric':
                bridge['records'][0]['horizontal_projection']['value_mm'] = 999
            else:
                bridge['records'][0]['system'] = 'return'
            with self.assertRaises(ValueError):
                append(parent, bridge, hashes)

    def test_axis_scope_limit_does_not_move_during_provenance_update(self):
        parent, bridge, hashes = self.fixture()
        parent['edges'][0]['attribute_paths'][0][1] = [-100, -100]
        with self.assertRaises(ValueError):
            append(parent, bridge, hashes)

    def test_duplicate_writer_or_accepted_state_stays_blocked(self):
        for mutation in ('existing', 'accepted', 'same_axis'):
            parent, bridge, hashes = self.fixture()
            if mutation == 'existing':
                parent['edges'][0][FIELD] = {}
            elif mutation == 'accepted':
                parent['metadata']['hil_ready'] = True
            else:
                bridge['records'][1]['iso_edges'] = bridge['records'][0]['iso_edges']
            with self.assertRaises(ValueError):
                append(parent, bridge, hashes)

    def test_restore_detects_lost_components_old_annotations_and_foreign_evidence(self):
        for mutation in ('component', 'annotation', 'evidence'):
            parent, bridge, hashes = self.fixture()
            graph, _ = append(parent, bridge, hashes)
            if mutation == 'component':
                graph['edges'][0]['old_component_inventory'] = []
            elif mutation == 'annotation':
                graph['annotations_history'] = []
            else:
                graph['edges'][0][FIELD]['native_prefix_bridge_sha256'] = '9'*64
            with self.assertRaises(ValueError):
                restore(graph, parent)


if __name__ == '__main__':
    unittest.main()
