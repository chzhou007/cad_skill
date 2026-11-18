"""Lightweight subprocess fixtures; no CAD owners or large reconstruction."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

import pipeline_batch_runtime as runtime


class BatchRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / "source.txt"
        self.source.write_text("fixed source", encoding="utf8")
        self.owner = self.base / "owner.py"
        self.owner.write_text(
            "import pathlib,sys\n"
            "mode,out=sys.argv[1:3]\n"
            "if mode=='fail': raise SystemExit(7)\n"
            "p=pathlib.Path(out);p.mkdir(parents=True,exist_ok=False)\n"
            "(p/'result.txt').write_text('artifact '+mode,encoding='utf8')\n"
            "print('stage done')\n", encoding="utf8")

    def job(self, ident, mode="ok", deps=None, **extra):
        return {"id": ident, "command": [sys.executable, str(self.owner), mode, "{stage_output}"],
                "cwd": str(self.base), "cores": 1, "depends_on": deps or [],
                "inputs": {str(self.source): runtime.sha(self.source)},
                "implementation": {str(self.owner): runtime.sha(self.owner)},
                "outputs": ["{stage_output}"], "cacheable": True, **extra}

    def manifest(self, jobs, name="manifest.json"):
        path = self.base / name
        path.write_text(json.dumps({"schema_version": 1, "core_budget": 2, "jobs": jobs}), encoding="utf8")
        return path

    def run_batch(self, manifest, name, resume=None):
        return runtime.run_manifest(manifest, self.base / name, resume_from=resume)

    def test_failed_prerequisite_blocks_publish_independent_continues(self):
        manifest = self.manifest([self.job("check", "fail"), self.job("publish", deps=["check"]),
                                  self.job("unrelated")])
        result = self.run_batch(manifest, "run")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stages"]["check"]["exit_code"], 7)
        self.assertEqual(result["stages"]["publish"]["status"], "blocked_by_dependency")
        self.assertEqual(result["stages"]["unrelated"]["status"], "succeeded")
        self.assertFalse((self.base / "run/stages/publish/artifacts").exists())
        self.assertTrue(Path(result["stages"]["check"]["log"]).is_file())

    def test_resume_is_explicit_cached_copy_and_prior_is_immutable(self):
        manifest = self.manifest([self.job("extract"), self.job("publish", deps=["extract"])])
        first = self.run_batch(manifest, "first")
        old_state = (self.base / "first/status.json").read_bytes()
        second = self.run_batch(manifest, "second", self.base / "first")
        self.assertEqual(second["cached_stage_count"], 2)
        self.assertFalse(second["cold_execution"])
        self.assertFalse(second["persisted_verification_reuse"])
        self.assertEqual((self.base / "first/status.json").read_bytes(), old_state)
        a = Path(first["stages"]["extract"]["artifacts"][0]["path"]) / "result.txt"
        b = Path(second["stages"]["extract"]["artifacts"][0]["path"]) / "result.txt"
        b.write_text("new run edit", encoding="utf8")
        self.assertEqual(a.read_text(encoding="utf8"), "artifact ok")

    def test_source_hash_change_rejects_stale_plan_and_invalidates_resume(self):
        manifest = self.manifest([self.job("extract")])
        self.run_batch(manifest, "first")
        self.source.write_text("new source", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            self.run_batch(manifest, "stale")
        new_manifest = self.manifest([self.job("extract")], "new.json")
        second = self.run_batch(new_manifest, "second", self.base / "first")
        self.assertEqual(second["stages"]["extract"]["status"], "succeeded")
        self.assertEqual(second["cached_stage_count"], 0)

    def test_implementation_hash_change_invalidates_resume(self):
        first_manifest = self.manifest([self.job("extract")])
        self.run_batch(first_manifest, "first")
        self.owner.write_text(self.owner.read_text(encoding="utf8") + "# changed implementation\n", encoding="utf8")
        second_manifest = self.manifest([self.job("extract")], "new.json")
        second = self.run_batch(second_manifest, "second", self.base / "first")
        self.assertEqual(second["cached_stage_count"], 0)
        self.assertEqual(second["stages"]["extract"]["status"], "succeeded")

    def test_output_tamper_rejects_reuse_even_same_length(self):
        manifest = self.manifest([self.job("extract")])
        self.run_batch(manifest, "first")
        (self.base / "first/stages/extract/artifacts/result.txt").write_text("artifact NO", encoding="utf8")
        second = self.run_batch(manifest, "second", self.base / "first")
        self.assertEqual(second["stages"]["extract"]["cache_miss_reason"], "cached_output_hash_mismatch")
        self.assertEqual(second["cached_stage_count"], 0)

    def test_same_progress_wait_does_not_increment_revision(self):
        manifest = self.manifest([self.job("extract")])
        run = self.base / "planned"
        before = runtime.plan_manifest(manifest, run)
        original = (run / "status.json").read_bytes()
        after = runtime.wait_for_change(run, before["revision"], timeout=0.02)
        self.assertFalse(after["changed"])
        self.assertEqual(after["revision"], before["revision"])
        self.assertEqual((run / "status.json").read_bytes(), original)

    def test_query_limits_stage_output_and_never_reads_logs(self):
        manifest = self.manifest([self.job("stage" + str(i)) for i in range(45)])
        run = self.base / "planned"
        runtime.plan_manifest(manifest, run)
        result = runtime.query_status(run, limit=3)
        self.assertEqual(result["stage_count"], 45)
        self.assertEqual(len(result["stages"]), 3)
        self.assertEqual(result["omitted_stage_count"], 42)
        self.assertLess(len(json.dumps(result)), 2500)

    def test_source_write_overlap_and_undeclared_parent_reference_rejected(self):
        overlap = self.manifest([self.job("bad", outputs=[str(self.source)])])
        with self.assertRaisesRegex(ValueError, "outputs must stay"):
            runtime.plan_manifest(overlap, self.base / "bad")
        job = self.job("bad")
        job["command"].append("{stage_output:missing}")
        bad_reference = self.manifest([job], "bad-reference.json")
        with self.assertRaisesRegex(ValueError, "requires ancestor dependency"):
            runtime.plan_manifest(bad_reference, self.base / "bad-reference")

    def test_cache_disabled_stage_executes_on_resume(self):
        manifest = self.manifest([self.job("extract", cacheable=False)])
        self.run_batch(manifest, "first")
        second = self.run_batch(manifest, "second", self.base / "first")
        self.assertEqual(second["cached_stage_count"], 0)

    def test_dependency_changed_content_invalidates_downstream_resume(self):
        manifest = self.manifest([self.job("extract"), self.job("publish", deps=["extract"])])
        self.run_batch(manifest, "first")
        revised = self.manifest([self.job("extract", "changed"), self.job("publish", deps=["extract"])], "revised.json")
        second = self.run_batch(revised, "second", self.base / "first")
        self.assertEqual(second["cached_stage_count"], 0)
        self.assertEqual(second["stages"]["publish"]["status"], "succeeded")

    def test_multiple_dependencies_block_without_waiting_for_unrelated_result(self):
        manifest = self.manifest([self.job("fail", "fail"), self.job("wait"),
                                  self.job("publish", deps=["fail", "wait"])])
        result = self.run_batch(manifest, "run")
        self.assertEqual(result["stages"]["publish"]["status"], "blocked_by_dependency")

    def test_detached_start_reaches_terminal_with_file_backed_logs(self):
        manifest = self.manifest([self.job("extract")])
        run = self.base / "detached"
        result = runtime.start_manifest(manifest, run)
        deadline = time.monotonic() + 10
        while result["status"] not in runtime.TERMINAL and time.monotonic() < deadline:
            result = runtime.wait_for_change(run, result["revision"], timeout=0.5)
        self.assertEqual(result["status"], "succeeded", (run / "executor.log").read_text(encoding="utf8"))
        self.assertTrue((run / "summary.json").is_file())
        self.assertTrue((run / "logs/extract.log").is_file())
        time.sleep(0.05)  # Allow the detached CLI to close its Windows log handle after its final print.
        runtime.query_status(run)  # Reap the locally launched process handle.

    def test_detached_start_preserves_empty_environment_values_bound_by_plan(self):
        # Windows os.environ retains this empty value while its implicit OS
        # environment removes the key; the detached owner must receive the mapping.
        with mock.patch.dict(os.environ, {"CAD_BATCH_EMPTY_ENV_FIXTURE": ""}):
            self.test_detached_start_reaches_terminal_with_file_backed_logs()

    def test_dead_executor_becomes_failed_once_without_inventing_success(self):
        manifest = self.manifest([self.job("extract")])
        run = self.base / "lost"
        runtime.plan_manifest(manifest, run)
        state = runtime._read(run / "status.json")
        state.update(status="running", executor_pid=123456, executor_identity="old")
        state["stages"]["extract"]["status"] = "running"
        runtime._write(run / "status.json", state)
        with mock.patch.object(runtime, "_process_info", return_value={"alive": False, "identity": None}):
            result = runtime.query_status(run)
            again = runtime.query_status(run)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["revision"], state["revision"] + 1)
        self.assertEqual(again["revision"], result["revision"])
        self.assertEqual(result["stages"][0]["status"], "interrupted")
        self.assertTrue((run / "summary.json").is_file())

    def test_shared_core_budget_rejects_oversubscription(self):
        manifest = self.manifest([self.job("heavy", cores=3)])
        with self.assertRaisesRegex(ValueError, "exceeds shared core budget"):
            runtime.plan_manifest(manifest, self.base / "run")

    def test_downstream_cannot_mutate_ancestor_then_publish(self):
        self.owner.write_text(self.owner.read_text(encoding="utf8") +
                              "if mode=='mutate': pathlib.Path(sys.argv[3]).write_text('changed',encoding='utf8')\n",
                              encoding="utf8")
        mutate = self.job("mutate", "mutate", deps=["extract"])
        mutate["command"].append("{stage_output:extract}/result.txt")
        manifest = self.manifest([self.job("extract"), mutate, self.job("publish", deps=["mutate"])])
        result = self.run_batch(manifest, "run")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stages"]["mutate"]["status"], "failed")
        self.assertEqual(result["stages"]["publish"]["status"], "blocked_by_dependency")


if __name__ == "__main__":
    unittest.main()
