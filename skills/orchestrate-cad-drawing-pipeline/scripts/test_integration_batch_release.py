import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import integration_batch_release as integration


class IntegrationReleaseTests(unittest.TestCase):
    def test_real_cli_accepts_dispatcher_arguments(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as caught:
            integration.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("{plan,stage}", output.getvalue())

    def routing_fixture(self):
        graph = {"edges": [{"edge_id": "E1", "system": "supply", "attribute_paths": [[[0, 0], [2, 0], [2, 3]]]}]}
        rows = [{"edge_id": "E1", "system": "supply", "path_index": 0, "segment_index": i,
                 "scope_points": graph["edges"][0]["attribute_paths"][0][i:i + 2],
                 "connection_proved_by_direction": False, "physical_length_mm": None,
                 "DN_assigned": None, "human_accepted": False} for i in range(2)]
        return graph, {"edges": [{"edge_id": "E1"}], "records": rows}

    def test_complete_segment_coverage_rejects_same_count_wrong_scope(self):
        graph, route = self.routing_fixture()
        self.assertEqual(integration.validate_routing_coverage(graph, route), 2)
        bad = copy.deepcopy(route)
        bad["records"][0]["scope_points"][1][0] += 1
        with self.assertRaisesRegex(ValueError, "source paths"):
            integration.validate_routing_coverage(graph, bad)

    def test_direction_cannot_assign_length_or_acceptance(self):
        graph, route = self.routing_fixture()
        for key, value in (("physical_length_mm", 0), ("DN_assigned", 100),
                           ("human_accepted", True), ("connection_proved_by_direction", True)):
            bad = copy.deepcopy(route)
            bad["records"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                integration.validate_routing_coverage(graph, bad)

    def test_duplicate_or_missing_segments_are_not_coverage(self):
        graph, route = self.routing_fixture()
        for rows in ([route["records"][0]] * 2, route["records"][:1]):
            with self.assertRaises(ValueError):
                integration.validate_routing_coverage(graph, dict(route, records=rows))

    def test_effective_values_compare_every_field_and_unknown_null(self):
        old = [{"edge_id": "E1", "values": {"length": None, "DN": 200, "evidence": "原值"}}]
        self.assertEqual(integration.compare_values(old, copy.deepcopy(old))["cells"], 3)
        for key, value in (("length", 0), ("DN", 250), ("evidence", "changed")):
            bad = copy.deepcopy(old)
            bad[0]["values"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "values changed"):
                integration.compare_values(old, bad)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            integration.compare_values(old, old + old)

    def recipe_fixture(self, root):
        source = root / "source.json"
        integration.dump(source, {"native": "fixture"})
        lock = root / "lock.json"
        integration.dump(lock, {"files": {str(source): integration.sha(source)}})
        recipe = dict(schema=integration.SCHEMA, scope="complete_member_contact_family_and_all_edge_preservation",
                      cwd=str(root), authority=integration.pin(source), member_manifest=integration.pin(source),
                      publication_manifest=integration.pin(source), input_lock=integration.pin(lock), human_accepted=False)
        path = root / "recipe.json"
        integration.dump(path, recipe)
        return path, source

    def test_plan_has_real_owner_dependencies_and_no_unsafe_cache_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            recipe, _ = self.recipe_fixture(root)
            result = integration.stage_plan(recipe, root / "tasks.json")
            jobs = {j["id"]: j for j in result["jobs"]}
            self.assertEqual(len(jobs), 8)
            self.assertEqual(jobs["member-verify"]["depends_on"], ["member-publish"])
            self.assertEqual(jobs["member-publish"]["cores"], 16)
            self.assertIn("direction-native", jobs["direction-publish"]["depends_on"])
            self.assertTrue(all(j["cacheable"] is False for j in jobs.values()))
            self.assertTrue(all(j["outputs"] == ["{stage_output}"] for j in jobs.values()))
            self.assertFalse(result["human_accepted"])

    def test_fixed_input_drift_blocks_stage_before_any_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            recipe, source = self.recipe_fixture(root)
            source.write_text("changed", encoding="utf8")
            with self.assertRaisesRegex(ValueError, "changed"):
                integration.run_stage(recipe, "member-native", root / "out")
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
