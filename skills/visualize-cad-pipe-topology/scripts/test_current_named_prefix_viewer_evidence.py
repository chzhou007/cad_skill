import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from confirm_crossview_paths import encode, sha
import adopt_current_named_prefix_evidence as owner
import test_adopt_current_named_prefix_evidence as fixtures
import current_named_prefix_viewer_evidence as viewer
import known_junction_main_viewer_evidence as known
from attribute_scope_inventory import inventory
from build_visualization import verified_source_attribute_ancestor


class CurrentNamedPrefixViewerTests(unittest.TestCase):
    def fixture(self, root):
        parent, bridge, hashes = fixtures.CurrentNamedPrefixFusionTests().fixture()
        folder = root/'parent'
        folder.mkdir()
        old = folder/'graph_with_edges.json'
        old.write_bytes(encode(parent))
        hashes['parent'] = sha(old)
        graph, stage = owner.append(parent, bridge, hashes)
        target = root/'graph_with_edges.json'
        target.write_bytes(encode(graph))
        proof_file = root/'bridge/prefix-version-bridge.json'
        proof_file.parent.mkdir()
        proof_file.write_bytes(encode(bridge))
        proof_file.with_name('prefix-version-bridge-receipt.json').write_bytes(encode(dict(
            inputs=dict(current_graph=dict(path=str(root/'current-local-graph.json'), sha256='a'*64)))))
        audit = dict(output_graph_sha256=sha(target), stage=stage,
            parent_graph=dict(path=str(old), sha256=sha(old)),
            verified_complete_parent=dict(output_graph_sha256=sha(old)),
            native_prefix_bridge=dict(path=str(proof_file), sha256=sha(proof_file)), hil_ready=False, human_accepted=False)
        return target, graph, old, parent, audit

    def test_reuses_only_fresh_complete_parent_audit_and_keeps_ancestry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, graph, old, parent, audit = self.fixture(Path(tmp))
            retained = dict(records=['historical_source_proof'], prior_unknown_lengths=True)
            with patch.object(owner, 'verify_output', return_value=audit) as native, \
                 patch.object(known, 'from_audit', return_value=(old, retained)) as ancestor:
                result, proof = verified_source_attribute_ancestor(path, graph)
            native.assert_called_once_with(path.parent)
            ancestor.assert_called_once_with(old, parent, audit['verified_complete_parent'])
            self.assertEqual(result, old)
            self.assertEqual(proof['records'], ['historical_source_proof'])
            self.assertFalse(proof['human_accepted'])
            self.assertEqual(proof['current_named_prefix_evidence_fusion_audit'], audit)

    def test_dangling_edge_evidence_cannot_fall_back_to_an_old_root(self):
        with self.assertRaises(ValueError):
            verified_source_attribute_ancestor(None, dict(edges=[dict(current_named_prefix_source_evidence={})],
                sourceKnownJunctionMainAttributes=dict(retained=True)))

    def test_modified_component_or_pending_history_blocks_native_view(self):
        for mutation in ('component', 'history'):
            with tempfile.TemporaryDirectory() as tmp:
                path, graph, _, _, audit = self.fixture(Path(tmp))
                if mutation == 'component':
                    graph['edges'][0]['old_component_inventory'] = []
                else:
                    graph['historical_pending'] = []
                path.write_bytes(encode(graph))
                audit['output_graph_sha256'] = sha(path)
                with patch.object(owner, 'verify_output', return_value=audit):
                    with self.assertRaises(ValueError):
                        viewer.verify(path, graph)

    def test_manifest_dependencies_use_real_known_parent_not_new_root_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _, old, _, audit = self.fixture(Path(tmp))
            proof = dict(current_named_prefix_evidence_fusion_audit=audit)
            with patch.object(known, 'dependency_paths', return_value=dict(known_junction_main_fusion_audit=old.parent/'known-audit.json')) as prior:
                paths = viewer.dependency_paths(proof, path)
            prior.assert_called_once_with(proof, old)
            self.assertEqual(paths['known_junction_main_fusion_audit'].parent, old.parent)
            self.assertEqual(paths['current_named_prefix_fusion_audit'].parent, path.parent)
            self.assertIn('current_named_prefix_current_graph', paths)

    def test_evidence_inventory_does_not_increase_plan_or_vertical_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, graph, _, parent, _ = self.fixture(Path(tmp))
            before, after = inventory(parent), inventory(graph)
            self.assertEqual(before['plan'], after['plan'])
            self.assertEqual(before['axis'], after['axis'])
            self.assertEqual(after['evidence']['records']-before['evidence']['records'], 4)
            self.assertEqual(after['evidence']['by_field'][owner.FIELD], 4)

    def test_inventory_keeps_current_evidence_payload_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, graph, _, _, _ = self.fixture(Path(tmp))
            changed = copy.deepcopy(graph)
            changed['edges'][0][owner.FIELD]['current_plan_graph_sha256'] = '9'*64
            a, b = inventory(graph), inventory(changed)
            self.assertEqual(a['evidence'], b['evidence'])
            self.assertNotEqual(a['records'], b['records'])


if __name__ == '__main__':
    unittest.main()
