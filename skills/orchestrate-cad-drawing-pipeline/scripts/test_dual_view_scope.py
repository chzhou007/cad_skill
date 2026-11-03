import json
import tempfile
import unittest
from pathlib import Path

import dual_view_scope as scope

ROOT = Path(__file__).resolve().parents[3]
LEDGER = Path(__file__).resolve().parents[1] / "assets" / "sh16-s0-ledger.json"


class DualViewScopeTest(unittest.TestCase):
    def test_tracked_ledger_locks_scope_without_claiming_drawings_correct(self):
        data = scope.load_ledger(LEDGER, ROOT)
        self.assertFalse(data["historical_baseline_is_correct"])
        self.assertEqual(data["code_baseline"]["commit"], "d66dc70")
        self.assertEqual(data["layers"], list(scope.LAYERS))
        self.assertTrue(all(item["drawing_correct"] is False for item in data["items"]))
        self.assertGreaterEqual(len(data["items"]), 20)

    def test_reproduced_rule_must_point_at_a_real_test(self):
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        data["items"][0]["tests"] = ["missing_test.py"]
        data["items"][0]["status"] = "reproduced"
        errors = scope.validate_ledger(data, ROOT)
        self.assertTrue(any("test file missing" in error for error in errors))

    def test_historical_baseline_cannot_be_marked_correct(self):
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        data["historical_baseline_is_correct"] = True
        self.assertTrue(any("historical baseline" in error for error in scope.validate_ledger(data, ROOT)))

    def test_mapping_requires_evidence_and_fusion_cites_both_hashes(self):
        with self.assertRaises(scope.ScopeError):
            scope.mapping_link("equipment", ["P1"], ["I1"], [])
        link = scope.mapping_link("path", ["P1", "P2"], ["I1"], ["handle-a"])
        record = scope.fusion_record(
            {"layer": "plan_topology", "content_sha256": "a" * 64},
            {"layer": "isometric_topology", "content_sha256": "b" * 64},
            [link],
            [],
        )
        self.assertEqual(record["plan_sha256"], "a" * 64)
        self.assertEqual(record["isometric_sha256"], "b" * 64)

    def test_local_topology_change_stales_fusion_and_keeps_history(self):
        record = {
            "state": "current",
            "mapping": {"state": "current"},
            "diameter_inheritance": {"state": "current"},
            "attribute_fusion": {"state": "current"},
            "human_confirmation": "none",
        }
        updated = scope.invalidate_dependents(record, ["plan_topology"])
        self.assertEqual(updated["state"], "stale")
        self.assertEqual(updated["mapping"]["state"], "stale")
        self.assertEqual(updated["diameter_inheritance"]["state"], "stale")
        self.assertEqual(updated["attribute_fusion"]["state"], "stale")
        self.assertEqual(updated["human_confirmation"], "invalidated_keep_history")
        self.assertEqual(record["state"], "current")

    def test_ledger_round_trip_rejects_a_collapsed_layer_list(self):
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        data["layers"] = ["cross_view_fusion"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(scope.ScopeError):
                scope.load_ledger(path, ROOT)


if __name__ == "__main__":
    unittest.main()
