import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from confirm_crossview_paths import load, sha, encode
from reviewed_interface_owner_gate import check


class Tests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        parent = root / 'parent/graph_with_edges.json'
        parent.parent.mkdir()
        parent.write_text('{}', 'utf8')
        run = root / 'owners'
        run.mkdir()
        path = run / 'graph_with_edges.json'
        node = lambda n: dict(node_id=n, boundary_type='unresolved_source_terminal')
        graph = dict(nodes=[node('remaining')], edges=[], metadata=dict(hil_ready=False),
            sourceReviewedInterfaceOwners=dict(input_graph_sha256=sha(parent), source_sha256='S',
                physical_ports_verified=False, human_accepted=False,
                records=[dict(retired_interface_id='VIF', equipment_id='D', system='supply')]))
        path.write_bytes(encode(graph))
        audit = dict(mode='source_reviewed_paired_interface_owners_v1', output_graph_sha256=sha(path),
            proof=dict(parent_mode='inherited_wave_pair_continuity'),
            inputs=dict(graph=dict(path=str(parent), sha256=sha(parent)), source=dict(sha256='S')))
        report = dict(status='pending', errors=[],
            pending=['2 graph nodes have unresolved source-terminal or equipment-overlap semantics', 'other native issue'],
            graph_unresolved_node_blockers=[node('VIF'), node('remaining')],
            equipment_source_port_blockers=[dict(node_id='D', physical_port_verified=False)])
        return run, path, graph, audit, report

    def test_retires_only_confirmed_glyph_blocker_preserves_other_evidence(self):
        run, path, graph, audit, report = self.fixture()
        original = copy.deepcopy(report)
        with patch('attach_reviewed_interface_owners.verify_output', return_value=audit) as verify, \
                patch('source_comparison_gate.check', return_value=report):
            result = check(run, {}, sha(path), path)
        verify.assert_called_once_with(run)
        self.assertEqual(report, original)
        self.assertEqual(result['graph_unresolved_node_blockers'], [dict(
            node_id='remaining', boundary_type='unresolved_source_terminal', resolution_state=None)])
        self.assertEqual(result['equipment_source_port_blockers'], original['equipment_source_port_blockers'])
        self.assertIn('other native issue', result['pending'])
        self.assertEqual(result['reviewed_interface_owner_stage']['source_replay'], 'passed')
        self.assertFalse(result['hil_ready'])

    def test_parent_errors_remain_blocking(self):
        run, path, graph, audit, report = self.fixture()
        report['errors'] = ['unreadable Chinese']
        with patch('attach_reviewed_interface_owners.verify_output', return_value=audit), \
                patch('source_comparison_gate.check', return_value=report):
            result = check(run, {}, sha(path), path)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['errors'], report['errors'])

    def test_failed_ancestor_without_a_blocker_list_keeps_original_failure(self):
        run, path, graph, audit, report = self.fixture()
        report = dict(status='failed', errors=['circle parent rejected'], pending=['old issue'])
        with patch('attach_reviewed_interface_owners.verify_output', return_value=audit), \
                patch('source_comparison_gate.check', return_value=report):
            result = check(run, {}, sha(path), path)
        self.assertEqual(result['errors'], ['circle parent rejected'])
        self.assertTrue(result['reviewed_interface_owner_stage']['parent_comparison_failed'])

    def test_native_circle_ancestor_keeps_its_artifact_directory_contract(self):
        run, path, graph, audit, report = self.fixture()
        old_parent = Path(audit['inputs']['graph']['path'])
        parent = old_parent.parent / 'topology-native-circle-path-normalization/graph_with_edges.json'
        parent.parent.mkdir()
        parent.write_bytes(old_parent.read_bytes())
        audit['inputs']['graph']['path'] = str(parent)
        audit['proof']['parent_mode'] = 'native_circle_path_normalization'
        with patch('attach_reviewed_interface_owners.verify_output', return_value=audit), \
                patch('source_comparison_gate.check', return_value=report) as compare:
            result = check(run, {}, sha(path), path)
        self.assertEqual(compare.call_args.args[2], parent.parent)
        self.assertEqual(result['reviewed_interface_owner_stage']['source_replay'], 'passed')

    def test_unrelated_removed_node_and_new_blocker_cannot_be_hidden(self):
        for mode in ('removed', 'added'):
            run, path, graph, audit, report = self.fixture()
            if mode == 'removed':
                report['graph_unresolved_node_blockers'].append(dict(node_id='unrelated'))
            else:
                graph['nodes'].append(dict(node_id='new', boundary_type='unresolved_source_terminal'))
                path.write_bytes(encode(graph))
                audit['output_graph_sha256'] = sha(path)
            with self.subTest(mode=mode), patch('attach_reviewed_interface_owners.verify_output', return_value=audit), \
                    patch('source_comparison_gate.check', return_value=report):
                with self.assertRaisesRegex(ValueError, 'unrelated unresolved'):
                    check(run, {}, sha(path), path)

    def test_stale_hash_rejected_before_parent_consumption(self):
        run, path, graph, audit, report = self.fixture()
        with patch('attach_reviewed_interface_owners.verify_output', return_value=audit), \
                patch('source_comparison_gate.check') as parent:
            with self.assertRaisesRegex(ValueError, 'evidence or invalidation'):
                check(run, {}, 'wrong', path)
        parent.assert_not_called()

    def test_new_child_dispatches_before_retained_circle_wave_and_ownership_roots(self):
        from source_comparison_gate import check as entry
        run, path, graph, audit, report = self.fixture()
        graph.update(sourceLayoutEquipmentOwnership={}, sourceCirclePathNormalization={}, sourceInheritedWavePairContinuity={})
        path.write_bytes(encode(graph))
        with patch('reviewed_interface_owner_gate.check', return_value=dict(chosen='new_owner')) as current, \
                patch('source_comparison_gate.check_layout_equipment_ownership_graph') as ancestor:
            self.assertEqual(entry({}, sha(path), run, path), dict(chosen='new_owner'))
        current.assert_called_once()
        ancestor.assert_not_called()
        with patch('reviewed_interface_owner_gate.check', side_effect=ValueError('native changed')):
            result = entry(dict(errors=['old'], pending=['pending']), sha(path), run, path)
        self.assertIn('old', result['errors'])
        self.assertEqual(result['pending'], ['pending'])
        self.assertFalse(result['hil_ready'])

    def test_edge_only_claim_cannot_fall_through_to_an_ancestor(self):
        from source_comparison_gate import check as entry
        run, path, graph, audit, report = self.fixture()
        del graph['sourceReviewedInterfaceOwners']
        graph['edges'] = [dict(reviewed_interface_owner={})]
        path.write_bytes(encode(graph))
        with patch('reviewed_interface_owner_gate.check', side_effect=ValueError('missing owner root')) as current:
            result = entry({}, sha(path), run, path)
        current.assert_called_once()
        self.assertEqual(result['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
