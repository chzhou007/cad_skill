import copy
import unittest
import ezdxf
from preserve_unidentified_equipment import preserve


def fixture():
    doc = ezdxf.new()
    block = doc.blocks.new('40kW')
    block.add_lwpolyline([(0, 0), (500, 0), (500, 500), (0, 500)], close=True)
    a = doc.modelspace().add_blockref('40kW', (0, 0), dxfattribs={'layer': '空调'})
    b = doc.modelspace().add_blockref('40kW', (1000, 0), dxfattribs={'layer': '空调'})
    bindings = [{'source_handle': a.dxf.handle, 'source_block': '40kW', 'bounds': [[0, 0], [500, 500]], 'label_candidates': ['A']},
                {'source_handle': b.dxf.handle, 'source_block': '40kW', 'bounds': [[1000, 0], [1500, 500]], 'label_candidates': ['A']}]
    graph = {'metadata': {'source_sha256': 's'}, 'nodes': [], 'edges': []}
    policy = {'source_sha256': 's', 'graph_sha256': 'g', 'bindings_sha256': 'b', 'floor': 1,
              'expected_missing_source_handles': [a.dxf.handle, b.dxf.handle]}
    return doc, graph, bindings, policy


class PreservationTest(unittest.TestCase):
    def test_duplicate_label_preserves_two_instances_without_connecting(self):
        doc, graph, bindings, policy = fixture()
        out, audit = preserve(doc, graph, bindings, policy, 's', 'g', 'b')
        self.assertEqual(len(out['nodes']), 2)
        self.assertEqual(out['edges'], [])
        self.assertEqual(graph['nodes'], [])
        self.assertTrue(all(n['identity_status'] == 'unresolved' and not n['source_instance_evidence']['ports_inferred'] for n in out['nodes']))
        self.assertFalse(audit['hil_ready'])

    def test_changed_inventory_and_geometry_fail_closed(self):
        doc, graph, bindings, policy = fixture()
        policy['expected_missing_source_handles'].pop()
        with self.assertRaises(ValueError): preserve(doc, graph, bindings, policy, 's', 'g', 'b')
        policy['expected_missing_source_handles'].append(bindings[1]['source_handle'])
        bindings[0]['bounds'][1][0] += 10
        with self.assertRaises(ValueError): preserve(doc, graph, bindings, policy, 's', 'g', 'b')

    def test_existing_node_is_not_duplicated(self):
        doc, graph, bindings, policy = fixture()
        graph['nodes'].append({'node_id': 'A', 'node_type': 'equipment', 'source_handle': bindings[0]['source_handle']})
        policy['expected_missing_source_handles'] = [bindings[1]['source_handle']]
        out, _ = preserve(doc, graph, bindings, policy, 's', 'g', 'b')
        self.assertEqual(len(out['nodes']), 2)
        with self.assertRaises(ValueError): preserve(doc, graph, bindings, policy, 's', 'changed', 'b')


if __name__ == '__main__': unittest.main()
