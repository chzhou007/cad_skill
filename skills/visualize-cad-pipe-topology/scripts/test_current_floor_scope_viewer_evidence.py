import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SKILLS = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(SKILLS/'build-cad-pipe-topology/scripts'), str(SKILLS/'orchestrate-cad-drawing-pipeline/scripts')]
import test_adopt_current_floor_plan_scopes as fixtures
from adopt_current_floor_plan_scopes import adopt
from current_floor_scope_viewer_evidence import verify
from build_visualization import verified_source_attribute_ancestor


class CurrentFloorViewerTests(unittest.TestCase):
    def fixture(self, folder):
        parent, stages, evidence = fixtures.CurrentFloorAdoptionTests().fixture()
        p = folder/'parent'; p.mkdir(); old = p/'graph_with_edges.json'; old.write_text(json.dumps(parent), encoding='utf-8')
        ph = hashlib.sha256(old.read_bytes()).hexdigest(); graph, stage = adopt(parent, stages, evidence, 2, ph)
        target = folder/'graph_with_edges.json'; target.write_text(json.dumps(graph), encoding='utf-8')
        audit = dict(stage=stage, output_graph_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            parent_graph=dict(path=str(old), sha256=ph), verified_complete_parent=dict(output_graph_sha256=ph), human_accepted=False, hil_ready=False)
        return target, graph, old, parent, audit

    def test_dispatch_reuses_fresh_complete_parent_without_changing_old_proofs(self):
        with tempfile.TemporaryDirectory() as temp:
            target, graph, old, parent, audit = self.fixture(Path(temp))
            proof = dict(records=['HISTORY'], plan_DN_scope_fusion=['OLD-DN'])
            with patch('adopt_current_floor_plan_scopes.verify_output', return_value=audit) as native, \
                 patch('external_feed_plan_viewer_evidence.from_audit', return_value=(old, proof)) as ancestor:
                result, evidence = verified_source_attribute_ancestor(target, graph)
            native.assert_called_once_with(target.parent); ancestor.assert_called_once_with(old, parent, audit['verified_complete_parent'])
            self.assertEqual(result, old); self.assertEqual(evidence['records'], ['HISTORY'])
            self.assertEqual(evidence['plan_DN_scope_fusion'], ['OLD-DN']); self.assertFalse(evidence['hil_ready'])

    def test_missing_root_or_modified_historical_component_is_rejected(self):
        with self.assertRaises(ValueError): verified_source_attribute_ancestor(None, dict(edges=[dict(current_floor_plan_scope_evidence={})]))
        with tempfile.TemporaryDirectory() as temp:
            target, graph, _, _, audit = self.fixture(Path(temp))
            graph['edges'][0]['component_inventory'] = []
            target.write_text(json.dumps(graph), encoding='utf-8'); audit['output_graph_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
            with patch('adopt_current_floor_plan_scopes.verify_output', return_value=audit), self.assertRaises(ValueError): verify(target, graph)


if __name__ == '__main__': unittest.main()
