"""Capability query regressions: discovery coverage, truthful links and bounds."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pipeline_actions as actions


class DiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = actions.discover()

    def test_all_306_legacy_commands_including_92_manual_routes(self):
        additions = {"actions", "batch", "batch-release", "hil-feedback"}
        legacy = [r for r in self.registry["entries"] if r["command"] not in additions]
        self.assertEqual(306, len(legacy))
        self.assertEqual(214, sum(r["discovery"] == "argparse" for r in legacy))
        self.assertEqual(92, sum(r["discovery"] == "manual_dispatch" for r in legacy))
        self.assertTrue(all(r["handler"] for r in legacy))

    def test_hil_feedback_is_new_entry_with_shared_owner(self):
        result = actions.query(self.registry,"explain","hil-feedback")["result"]
        self.assertEqual("hil-feedback",result["command"])
        self.assertTrue(any(x["module"]=="hil_feedback_pipeline" for x in result["implementations"]["items"]))

    def test_hidden_entries_have_exact_real_owner_and_arguments(self):
        for name, module in (("package-current-review", "package_current_review"),
                             ("receive-current-review-answers", "receive_current_review_answers")):
            result = actions.query(self.registry, "explain", name)["result"]
            self.assertEqual("manual_dispatch", result["discovery"])
            self.assertEqual(["visualize-cad-pipe-topology"], result["owners"])
            self.assertEqual("delegated_to_owner", result["argument_contract"])
            impl = result["implementations"]["items"][0]
            self.assertEqual(module, impl["module"])
            self.assertTrue(Path(impl["script"]).is_file())
            self.assertEqual(actions.sha256(impl["script"]), impl["source"]["sha256"])
            flags = {flag for row in impl["observed_arguments"]["items"] for flag in row.get("flags", [])}
            expected = {"--binding", "--binding-sha256", "--output"} if name.startswith("package") else {
                "--existing", "--reply", "--page-root", "--output", "--question-id"}
            self.assertTrue(expected <= flags)

    def test_source_conditional_branch_selects_correct_module(self):
        for command, expected in (("reconstruct-expanded-main-seed-bend-DN", "expanded_main_seed_bend_DN"),
                                  ("refresh-expanded-main-seed-bend-DN-viewer", "refresh_expanded_main_seed_bend_DN"),
                                  ("reconstruct-reviewed-ring-crossview-DN", "reapply_reviewed_ring_crossview_DN"),
                                  ("reconstruct-reviewed-ring-plan-DN", "reviewed_ring_main_partition")):
            row = next(r for r in self.registry["entries"] if r["command"] == command)
            self.assertEqual([expected], [x["module"] for x in row["implementations"]])

    def test_defaults_bounded_and_exact_search_ranked_first(self):
        page = actions.query(self.registry)["results"]
        self.assertEqual(10, page["returned"])
        self.assertTrue(page["truncated"])
        found = actions.query(self.registry, "search", "package-current-review")["results"]
        self.assertEqual("package-current-review", found["items"][0]["command"])
        self.assertLess(len(json.dumps(actions.query(self.registry), ensure_ascii=False)), 18000)
        later = actions.query(self.registry, limit=3, offset=3)["results"]
        self.assertEqual(3, later["returned"])
        self.assertEqual(self.registry["entries"][3]["command"], later["items"][0]["command"])

    def test_bad_bounds_and_unknown_queries_fail(self):
        for limit in (0, -1, 51, True):
            with self.assertRaises(ValueError):
                actions.query(self.registry, limit=limit)
        with self.assertRaises(ValueError):
            actions.query(self.registry, offset=-1)
        for op, value in (("explain", "not-an-entry"), ("feature", "not-a-feature"), ("search", "")):
            with self.assertRaises(ValueError):
                actions.query(self.registry, op, value)

    def test_exact_file_feature_links_and_registry_detail_pointer(self):
        result = actions.query(self.registry, "explain", "package-current-review")["result"]
        ids = result["feature_ids"]["items"]
        expected = "published_current_viewer_bundled_runtime_delivery"
        self.assertIn(expected, ids)
        feature = actions.query(self.registry, "feature", expected, limit=2)
        self.assertIn("/features/", feature["feature"]["detail_pointer"])
        self.assertLessEqual(feature["feature"]["files"]["returned"], 2)
        self.assertIn("package-current-review", [r["command"] for r in feature["results"]["items"]])
        # A generic reference to pipeline.py cannot make plan own every feature.
        plan = next(r for r in self.registry["entries"] if r["command"] == "plan")
        self.assertEqual([], plan["feature_ids"])

    def test_query_does_not_import_pipeline_or_modify_source(self):
        targets = [actions.DEFAULT_PIPELINE, actions.DEFAULT_REGISTRY]
        before = [actions.sha256(path) for path in targets]
        script = "import pipeline_actions as a,sys; a.discover(); assert 'pipeline' not in sys.modules; assert 'source_comparison_gate' not in sys.modules"
        result = subprocess.run([sys.executable, "-c", script], cwd=Path(actions.__file__).parent,
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(before, [actions.sha256(path) for path in targets])

    def test_cli_errors_are_compact_json(self):
        for argv in (["list", "--limit", "999"], ["explain", "missing"],
                     ["current-project"], ["list", "--bad-argument"]):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = actions.main(argv)
            self.assertEqual(1, code)
            self.assertEqual("failed", json.loads(output.getvalue())["status"])
            self.assertLess(len(output.getvalue()), 1200)


class CurrentProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.authority = self.root / "baseline.json"
        self.authority.write_text(json.dumps({
            "project_id": "SH16", "current_metrics": {"missing_DN": 8},
            "review": {"received": 7, "pending": 3, "human_accepted": False},
            "whole_goal_complete": False,
            "remaining_work": ["unresolved source scope " + str(i) for i in range(100)]
        }), encoding="utf-8")
        self.pointer = self.root / "current.json"
        self.write_pointer()

    def write_pointer(self, **changes):
        data = dict(schema_version=1, project_id="SH16",
                    authority={"path": "baseline.json", "sha256": actions.sha256(self.authority)})
        data.update(changes)
        self.pointer.write_text(json.dumps(data), encoding="utf-8")

    def test_hash_bound_authority_is_compact_and_unknown_is_unknown(self):
        newer = self.root / "newest.json"
        newer.write_text('{"whole_goal_complete":true}', encoding="utf-8")
        result = actions.current_project(pointer=self.pointer, limit=4)
        self.assertEqual(str(self.authority), result["authority"]["path"])
        self.assertFalse(result["semantic_state"]["whole_goal_complete"])
        self.assertEqual("unknown", result["semantic_state"]["local_topologies"])
        self.assertFalse(result["semantic_state"]["review"]["human_accepted"])
        self.assertEqual(100, result["unresolved_classes"]["total"])
        self.assertEqual(4, len(result["unresolved_classes"]["items"]))
        direct = actions.current_project(self.authority, actions.sha256(self.authority))
        self.assertEqual(result["authority"], direct["authority"])

    def test_stale_hash_missing_path_bad_schema_and_absent_authority_fail(self):
        self.authority.write_text('{"whole_goal_complete":true}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            actions.current_project(pointer=self.pointer)
        with self.assertRaises(ValueError):
            actions.current_project(self.authority)
        with self.assertRaises(ValueError):
            actions.current_project()
        with self.assertRaises(ValueError):
            actions.current_project(self.authority, "0" * 64, self.pointer)
        self.write_pointer(authority={"path": "missing.json", "sha256": "0" * 64})
        with self.assertRaises(OSError):
            actions.current_project(pointer=self.pointer)
        self.write_pointer(authority="not-an-object")
        with self.assertRaises(ValueError):
            actions.current_project(pointer=self.pointer)

    def test_project_mismatch_rejected(self):
        self.write_pointer(project_id="OTHER")
        with self.assertRaisesRegex(ValueError, "project_id"):
            actions.current_project(pointer=self.pointer)


if __name__ == "__main__":
    unittest.main()
