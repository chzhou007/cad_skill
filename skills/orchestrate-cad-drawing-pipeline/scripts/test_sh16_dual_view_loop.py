import json
import unittest
from pathlib import Path

import sh16_dual_view_loop as loop

ROOT = Path(__file__).resolve().parents[3]
LEDGER = Path(__file__).resolve().parents[1] / "assets" / "sh16-s0-ledger.json"
ISO = ROOT / "fixtures" / "isometric-sh16-11" / "graph_with_edges.json"


def sample_plan():
    return {
        "tees": [
            {"node_id": "T025", "branch_line_length": 16350.0},
            {"node_id": "T065", "branch_line_length": 16150.0},
        ],
        "omission_symbols": [{"circle_handle": "B99D"}],
    }


class DualViewLoopTest(unittest.TestCase):
    def test_one_plan_checked_loop_does_not_start_mapping_or_fusion(self):
        iso = json.loads(ISO.read_text(encoding="utf-8"))
        result = loop.classify_loop(sample_plan(), iso)
        self.assertEqual(result["mapping"], [])
        self.assertTrue(all(region["eligible_for_mapping"] is False for region in result["checked_regions"]))
        self.assertIsNone(result["candidate_attributes"][0]["diameter"])
        self.assertIsNone(result["candidate_attributes"][1]["length"]["value"])
        self.assertFalse(result["candidate_attributes"][0]["fused"])
        self.assertEqual(result["differences"][0]["kind"], "plan_only")
        self.assertFalse(result["differences"][0]["may_overwrite_other_view"])
        self.assertEqual(result["isometric_inspection"]["proven_fix"], None)

    def test_ledger_does_not_accept_a_drawing(self):
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        self.assertTrue(all(item["drawing_correct"] is False for item in data["items"]))
        self.assertEqual(data["milestones"]["M1"], "closed")
        self.assertNotEqual(data["milestones"]["M2"], "closed")

    def test_lf20_dxf_existence_is_separate_from_a_backtest(self):
        record = loop.lf20_backtest_record()
        self.assertFalse(record["backtest_ran"])
        self.assertIsNone(record["gain"])
        self.assertIsNone(record["regression"])
        self.assertTrue(record["missing_skill_inputs"])
        self.assertTrue(all(sheet["exists"] for sheet in record["sheets"]))

    def test_release_dxf_matches_the_checked_plan_classes(self):
        if not loop.RELEASE_DXF.is_dir():
            self.skipTest("release DXF is not in this checkout")
        compared = loop.compare_plan_sources()
        self.assertEqual([row["node_id"] for row in compared["tees"]], ["T025", "T065"])
        self.assertTrue(all(row["status"] == "matches_source" and row["drawing_acceptance"] is False for row in compared["tees"]))
        self.assertEqual(
            {row["circle_handle"] for row in compared["omission_symbols"]},
            {"B99D", "B99E", "B9A7", "B9A8"},
        )
        self.assertEqual(compared["shared_label"]["status"], "matches_source_identity_unresolved")
        self.assertEqual(compared["equipment_ports"]["ports_created"], 0)


if __name__ == "__main__":
    unittest.main()
