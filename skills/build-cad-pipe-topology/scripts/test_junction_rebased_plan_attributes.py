import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from confirm_crossview_paths import encode, sha
from junction_rebased_plan_attributes import MODE, STATUS, DETAIL_STATUS, attribute, check_result, metric_bindings


class CurrentCorridorAttributeTests(unittest.TestCase):
    def fixture(self):
        records = []
        for system in ('supply', 'return'):
            for index in range(5):
                eid = system+str(index)
                dn = dict(edge_id=eid, system=system, nominal_mm=200, human_accepted=False,
                    scope_paths=[[[0, 0], [1, 0]]], scope='native_plan_drawn_pipe_paths_only')
                metric = dict(status='native_plan_horizontal_projection_partial_length', value_mm=1,
                    pieces=[dict(length_mm=1)], installed_whole_edge_length_mm=None, unshown_connection_length_mm=None)
                records.append(dict(mapping_id=eid, group_id='G', kind='equipment_branch' if index < 3 else 'main_between_equipment_branches',
                    floor=2, system=system, plan_edges=[eid], iso_edges=['A'+eid], diameter=dn, horizontal_projection=metric,
                    whole_axis_DN_selected=False, whole_axis_physical_length_mm=None, physical_ports_verified=False, human_accepted=False))
        data = dict(mode=MODE, status=STATUS, source_sha256='SOURCE', graph_sha256='GRAPH', mapping_sha256='MAP',
            equipment_scope=['D1', 'D2', 'D3'], groups=[dict(group_id='G', equipment_scope=['D1', 'D2', 'D3'],
                record_ids=[r['mapping_id'] for r in records])], records=records,
            local_graphs_mutated=False, physical_values_fused=False, whole_axis_DN_assigned=0, installed_lengths_assigned=0, human_accepted=False)
        return data

    def detail(self, data):
        row = data['records'][0]
        row['horizontal_projection'].update(status=DETAIL_STATUS, value_mm=None,
            detail_context=dict(physical_units_applied=False, plan_graph_sha256='GRAPH', plan_source_sha256='SOURCE',
                plan_edges=row['plan_edges'], human_accepted=False))

    def test_unknown_detail_and_DN_conflicts_stay_unknown(self):
        data = self.fixture(); self.detail(data); data['records'][1]['diameter']['nominal_mm'] = None
        result = check_result(data)
        self.assertEqual((result['known_DN_scopes'], result['measured_plan_XY_scopes'], result['unmeasured_detail_scopes']), (9, 9, 1))
        self.assertFalse(result['physical_values_fused'])

    def test_source_only_scope_blocks_promotions_duplicate_paths_and_lost_services(self):
        for change in ('length', 'scope', 'duplicate', 'service', 'graph'):
            data = self.fixture()
            if change == 'length': data['records'][0]['whole_axis_physical_length_mm'] = 1
            elif change == 'scope': data['records'][0]['diameter']['system'] = 'return'
            elif change == 'duplicate': data['records'][1]['iso_edges'] = data['records'][0]['iso_edges']
            elif change == 'service': data['records'][0]['kind'] = 'main_between_equipment_branches'
            else: data['physical_values_fused'] = True
            with self.subTest(change=change), self.assertRaises(ValueError): check_result(data)

    def test_detail_needs_matching_current_native_context_and_cannot_be_zero(self):
        for change in ('source', 'graph', 'zero', 'measured'):
            data = self.fixture(); self.detail(data); metric = data['records'][0]['horizontal_projection']
            if change == 'source': metric['detail_context']['plan_source_sha256'] = 'OTHER'
            elif change == 'graph': metric['detail_context']['plan_graph_sha256'] = 'OLD'
            elif change == 'zero': metric['value_mm'] = 0
            else: metric['value_mm'] = 100
            with self.subTest(change=change), self.assertRaises(ValueError): check_result(data)

    def test_original_metric_policy_cannot_move_between_groups(self):
        mapping = dict(groups=[dict(group_id='G', previous_mapping_sha256='HISTORICAL')])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'metric.json'; path.write_bytes(encode(dict(mapping_sha256='HISTORICAL')))
            spec = dict(group_id='G', path=str(path), sha256=sha(path))
            self.assertEqual(metric_bindings(mapping, [spec])['G']['mapping_sha256'], 'HISTORICAL')
            for changed in (dict(spec, group_id='OTHER'), dict(spec, sha256='STALE')):
                with self.assertRaises(ValueError): metric_bindings(mapping, [changed])
            path.write_bytes(encode(dict(mapping_sha256='OTHER'))); spec['sha256'] = sha(path)
            with self.assertRaises(ValueError): metric_bindings(mapping, [spec])

    def test_DN_path_extent_must_match_before_metric_reading(self):
        data = self.fixture(); records = copy.deepcopy(data['records'])
        graph = dict(edges=[dict(edge_id=r['plan_edges'][0], attribute_paths=[[[0, 0], [1, 0]]]) for r in records])
        mapping = dict(mode='source_checked_junction_rebased_corridor_groups_v1', plan_graph_sha256='GRAPH',
            source_sha256=dict(plan='SOURCE'), human_accepted=False, records=records,
            groups=[dict(group_id='G', equipment_scope=data['equipment_scope'], records=records)], equipment_scope=data['equipment_scope'])
        dn = dict(mode='junction_rebased_calibrated_plan_DN_scopes_v1', graph_sha256='GRAPH', source_sha256='SOURCE',
            physical_values_fused=False, human_accepted=False, records=[r['diameter'] for r in records])
        dn['records'][0]['scope_paths'] = [[[0, 0], [2, 0]]]
        before = encode(graph)
        with patch('junction_rebased_plan_attributes.audit_paths', return_value={}), \
             patch('junction_rebased_plan_attributes.metric_context', return_value=({}, False)), \
             patch('junction_rebased_plan_attributes.projection') as metric, self.assertRaises(ValueError):
            attribute(None, graph, mapping, dn, {'G': {}}, 'SOURCE', 'GRAPH')
        metric.assert_not_called(); self.assertEqual(encode(graph), before)


if __name__ == '__main__': unittest.main()
