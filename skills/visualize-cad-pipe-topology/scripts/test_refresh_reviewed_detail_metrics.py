import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from refresh_reviewed_detail_metrics import context_from, provider_from, NATIVE_MODE


class Tests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name); (root / 'public/data').mkdir(parents=True)
        edge = dict(edge_id='E', system='supply', start_node_id='A', end_node_id='B', attribute_paths=[[[0, 0], [10, 0]]])
        graph = root / 'public/data/graph.json'; graph.write_text(json.dumps(dict(edges=[edge])), encoding='utf-8')
        old = dict(axis_edge_id='OLD', original='unchanged')
        context = dict(current_rendered_graph_sha256=hashlib.sha256(graph.read_bytes()).hexdigest(),
            anchored_plan_metrics=dict(records=[old], count=1, source_bindings=dict(native_axis_graph='a' * 64)))
        (root / 'public/data/manifest.json').write_text(json.dumps(dict(attributeValueContext=context)), encoding='utf-8')
        path = root / 'proof.json'; path.write_bytes(b'proof')
        row = dict(axis_edge_id='E', system='supply', axis_nodes=['A', 'B'], axis_attribute_paths=edge['attribute_paths'],
            nominal_mm=None, DN_evidence_changed=False, physical_installed_length_mm=None, net_pipe_cut_length_mm=None,
            source_scope_id='NEW', source_detail_resolution=dict(question_id='Q'))
        proof = dict(mode=NATIVE_MODE, reviewed_scope_native_T_paths_and_components_replayed=True,
            original_metric_readers_reused=True, source_graphs_mutated=False, component_owners_changed=False,
            human_accepted=False, DN_values_assigned=0, vertical_values_assigned=0, installed_lengths_assigned=0,
            records=[row], inputs=dict(axis_graph=dict(sha256='a' * 64), answer_receipt=dict(sha256='b' * 64)))
        return root, proof, path, context

    def test_append_preserves_old_context_and_scope_bindings(self):
        root, proof, path, original = self.fixture(); before = copy.deepcopy(proof)
        result = context_from(root, proof, path)
        self.assertEqual(result['anchored_plan_metrics']['records'][0], original['anchored_plan_metrics']['records'][0])
        self.assertEqual(result['anchored_plan_metrics']['source_bindings'], original['anchored_plan_metrics']['source_bindings'])
        self.assertEqual(result['anchored_plan_metrics']['count'], 2)
        self.assertEqual(proof, before)

    def test_replacing_old_metric_or_assigning_DN_or_installed_length_rejected(self):
        for key, value in [('axis_edge_id', 'OLD'), ('nominal_mm', 300), ('physical_installed_length_mm', 10)]:
            root, proof, path, _ = self.fixture(); proof['records'][0][key] = value
            with self.subTest(key=key), self.assertRaises((ValueError, KeyError)): context_from(root, proof, path)

    def test_old_nested_summary_cannot_decrement_current_published_coverage(self):
        root, _, _, _ = self.fixture()
        observation = dict(mapping_id='M')
        old = dict(mode='parent', records=[dict(edge_id='E', correspondence_observations=[observation])],
            remaining_horizontal_attributes=[dict(edge_id='E', complete_centerline=False,
                known_whole_DN=None, attributes={}, next_scope='source_detail', floor=3)],
            counts=dict(pure_horizontal_complete_centerline=246, pure_horizontal_complete_DN_and_centerline=230),
            current_horizontal_frontier=dict(pure_horizontal_complete_centerline=244, pure_horizontal_complete=228),
            member_domain_observations=[], ordinary_junction_mappings={}, current_component_inventory={})
        path = root / 'provider.json'; path.write_text(json.dumps(old), encoding='utf-8')
        row = dict(axis_edge_id='E', original_observation=observation, complete_horizontal_centerline_mm=10,
            source_scope_id='M', source_detail_resolution=dict(question_id='Q'))
        proof = dict(inputs=dict(current_provider=dict(path=str(path))), records=[row])
        actual = [dict(edge_id='E', values=dict(anchored_metric_complete_centerline_mm=10, anchored_metric_mapping_id='M'))]
        result = provider_from(proof, actual)
        self.assertEqual(result['current_horizontal_frontier']['pure_horizontal_complete_centerline'], 247)
        self.assertEqual(result['current_horizontal_frontier']['pure_horizontal_complete'], 230)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), old)


if __name__ == '__main__': unittest.main()
