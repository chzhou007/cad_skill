import copy
import unittest

import ezdxf

import audit_corridor_anchor_dependence as audit
from crossview_equipment_branch_inventory import service_route
from match_junction_rebased_corridors import correspond_group
from test_match_source_checked_crossview_paths import fixture


class AnchorDependenceTests(unittest.TestCase):
    def test_adjacent_label_swap_is_rejected_but_complete_reversal_is_not(self):
        _, graph, taps = fixture()
        graphs = dict(plan=graph, iso=graph)
        anchors = dict(plan=taps, iso=taps)
        original = copy.deepcopy(anchors)
        self.assertEqual(audit.trial(graphs, anchors, {'D1': 'D2', 'D2': 'D1'}, 'supply', 1)['status'], 'blocked')
        self.assertEqual(audit.trial(graphs, anchors, {f'D{i}': f'D{3-i}' for i in range(4)}, 'supply', 1)['status'], 'order_only_not_rejected')
        self.assertEqual(anchors, original)

    def test_minimum_three_anchors_still_admits_coherent_reversal(self):
        _, graph, taps = fixture()
        taps = {k: v for k, v in taps.items() if k != 'D3'}
        result = audit.trial(dict(plan=graph, iso=graph), dict(plan=taps, iso=taps),
                             {'D0': 'D2', 'D2': 'D0'}, 'supply', 1)
        self.assertEqual(result['status'], 'order_only_not_rejected')

    def test_wrong_floor_or_supply_return_does_not_become_an_order_match(self):
        _, graph, taps = fixture()
        for system, floor in [('return', 1), ('supply', 2)]:
            result = audit.trial(dict(plan=graph, iso=graph), dict(plan=taps, iso=taps), {}, system, floor)
            self.assertEqual(result['status'], 'blocked')

    def native_fixture(self):
        docs, graphs = {}, {}
        for view in ('plan', 'iso'):
            doc = ezdxf.new()
            nodes, edges = [], []
            for i in range(4):
                nodes.append(dict(node_id=f'D{i}', node_type='equipment', floor=1, x=i*10, y=50))
            for system, y, layer, prefix in [('supply', 0, '空调冷冻水供水', 'S'), ('return', 100, '空调冷冻水回水', 'R')]:
                doc.modelspace().add_line((-10, y), (40, y), dxfattribs={'layer': layer})
                for i in range(4):
                    nid = prefix+str(i)
                    nodes.append(dict(node_id=nid, node_type='tee', floor=1, x=i*10, y=y))
                    edges.append(dict(edge_id=prefix+'B'+str(i), system=system,
                        start_node_id=nid, end_node_id=f'D{i}', attribute_paths=[[[i*10, y], [i*10, 50]]]))
                    if i:
                        edges.append(dict(edge_id=prefix+'M'+str(i), system=system,
                            start_node_id=prefix+str(i-1), end_node_id=nid,
                            attribute_paths=[[[(i-1)*10, y], [i*10, y]]]))
                for i, x in [(0, -10), (3, 40)]:
                    boundary = prefix+'OUT'+str(i)
                    nodes.append(dict(node_id=boundary, node_type='boundary', floor=1, x=x, y=y))
                    edges.append(dict(edge_id=boundary, system=system, start_node_id=prefix+str(i),
                        end_node_id=boundary, attribute_paths=[[[i*10, y], [x, y]]]))
            docs[view], graphs[view] = doc, dict(nodes=nodes, edges=edges)
        inventory = dict(records=[dict(equipment_id=f'D{i}', floor=1, ready_for_mapping_comparison=True,
            views={v: dict(services={s: dict(trace=service_route(graphs[v], f'D{i}', s),
                ready_for_mapping_comparison=True) for s in ('supply', 'return')}) for v in graphs}) for i in range(4)])
        spec = dict(group_id='G', equipment_ids=[f'D{i}' for i in range(4)], floor=1, mapping_prefix='TEST')
        hashes = {v: dict(source_sha256='S'*64, graph_sha256='G'*64) for v in graphs}
        return docs, graphs, inventory, spec, hashes

    def test_native_audit_keeps_remaining_routes_distinct_from_withheld_prediction(self):
        docs, graphs, inventory, spec, hashes = self.native_fixture()
        baseline = correspond_group(docs, graphs, inventory, spec, hashes)
        original = copy.deepcopy(graphs)
        result = audit.audit_group(docs, graphs, inventory, spec, hashes, baseline)
        self.assertEqual(len(result['anchors']), 8)
        self.assertEqual(result['source_paths'], 14)
        self.assertTrue(result['fresh_native_corridor_geometry_and_coverage_replayed'])
        self.assertFalse(result['complete_native_inventory_ancestry_replayed'])
        self.assertTrue(all(not row['omitted_T_predicted'] for row in result['leave_one_anchor_out']))
        self.assertTrue(all(row['both_services_blocked'] for row in result['pair_label_swaps']))
        self.assertTrue(all(row['result']['status'] == 'order_only_not_rejected' for row in result['coherent_reversals']))
        self.assertEqual(graphs, original)

    def test_altered_baseline_path_blocks_before_it_can_be_reported_as_passed(self):
        docs, graphs, inventory, spec, hashes = self.native_fixture()
        baseline = correspond_group(docs, graphs, inventory, spec, hashes)
        baseline['records'][0]['iso_edges'] = ['WRONG']
        with self.assertRaisesRegex(ValueError, 'Fresh native corridor differs'):
            audit.audit_group(docs, graphs, inventory, spec, hashes, baseline)

    def test_duplicate_native_line_blocks_correspondence_despite_same_labels(self):
        docs, graphs, inventory, spec, hashes = self.native_fixture()
        baseline = correspond_group(docs, graphs, inventory, spec, hashes)
        docs['iso'].modelspace().add_line((-10, 0), (40, 0), dxfattribs={'layer': '空调冷冻水供水'})
        with self.assertRaisesRegex(ValueError, 'unique native LINE'):
            audit.audit_group(docs, graphs, inventory, spec, hashes, baseline)


if __name__ == '__main__':
    unittest.main()
