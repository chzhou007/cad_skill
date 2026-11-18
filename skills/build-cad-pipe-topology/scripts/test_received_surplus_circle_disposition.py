"""Reject a false circle closure when source/topology or protected services change."""
import copy
import unittest
import ezdxf
from verify_received_surplus_circle_disposition import bind_answer, circle_disposition, protect_interfaces


class AnswerBindingTests(unittest.TestCase):
    def fixture(self):
        evidence = dict(source_sha256='SOURCE', graph_sha256='GRAPH', pair_sha256='PAIR',
                        interface_ids=['O1', 'O2', 'O3', 'O4'], canonical_interface_ids=['C1', 'C2', 'C3', 'C4'], equipment_ids=['D1', 'D2'])
        question = dict(id='Q', text='Original exact scope', options=['Erratum'], source_evidence=evidence)
        section = dict(image={'path':'pair.png', 'sha256':'PAIR'}, contexts=[], questions=[question])
        definitions = {'sections':[section]}
        reply = copy.deepcopy(definitions)
        answer = dict(decision='Erratum', comment='Two surplus context circles', updated_at='T', source_pair_sha256='PAIR')
        reply['sections'][0]['questions'][0]['answer'] = answer
        reply['browser_answer_snapshot'] = {'Q':answer}
        render = dict(pair_sha256='PAIR', source_sha256='SOURCE', graph_sha256='GRAPH', main_circle_context_only=[{'handle':'CIRCLE1'}, {'handle':'CIRCLE2'}])
        manifest = dict(question_id='Q', expected_decision='Erratum', expected_comment='Two surplus context circles',
                        inputs={'pair':{'sha256':'PAIR'}, 'source':{'sha256':'SOURCE'}, 'reviewed_graph':{'sha256':'GRAPH'}},
                        circles=[{'circle_handle':'CIRCLE1'}, {'circle_handle':'CIRCLE2'}],
                        interfaces=[dict(abbreviated_interface='O'+str(i), canonical_interface='C'+str(i), equipment_id='D1' if i<3 else 'D2')for i in range(1,5)])
        return definitions, reply, question, render, manifest

    def test_original_answer_and_pair_bound(self):
        self.assertFalse(bind_answer(*self.fixture())['equipment_ownership_inferred_from_erratum'])

    def test_altered_comment_cannot_close_erratum(self):
        values = list(self.fixture())
        values[1]['browser_answer_snapshot']['Q']['comment'] = 'Different meaning'
        with self.assertRaisesRegex(ValueError, 'explicit scoped'):
            bind_answer(*values)

    def test_wrong_circle_selection_cannot_consume_answer(self):
        values = list(self.fixture())
        values[4]['circles'][0]['circle_handle'] = 'REAL_INTERFACE'
        with self.assertRaisesRegex(ValueError, 'exact two main-context'):
            bind_answer(*values)

    def test_pair_drift_cannot_inherit_answer(self):
        values = list(self.fixture())
        values[4]['inputs']['pair']['sha256'] = 'DIFFERENT'
        with self.assertRaisesRegex(ValueError, 'Pair binding'):
            bind_answer(*values)


class CircleDispositionTests(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        msp = self.doc.modelspace()
        self.line = msp.add_line((-100, 0), (100, 0), dxfattribs={'layer': 'SUPPLY'})
        self.circle = msp.add_circle((0, 0), 5, dxfattribs={'layer': 'SUPPLY'})
        self.graph = {'nodes': [{'node_id': 'A', 'x': -100, 'y': 0}, {'node_id': 'B', 'x': 100, 'y': 0}],
                      'edges': [{'edge_id': 'E', 'system': 'supply', 'start_node_id': 'A', 'end_node_id': 'B',
                                 'attribute_paths': [[[-100, 0], [100, 0]]], 'source_handles': [self.line.dxf.handle]}]}
        self.binding = dict(circle_handle=self.circle.dxf.handle, main_line_handle=self.line.dxf.handle,
                            layer='SUPPLY', current_edge_id='E', system='supply')
        self.archived = dict(center=[0, 0, 0], radius=5, layer='SUPPLY')

    def check(self):
        return circle_disposition(self.doc, self.graph, self.binding, self.archived)

    def test_native_through_circle_is_display_only_without_mutation(self):
        before = copy.deepcopy(self.graph)
        self.assertEqual(self.check()['active_graph_circle_references'], 0)
        self.assertEqual(self.graph, before)
        self.assertTrue(self.circle.is_alive)

    def test_branch_line_cannot_be_hidden_by_ignoring_circle(self):
        self.doc.modelspace().add_line((0, 0), (0, 50), dxfattribs={'layer': 'SUPPLY'})
        with self.assertRaisesRegex(ValueError, 'additional local'):
            self.check()

    def test_active_tee_is_not_existing_display_only_disposition(self):
        self.graph['nodes'].append({'node_id': 'T', 'x': 0, 'y': 0})
        with self.assertRaisesRegex(ValueError, 'graph node'):
            self.check()

    def test_polyline_branch_cannot_be_hidden(self):
        self.doc.modelspace().add_lwpolyline([(0, 0), (0, 50)], dxfattribs={'layer': 'SUPPLY'})
        with self.assertRaisesRegex(ValueError, 'additional local same-service source geometry'):
            self.check()

    def test_circle_used_as_attribute_evidence_is_not_display_only(self):
        self.graph['edges'][0]['diameter_evidence'] = {'handle': self.circle.dxf.handle}
        with self.assertRaisesRegex(ValueError, 'active graph identity'):
            self.check()

    def test_parallel_graph_pipe_is_ambiguous(self):
        self.graph['edges'].append(dict(self.graph['edges'][0], edge_id='EXTRA'))
        with self.assertRaisesRegex(ValueError, 'one continuous graph'):
            self.check()

    def test_supply_return_mismatch_rejected(self):
        self.graph['edges'][0]['system'] = 'return'
        with self.assertRaisesRegex(ValueError, 'exact native source owner'):
            self.check()

    def test_source_circle_drift_rejected(self):
        self.circle.dxf.center = (1, 0, 0)
        with self.assertRaisesRegex(ValueError, 'archived source circle'):
            self.check()

    def test_graph_continuation_beyond_native_line_rejected(self):
        self.graph['edges'][0]['attribute_paths'] = [[[-200, 0], [200, 0]]]
        with self.assertRaisesRegex(ValueError, 'exact native source owner'):
            self.check()


class ProtectedInterfacesTests(unittest.TestCase):
    def fixture(self):
        graph = {'nodes': [{'node_id': 'D1', 'node_type': 'equipment'}, {'node_id': 'D2', 'node_type': 'equipment'}], 'edges': [],
                 'confirmedSideviewCanonicalization': {'records': []}, 'sourceOrderedSideviewEquipmentOwnership': {'records': []}}
        bindings = []
        for i, (device, service) in enumerate([('D1', 'supply'), ('D1', 'return'), ('D2', 'supply'), ('D2', 'return')]):
            b = dict(question_id='Q'+device, abbreviated_interface='OLD'+str(i), canonical_interface='VIF'+str(i),
                     canonical_edge='E'+str(i), system=service, equipment_id=device)
            bindings.append(b)
            graph['confirmedSideviewCanonicalization']['records'].append(dict(b))
            graph['sourceOrderedSideviewEquipmentOwnership']['records'].append(dict(question_id=b['question_id'], original_canonical_interface_id=b['canonical_interface'], equipment_id=device, edge_id=b['canonical_edge'], system=service, body_evidence={'ownership_basis':'complete_native_row_order_checked_against_independent_owners'}, physical_port_verified=False, interface_to_equipment_length_known=False))
            graph['edges'].append(dict(edge_id=b['canonical_edge'], system=service, start_node_id='T'+str(i), end_node_id=device, equipment_connector_length_mm=None, physical_length='unknown'))
        return graph, bindings

    def test_real_service_pairs_remain(self):
        graph, bindings = self.fixture()
        self.assertEqual(len(protect_interfaces(graph, bindings)), 4)

    def test_erratum_does_not_authorize_deleting_real_interface_edge(self):
        graph, bindings = self.fixture()
        graph['edges'][0]['end_node_id'] = 'UNRELATED'
        with self.assertRaisesRegex(ValueError, 'protected equipment service'):
            protect_interfaces(graph, bindings)

    def test_unsupported_connector_length_rejected(self):
        graph, bindings = self.fixture()
        graph['edges'][0]['equipment_connector_length_mm'] = 1000
        with self.assertRaisesRegex(ValueError, 'protected equipment service'):
            protect_interfaces(graph, bindings)


if __name__ == '__main__':
    unittest.main()
