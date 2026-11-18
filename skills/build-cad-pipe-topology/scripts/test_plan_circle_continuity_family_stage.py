import json
import tempfile
import unittest
from pathlib import Path

from plan_circle_continuity_family_stage import load_policy_map, run_stage


class CircleFamilyStageTests(unittest.TestCase):
    def test_absent_map_keeps_old_family(self):
        self.assertEqual(load_policy_map(None), {})

    def test_relative_policy_paths_and_task_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'policy.json').write_text('{}', encoding='utf-8')
            mapping = root/'map.json'
            mapping.write_text(json.dumps({'TASK': {'continuity_policy': 'policy.json'}}), encoding='utf-8')
            self.assertEqual(load_policy_map(mapping, {'TASK'})['TASK']['continuity_policy'], root/'policy.json')
            with self.assertRaises(ValueError): load_policy_map(mapping, {'OTHER'})

    def test_missing_or_arbitrary_dependency_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            mapping = Path(folder)/'map.json'
            for settings in [{'graph': 'elsewhere'}, {'continuity_policy': 'missing.json'}, {'pending_junction_policy': 'missing.json'}]:
                mapping.write_text(json.dumps({'TASK': settings}), encoding='utf-8')
                with self.assertRaises(ValueError): load_policy_map(mapping, {'TASK'})

    def test_parent_outside_task_or_settings_override_block_before_native_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, 'current task graph'):
                run_stage(root/'source', root/'graph', {}, root/'task')
            with self.assertRaisesRegex(ValueError, 'cannot override'):
                run_stage(root/'source', root/'task/graph', {'output': 'bad'}, root/'task')


if __name__ == '__main__':
    unittest.main()
