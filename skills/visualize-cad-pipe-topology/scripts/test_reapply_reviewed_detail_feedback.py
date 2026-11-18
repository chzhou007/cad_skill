"""Publication contract tests; native source replay is separately integration-tested.

Fixtures use the real shared JS metric validator and the app-selected facade.
Only the expensive native CAD verifier is mocked in publication tests.
"""
import contextlib
import copy
import json
import io
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import reapply_reviewed_detail_feedback as owner


class Tests(unittest.TestCase):
    def fixture(self, existing=True):
        temp = tempfile.TemporaryDirectory(prefix='reviewed-detail-reapply-test-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        parent = root / 'parent'
        (parent / 'public/data').mkdir(parents=True)
        (parent / 'annotations').mkdir()
        (parent / 'annotations/history.json').write_text('{"old":"人工历史","revision":7}', encoding='utf-8')
        (parent / 'historical-proof.json').write_text('{"historical":"immutable"}', encoding='utf-8')
        source = root / 'axis.dxf'; source.write_bytes(b'axis-native-source')
        native_graph = root / 'axis-graph.json'; native_graph.write_bytes(b'axis-native-graph')
        plan_source = root / 'plan.dxf'; plan_source.write_bytes(b'plan-native-source')
        plan_graph = root / 'plan-graph.json'; plan_graph.write_bytes(b'plan-native-graph')
        edges = [dict(edge_id=eid, system='supply', floor_start=3, floor_end=3,
                      start_node_id=eid + 'A', end_node_id=eid + 'B',
                      attribute_paths=[[[0, index], [10, index]]])
                 for index, eid in enumerate(('E1', 'E2', 'OTHER'))]
        graph_path = parent / 'public/data/graph.json'
        graph_path.write_bytes(owner.encode(dict(edges=edges, nodes=[{'id': 'kept'}], components=['kept'])))
        old_receipt_hash = 'b' * 64
        def record(edge, index):
            row = dict(axis_edge_id=edge['edge_id'], mapping_id='M' + str(index),
                       source_scope_id='REVIEWED-DETAIL-METRIC:M' + str(index),
                       system='supply', axis_nodes=[edge['start_node_id'], edge['end_node_id']],
                       axis_attribute_paths=edge['attribute_paths'], floor=3, plan_edge_id='P' + str(index),
                       complete_horizontal_centerline_mm=10, projection=dict(value_mm=10,
                           pieces=[dict(length_mm=10, source_line_handle='L' + str(index))]),
                       nominal_mm=None, DN_evidence_changed=False, physical_installed_length_mm=None,
                       net_pipe_cut_length_mm=None, related_HIL_confirmation_inherited=False,
                       source_paths_mutated=False, unknown_length_filled_with_zero=False,
                       DN_used_for_matching=False, human_accepted=False,
                       plan_source_sha256=owner.sha(plan_source), plan_graph_sha256=owner.sha(plan_graph),
                       axis_source_sha256=owner.sha(source), native_axis_graph_sha256=owner.sha(native_graph),
                       component_profiles={'plan': {'ball_valve': 1}, 'iso': {'ball_valve': 2}},
                       source_detail_resolution=dict(question_id='Q', answer_receipt_sha256=old_receipt_hash,
                           pair_sha256='c' * 64, answer=dict(decision=owner.DECISION,
                               source_pair_sha256='c' * 64, updated_at='old-time'),
                           policy='plan_omits_axis_component_detail', physical_ball_valve_count=2,
                           source_instances_retained=True, crossview_components_merged=False,
                           plan_valve_positions_invented=False))
            return row
        selected = [record(e, i) for i, e in enumerate(edges[:2])]
        unrelated = record(edges[-1], 2)
        unrelated.pop('source_detail_resolution')
        unrelated['source_scope_id'] = 'UNRELATED-OWNER'
        metric_root = dict(mode='qualified_anchored_native_plan_metrics_v1',
                           records=[unrelated] + copy.deepcopy(selected) if existing else [unrelated],
                           count=3 if existing else 1, original_metric_readers_reused=True,
                           source_graphs_mutated=False, component_owners_changed=False,
                           DN_values_assigned=0, vertical_values_assigned=0, installed_lengths_assigned=0,
                           human_accepted=False, source_bindings=dict(native_axis_graph=owner.sha(native_graph),
                               raw_axis_graph='d' * 64, rendered_graph=owner.sha(graph_path),
                               native_metric_proof='e' * 64))
        if existing:
            metric_root['reviewed_detail_extension'] = dict(mode=owner.EXTENSION_MODE,
                question_id='Q', source_scope_ids=[r['source_scope_id'] for r in selected],
                count=2, human_accepted=False, native_metric_proof_sha256='f' * 64,
                answer_receipt_sha256=old_receipt_hash, preserved_owner_note='history')
        context = dict(current_rendered_graph_sha256=owner.sha(graph_path), source_graph_sha256='d' * 64,
                       anchored_plan_metrics=metric_root, unrelated_late_context={'future': [1, 2, 3]})
        manifest = dict(bundleId='original-bundle', preferredPort=10564, projectId='SH16-test',
                        attributeValueContext=context, sourceHashes=dict(main_dxf=owner.sha(source), graph='d' * 64),
                        reviewContentHashes=dict(viewer_graph=owner.sha(graph_path),
                            attribute_value_context=owner.digest(context), effective_edge_attributes='a' * 64),
                        templateHashes={}, unrelated_late_feature={'precious': 'untouched'})
        if existing:
            manifest['directionalPipeAttributes'] = {'path': 'data/directional-pipe-attributes.json'}
            for name in ('directional-pipe-attributes.json', 'edge-review-queue.json', 'graph-with-directional-attributes.json'):
                (parent / 'public/data' / name).write_bytes(owner.encode({'frozen': name, 'records': []}))
        (parent / 'public/data/manifest.json').write_bytes(owner.encode(manifest))
        (parent / 'public/index.html').write_text('<p>original-bundle</p>', encoding='utf-8')
        (parent / 'public/app.js').write_text("import {crossViewAttributeCsvValues} from './edge-attributes-current.js';\n", encoding='utf-8')
        # An older facade is deliberately wrong: discovery must use app.js.
        (parent / 'public/edge-attributes-plan-crossover.js').write_text(
            "export function crossViewAttributeCsvValues(){throw Error('stale facade selected');}", encoding='utf-8')
        module = Path(owner.__file__).resolve().parents[1] / 'assets/viewer/public/anchored-native-plan-metrics.js'
        shutil.copy2(module, parent / 'public/anchored-native-plan-metrics.js')
        (parent / 'public/edge-attributes-current.js').write_text(
            "import{anchoredNativeMetricCsvValues}from'./anchored-native-plan-metrics.js';\n"
            "export function crossViewAttributeCsvValues(e,c){return {late_feature:e.edge_id,"
            "...anchoredNativeMetricCsvValues(e,c)};}", encoding='utf-8')
        answer = dict(question_id='Q', pair_sha256='1' * 64,
                      explicit_answer=dict(decision=owner.DECISION, source_pair_sha256='1' * 64, updated_at='fresh-time'),
                      source_evidence=dict(related_current_axis_edges=['E1', 'E2'], source_plan_edges=['P0', 'P1']))
        receipt_path = root / 'answer-receipt.json'
        receipt_path.write_bytes(owner.encode(dict(mode='version_bound_current_review_answer_intake_v1', records=[answer])))
        inputs = {name: dict(path=str(path), sha256=owner.sha(path)) for name, path in (
            ('axis_source', source), ('axis_graph', native_graph), ('plan_source', plan_source),
            ('plan_graph', plan_graph), ('answer_receipt', receipt_path))}
        fresh = copy.deepcopy(selected)
        for row in fresh:
            resolution = row['source_detail_resolution']
            resolution.update(answer=answer['explicit_answer'], pair_sha256=answer['pair_sha256'],
                              answer_receipt_sha256=owner.sha(receipt_path))
        proof = dict(mode=owner.NATIVE_MODE, inputs=inputs, records=fresh,
                     reviewed_scope_native_T_paths_and_components_replayed=True,
                     original_metric_readers_reused=True, source_graphs_mutated=False,
                     component_owners_changed=False, human_accepted=False,
                     DN_values_assigned=0, vertical_values_assigned=0, installed_lengths_assigned=0)
        proof_dir = root / 'native'; proof_dir.mkdir()
        proof_path = proof_dir / 'reviewed-detail-plan-metrics.json'
        proof_path.write_bytes(owner.encode(proof))
        return root, parent, proof, proof_path, manifest

    def apply(self, existing=True):
        root, parent, proof, path, original = self.fixture(existing)
        output = root / 'output'
        with patch.object(owner, 'verified_native', return_value=proof) as replay:
            report = owner.refresh(parent, output, path)
            checked = owner.verify(output)
        self.assertEqual(replay.call_count, 2)
        self.assertEqual(checked['artifact_replay'], 'passed')
        return root, parent, proof, path, original, output, report

    def test_existing_owner_fresh_evidence_current_reader_and_all_history_preserved(self):
        _, parent, proof, _, original, output, report = self.apply()
        manifest = owner.load(output / 'public/data/manifest.json')
        self.assertEqual(manifest['reviewContentHashes'], original['reviewContentHashes'])
        self.assertEqual(owner.review_identity(manifest), owner.review_identity(original))
        self.assertEqual(manifest['attributeValueContext']['anchored_plan_metrics']['count'], 3)
        self.assertEqual(manifest['unrelated_late_feature'], original['unrelated_late_feature'])
        self.assertEqual(manifest['attributeValueContext']['unrelated_late_context'],
                         original['attributeValueContext']['unrelated_late_context'])
        self.assertEqual(report['reader_facade'], 'edge-attributes-current.js')
        self.assertEqual(report['delta']['new_complete_centerlines'], 0)
        values = {r['edge_id']: r['values'] for r in owner.actual_reader(output)['records']}
        self.assertEqual(json.loads(values['E1']['anchored_metric_evidence_json']), proof['records'][0])
        for name, digest in owner.inventory(parent).items():
            if name not in ('public/data/manifest.json', 'public/index.html'):
                self.assertEqual(owner.sha(output / name), digest, name)

    def test_initial_extension_append_and_review_identity_invalidation(self):
        _, _, _, _, original, output, report = self.apply(existing=False)
        manifest = owner.load(output / 'public/data/manifest.json')
        self.assertNotEqual(owner.review_identity(manifest), owner.review_identity(original))
        self.assertEqual(report['delta']['new_complete_centerlines'], 2)
        self.assertEqual(manifest['attributeValueContext']['anchored_plan_metrics']['count'], 3)

    def test_repeated_application_does_not_duplicate_counts_or_erase_lineage(self):
        root, _, proof, path, _, output, _ = self.apply()
        second = root / 'second'
        with patch.object(owner, 'verified_native', return_value=proof):
            report = owner.refresh(output, second, path)
            owner.verify(second)
        manifest = owner.load(second / 'public/data/manifest.json')
        self.assertEqual(manifest['attributeValueContext']['anchored_plan_metrics']['count'], 3)
        self.assertEqual(report['delta']['changed_evidence_edges'], [])
        self.assertIn('previous', manifest['reviewedDetailFeedback'])
        self.assertEqual(len(list((second / 'reviewed-detail-feedback').glob('*/receipt.json'))), 2)

    def test_changed_values_connectivity_and_scope_rejected_before_output(self):
        for key, value in [('complete_horizontal_centerline_mm', 11), ('axis_nodes', ['wrong', 'B']),
                           ('source_scope_id', 'WRONG'), ('system', 'return'), ('floor', 4),
                           ('nominal_mm', 100), ('physical_installed_length_mm', 10)]:
            with self.subTest(key=key):
                root, parent, proof, path, _ = self.fixture()
                proof['records'][0][key] = value
                if key == 'complete_horizontal_centerline_mm':
                    proof['records'][0]['projection']['value_mm'] = value
                with patch.object(owner, 'verified_native', return_value=proof), self.assertRaises(ValueError):
                    owner.refresh(parent, root / 'rejected', path)
                self.assertFalse((root / 'rejected').exists())

    def test_wrong_question_receipt_and_source_rejected(self):
        for mutation in ('question', 'receipt', 'source', 'decision', 'pair', 'comment'):
            with self.subTest(mutation=mutation):
                _, parent, proof, path, _ = self.fixture()
                resolution = proof['records'][0]['source_detail_resolution']
                if mutation == 'question': resolution['question_id'] = 'OTHER'
                if mutation == 'receipt': resolution['answer_receipt_sha256'] = '0' * 64
                if mutation == 'source': proof['records'][0]['plan_source_sha256'] = '0' * 64
                if mutation == 'decision': resolution['answer']['decision'] = 'different'
                if mutation == 'pair': resolution['pair_sha256'] = '0' * 64
                if mutation == 'comment': resolution['answer']['comment'] = 'connectivity changed'
                with self.assertRaises(ValueError): owner.context_from(parent, proof, path)

    def test_duplicate_owner_or_subset_scope_rejected(self):
        for kind in ('duplicate', 'subset', 'extension_question'):
            _, parent, proof, path, manifest = self.fixture()
            extension = manifest['attributeValueContext']['anchored_plan_metrics']['reviewed_detail_extension']
            if kind == 'duplicate': proof['records'].append(copy.deepcopy(proof['records'][0]))
            if kind == 'subset': extension['source_scope_ids'].pop()
            if kind == 'extension_question': extension['question_id'] = 'wrong'
            (parent / 'public/data/manifest.json').write_bytes(owner.encode(manifest))
            with self.subTest(kind=kind), self.assertRaises(ValueError): owner.context_from(parent, proof, path)

    def test_initial_extension_cannot_leave_frozen_directional_or_frontier_stale(self):
        for filename in ('edge-review-queue.json', 'directional-pipe-attributes.json',
                         'graph-with-directional-attributes.json', 'horizontal-frontier.json'):
            _, parent, proof, path, _ = self.fixture(existing=False)
            (parent / 'public/data' / filename).write_bytes(b'{}')
            with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, 'directional/frontier rebuild'):
                owner.context_from(parent, proof, path)

    def test_wrong_current_graph_binding_rejected(self):
        _, parent, proof, path, _ = self.fixture()
        (parent / 'public/data/graph.json').write_bytes(b'{"edges":[]}')
        with self.assertRaisesRegex(ValueError, 'current rendered graph changed'):
            owner.context_from(parent, proof, path)

    def test_unrelated_effective_field_change_and_stale_evidence_rejected(self):
        _, parent, proof, path, _ = self.fixture()
        before = owner.actual_reader(parent)
        context, _, _ = owner.context_from(parent, proof, path)
        manifest = owner.load(parent / 'public/data/manifest.json')
        manifest['attributeValueContext'] = context
        (parent / 'public/data/manifest.json').write_bytes(owner.encode(manifest))
        after = owner.actual_reader(parent)
        for bad in ('extra', 'unrelated', 'stale'):
            changed = copy.deepcopy(after)
            if bad == 'extra': changed['records'][0]['values']['invented'] = 1
            if bad == 'unrelated': changed['records'][-1]['values']['late_feature'] = 'changed'
            if bad == 'stale': changed['records'][0]['values']['anchored_metric_evidence_json'] = before['records'][0]['values']['anchored_metric_evidence_json']
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                owner.compare_readers(before, changed, proof['records'], True)

    def test_verification_detects_annotation_or_derived_file_tampering(self):
        for name in ('annotations/history.json', 'public/data/directional-pipe-attributes.json'):
            _, _, proof, _, _, output, _ = self.apply()
            (output / name).write_bytes(b'changed')
            with patch.object(owner, 'verified_native', return_value=proof), self.assertRaisesRegex(ValueError, 'history changed'):
                owner.verify(output)

    def test_fresh_native_replay_failure_never_publishes(self):
        root, parent, _, path, _ = self.fixture()
        with (patch.object(owner, 'verified_native', side_effect=ValueError('native scope rejected')),
              self.assertRaisesRegex(ValueError, 'native scope rejected')):
            owner.refresh(parent, root / 'rejected', path)
        self.assertFalse((root / 'rejected').exists())

    def test_verified_native_calls_owner_not_saved_status_and_checks_requested_file(self):
        _, _, proof, path, _ = self.fixture()
        native = types.ModuleType('reviewed_source_detail_metrics')
        called = []
        def verify(directory):
            called.append(directory)
            return copy.deepcopy(proof)
        native.verify_output = verify
        runtime = types.ModuleType('native_projection_runtime_v1')
        runtime.default_native_runtime = lambda _: contextlib.nullcontext()
        with patch.dict(sys.modules, reviewed_source_detail_metrics=native, native_projection_runtime_v1=runtime):
            self.assertEqual(owner.verified_native(path), proof)
            self.assertEqual(called, [path.parent])
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'fresh native replay differs'):
                owner.verified_native(path)

    def test_external_verification_receipt_does_not_modify_sealed_viewer(self):
        root, _, proof, _, _, output, _ = self.apply()
        before = owner.inventory(output)
        destination = root / 'verification'
        with (patch.object(owner, 'verified_native', return_value=proof),
              patch.object(sys, 'argv', ['owner', '--verify-output', str(output),
                                        '--verification-output', str(destination)]),
              contextlib.redirect_stdout(io.StringIO())):
            owner.main()
        self.assertEqual(owner.load(destination / 'verification.json')['status'], 'passed')
        self.assertEqual(owner.inventory(output), before)

    def test_unrelated_reader_evidence_keeps_nested_original_key_order(self):
        root, parent, proof, path, manifest = self.fixture()
        # Later publishers may append unsorted records. Their JS evidence_json
        # output is an exact historical field, not merely a parsed JSON object.
        evidence = {'z_first': '原始顺序', 'a_later': {'z_nested': 3, 'a_nested': 4},
                    'm_records': [{'z_source': 'CAD', 'a_value': 42}]}
        manifest['attributeValueContext']['unrelated_late_context'] = evidence
        manifest_path = parent / 'public/data/manifest.json'
        manifest_path.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        facade = parent / 'public/edge-attributes-current.js'
        facade.write_text(facade.read_text(encoding='utf-8').replace(
            'late_feature:e.edge_id,',
            'late_feature:e.edge_id,late_evidence_json:JSON.stringify(c.unrelated_late_context),'), encoding='utf-8')
        before = owner.actual_reader(parent)
        output = root / 'ordered-output'
        with patch.object(owner, 'verified_native', return_value=proof):
            owner.refresh(parent, output, path)
            owner.verify(output)
        after = owner.actual_reader(output)
        self.assertEqual([r['values']['late_evidence_json'] for r in before['records']],
                         [r['values']['late_evidence_json'] for r in after['records']])
        current = owner.load(output / 'public/data/manifest.json')['attributeValueContext']['unrelated_late_context']
        self.assertEqual(list(current), list(evidence))
        self.assertEqual(list(current['a_later']), list(evidence['a_later']))


if __name__ == '__main__':
    unittest.main()
