import copy
import unittest

import ezdxf
from reconstruct_reviewed_plan_gaps import source_pairs, merge
from native_line_path_evidence import LAYERS


def fixture():
    doc = ezdxf.new()
    nodes, edges, rows, source_scope, retained = [], [], [], dict(
        source_sha256='S', graph_sha256='G', gap_drawing_units=100), {}
    for system, x in [('supply', 400), ('return', 0)]:
        ids = [system + str(i) for i in range(4)]
        source_scope[system + '_nodes'] = ids[1:3]
        for i, y in enumerate([0, 10, 110, 120]):
            nodes.append(dict(node_id=ids[i], node_type='tee' if i in (0, 3) else 'virtual_equipment',
                subtype='physical_tee' if i in (0, 3) else 'unresolved_source_terminal',
                system=system, floor=2, x=x, y=y))
        for i, pair in enumerate([(0, 1), (2, 3)]):
            a, b = pair
            path = [[x, nodes[-4+a]['y']], [x, nodes[-4+b]['y']]]
            line = doc.modelspace().add_line(path[0], path[1], dxfattribs=dict(layer=LAYERS[system]))
            eid, component = system + '-edge' + str(i), system + '-valve' + str(i)
            edges.append(dict(edge_id=eid, start_node_id=ids[a], end_node_id=ids[b], system=system,
                start_floor=2, end_floor=2, path=path, path_points=path, attribute_paths=[path],
                path_length=10, source_handles=[line.dxf.handle],
                equipment_names=[component], equipment_counts=dict(ball_valve=1)))
            rows.append(dict(edge_id=eid, device_name=component, equipment_type='ball_valve'))
        retained[system] = system + '-edge0'
    graph = dict(metadata={}, nodes=nodes, edges=edges, virtual_equipment_ports=[])
    question = dict(id='Q', source_evidence=source_scope,
        answer=dict(decision='两处均各自连续，供回水独立'))
    return doc, graph, question, rows, retained


class Tests(unittest.TestCase):
    def test_native_continuity_merges_routes_not_services_and_conserves_components(self):
        doc, graph, question, rows, retained = fixture()
        before, before_rows = copy.deepcopy(graph), copy.deepcopy(rows)
        proof = source_pairs(doc, graph, question)
        output, devices = merge(graph, rows, proof, retained, 'S', 'G')
        self.assertEqual(graph, before)
        self.assertEqual(rows, before_rows)
        self.assertEqual(len(output['nodes']), 4)
        self.assertEqual(len(output['edges']), 2)
        self.assertEqual(len(devices), 4)
        self.assertEqual({n['node_id'] for n in output['nodes']}, {'supply0', 'supply3', 'return0', 'return3'})
        for edge in output['edges']:
            self.assertEqual(edge['path_length'], 20)
            self.assertEqual(edge['drawing_path_length'], 120)
            self.assertEqual(len(edge['attribute_paths']), 2)
            self.assertEqual(edge['equipment_counts'], dict(ball_valve=2))
            self.assertEqual(edge['edge_type'], 'tee_to_tee')
            self.assertIsNone(edge['physical_length_mm'])
            self.assertFalse(edge['path_length_complete'])
            self.assertEqual({d['edge_id'] for d in devices if d['device_name'].startswith(edge['system'])}, {edge['edge_id']})

    def test_rotated_plan_still_uses_native_facing_endpoints(self):
        doc, graph, question, rows, retained = fixture()
        for entity in doc.modelspace():
            a, b = entity.dxf.start, entity.dxf.end
            entity.dxf.start = (-a.y, a.x, a.z)
            entity.dxf.end = (-b.y, b.x, b.z)
        for node in graph['nodes']:
            node['x'], node['y'] = -node['y'], node['x']
        for edge in graph['edges']:
            for key in ('path', 'path_points', 'attribute_paths'):
                paths = edge[key] if key == 'attribute_paths' else [edge[key]]
                # Rebuild independently: fixture paths intentionally share objects.
                edge[key] = [[[-p[1], p[0]] for p in path] for path in paths] if key == 'attribute_paths' else [[-p[1], p[0]] for p in paths[0]]
        self.assertEqual(len(source_pairs(doc, graph, question)), 2)

    def test_unconfirmed_or_partial_answer_cannot_restore_any_gap(self):
        doc, graph, question, rows, retained = fixture()
        question['answer']['decision'] = '供回水处理不同，见说明'
        with self.assertRaisesRegex(ValueError, 'confirmation'):
            source_pairs(doc, graph, question)

    def test_wrong_service_and_extra_incident_branch_are_rejected(self):
        for mode in ('service', 'degree'):
            doc, graph, question, rows, retained = fixture()
            if mode == 'service':
                graph['nodes'][1]['system'] = 'return'
            else:
                graph['edges'].append(dict(graph['edges'][0], edge_id='extra'))
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'system or degree'):
                source_pairs(doc, graph, question)

    def test_native_z_or_gap_scope_cannot_be_replaced_by_global_tolerance(self):
        for mode in ('Z', 'scope'):
            doc, graph, question, rows, retained = fixture()
            if mode == 'Z':
                line = list(doc.modelspace())[1]
                line.dxf.start = (*list(line.dxf.start)[:2], 5)
                line.dxf.end = (*list(line.dxf.end)[:2], 5)
            else:
                question['source_evidence']['gap_drawing_units'] = 200
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'gap or native Z'):
                source_pairs(doc, graph, question)

    def test_existing_DN_or_fused_attributes_require_recomposition(self):
        doc, graph, question, rows, retained = fixture()
        graph['edges'][0]['diameter_nominal_mm'] = 200
        with self.assertRaisesRegex(ValueError, 'unsupported attributes'):
            source_pairs(doc, graph, question)

    def test_duplicate_component_is_not_silently_deduplicated(self):
        doc, graph, question, rows, retained = fixture()
        proof = source_pairs(doc, graph, question)
        graph['edges'][1]['equipment_names'] = graph['edges'][0]['equipment_names'][:]
        with self.assertRaisesRegex(ValueError, 'duplicated across fragments'):
            merge(graph, rows, proof, retained, 'S', 'G')

    def test_unrelated_edge_and_equipment_instance_preserved(self):
        doc, graph, question, rows, retained = fixture()
        graph['nodes'].append(dict(node_id='DEVICE', node_type='equipment', floor=2))
        graph['edges'].append(dict(graph['edges'][0], edge_id='unrelated', equipment_names=[], equipment_counts={},
            start_node_id='supply0', end_node_id='supply3'))
        proof = source_pairs(doc, graph, question)
        output, _ = merge(graph, rows, proof, retained, 'S', 'G')
        self.assertEqual(output['edges'][-1], graph['edges'][-1])
        self.assertEqual(output['nodes'][-1], graph['nodes'][-1])


if __name__ == '__main__':
    unittest.main()
