import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from source_comparison_gate import check


class SourceGraphPendingGateTest(unittest.TestCase):
    def evaluate(self, graph):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gp = root/'graph_with_edges.json'; gp.write_text(json.dumps(graph), encoding='utf8')
            evidence = root/'native.png'; evidence.write_bytes(b'evidence')
            h = hashlib.sha256(gp.read_bytes()).hexdigest()
            receipt = {'graph_sha256': h, 'rounds_completed': 1,
                       'families': [{'id': 'fixture', 'status': 'resolved', 'source_handles': ['H'], 'disposition': 'claimed'}],
                       'native_comparisons': [{'path': evidence.name, 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}]}
            return check(receipt, h, root, gp)

    def test_explicit_graph_not_ready_cannot_be_overridden_by_receipt(self):
        result = self.evaluate({'nodes': [], 'edges': [], 'metadata': {'hil_ready': False}})
        self.assertEqual(result['status'], 'pending')
        self.assertFalse(result['hil_ready'])
        self.assertTrue(any('explicitly marks HIL not ready' in p for p in result['pending']))

    def test_unresolved_equipment_ports_block(self):
        graph = {'nodes': [{'node_id': 'CRAH', 'node_type': 'equipment', 'connection_status': 'ports_unresolved'}], 'edges': []}
        result = self.evaluate(graph)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual([x['node_id'] for x in result['equipment_source_port_blockers']], ['CRAH'])
        graph['nodes'][0]['connection_status'] = 'ports_proven'
        self.assertTrue(self.evaluate(graph)['hil_ready'])

    def test_source_glyph_system_conflict_blocks_independently(self):
        graph = {'nodes': [{'node_id': 'U', 'node_type': 'virtual_equipment',
                            'resolution_state': 'source_glyph_system_conflict_pending'}], 'edges': []}
        result = self.evaluate(graph)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['graph_unresolved_node_blockers'][0]['node_id'], 'U')

    def test_source_main_continuity_keeps_branch_pending(self):
        graph = {'nodes': [{'node_id': 'U', 'node_type': 'virtual_equipment',
                            'resolution_state': 'source_main_continuation_branch_pending'}], 'edges': []}
        result = self.evaluate(graph)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['graph_unresolved_node_blockers'][0]['node_id'], 'U')

    def test_circle_crossover_conflict_cannot_be_overridden_by_receipt(self):
        graph = {'nodes': [], 'edges': [], 'sourceCircleCrossoverConflicts': [{'circle_conflicts': [{'circle_handle': 'C'}]}]}
        result = self.evaluate(graph)
        self.assertEqual(result['status'], 'pending')
        self.assertIn('circle_crossover_conflict', result['graph_algorithm_family_blockers'])
        graph['sourceCircleCrossoverConflicts'] = 'bad'
        self.assertEqual(self.evaluate(graph)['status'], 'failed')

    def test_inline_system_conflict_blocks_even_if_receipt_is_resolved(self):
        graph = {'nodes': [], 'edges': [], 'sourceInlineSystemConflicts': [{'joint_handle': 'H'}]}
        result = self.evaluate(graph)
        self.assertEqual(result['status'], 'pending')
        self.assertIn('inline_component_system_conflict', result['graph_algorithm_family_blockers'])

    def test_claimed_upstream_resolution_requires_reproducible_source_artifacts(self):
        for graph in [
            {'nodes':[], 'edges':[], 'sourceInlineSystemResolutions':[{'joint_handle':'H'}]},
            {'nodes':[], 'edges':[{'edge_id':'E','source_inline_system_resolutions':[{'joint_handle':'H'}]}]},
        ]:
            with self.subTest(graph=graph):
                result=self.evaluate(graph)
                self.assertEqual(result['status'],'failed')
                self.assertTrue(any('upstream joint system repair' in e for e in result['errors']))

    def test_floor_correction_requires_reproducible_source_artifacts(self):
        result=self.evaluate({'nodes':[],'edges':[],'sourceFloorLabelRepair':{'changes':[{'node_id':'T'}]}})
        self.assertEqual(result['status'],'failed')
        self.assertTrue(any('source floor label repair' in e for e in result['errors']))


if __name__ == '__main__': unittest.main()
