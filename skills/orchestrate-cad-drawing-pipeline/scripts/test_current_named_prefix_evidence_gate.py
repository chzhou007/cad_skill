import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from confirm_crossview_paths import encode, sha
import adopt_current_named_prefix_evidence as owner
import current_named_prefix_evidence_gate as gate
import source_comparison_gate as dispatcher
import test_adopt_current_named_prefix_evidence as fixtures


class CurrentNamedPrefixComparisonTests(unittest.TestCase):
    def setup_files(self, base, errors=None):
        parent, bridge, hashes = fixtures.CurrentNamedPrefixFusionTests().fixture()
        old = base / 'parent'
        new = base / 'new'
        old.mkdir()
        new.mkdir()
        parent_path = old / 'graph_with_edges.json'
        parent_path.write_bytes(encode(parent))
        hashes['parent'] = sha(parent_path)
        graph, stage = owner.append(parent, bridge, hashes)
        graph_path = new / 'graph_with_edges.json'
        graph_path.write_bytes(encode(graph))
        prior = dict(status='failed' if errors else 'pending', graph_sha256=sha(parent_path),
            errors=list(errors or []), pending=['old unresolved physical length'],
            hil_ready=False, human_accepted=False, original_review_history=['keep'])
        (old / 'source-comparison-gate.json').write_bytes(encode(prior))
        audit = dict(output_graph_sha256=sha(graph_path), parent_graph=dict(path=str(parent_path), sha256=sha(parent_path)),
            verified_complete_parent=dict(output_graph_sha256=sha(parent_path)), stage=stage,
            hil_ready=False, human_accepted=False)
        return graph_path, prior, audit

    def test_preserves_complete_old_pending_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, prior, audit = self.setup_files(Path(tmp))
            with patch.object(owner, 'verify_output', return_value=audit) as verify:
                result = gate.check(path.parent, prior, sha(path), path)
            verify.assert_called_once_with(path.parent)
            self.assertEqual(result['pending'][:-1], prior['pending'])
            self.assertEqual(result['original_review_history'], prior['original_review_history'])
            self.assertEqual(result['current_named_prefix_evidence_stage']['source_replay'], 'passed')
            self.assertFalse(result['hil_ready'])

    def test_current_proof_does_not_clear_an_old_source_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, prior, audit = self.setup_files(Path(tmp), ['old source blocker'])
            with patch.object(owner, 'verify_output', return_value=audit):
                result = gate.check(path.parent, prior, sha(path), path)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['errors'], ['old source blocker'])

    def test_tampered_parent_or_report_cannot_pass(self):
        for mutation in ('parent', 'pending'):
            with tempfile.TemporaryDirectory() as tmp:
                path, prior, audit = self.setup_files(Path(tmp))
                supplied = copy.deepcopy(prior)
                if mutation == 'parent':
                    Path(audit['parent_graph']['path']).write_bytes(b'{}')
                else:
                    supplied['pending'] = []
                with patch.object(owner, 'verify_output', return_value=audit):
                    with self.assertRaises(ValueError):
                        gate.check(path.parent, supplied, sha(path), path)

    def test_native_failure_propagates_before_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, prior, _ = self.setup_files(Path(tmp))
            with patch.object(owner, 'verify_output', side_effect=ValueError('native ancestry changed')):
                with self.assertRaisesRegex(ValueError, 'native ancestry changed'):
                    gate.check(path.parent, prior, sha(path), path)

    def test_actual_dispatch_checks_new_evidence_before_retained_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, prior, _ = self.setup_files(Path(tmp))
            from confirm_crossview_paths import load
            graph = load(path)
            graph['sourceKnownJunctionMainAttributes'] = {'retained_parent': True}
            path.write_bytes(encode(graph))
            expected = dict(status='pending', new_prefix_dispatch_reached=True)
            with patch.object(gate, 'check', return_value=expected) as verify:
                actual = dispatcher.check(prior, sha(path), path.parent, path)
            self.assertEqual(actual, expected)
            verify.assert_called_once()


if __name__ == '__main__':
    unittest.main()
